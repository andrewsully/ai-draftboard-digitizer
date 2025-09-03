import csv
import json
import cv2
import numpy as np
import os
from typing import List, Dict

def write_row_major_text(results: List[Dict], output_path: str = "out/rows.txt"):
    """
    Write results in row-major format.
    
    Args:
        results: List of reconciled player results
        output_path: Output file path
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Group by row
    rows = {}
    for result in results:
        if not result:
            continue
        row = result.get('row')
        if row is None:
            continue
        rows.setdefault(row, []).append(result)
    
    with open(output_path, 'w') as f:
        for row_num in sorted(rows.keys()):
            row_players = sorted(rows[row_num], key=lambda x: x['col'])
            row_text = f"Row {row_num + 1}: "
            
            player_texts = []
            for player in row_players:
                if player.get('is_dst', False):
                    player_text = f"{player.get('last','')} ({player.get('team','')}, {player.get('pos','')}, BYE {player.get('bye','')})"
                else:
                    player_text = f"{player.get('last','')}, {player.get('first','')} ({player.get('team','')}, {player.get('pos','')}, BYE {player.get('bye','')})"
                player_texts.append(player_text)
            
            row_text += "; ".join(player_texts)
            f.write(row_text + "\n")

def write_column_major_text(results: List[Dict], output_path: str = "out/cols.txt"):
    """
    Write results in column-major format.
    
    Args:
        results: List of reconciled player results
        output_path: Output file path
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Group by column
    cols = {}
    for result in results:
        if not result:
            continue
        col = result.get('col')
        if col is None:
            continue
        cols.setdefault(col, []).append(result)
    
    with open(output_path, 'w') as f:
        for col_num in sorted(cols.keys()):
            col_players = sorted(cols[col_num], key=lambda x: x['row'])
            col_text = f"Col {col_num + 1}: "
            
            player_texts = []
            for player in col_players:
                if player.get('is_dst', False):
                    player_text = f"{player.get('last','')} ({player.get('team','')}, {player.get('pos','')}, BYE {player.get('bye','')})"
                else:
                    player_text = f"{player.get('last','')}, {player.get('first','')} ({player.get('team','')}, {player.get('pos','')}, BYE {player.get('bye','')})"
                player_texts.append(player_text)
            
            col_text += "; ".join(player_texts)
            f.write(col_text + "\n")

def write_csv(results: List[Dict], output_path: str = "out/board.csv"):
    """
    Write results to CSV format.
    
    Args:
        results: List of reconciled player results
        output_path: Output file path
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    fieldnames = [
        'row', 'col', 'full_name', 'first', 'last', 'team', 'pos', 'bye',
        'is_dst', 'match_score', 'use_match', 'source_last', 'conf_last',
        'raw_ocr_pos', 'raw_color_pos', 'raw_ocr_bye', 'raw_ocr_last',
        'raw_ocr_team', 'raw_ocr_first'
    ]
    
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            if not result:
                continue
            raw = result.get('raw_ocr', {}) or {}
            row = {
                'row': result.get('row',''),
                'col': result.get('col',''),
                'full_name': result.get('full_name',''),
                'first': result.get('first',''),
                'last': result.get('last',''),
                'team': result.get('team',''),
                'pos': result.get('pos',''),
                'bye': result.get('bye',''),
                'is_dst': result.get('is_dst', False),
                'match_score': result.get('match_score',''),
                'use_match': result.get('use_match',''),
                'source_last': result.get('source_last',''),
                'conf_last': result.get('conf_last',''),
                'raw_ocr_pos': raw.get('pos',''),
                'raw_color_pos': raw.get('color_pos',''),
                'raw_ocr_bye': raw.get('bye',''),
                'raw_ocr_last': raw.get('last',''),
                'raw_ocr_team': raw.get('team',''),
                'raw_ocr_first': raw.get('first','')
            }
            writer.writerow(row)

def write_json(results: List[Dict], output_path: str = "out/board.json"):
    """
    Write results to JSON format.
    
    Args:
        results: List of reconciled player results
        output_path: Output file path
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

