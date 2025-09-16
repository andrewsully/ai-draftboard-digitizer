import pandas as pd
import re
from dataclasses import dataclass
from rapidfuzz import fuzz
from typing import List, Tuple, Optional
from ocr_cell import normalize_team, clean_pos_text
import math  # at the top with your other imports


@dataclass
class Player:
    """Player data structure."""
    first: str
    last: str
    team: str
    pos: str
    bye: int
    is_dst: bool = False
    
    @property
    def full(self):
        return f"{self.first} {self.last}".strip()


def player_identity(p: Player) -> Tuple[str, str, str, str, int]:
    """
    Unique identity tuple for a player for use in used_players sets.
    Uses stable, CSV-derived attributes to avoid collisions on shared last names.
    """
    return (p.first, p.last, p.team, p.pos, p.bye)

def load_players(csv_path: str) -> List[Player]:
    """
    Load players from CSV into canonical lookup table.
    
    Args:
        csv_path: Path to the CSV file
    
    Returns:
        List of Player objects
    """
    df = pd.read_csv(csv_path)
    players = []
    
    for _, row in df.iterrows():
        player_name = str(row.get('PLAYER NAME', ''))
        team = str(row.get('TEAM', '')).upper()
        pos = str(row.get('POS', '')).upper()
        
        # Handle bye week - can be '-' for free agents
        bye_week_str = str(row.get('BYE WEEK', '0'))
        if bye_week_str == '-' or bye_week_str == '':
            bye_week = 0  # Default for free agents
        else:
            bye_week = int(bye_week_str)
        
        # Handle DST entries specially
        if pos == 'DST':
            # For DST, the player name is the full team name
            full_team_name = player_name.upper()
            
            players.append(Player(
                first="",
                last=full_team_name,
                team=team,
                pos="DST",
                bye=bye_week,
                is_dst=True
            ))
        else:
            # For regular players, split the name
            name_parts = player_name.split(' ', 1)
            if len(name_parts) == 2:
                first, last = name_parts
            else:
                first, last = "", name_parts[0]
            
            players.append(Player(
                first=first.upper(),
                last=last.upper(),
                team=team,
                pos=pos,
                bye=bye_week,
                is_dst=False
            ))
    
    return players

def normalize_name(s: str) -> str:
    """
    Normalize name for matching (remove suffixes, etc.).
    
    Args:
        s: Name string
    
    Returns:
        Normalized name
    """
    if not s:
        return ""
    
    # Convert to uppercase and remove non-alphabetic characters
    s = re.sub(r"[^A-Z ]", "", s.upper())
    
    # Remove common suffixes
    s = s.replace(" JR", "").replace(" II", "").replace(" III", "").replace(" IV", "")
    s = s.replace(" SR", "").replace(" JR", "")
    
    return s.strip()

def grid_to_draft_pick(row: int, col: int, cols: int = 10) -> int:
    """
    Convert grid position to draft pick number using snake draft logic.
    
    Args:
        row: Row number (0-based)
        col: Column number (0-based)
        cols: Number of columns (default 10)
    
    Returns:
        Draft pick number (1-based)
    """
    # Calculate base pick for this row
    base_pick = row * cols + 1
    
    # Even rows (0, 2, 4...) go left to right
    # Odd rows (1, 3, 5...) go right to left (snake draft)
    if row % 2 == 0:
        # Left to right
        return base_pick + col
    else:
        # Right to left
        return base_pick + (cols - 1 - col)

def draft_pick_to_grid(pick: int, cols: int = 10) -> tuple:
    """
    Convert draft pick number to grid position.
    
    Args:
        pick: Draft pick number (1-based)
        cols: Number of columns (default 10)
    
    Returns:
        Tuple of (row, col) (0-based)
    """
    # Calculate row
    row = (pick - 1) // cols
    
    # Calculate column within the row
    col_in_row = (pick - 1) % cols
    
    # Even rows go left to right, odd rows go right to left
    if row % 2 == 0:
        col = col_in_row
    else:
        col = cols - 1 - col_in_row
    
    return (row, col)

