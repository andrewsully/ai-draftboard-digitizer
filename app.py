#!/usr/bin/env python3
"""
Flask web application for Fantasy Football Draft Board OCR
"""

import os
import json
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from PIL import Image
import io
import base64
from sklearn.cluster import KMeans

# Import our existing modules
import sys
sys.path.append('src')

from src.preprocess import normalize_board
from src.grid import cells_from_rectified
from src.ocr_cell import read_cell
from src.reconcile import load_players, reconcile_cell_with_position, grid_to_draft_pick
from src.emit import emit_all_outputs
from src.manual_color_calibration import ManualColorCalibrator

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'web_output'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['OUTPUT_FOLDER'], 'results'), exist_ok=True)
os.makedirs(os.path.join(app.config['OUTPUT_FOLDER'], 'results', 'cells'), exist_ok=True)
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

# Global variables to store session data
session_data = {}

@app.route('/')
def index():
    """Main page with upload interface"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    """Handle image upload"""
    print(f"Upload request received. Files: {list(request.files.keys())}")
    print(f"Request content type: {request.content_type}")
    
    if 'image' not in request.files:
        print("No 'image' field in request.files")
        return jsonify({'error': 'No image uploaded'}), 400
    
    file = request.files['image']
    print(f"File received: {file.filename}, size: {file.content_length if hasattr(file, 'content_length') else 'unknown'}")
    
    if file.filename == '':
        print("Empty filename")
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        try:
            # Save uploaded image
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            print(f"Saving file to: {filepath}")
            file.save(filepath)
            
            # Verify file was saved
            if os.path.exists(filepath):
                print(f"File saved successfully: {os.path.getsize(filepath)} bytes")
            else:
                print("File was not saved!")
                return jsonify({'error': 'Failed to save file'}), 500
            
            # Store in session
            session_data['original_image'] = filepath
            
            # Return success with image info
            return jsonify({
                'success': True,
                'filename': filename,
                'message': 'Image uploaded successfully'
            })
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
    else:
        print("File object is None or empty")
        return jsonify({'error': 'Invalid file'}), 400

@app.route('/crop', methods=['POST'])
def crop_image():
    """Handle simple image cropping"""
    data = request.get_json()
    
    if 'original_image' not in session_data:
        return jsonify({'error': 'No image uploaded'}), 400
    
    # Get crop coordinates
    x = int(data['x'])
    y = int(data['y'])
    width = int(data['width'])
    height = int(data['height'])
    
    # Get draft configuration
    team_count = int(data.get('teamCount', 10))
    round_count = int(data.get('roundCount', 16))
    
    # Store draft configuration in session
    session_data['team_count'] = team_count
    session_data['round_count'] = round_count
    
        # Load and crop image
    image = cv2.imread(session_data['original_image'])
    cropped = image[y:y+height, x:x+width]

    # Save cropped image (preserve original colors)
    cropped_path = os.path.join(app.config['UPLOAD_FOLDER'], 'cropped_board.png')
    # Use PNG with higher quality settings to preserve colors
    # OpenCV uses BGR by default, but PNG should handle this correctly
    cv2.imwrite(cropped_path, cropped, [cv2.IMWRITE_PNG_COMPRESSION, 0])
    
    # Store in session
    session_data['cropped_image'] = cropped_path
    
    # Convert to base64 for preview
    _, buffer = cv2.imencode('.png', cropped)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return jsonify({
        'success': True,
        'cropped_image': f'data:image/png;base64,{img_base64}',
        'message': 'Image cropped successfully'
    })

@app.route('/advanced_crop', methods=['POST'])
def advanced_crop():
    """Handle advanced cropping with perspective transformation"""
    data = request.get_json()
    
    if 'original_image' not in session_data:
        return jsonify({'error': 'No image uploaded'}), 400
    
    try:
        # Get corner points
        corners = data.get('corners', [])
        if len(corners) != 4:
            return jsonify({'error': 'Need exactly 4 corner points'}), 400
        
        # Get draft configuration
        team_count = int(data.get('teamCount', 10))
        round_count = int(data.get('roundCount', 16))
        
        # Store draft configuration in session
        session_data['team_count'] = team_count
        session_data['round_count'] = round_count
        
        # Load original image
        image = cv2.imread(session_data['original_image'])
        height, width = image.shape[:2]
        
        # Convert corner points to numpy array
        src_points = np.array([[corner['x'], corner['y']] for corner in corners], dtype=np.float32)
        
        # Calculate the bounding box of the selected area
        x_coords = [corner['x'] for corner in corners]
        y_coords = [corner['y'] for corner in corners]
        
        # Calculate output dimensions based on the selected area
        output_width = int(max(x_coords) - min(x_coords))
        output_height = int(max(y_coords) - min(y_coords))
        
        # Define destination points for a rectangular output
        dst_points = np.array([
            [0, 0],                           # top-left
            [output_width, 0],                # top-right
            [output_width, output_height],    # bottom-right
            [0, output_height]                # bottom-left
        ], dtype=np.float32)
        
        # Calculate perspective transformation matrix
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # Apply perspective transformation
        corrected = cv2.warpPerspective(image, matrix, (output_width, output_height))
        
        # Save corrected image (preserve original colors)
        corrected_path = os.path.join(app.config['UPLOAD_FOLDER'], 'corrected_board.png')
        # Use PNG with higher quality settings to preserve colors
        # OpenCV uses BGR by default, but PNG should handle this correctly
        cv2.imwrite(corrected_path, corrected, [cv2.IMWRITE_PNG_COMPRESSION, 0])
        
        # Store in session
        session_data['cropped_image'] = corrected_path
        
        # Convert to base64 for preview
        _, buffer = cv2.imencode('.png', corrected)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'cropped_image': f'data:image/png;base64,{img_base64}',
            'message': 'Perspective correction applied successfully'
        })
        
    except Exception as e:
        return jsonify({'error': f'Advanced cropping failed: {str(e)}'}), 500

@app.route('/calibrate', methods=['POST'])
def calibrate_colors():
    """Handle color calibration"""
    data = request.get_json()
    
    if 'cropped_image' not in session_data:
        return jsonify({'error': 'No cropped image available'}), 400
    
    # Create custom color profiles from user selections
    color_profiles = {}
    
    for position, color_data in data['colors'].items():
        h, s, v = color_data['hsv']
        
        # Create HSV range with position-specific tolerance
        if position == 'QB':  # Orange - can be more variable
            h_tolerance, s_tolerance, v_tolerance = 20, 50, 50
        elif position == 'RB':  # Brown - needs more tolerance
            h_tolerance, s_tolerance, v_tolerance = 25, 60, 60
        elif position == 'WR':  # Blue - fairly consistent
            h_tolerance, s_tolerance, v_tolerance = 15, 35, 35
        elif position == 'TE':  # Red - can vary
            h_tolerance, s_tolerance, v_tolerance = 20, 45, 45
        elif position == 'K':   # Gray - reduce tolerance to prevent catch-all
            h_tolerance, s_tolerance, v_tolerance = 15, 30, 30
        elif position == 'DST': # Green - fairly consistent
            h_tolerance, s_tolerance, v_tolerance = 15, 40, 40
        else:
            h_tolerance, s_tolerance, v_tolerance = 15, 40, 40
        
        h_min = max(0, h - h_tolerance)
        h_max = min(180, h + h_tolerance)
        s_min = max(0, s - s_tolerance)
        s_max = min(255, s + s_tolerance)
        v_min = max(0, v - v_tolerance)
        v_max = min(255, v + v_tolerance)
        
        color_profiles[position] = {
            'hsv_ranges': [[h_min, s_min, v_min], [h_max, s_max, v_max]],
            'confidence': 1.0
        }
    
    # Store color profiles in session
    session_data['color_profiles'] = color_profiles
    
    return jsonify({
        'success': True,
        'message': 'Color calibration completed'
    })

@app.route('/auto_detect_colors', methods=['POST'])
def auto_detect_colors():
    """Automatically detect position colors using OCR-based sampling of cells.

    Strategy:
    - Build a rectified board and grid
    - OCR cells to find those with recognizable POS text and last names
    - For each POS, collect up to 5 unique last-name samples and compute HSV ranges
    - Fallback to global KMeans color clustering if insufficient samples
    """
    if 'cropped_image' not in session_data:
        return jsonify({'error': 'No cropped image available'}), 400

    try:
        # Build rectified board and cells
        from src.preprocess import normalize_board
        from src.grid import cells_from_rectified
        from src.ocr_cell import read_cell_whole, dominant_nonwhite_hsv
        from src.reconcile import load_players

        players = load_players("data/top500_playernames.csv")
        team_count = session_data.get('team_count', 10)
        round_count = session_data.get('round_count', 16)

        rectified = normalize_board(session_data['cropped_image'], app.config['OUTPUT_FOLDER'])
        cells = cells_from_rectified(rectified, rows=round_count, cols=team_count, output_dir=app.config['OUTPUT_FOLDER'])

        # Collect HSV samples per POS using OCR-derived POS and unique last names
        target_positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
        pos_to_samples = {p: [] for p in target_positions}
        pos_to_lastnames = {p: set() for p in target_positions}

        def clean_pos_text_local(pos_text: str):
            if not pos_text:
                return None
            import re as _re
            p = _re.sub(r'[^A-Z]', '', str(pos_text).upper())
            return p if p in target_positions else None

        for (row, col, x, y, w, h) in cells:
            cell_img = rectified[y:y+h, x:x+w]
            ocr_whole = read_cell_whole(cell_img)
            pos = clean_pos_text_local(ocr_whole.get('ocr_pos'))
            last = str(ocr_whole.get('ocr_last') or '').strip().upper()
            if not pos or not last:
                continue
            if last in pos_to_lastnames[pos]:
                continue

            hsv = dominant_nonwhite_hsv(cell_img)
            pos_to_samples[pos].append(hsv)
            pos_to_lastnames[pos].add(last)

            # Stop early if we have enough samples for all (reduced to 2 for speed)
            if all(len(pos_to_samples[p]) >= 2 for p in target_positions):
                break

        # Build color profiles from samples
        color_profiles = {}
        session_color_profiles = {}

        for pos in target_positions:
            samples = pos_to_samples.get(pos, [])
            if len(samples) < 2:
                continue
            samples = np.array(samples, dtype=np.float32)
            h_vals = samples[:, 0]
            s_vals = samples[:, 1]
            v_vals = samples[:, 2]

            # Use percentiles with padding
            h_min, h_max = np.percentile(h_vals, [10, 90])
            s_min, s_max = np.percentile(s_vals, [10, 90])
            v_min, v_max = np.percentile(v_vals, [10, 90])

            h_spread = max(1, int(h_max - h_min))
            s_spread = max(1, int(s_max - s_min))
            v_spread = max(1, int(v_max - v_min))

            h_pad = max(8, int(0.20 * h_spread))
            s_pad = max(20, int(0.20 * s_spread))
            v_pad = max(20, int(0.20 * v_spread))

            h_lo = int(max(0, h_min - h_pad))
            h_hi = int(min(180, h_max + h_pad))
            s_lo = int(max(0, s_min - s_pad))
            s_hi = int(min(255, s_max + s_pad))
            v_lo = int(max(0, v_min - v_pad))
            v_hi = int(min(255, v_max + v_pad))

            # Center for UI
            h_c = int((h_lo + h_hi) / 2)
            s_c = int((s_lo + s_hi) / 2)
            v_c = int((v_lo + v_hi) / 2)

            hsv_pixel = np.uint8([[[h_c, s_c, v_c]]])
            bgr_pixel = cv2.cvtColor(hsv_pixel, cv2.COLOR_HSV2BGR)[0][0]
            rgb = [int(bgr_pixel[2]), int(bgr_pixel[1]), int(bgr_pixel[0])]

            color_profiles[pos] = {
                'rgb': rgb,
                'hsv': [h_c, s_c, v_c],
            }
            session_color_profiles[pos] = {
                'hsv_ranges': [[h_lo, s_lo, v_lo], [h_hi, s_hi, v_hi]],
                'confidence': 1.0
            }

        # If not enough positions were derived, fallback to KMeans heuristic
        if len(color_profiles) < 3:
            img_bgr = cv2.imread(session_data['cropped_image'])
            if img_bgr is None:
                return jsonify({'error': 'Failed to load cropped image'}), 500

            img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            hsv_flat = img_hsv.reshape(-1, 3)
            s_threshold = 40
            v_threshold = 60
            mask = (hsv_flat[:, 1] >= s_threshold) & (hsv_flat[:, 2] >= v_threshold)
            filtered = hsv_flat[mask]
            if filtered.shape[0] < 1000:
                filtered = hsv_flat
            kmeans = KMeans(n_clusters=6, n_init=10, random_state=42)
            labels = kmeans.fit_predict(filtered)
            centers = kmeans.cluster_centers_
            counts = np.bincount(labels, minlength=6)
            order = np.argsort(counts)[::-1]
            pos_order = ['WR', 'RB', 'QB', 'TE', 'DST', 'K']
            for rank, cluster_idx in enumerate(order):
                pos = pos_order[rank]
                if pos in color_profiles:
                    continue
                h_c, s_c, v_c = centers[cluster_idx]
                h_c = int(max(0, min(180, round(h_c))))
                s_c = int(max(0, min(255, round(s_c))))
                v_c = int(max(0, min(255, round(v_c))))
                hsv_pixel = np.uint8([[[h_c, s_c, v_c]]])
                bgr_pixel = cv2.cvtColor(hsv_pixel, cv2.COLOR_HSV2BGR)[0][0]
                rgb = [int(bgr_pixel[2]), int(bgr_pixel[1]), int(bgr_pixel[0])]
                color_profiles[pos] = {'rgb': rgb, 'hsv': [h_c, s_c, v_c]}
                session_color_profiles[pos] = {
                    'hsv_ranges': [[h_c, s_c, v_c], [h_c, s_c, v_c]],
                    'confidence': 0.5
                }

        # Store in session
        session_data['color_profiles'] = session_color_profiles
        return jsonify({'success': True, 'colorProfiles': color_profiles})
    except Exception as e:
        return jsonify({'error': f'Auto-detect colors failed: {str(e)}'}), 500

@app.route('/process', methods=['POST'])
def process_board():
    """Process the draft board with custom color profiles"""
    if 'cropped_image' not in session_data or 'color_profiles' not in session_data:
        return jsonify({'error': 'Missing cropped image or color profiles'}), 400
    
    try:
        # Load player database
        players = load_players("data/top500_playernames.csv")
        
        # Create custom calibrator with user's color profiles
        calibrator = ManualColorCalibrator()
        calibrator.profiles = {}
        
        for position, profile_data in session_data['color_profiles'].items():
            from src.manual_color_calibration import ColorProfile
            calibrator.profiles[position] = ColorProfile(
                position=position,
                hsv_ranges=[(tuple(profile_data['hsv_ranges'][0]), tuple(profile_data['hsv_ranges'][1]))],
                confidence=profile_data['confidence']
            )
        
        # Preprocess the cropped image
        rectified_image = normalize_board(session_data['cropped_image'], app.config['OUTPUT_FOLDER'])
        
        # Extract grid cells with custom dimensions
        team_count = session_data.get('team_count', 10)
        round_count = session_data.get('round_count', 16)
        cells = cells_from_rectified(rectified_image, rows=round_count, cols=team_count, output_dir=app.config['OUTPUT_FOLDER'])
        
        # Process all cells
        results = []
        unrecognized_cells = []
        used_players = set()
        total_cells = len(cells)
        
        debug_ocr = []

        for i, (row, col, x, y, w, h) in enumerate(cells):
            cell_img = rectified_image[y:y+h, x:x+w]
            
            # Run both OCR strategies and pick the better during reconciliation
            ocr_result_roi = read_cell(cell_img)
            from src.ocr_cell import read_cell_whole
            ocr_result_whole = read_cell_whole(cell_img)
            
            # Override color detection with custom calibrator
            # Get the dominant color HSV from the cell image
            from src.ocr_cell import dominant_nonwhite_hsv
            hsv = dominant_nonwhite_hsv(cell_img)
            
            # Use custom calibrator to detect position from color (Original cell)
            position, confidence = calibrator.detect_position_from_color(hsv)
            color_pos = position if confidence > 0.3 else None
            ocr_result_roi['color_pos'] = color_pos
            ocr_result_whole['color_pos'] = color_pos
            
            # Run reconciliation for both and choose the higher score
            result_roi = reconcile_cell_with_position(
                ocr_result_roi, row, col, used_players, players, confidence_threshold=45.0
            )
            # Whole-cell OCR: also try swapping first/last if that improves the score
            result_whole = reconcile_cell_with_position(
                ocr_result_whole, row, col, used_players, players, confidence_threshold=45.0
            )
            swapped_whole = dict(ocr_result_whole)
            swapped_whole['ocr_first'], swapped_whole['ocr_last'] = (
                ocr_result_whole.get('ocr_last', ''), ocr_result_whole.get('ocr_first', '')
            )
            swapped_whole['color_pos'] = color_pos
            result_whole_swapped = reconcile_cell_with_position(
                swapped_whole, row, col, used_players, players, confidence_threshold=45.0
            )
            # If swapped yields higher match_score, use it as the whole result and update ocr_result_whole
            if (result_whole_swapped and result_whole_swapped.get('match_score', 0) > (result_whole or {}).get('match_score', 0)):
                result_whole = result_whole_swapped
                ocr_result_whole = swapped_whole

            # Pick better result (by match_score), prefer ROI on tie
            if (result_whole and result_whole.get('match_score', 0) > (result_roi or {}).get('match_score', 0)):
                result = result_whole
                chosen_source = 'whole'
            else:
                result = result_roi
                chosen_source = 'roi'

            # Collect debug comparison info for this cell
            # Include top-3 candidate suggestions (filtered by used players and color)
            try:
                from src.reconcile import top_n_matches_with_position
                chosen_ocr = (ocr_result_whole if result is result_whole else ocr_result_roi)
                top3 = top_n_matches_with_position(
                    chosen_ocr.get('ocr_last') or '',
                    row, col, used_players, players, color_pos,
                    ocr_results=chosen_ocr, include_used=True, n=3
                )
                top3_list = [
                    {
                        'name': cand_player.full,
                        'pos': cand_player.pos,
                        'team': cand_player.team,
                        'score': cand_score,
                        'rank': cand_rank,
                        'used': bool((_bd or {}).get('is_used'))
                    }
                    for (cand_score, cand_player, cand_rank, _bd) in top3
                ]
            except Exception:
                top3_list = []

            debug_ocr.append({
                'row': row,
                'col': col,
                'chosen': chosen_source,
                'roi': {
                    'ocr_pos': ocr_result_roi.get('ocr_pos'),
                    'ocr_bye': ocr_result_roi.get('ocr_bye'),
                    'ocr_last': ocr_result_roi.get('ocr_last'),
                    'ocr_team': ocr_result_roi.get('ocr_team'),
                    'ocr_first': ocr_result_roi.get('ocr_first'),
                    'color_pos': ocr_result_roi.get('color_pos'),
                    'match_score': (result_roi or {}).get('match_score')
                },
                'whole': {
                    'ocr_pos': ocr_result_whole.get('ocr_pos'),
                    'ocr_bye': ocr_result_whole.get('ocr_bye'),
                    'ocr_last': ocr_result_whole.get('ocr_last'),
                    'ocr_team': ocr_result_whole.get('ocr_team'),
                    'ocr_first': ocr_result_whole.get('ocr_first'),
                    'color_pos': ocr_result_whole.get('color_pos'),
                    'match_score': (result_whole or {}).get('match_score')
                },
                'top3': top3_list
            })

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

            # Check if this cell needs manual correction (low confidence or no match)
            if not result or not result.get('use_match', False) or result.get('match_score', 0) < 45.0:
                # Save cell image for manual correction
                cell_filename = f'cell_r{row}_c{col}.png'
                cell_path = os.path.join(app.config['OUTPUT_FOLDER'], 'results', 'cells', cell_filename)
                os.makedirs(os.path.dirname(cell_path), exist_ok=True)

                # Save the image
                cv2.imwrite(cell_path, cell_img)

                # Add to unrecognized cells list
                suggested_player = None
                if result and result.get('best_candidate'):
                    cand = result['best_candidate']
                    suggested_player = {
                        'name': cand.get('full_name', ''),
                        'position': cand.get('pos', ''),
                        'team': cand.get('team', ''),
                        'confidence': result.get('best_candidate_confidence', 0),
                        'is_db': True
                    }

                # Use the OCR result source that produced the chosen result for display
                chosen_ocr = ocr_result_whole if result is result_whole else ocr_result_roi

                unrecognized_cells.append({
                    'index': i,
                    'row': row,
                    'col': col,
                    'cell_image': f'/cell_image/{cell_filename}',
                    'ocr_text': f"{chosen_ocr.get('ocr_first', '')} {chosen_ocr.get('ocr_last', '')}".strip(),
                    'detected_position': chosen_ocr.get('color_pos'),
                    'confidence': result.get('match_score', 0) if result else 0,
                    'suggested_player': suggested_player
                })

            results.append(result)
            
            # Log progress
            progress = (i + 1) / total_cells * 100
            print(f"Processing cell {i+1}/{total_cells} ({progress:.1f}%)")
            
            # Store progress in session for frontend to check
            session_data['processing_progress'] = {
                'current': i + 1,
                'total': total_cells,
                'percentage': progress
            }
        
        # Generate outputs
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], 'results')
        os.makedirs(output_dir, exist_ok=True)
        
        # Build position color map from calibrated profiles if available (use RGB -> BGR)
        position_colors = None
        if 'color_profiles' in session_data:
            position_colors = {}
            for pos, profile in session_data['color_profiles'].items():
                # Prefer explicit RGB if provided; otherwise derive from HSV center
                rgb = profile.get('rgb')
                if rgb and isinstance(rgb, (list, tuple)) and len(rgb) == 3:
                    bgr = (int(rgb[2]), int(rgb[1]), int(rgb[0]))
                    position_colors[pos] = bgr
                else:
                    hsv_ranges = profile.get('hsv_ranges')
                    # Expecting [[h_min, s_min, v_min], [h_max, s_max, v_max]] per /calibrate
                    if (
                        isinstance(hsv_ranges, (list, tuple)) and len(hsv_ranges) == 2 and
                        isinstance(hsv_ranges[0], (list, tuple)) and len(hsv_ranges[0]) == 3 and
                        isinstance(hsv_ranges[1], (list, tuple)) and len(hsv_ranges[1]) == 3
                    ):
                        (h_min, s_min, v_min) = hsv_ranges[0]
                        (h_max, s_max, v_max) = hsv_ranges[1]
                        h = int((h_min + h_max) / 2)
                        s = int((s_min + s_max) / 2)
                        v = int((v_min + v_max) / 2)
                        # Convert HSV (OpenCV uses H:0-180, S:0-255, V:0-255) to BGR
                        hsv_pixel = np.uint8([[[h, s, v]]])
                        bgr_pixel = cv2.cvtColor(hsv_pixel, cv2.COLOR_HSV2BGR)[0][0]
                        position_colors[pos] = (int(bgr_pixel[0]), int(bgr_pixel[1]), int(bgr_pixel[2]))

        # Decide whether to generate overlay now or defer until after manual corrections
        unrecognized_count = len(unrecognized_cells)
        if unrecognized_count == 0:
            emit_all_outputs(results, rectified_image, cells, output_dir, position_colors=position_colors)
            overlay_ready = True
        else:
            # Write non-image outputs now; skip overlay for speed and to avoid stale view
            emit_all_outputs(results, None, None, output_dir, position_colors=position_colors)
            overlay_ready = False
        
        # Prepare results for frontend
        processed_results = []
        team_count = session_data.get('team_count', 10)
        for i, result in enumerate(results):
            if result and 'last' in result:
                row_val = result.get('row', 0)
                col_val = result.get('col', 0)
                pick_num = grid_to_draft_pick(row_val, col_val, cols=team_count)
                processed_results.append({
                    'pick': pick_num,
                    'row': row_val,
                    'col': col_val,
                    'player': result.get('full_name', ''),
                    'position': result.get('pos', ''),
                    'team': result.get('team', ''),
                    'bye': result.get('bye', 0),
                    'confidence': result.get('conf_last', 0),
                    'score_breakdown': result.get('score_breakdown', {})
                })
        
        # Store results and metadata in session
        session_data['full_results'] = results  # full list aligned to cells
        session_data['results'] = processed_results
        session_data['unrecognized_cells'] = unrecognized_cells
        session_data['cell_rois'] = [
            {
                'row': int(r), 'col': int(c), 'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)
            } for (r, c, x, y, w, h) in cells
        ]
        session_data['debug_ocr'] = debug_ocr
        session_data['overlay_ready'] = overlay_ready
        # Save rectified path for later overlay regeneration
        session_data['rectified_path'] = os.path.join(app.config['OUTPUT_FOLDER'], 'rectified.png')

        return jsonify({
            'success': True,
            'results': processed_results,
            'unrecognized_cells': unrecognized_cells,
            'total_cells': len(cells),
            'successful_matches': len(processed_results),
            'unrecognized_count': len(unrecognized_cells),
            'success_rate': f"{len(processed_results)/len(cells)*100:.1f}%",
            'colorProfiles': session_data.get('color_profiles', {}),
            'debug_ocr': debug_ocr,
            'cell_rois': session_data['cell_rois']
        })
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/download/<filetype>')
def download_results(filetype):
    """Download results in various formats"""
    if 'results' not in session_data:
        return jsonify({'error': 'No results available'}), 400
    
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], 'results')
    
    if filetype == 'csv':
        filepath = os.path.join(output_dir, 'board.csv')
        return send_file(filepath, as_attachment=True, download_name='draft_board_results.csv')
    
    elif filetype == 'json':
        filepath = os.path.join(output_dir, 'board.json')
        return send_file(filepath, as_attachment=True, download_name='draft_board_results.json')
    
    elif filetype == 'overlay':
        filepath = os.path.join(output_dir, 'overlay.png')
        return send_file(filepath, as_attachment=True, download_name='draft_board_overlay.png')
    
    else:
        return jsonify({'error': 'Invalid file type'}), 400

@app.route('/debug/overlay')
def debug_overlay():
    """Serve overlay image for debug view"""
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], 'results')
    filepath = os.path.join(output_dir, 'overlay.png')
    
    # If overlay isn't ready or file missing, try to generate on-demand
    if (not session_data.get('overlay_ready', False)) or (not os.path.exists(filepath)):
        try:
            rectified_path = session_data.get('rectified_path')
            rois = session_data.get('cell_rois', [])
            full_results = session_data.get('full_results')
            if rectified_path and os.path.exists(rectified_path) and rois and full_results:
                rectified_image = cv2.imread(rectified_path)
                cells = [(r['row'], r['col'], r['x'], r['y'], r['w'], r['h']) for r in rois]
                # Rebuild position colors if available
                position_colors = None
                if 'color_profiles' in session_data:
                    position_colors = {}
                    for pos, profile in session_data['color_profiles'].items():
                        rgb = profile.get('rgb')
                        if rgb and isinstance(rgb, (list, tuple)) and len(rgb) == 3:
                            position_colors[pos] = (int(rgb[2]), int(rgb[1]), int(rgb[0]))
                emit_all_outputs(full_results, rectified_image, cells, output_dir, position_colors=position_colors)
                session_data['overlay_ready'] = True
            else:
                return jsonify({'error': 'Overlay prerequisites not ready'}), 404
        except Exception as e:
            return jsonify({'error': f'Failed to build overlay: {str(e)}'}), 500

    return send_file(filepath, mimetype='image/png')

@app.route('/cell_image/<filename>')
def get_cell_image(filename):
    """Serve individual cell images for manual correction"""
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], 'results', 'cells')
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/png')
    else:
        return jsonify({'error': 'Cell image not found'}), 404

@app.route('/debug/cell_image/<int:row>/<int:col>/<mode>')
def debug_cell_image(row: int, col: int, mode: str):
    """Serve per-cell images for debug panel: raw or preprocessed."""
    try:
        rois = session_data.get('cell_rois', [])
        rectified_path = session_data.get('rectified_path')
        if not rois or not rectified_path or not os.path.exists(rectified_path):
            return jsonify({'error': 'No rectified image or ROIs available'}), 404

        # Find matching ROI
        roi = next((r for r in rois if int(r['row']) == row and int(r['col']) == col), None)
        if not roi:
            return jsonify({'error': 'Cell ROI not found'}), 404

        img = cv2.imread(rectified_path)
        if img is None:
            return jsonify({'error': 'Failed to load rectified image'}), 500

        x, y, w, h = int(roi['x']), int(roi['y']), int(roi['w']), int(roi['h'])
        cell_img = img[y:y+h, x:x+w]
        if cell_img is None or cell_img.size == 0:
            return jsonify({'error': 'Invalid cell crop'}), 500

        out_img = cell_img
        if mode.lower() == 'pre':
            try:
                from src.ocr_cell import neutral_otsu
                out_img = neutral_otsu(cell_img, invert=True, antimerge=False, return_bgr=True)
            except Exception as _:
                out_img = cell_img

        ok, buf = cv2.imencode('.png', out_img)
        if not ok:
            return jsonify({'error': 'Encoding failed'}), 500
        return send_file(io.BytesIO(buf.tobytes()), mimetype='image/png')
    except Exception as e:
        return jsonify({'error': f'Failed to produce cell image: {str(e)}'}), 500

@app.route('/player_names')
def get_player_names():
    """Get list of all player names for type-ahead filtering"""
    try:
        players = load_players("data/top500_playernames.csv")
        player_names = [f"{player.first} {player.last}".strip() for player in players]
        return jsonify({
            'success': True,
            'player_names': sorted(list(set(player_names)))  # Remove duplicates and sort
        })
    except Exception as e:
        return jsonify({'error': f'Failed to load player names: {str(e)}'}), 500

@app.route('/update_manual_correction', methods=['POST'])
def update_manual_correction():
    """Update results with manual corrections"""
    try:
        data = request.get_json()
        cell_index = data.get('cell_index')
        player_name = data.get('player_name')

        if 'results' not in session_data:
            return jsonify({'error': 'No results available'}), 400

        if cell_index is None or player_name is None:
            return jsonify({'error': 'Missing cell_index or player_name'}), 400

        # Find the player in the database
        players = load_players("data/top500_playernames.csv")
        selected_player = None
        for player in players:
            full_name = f"{player.first} {player.last}".strip()
            if full_name.lower() == player_name.lower():
                selected_player = player
                break

        if not selected_player:
            return jsonify({'error': 'Player not found in database'}), 400

        # Update session full_results aligned to cells
        from src.reconcile import grid_to_draft_pick
        full_results = session_data.get('full_results', [])
        rois = session_data.get('cell_rois', [])
        if 0 <= cell_index < len(rois):
            row = rois[cell_index]['row']
            col = rois[cell_index]['col']
            expected_pick = grid_to_draft_pick(row, col, cols=session_data.get('team_count', 10))

            full_results[cell_index] = {
                'row': row,
                'col': col,
                'full_name': selected_player.full,
                'first': selected_player.first,
                'last': selected_player.last,
                'team': selected_player.team,
                'pos': selected_player.pos,
                'bye': selected_player.bye,
                'is_dst': selected_player.is_dst,
                'match_score': 100.0,
                'use_match': True,
                'source_last': 'csv',
                'conf_last': 100.0,
                'expected_pick': expected_pick,
                'expected_rank': 0,
                'actual_pick': expected_pick,
                'position_diff': 0,
                'raw_ocr': session_data.get('debug_ocr', [{}])[cell_index] if cell_index < len(session_data.get('debug_ocr', [])) else {}
            }

            # Rebuild processed_results for table view from full_results
            processed_results = []
            team_count = session_data.get('team_count', 10)
            for r in full_results:
                if r and 'last' in r:
                    pick_num = grid_to_draft_pick(r.get('row', 0), r.get('col', 0), cols=team_count)
                    processed_results.append({
                        'pick': pick_num,
                        'row': r.get('row', 0),
                        'col': r.get('col', 0),
                        'player': r.get('full_name', ''),
                        'position': r.get('pos', ''),
                        'team': r.get('team', ''),
                        'bye': r.get('bye', 0),
                        'confidence': r.get('conf_last', 0),
                        'score_breakdown': r.get('score_breakdown', {})
                    })

            session_data['full_results'] = full_results
            session_data['results'] = processed_results

            # Remove from unrecognized cells if it exists
            unrecognized_cells = session_data.get('unrecognized_cells', [])
            session_data['unrecognized_cells'] = [
                cell for cell in unrecognized_cells if cell['index'] != cell_index
            ]

            # If no more unrecognized cells remain, regenerate overlay now
            if not session_data['unrecognized_cells']:
                try:
                    # Reconstruct outputs with overlay
                    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], 'results')
                    # Load rectified image from saved path
                    rectified_path = session_data.get('rectified_path')
                    rectified_image = None
                    if rectified_path and os.path.exists(rectified_path):
                        rectified_image = cv2.imread(rectified_path)
                    # Rebuild cells list from stored rois
                    rois = session_data.get('cell_rois', [])
                    cells = [(r['row'], r['col'], r['x'], r['y'], r['w'], r['h']) for r in rois]
                    # Re-use last known position colors (if any)
                    position_colors = None
                    if 'color_profiles' in session_data:
                        position_colors = {}
                        for pos, profile in session_data['color_profiles'].items():
                            rgb = profile.get('rgb')
                            if rgb and isinstance(rgb, (list, tuple)) and len(rgb) == 3:
                                position_colors[pos] = (int(rgb[2]), int(rgb[1]), int(rgb[0]))
                    # Use full_results if available to preserve cell alignment
                    full_results = session_data.get('full_results')
                    if rectified_image is not None and rois and full_results:
                        emit_all_outputs(full_results, rectified_image, cells, output_dir, position_colors=position_colors)
                        session_data['overlay_ready'] = True
                except Exception as _:
                    pass

            return jsonify({
                'success': True,
                'message': f'Updated cell {cell_index + 1} with {selected_player.full}',
                'overlay_ready': session_data.get('overlay_ready', False)
            })
        else:
            return jsonify({'error': 'Invalid cell index'}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to update manual correction: {str(e)}'}), 500

@app.route('/get_current_results')
def get_current_results():
    """Return the latest results and summary for display after manual corrections"""
    # Ensure keys exist to avoid KeyError
    results = session_data.get('results', [])
    unrecognized_cells = session_data.get('unrecognized_cells', [])

    total_cells = len(results) + len(unrecognized_cells)
    successful_matches = len(results)
    manual_corrections = sum(1 for r in results if r.get('confidence') == 100.0)
    success_rate = f"{(successful_matches / total_cells * 100):.1f}%" if total_cells else "0.0%"

    return jsonify({
        'success': True,
        'results': results,
        'total_cells': total_cells,
        'successful_matches': successful_matches,
        'manual_corrections': manual_corrections,
        'success_rate': success_rate
    })

@app.route('/progress')
def get_progress():
    """Get current processing progress"""
    progress = session_data.get('processing_progress', {
        'current': 0,
        'total': 0,
        'percentage': 0
    })
    return jsonify(progress)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
