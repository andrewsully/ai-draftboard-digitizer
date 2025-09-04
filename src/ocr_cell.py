import cv2
import numpy as np
import pytesseract
import re
import os
from typing import Dict, Tuple, Optional

def neutral_otsu(img_bgr: np.ndarray, *, invert: bool = True, antimerge: bool = False, return_bgr: bool = False) -> np.ndarray:
    """
    Same-size, ROI-agnostic OCR enhancer:
      BGR→gray → CLAHE(2.2,8x8) → blur(3x3) → unsharp(1.3,-0.3) → Otsu(threshold, invert)
      → open(2x2,1) → optional erosion(2x2,1).
    No resizing. Designed to make white-on-color text become solid black on white for OCR.
    """
    h, w = img_bgr.shape[:2]

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(20, 20))
    norm = clahe.apply(gray)
    blurred = cv2.GaussianBlur(norm, (3, 3), 0)
    sharp = cv2.addWeighted(norm, 1.3, blurred, -0.3, 0)

    thresh_flag = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    _, binary = cv2.threshold(sharp, 0, 255, thresh_flag | cv2.THRESH_OTSU)

    k = np.ones((2, 2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, k, iterations=1)

    if antimerge:
        binary = cv2.erode(binary, k, iterations=1)  # gently separate touching glyphs

    assert binary.shape[:2] == (h, w), "Size changed unexpectedly"

    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR) if return_bgr else binary

def ocr(img, psm=7, whitelist=None):
    """
    Perform OCR on an image.
    
    Args:
        img: Input image
        psm: Page segmentation mode
        whitelist: Allowed characters
    
    Returns:
        OCR text result
    """
    cfg = f'--psm {psm}'
    if whitelist:
        cfg += f' -c tessedit_char_whitelist="{whitelist}"'
    return pytesseract.image_to_string(img, config=cfg).strip()

def mean_hsv(img, rect):
    """
    Calculate mean HSV values for a region.
    
    Args:
        img: Input image (BGR)
        rect: Rectangle (x, y, w, h)
    
    Returns:
        Mean HSV values (H, S, V)
    """
    x, y, w, h = rect
    hsv = cv2.cvtColor(img[y:y+h, x:x+w], cv2.COLOR_BGR2HSV)
    return hsv.reshape(-1, 3).mean(axis=0)  # H,S,V floats

def dominant_nonwhite_hsv(cell_img, white_thresh: int = 200):
    """
    Get the dominant non-white HSV color from a card image.
    - Converts to HSV
    - Masks out near-white pixels (high V, low S)
    - Finds most common remaining color
    """
    hsv = cv2.cvtColor(cell_img, cv2.COLOR_BGR2HSV)
    
    # Mask out near-white pixels (Saturation low or Value very high)
    nonwhite_mask = ~((hsv[:,:,1] < 40) & (hsv[:,:,2] > white_thresh))
    
    # Flatten HSV pixels that are non-white
    pixels = hsv[nonwhite_mask]
    if len(pixels) == 0:
        return (0, 0, 0)  # fallback if card is all white
    
    # Cluster with k-means to find dominant background
    pixels = np.float32(pixels)
    k = 2  # Reduced from 3 - simpler clustering for clearer dominant color
    _, labels, centers = cv2.kmeans(
        pixels, k, None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0),
        10, cv2.KMEANS_RANDOM_CENTERS
    )
    
    # Choose the cluster with the most members
    counts = np.bincount(labels.flatten())
    dominant = centers[np.argmax(counts)]
    
    return tuple(map(float, dominant))

# Global calibrator instance to avoid re-analyzing images
_calibrator_instance = None

def pos_from_color(hsv):
    """
    Map HSV color to position using manual color profiles.
    
    Args:
        hsv: HSV values (H, S, V)
    
    Returns:
        Position string or None
    """
    global _calibrator_instance
    
    try:
        from .manual_color_calibration import ManualColorCalibrator
        
        # Use cached calibrator instance
        if _calibrator_instance is None:
            _calibrator_instance = ManualColorCalibrator()
            # Deprecated: example-image analysis removed. Profiles are provided by UI/web flow.
        
        position, confidence = _calibrator_instance.detect_position_from_color(hsv)
        return position if confidence > 0.3 else None  # Lowered from 0.5
    except ImportError:
        # Fallback to original method if manual calibration module not available
        h, s, v = hsv
        
        # QB = orange
        if s > 60 and 15 <= h <= 25:
            return "QB"
        
        # TE = red
        if s > 60 and 0 <= h <= 10:
            return "TE"
        
        # WR = blue
        if s > 60 and 95 <= h <= 130:
            return "WR"
        
        # RB = brown-ish
        if s > 40 and 10 < h < 20 and v < 150:
            return "RB"
        
        # K = grey
        if s < 35 and v < 180:
            return "K"
        
        # DST = green
        if s > 50 and 40 <= h <= 80:
            return "DST"
        
        return None