# def _effective_rank(idx_in_players: int, players: List[Player], used_players: set) -> int:
#     """Return (1-based) rank after removing already-picked players ahead of idx."""
#     taken_before = 0
#     for j in range(idx_in_players):
#         if players[j].last in used_players:  # uses your existing last-name key
#             taken_before += 1
#     return (idx_in_players + 1) - taken_before



def calculate_draft_likelihood(player_rank: int, draft_pick: int) -> float:
    """
    Likelihood score (0–100) that a player with given rank is drafted at draft_pick.
    Uses a Gaussian decay with sigma proportional to rank to reflect real draft variance.
    """
    if player_rank < 1:
        player_rank = 1

    # sigma grows with rank (players later in ADP have wider variance)
    alpha, beta = 2.0, 0.1  # tweakable knobs
    sigma = alpha + beta * player_rank

    # Gaussian-shaped score centered at rank
    z = (draft_pick - player_rank) / sigma
    score = math.exp(-0.5 * z * z)

    return 100.0 * score


def best_match_with_position(last_guess: str, row: int, col: int, 
                           used_players: set, players: List[Player], 
                           color_position: str = None, ocr_results: dict = None) -> Tuple[float, Player, int, dict]:
    """
    Enhanced analytical matching using multi-factor confidence scoring.
    Returns (score, best_player, best_rank, breakdown).
    """
    index_map = {id(p): i for i, p in enumerate(players)}

    if not last_guess:
        return 0.0, players[0], 0, {}
    
    expected_pick = grid_to_draft_pick(row, col)

    # Extract additional OCR data
    ocr_first = ocr_results.get('ocr_first', '') if ocr_results else ''
    ocr_team  = ocr_results.get('ocr_team',  '') if ocr_results else ''
    ocr_bye   = ocr_results.get('ocr_bye')       if ocr_results else None
    ocr_pos   = ocr_results.get('ocr_pos',   '') if ocr_results else ''

    # Filter by color (strong filter)
    candidate_players = players
    if color_position and color_position in ['QB', 'RB', 'WR', 'TE', 'K', 'DST']:
        candidate_players = [p for p in players if p.pos == color_position]
        print(f"  Color position filter: {color_position} -> {len(candidate_players)} candidates (vs {len(players)} total)")

    cand_scores = []
    lg = normalize_name(last_guess)

    for p in candidate_players:
        # Skip if already used (by unique identity, not just last name)
        if player_identity(p) in used_players:
            continue

        total_score = 0.0
        score_breakdown = {}

        # 1) LASTNAME (0–40)
        lastname_score = fuzz.token_set_ratio(lg, normalize_name(p.last)) * 0.4
        total_score += lastname_score
        score_breakdown['lastname'] = lastname_score

        # 2) FIRSTNAME (0–15)
        if ocr_first and len(ocr_first) > 1:
            firstname_score = fuzz.token_set_ratio(normalize_name(ocr_first), normalize_name(p.first)) * 0.15
        else:
            firstname_score = 0.0
        total_score += firstname_score
        score_breakdown['firstname'] = firstname_score

        # 3) TEAM (0–15)
        team_score = 15.0 if ocr_team and p.team.upper() == ocr_team.upper() else 0.0
        total_score += team_score
        score_breakdown['team'] = team_score

        # 4) BYE (0–10)
        bye_score = 10.0 if (ocr_bye is not None and ocr_bye > 0 and p.bye == ocr_bye) else 0.0
        total_score += bye_score
        score_breakdown['bye'] = bye_score

        # 5) COLOR POS (0–15)
        color_score = 15.0 if (color_position and p.pos == color_position) else 0.0
        total_score += color_score
        score_breakdown['color_pos'] = color_score

        # 6) OCR POS (0–10)
        ocr_pos_score = 10.0 if (ocr_pos and clean_pos_text(ocr_pos) == p.pos) else 0.0
        total_score += ocr_pos_score
        score_breakdown['ocr_pos'] = ocr_pos_score

        # 7) DRAFT LIKELIHOOD (classic, 0–20) — live-board rank + ±1 window
        base_idx = index_map[id(p)]
        eff_rank = base_idx + 1
        draft_component = calculate_draft_likelihood(eff_rank, expected_pick) * 0.2
        total_score += draft_component
        score_breakdown['draft_likelihood'] = draft_component

        cand_scores.append((total_score, p, eff_rank, score_breakdown))

    if not cand_scores:
        return 0.0, players[0], 0, {}

    cand_scores.sort(key=lambda x: x[0], reverse=True)
    best_score, best_player, best_rank, breakdown = cand_scores[0]

    if expected_pick <= 25:
        print(f"  Pick {expected_pick} - Top 3 candidates:")
        for i, (score, player, rank, bd) in enumerate(cand_scores[:3]):
            print(f"    {i+1}. {player.full} (#{rank}) - Score: {score:.1f}")
            print(f"       Breakdown: Name={bd['lastname']:.1f}, Team={bd['team']:.1f}, Bye={bd['bye']:.1f}, Color={bd['color_pos']:.1f}, Draft={bd['draft_likelihood']:.1f}")

    return best_score, best_player, best_rank, breakdown
    
