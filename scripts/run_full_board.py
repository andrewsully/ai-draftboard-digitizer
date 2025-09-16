#!/usr/bin/env python3
"""
Run the full color-filtered OCR system on the entire draft board.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from preprocess import normalize_board
from grid import cells_from_rectified
from ocr_cell import read_cell
from reconcile import load_players, reconcile_cell_with_position
from emit import emit_all_outputs

def run_full_board():
    """Run the complete color-filtered system on the entire draft board."""
    print("Running Full Color-Filtered Draft Board Analysis")
    print("=" * 60)
    
    # Step 1: Load and preprocess
    print("\n1. Loading and preprocessing board...")
    rectified_image = normalize_board("../examples/sample_data/draftboard.png", "../outputs/full_board_out")
    
    # Step 2: Load player database
    print("\n2. Loading player database...")
    players = load_players("../data/top500_playernames.csv")
    print(f"Loaded {len(players)} players")
    
    # Step 3: Extract grid cells
    print("\n3. Extracting grid cells...")
    cells = cells_from_rectified(rectified_image, output_dir="../outputs/full_board_out")
    print(f"Extracted {len(cells)} cells")
    
    # Step 4: Process all cells with color filtering
    print("\n4. Processing cells with color-filtered matching...")
    results = []
    used_players = set()
    
    for i, (row, col, x, y, w, h) in enumerate(cells):
        cell_img = rectified_image[y:y+h, x:x+w]
        
        # Run OCR with color detection
        ocr_result = read_cell(cell_img)
        
        # Run reconciliation with color filtering
        result = reconcile_cell_with_position(
            ocr_result, row, col, used_players, players, confidence_threshold=40.0
        )
        
        if result and result.get('use_match'):
            sb = result.get('score_breakdown', {}) or {}
            lastname_pts = sb.get('lastname', 0.0)
            if lastname_pts >= 15.0:
                used_id = (
                    result.get('first'),
                    result.get('last'),
                    result.get('team'),
                    result.get('pos'),
                    result.get('bye') if result.get('bye') is not None else 0
                )
                used_players.add(used_id)
        
        results.append(result)
        
        # Progress reporting
        if i % 20 == 0:
            print(f"  Processed {i+1}/{len(cells)} cells")
    
    # Step 5: Generate all outputs
    print("\n5. Generating outputs...")
    emit_all_outputs(results, rectified_image, cells, "../outputs/full_board_out")
    
    # Step 6: Analyze results
    print("\n6. Final Results Analysis:")
    print("-" * 40)
    
    successful_matches = sum(1 for r in results if r and 'last' in r)
    low_confidence = sum(1 for r in results if r and r.get('confidence', 0) < 70.0)
    errors = sum(1 for r in results if not r or 'error' in r)
    
    print(f"Total cells processed: {len(cells)}")
    print(f"Successful matches: {successful_matches}")
    print(f"Low confidence: {low_confidence}")
    print(f"Errors: {errors}")
    print(f"Success rate: {successful_matches/len(cells)*100:.1f}%")
    
    # Position distribution
    print(f"\n7. Position Distribution:")
    position_counts = {}
    for result in results:
        if result and 'pos' in result:
            pos = result['pos']
            position_counts[pos] = position_counts.get(pos, 0) + 1
    
    for pos, count in sorted(position_counts.items()):
        print(f"  {pos}: {count} players")
    
    # Show top matches
    print(f"\n8. Top Draft Picks:")
    top_picks = []
    for i, result in enumerate(results):
        if result and 'last' in result:
            pick_num = i + 1
            player_name = result.get('full_name', 'Unknown')
            position = result.get('pos', 'Unknown')
            confidence = result.get('confidence', 0)
            top_picks.append((pick_num, player_name, position, confidence))
    
    for pick_num, player_name, position, confidence in top_picks[:15]:
        print(f"  Pick {pick_num:2d}: {player_name} ({position}) - {confidence:.1f}")
    
    print(f"\nResults saved to: ../outputs/full_board_out/")
    print(f"Check the following files:")
    print(f"  - ../outputs/full_board_out/board.csv (complete data)")
    print(f"  - ../outputs/full_board_out/rows.txt (row-major format)")
    print(f"  - ../outputs/full_board_out/cols.txt (column-major format)")
    print(f"  - ../outputs/full_board_out/overlay.png (visual overlay)")

if __name__ == "__main__":
    run_full_board()