def read_cell(cell_img):
    """
    Read a single cell/sticker with ROI strategy.
    
    Args:
        cell_img: Cell image
    
    Returns:
        Dictionary with OCR results and color-based position
    """
    H, W = cell_img.shape[:2]
    
    # Define ROI dimensions
    top_h = int(0.25 * H)
    bot_h = int(0.25 * H)
    side_w = int(0.35 * W)
    
    # Define ROIs: (x, y, w, h)
    rois = {
        'pos': (0, 0, side_w, top_h),
        'bye': (W - side_w, 0, side_w, top_h),
        'lastname': (int(0.10 * W), int(0.30 * H), int(0.80 * W), int(0.40 * H)),
        'team': (0, H - bot_h, side_w, bot_h),
        'firstname': (W - side_w, H - bot_h, side_w, bot_h),
    }
    
    def crop(roi):
        x, y, w, h = roi
        return cell_img[y:y+h, x:x+w]
    
    # Standard pipeline with neutral Otsu per-ROI
    pos_text = ocr(neutral_otsu(crop(rois['pos']), invert=True, antimerge=False, return_bgr=False), psm=7, whitelist="QBWRTEDSTK")
    bye_text = ocr(neutral_otsu(crop(rois['bye']), invert=True, antimerge=False, return_bgr=False), psm=7, whitelist="BYE 0123456789")
    last_text = ocr(neutral_otsu(crop(rois['lastname']), invert=True, antimerge=False, return_bgr=False), psm=7)
    team_text = ocr(neutral_otsu(crop(rois['team']), invert=True, antimerge=False, return_bgr=False), psm=7)
    first_text = ocr(neutral_otsu(crop(rois['firstname']), invert=True, antimerge=False, return_bgr=False), psm=7)
    
    # Extract bye digits
    bye_digits = None
    m = re.search(r'(\d{1,2})', bye_text.replace(" ", ""))
    if m:
        bye_digits = int(m.group(1))
    
    # Get color-based position from dominant non-white color
    hsv_pos = dominant_nonwhite_hsv(cell_img)
    color_pos = pos_from_color(hsv_pos)
    
    return {
        'ocr_pos': pos_text,
        'color_pos': color_pos,
        'ocr_bye': bye_digits,
        'ocr_last': last_text,
        'ocr_team': team_text,
        'ocr_first': first_text
    }

def read_cell_whole(cell_img: np.ndarray) -> Dict:
    """
    Whole-cell OCR approach: run OCR once on entire preprocessed cell
    and parse expected fields from the combined text/tokens.
    Color/HSV should be computed on the original image outside this function.
    """
    # Preprocess for OCR
    cell_ocr = neutral_otsu(cell_img, invert=True, antimerge=False, return_bgr=False)

    # Use Tesseract to get tokens with confidences
    try:
        from pytesseract import Output
        data = pytesseract.image_to_data(cell_ocr, config='--psm 6', output_type=Output.DICT)
        texts = [t.strip() for t in data.get('text', []) if t and t.strip()]
    except Exception:
        # Fallback to simple OCR if detailed data not available
        texts = [ocr(cell_ocr, psm=6)]

    all_text = " ".join(texts)

    # Parse BYE
    bye_digits = None
    m = re.search(r"\bBYE\s*(\d{1,2})\b", all_text.upper())
    if not m:
        # Try token-wise pairing
        upper_tokens = [t.upper() for t in texts]
        for i, t in enumerate(upper_tokens):
            if t == 'BYE' and i + 1 < len(upper_tokens):
                if upper_tokens[i+1].isdigit():
                    bye_digits = int(upper_tokens[i+1])
                    break
    else:
        bye_digits = int(m.group(1))

    # Parse position
    positions = {'QB', 'RB', 'WR', 'TE', 'K', 'DST'}
    ocr_pos = None
    for t in texts:
        tu = re.sub(r'[^A-Z]', '', t.upper())
        if tu in positions:
            ocr_pos = tu
            break

    # Parse team (try tokens against normalize_team)
    ocr_team = None
    for t in texts:
        cand = normalize_team(t)
        if cand is not None and len(cand) <= 3:  # likely an abbreviation
            ocr_team = cand
            break

    # Parse name candidates: pick a likely last name as the longest alpha token not in stopwords
    stopwords = positions.union({'BYE'})
    team_abbrevs = {
        'BAL','BUF','CIN','CLE','DEN','HOU','IND','JAX','KC','LV','LAC','MIA','NE','NYJ','PIT','TEN',
        'ARI','ATL','CAR','CHI','DAL','DET','GB','MIN','NO','NYG','PHI','SF','SEA','TB','WAS','FA'
    }
    stopwords = stopwords.union(team_abbrevs)

    alpha_tokens = []
    for t in texts:
        word = re.sub(r'[^A-Z]', '', t.upper())
        if len(word) >= 2 and word not in stopwords:
            alpha_tokens.append(word)

    ocr_last = ''
    ocr_first = ''
    if alpha_tokens:
        # Choose the longest token as last name candidate
        alpha_tokens.sort(key=lambda s: len(s), reverse=True)
        ocr_last = alpha_tokens[0]
        # Optionally choose another token as first name if available and different
        for w in alpha_tokens[1:]:
            if w != ocr_last:
                ocr_first = w
                break

    return {
        'ocr_pos': ocr_pos,
        'ocr_bye': bye_digits,
        'ocr_last': ocr_last,
        'ocr_team': ocr_team,
        'ocr_first': ocr_first
    }