def top_n_matches_with_position(last_guess: str, row: int, col: int,
                                used_players: set, players: List[Player],
                                color_position: str = None, ocr_results: dict = None,
                                include_used: bool = False,
                                n: int = 3) -> List[Tuple[float, Player, int, dict]]:
    """
    Return the top N candidate matches using the same scoring as best_match_with_position.
    Excludes already-used players and optionally filters by detected color position.
    """
    index_map = {id(p): i for i, p in enumerate(players)}

    if not last_guess:
        return []

    expected_pick = grid_to_draft_pick(row, col)

    ocr_first = ocr_results.get('ocr_first', '') if ocr_results else ''
    ocr_team  = ocr_results.get('ocr_team',  '') if ocr_results else ''
    ocr_bye   = ocr_results.get('ocr_bye')       if ocr_results else None
    ocr_pos   = ocr_results.get('ocr_pos',   '') if ocr_results else ''

    candidate_players = players
    if color_position and color_position in ['QB', 'RB', 'WR', 'TE', 'K', 'DST']:
        candidate_players = [p for p in players if p.pos == color_position]

    cand_scores: List[Tuple[float, Player, int, dict]] = []
    lg = normalize_name(last_guess)

    for p in candidate_players:
        is_used = player_identity(p) in used_players
        if (not include_used) and is_used:
            continue

        total_score = 0.0
        score_breakdown = {}

        lastname_score = fuzz.token_set_ratio(lg, normalize_name(p.last)) * 0.4
        total_score += lastname_score
        score_breakdown['lastname'] = lastname_score

        if ocr_first and len(ocr_first) > 1:
            firstname_score = fuzz.token_set_ratio(normalize_name(ocr_first), normalize_name(p.first)) * 0.15
        else:
            firstname_score = 0.0
        total_score += firstname_score
        score_breakdown['firstname'] = firstname_score

        team_score = 15.0 if ocr_team and p.team.upper() == ocr_team.upper() else 0.0
        total_score += team_score
        score_breakdown['team'] = team_score

        bye_score = 10.0 if (ocr_bye is not None and ocr_bye > 0 and p.bye == ocr_bye) else 0.0
        total_score += bye_score
        score_breakdown['bye'] = bye_score

        color_score = 15.0 if (color_position and p.pos == color_position) else 0.0
        total_score += color_score
        score_breakdown['color_pos'] = color_score

        ocr_pos_score = 10.0 if (ocr_pos and clean_pos_text(ocr_pos) == p.pos) else 0.0
        total_score += ocr_pos_score
        score_breakdown['ocr_pos'] = ocr_pos_score

        base_idx = index_map[id(p)]
        eff_rank = base_idx + 1
        draft_component = calculate_draft_likelihood(eff_rank, expected_pick) * 0.2
        total_score += draft_component
        score_breakdown['draft_likelihood'] = draft_component
        score_breakdown['is_used'] = is_used

        cand_scores.append((total_score, p, eff_rank, score_breakdown))

    cand_scores.sort(key=lambda x: x[0], reverse=True)
    return cand_scores[:max(0, n)]