def write_low_confidence_review(results: List[Dict], threshold: float = 80.0, 
                               output_path: str = "out/review_low_confidence.csv"):
    """
    Write low confidence results for manual review.
    
    Args:
        results: List of reconciled player results
        threshold: Confidence threshold
        output_path: Output file path
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    low_confidence = [r for r in results if r['match_score'] < threshold]
    
    if not low_confidence:
        # Create empty file with headers
        fieldnames = [
            'row', 'col', 'full_name', 'first', 'last', 'team', 'pos', 'bye',
            'match_score', 'raw_ocr_last', 'raw_ocr_team', 'raw_ocr_pos',
            'raw_color_pos', 'raw_ocr_bye', 'raw_ocr_first'
        ]
        
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
        return
    
    fieldnames = [
        'row', 'col', 'full_name', 'first', 'last', 'team', 'pos', 'bye',
        'match_score', 'raw_ocr_last', 'raw_ocr_team', 'raw_ocr_pos',
        'raw_color_pos', 'raw_ocr_bye', 'raw_ocr_first'
    ]
    
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in low_confidence:
            row = {
                'row': result['row'],
                'col': result['col'],
                'full_name': result['full_name'],
                'first': result['first'],
                'last': result['last'],
                'team': result['team'],
                'pos': result['pos'],
                'bye': result['bye'],
                'match_score': result['match_score'],
                'raw_ocr_last': result['raw_ocr']['last'],
                'raw_ocr_team': result['raw_ocr']['team'],
                'raw_ocr_pos': result['raw_ocr']['pos'],
                'raw_color_pos': result['raw_ocr']['color_pos'],
                'raw_ocr_bye': result['raw_ocr']['bye'],
                'raw_ocr_first': result['raw_ocr']['first']
            }
            writer.writerow(row)

def create_overlay_image(rectified_image: np.ndarray, results: List[Dict], 
                        cells: List[tuple], output_path: str = "out/overlay.png",
                        position_colors: Dict[str, tuple] = None):
    """
    Create overlay image with predicted text drawn on each cell.
    
    Args:
        rectified_image: The rectified board image
        results: List of reconciled player results
        cells: List of cell ROIs (row, col, x, y, w, h)
        output_path: Output file path
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Create a copy of the image for overlay
    overlay = rectified_image.copy()
    
    # If not provided, fallback to previous defaults
    if position_colors is None:
        position_colors = {
            'QB':  (0, 165, 255),
            'RB':  (101, 147, 205),
            'WR':  (255, 0, 0),
            'TE':  (0, 0, 255),
            'K':   (255, 0, 255),
            'DST': (0, 255, 0)
        }

    
    # Create a mapping from (row, col) to result
    result_map = {}
    for result in results:
        if not result:
            continue
        r = result.get('row')
        c = result.get('col')
        if r is None or c is None:
            continue
        result_map[(r, c)] = result
    
    # Draw text on each cell
    for row, col, x, y, w, h in cells:
        if (row, col) in result_map:
            result = result_map[(row, col)]
            
            # Get OCR position text (from raw OCR data)
            raw_ocr = result.get('raw_ocr', {}) or {}
            ocr_position = raw_ocr.get('pos', '')
            color_position = raw_ocr.get('color_pos', '')
            
            # Prepare text to display: show LAST NAME only (details now in tooltip)
            display_text = f"{result.get('last','')}"
            
            # Set font properties
            font = cv2.FONT_HERSHEY_SIMPLEX
            # Make last name labels larger/wider on the grid
            font_scale = min(w, h) / 160.0  # previously /200.0
            thickness = max(1, int(font_scale * 3))
            
            # Get text size for first line (lastname)
            (text_width, text_height), baseline = cv2.getTextSize(
                display_text.split('\n')[0], font, font_scale, thickness
            )
            
            # Calculate text position - shift down within the cell for better fit
            text_x = x + (w - text_width) // 2
            margin_top = max(5, int(h * 0.1))  # 10% of cell height (min 5px)
            # OpenCV uses baseline for Y, so add text_height to place top at margin
            text_y = y + margin_top + text_height
            
            # Draw background rectangle for better readability
            padding = 10
            cv2.rectangle(overlay, 
                         (text_x - padding, text_y - text_height - padding),
                         (text_x + text_width + padding, text_y + baseline + padding),
                         (255, 255, 255), -1)
            
            # Draw lastname text only
            cv2.putText(overlay, display_text, (text_x, text_y), 
                       font, font_scale, (0, 0, 0), thickness)
            
            # Draw INNER colored border based on color-detected position
            # Use color_position (from color detection) not final position
            position = color_position if color_position else ''
            border_color = position_colors.get(position, (255, 255, 255))  # White if no match
            border_thickness = 3
            
            # Draw inner border (inset by border_thickness)
            inner_x = x + border_thickness
            inner_y = y + border_thickness
            inner_w = w - 2 * border_thickness
            inner_h = h - 2 * border_thickness
            
            cv2.rectangle(overlay, (inner_x, inner_y), (inner_x + inner_w, inner_y + inner_h), 
                         border_color, border_thickness)
    
    # Save overlay image
    cv2.imwrite(output_path, overlay)

def emit_all_outputs(results: List[Dict], rectified_image: np.ndarray = None,
                    cells: List[tuple] = None, output_dir: str = "out",
                    position_colors: Dict[str, tuple] = None):
    """
    Generate all output formats.
    
    Args:
        results: List of reconciled player results
        rectified_image: The rectified board image (for overlay)
        cells: List of cell ROIs (for overlay)
        output_dir: Output directory
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Write text outputs
    write_row_major_text(results, os.path.join(output_dir, "rows.txt"))
    write_column_major_text(results, os.path.join(output_dir, "cols.txt"))
    
    # Write data outputs
    write_csv(results, os.path.join(output_dir, "board.csv"))
    write_json(results, os.path.join(output_dir, "board.json"))
    
    # Write review file
    write_low_confidence_review(results, output_path=os.path.join(output_dir, "review_low_confidence.csv"))
    
    # Create overlay if image and cells provided
    if rectified_image is not None and cells is not None:
        create_overlay_image(rectified_image, results, cells, 
                           os.path.join(output_dir, "overlay.png"),
                           position_colors=position_colors)