def normalize_team(team_text):
    """
    Normalize team text to standard abbreviations.
    
    Args:
        team_text: Raw team text from OCR
    
    Returns:
        Normalized team abbreviation
    """
    if not team_text:
        return None
    
    # Common team name mappings
    team_mappings = {
        'BALTIMORE': 'BAL', 'RAVENS': 'BAL',
        'BUFFALO': 'BUF', 'BILLS': 'BUF',
        'CINCINNATI': 'CIN', 'BENGALS': 'CIN',
        'CLEVELAND': 'CLE', 'BROWNS': 'CLE',
        'DENVER': 'DEN', 'BRONCOS': 'DEN',
        'HOUSTON': 'HOU', 'TEXANS': 'HOU',
        'INDIANAPOLIS': 'IND', 'COLTS': 'IND',
        'JACKSONVILLE': 'JAX', 'JAGUARS': 'JAX',
        'KANSAS CITY': 'KC', 'CHIEFS': 'KC',
        'LAS VEGAS': 'LV', 'RAIDERS': 'LV',
        'LOS ANGELES': 'LAC', 'CHARGERS': 'LAC',
        'MIAMI': 'MIA', 'DOLPHINS': 'MIA',
        'NEW ENGLAND': 'NE', 'PATRIOTS': 'NE',
        'NEW YORK': 'NYJ', 'JETS': 'NYJ',
        'PITTSBURGH': 'PIT', 'STEELERS': 'PIT',
        'TENNESSEE': 'TEN', 'TITANS': 'TEN',
        'ARIZONA': 'ARI', 'CARDINALS': 'ARI',
        'ATLANTA': 'ATL', 'FALCONS': 'ATL',
        'CAROLINA': 'CAR', 'PANTHERS': 'CAR',
        'CHICAGO': 'CHI', 'BEARS': 'CHI',
        'DALLAS': 'DAL', 'COWBOYS': 'DAL',
        'DETROIT': 'DET', 'LIONS': 'DET',
        'GREEN BAY': 'GB', 'PACKERS': 'GB',
        'MINNESOTA': 'MIN', 'VIKINGS': 'MIN',
        'NEW ORLEANS': 'NO', 'SAINTS': 'NO',
        'NEW YORK GIANTS': 'NYG', 'GIANTS': 'NYG',
        'PHILADELPHIA': 'PHI', 'EAGLES': 'PHI',
        'SAN FRANCISCO': 'SF', '49ERS': 'SF',
        'SEATTLE': 'SEA', 'SEAHAWKS': 'SEA',
        'TAMPA BAY': 'TB', 'BUCCANEERS': 'TB',
        'WASHINGTON': 'WAS', 'COMMANDERS': 'WAS',
        'FREE AGENT': 'FA', 'FA': 'FA'
    }
    
    # Try exact match first
    team_upper = team_text.upper().strip()
    if team_upper in team_mappings:
        return team_mappings[team_upper]
    
    # Try partial matches
    for key, value in team_mappings.items():
        if key in team_upper or team_upper in key:
            return value
    
    # If no match found, return the original text (might be a valid abbreviation)
    return team_upper if len(team_upper) <= 3 else None

def clean_pos_text(pos_text):
    """
    Clean position text from OCR.
    
    Args:
        pos_text: Raw position text from OCR
    
    Returns:
        Cleaned position text
    """
    if not pos_text:
        return None
    
    # Remove common OCR errors
    pos_clean = pos_text.upper().strip()
    pos_clean = re.sub(r'[^A-Z]', '', pos_clean)
    
    # Valid positions
    valid_positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
    
    if pos_clean in valid_positions:
        return pos_clean
    
    return None