def reconcile_cell_with_position(ocr_results: dict, row: int, col: int, 
                               used_players: set, players: List[Player],
                               confidence_threshold: float = 45.0) -> dict:
    """
    Reconcile OCR results with player database using draft position logic.
    
    Args:
        ocr_results: Dictionary with OCR results from read_cell
        row: Grid row
        col: Grid column
        used_players: Set of already used player IDs
        players: List of players to match against
        confidence_threshold: Minimum confidence score to accept match
    
    Returns:
        Dictionary with reconciled player data and confidence scores
    """
    # Extract OCR results
    last_guess = ocr_results.get('ocr_last', '')
    
    # Get color position from OCR results
    color_position = ocr_results.get('color_pos')
    
    # Find best match using enhanced analytical approach
    match_score, best_player, best_rank, breakdown = best_match_with_position(
        last_guess, row, col, used_players, players, color_position, ocr_results
    )
    
    # Calculate actual draft pick
    actual_pick = grid_to_draft_pick(row, col)
    
    # Determine if we should use the match
    use_match = match_score >= confidence_threshold
    
    # Build result
    result = {
        'row': row,
        'col': col,
        'full_name': best_player.full if use_match else f"{ocr_results.get('ocr_first', '')} {last_guess}".strip(),
        'first': best_player.first if use_match else ocr_results.get('ocr_first', ''),
        'last': best_player.last if use_match else last_guess,
        'team': best_player.team if use_match else normalize_team(ocr_results.get('ocr_team', '')),
        'pos': best_player.pos if use_match else (ocr_results.get('color_pos') or clean_pos_text(ocr_results.get('ocr_pos', ''))),
        'bye': best_player.bye if use_match else ocr_results.get('ocr_bye'),
        'is_dst': best_player.is_dst,
        'match_score': match_score,
        'use_match': use_match,
        'source_last': 'csv' if use_match else 'ocr',
        'conf_last': match_score,
        'expected_pick': grid_to_draft_pick(row, col),
        'expected_rank': best_rank,
        'actual_pick': actual_pick,
        'position_diff': abs(grid_to_draft_pick(row, col) - actual_pick),
        'raw_ocr': {
            'pos': ocr_results.get('ocr_pos', ''),
            'color_pos': ocr_results.get('color_pos'),
            'bye': ocr_results.get('ocr_bye'),
            'last': ocr_results.get('ocr_last', ''),
            'team': ocr_results.get('ocr_team', ''),
            'first': ocr_results.get('ocr_first', '')
        },
        'best_candidate': {
            'full_name': best_player.full,
            'first': best_player.first,
            'last': best_player.last,
            'team': best_player.team,
            'pos': best_player.pos,
            'bye': best_player.bye,
            'is_dst': best_player.is_dst,
            'rank': best_rank
        },
        'best_candidate_confidence': match_score,
        'score_breakdown': breakdown
    }
    
    return result

def handle_dst_special_case(ocr_results: dict, players: List[Player]) -> Optional[dict]:
    """
    Handle special case for DST (Defense/Special Teams).
    
    Args:
        ocr_results: OCR results from read_cell
        players: List of players
    
    Returns:
        Reconciled DST data or None if not DST
    """
    # Check if this looks like DST based on color or OCR
    color_pos = ocr_results.get('color_pos')
    ocr_pos = ocr_results.get('ocr_pos', '')
    
    is_dst_candidate = (
        color_pos == "DST" or 
        ocr_pos.upper() == "DST" or
        (not ocr_results.get('ocr_first') and ocr_results.get('ocr_last'))
    )
    
    if not is_dst_candidate:
        return None
    
    # Look for team name in lastname field
    team_name = ocr_results.get('ocr_last', '').upper()
    
    # Find matching DST in players list
    for player in players:
        if player.is_dst and team_name in player.last:
            return {
                'row': None,
                'col': None,
                'full_name': player.full,
                'first': "",
                'last': player.last,
                'team': player.team,
                'pos': "DST",
                'bye': player.bye,
                'is_dst': True,
                'match_score': 100.0,
                'use_match': True,
                'source_last': 'csv',
                'conf_last': 100.0,
                'expected_pick': 0,
                'actual_pick': 0,
                'position_diff': 0,
                'raw_ocr': ocr_results
            }
    
    return None
