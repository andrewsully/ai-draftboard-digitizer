import cv2
import numpy as np
import os

def normalize_board(image_path, output_dir="out"):
    """
    Normalize the draft board: apply basic enhancement since image is already well-cropped.
    
    Args:
        image_path: Path to the input draft board image
        output_dir: Directory to save output files
    
    Returns:
        enhanced_image: The enhanced board image (no perspective correction needed)
    """
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image from {image_path}")
    
    print(f"Original image shape: {img.shape}")
    
    # Since the image is already well-cropped, just apply basic enhancement
    # Convert to HSV and enhance contrast
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Apply CLAHE to V channel for better contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    hsv[:,:,2] = clahe.apply(hsv[:,:,2])
    
    # Convert back to BGR
    enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    # Apply bilateral denoising
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
    
    # Save enhanced image for debugging
    os.makedirs(output_dir, exist_ok=True)
    cv2.imwrite(os.path.join(output_dir, "rectified.png"), denoised)
    
    print(f"Enhanced image saved to {output_dir}/rectified.png")
    print("Note: No perspective correction applied - image was already well-cropped")
    
    return denoised

def enhance_for_ocr(image):
    """
    Enhance image for better OCR results.
    
    Args:
        image: Input image (BGR)
    
    Returns:
        enhanced_image: Enhanced image for OCR
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply bilateral filter to reduce noise while preserving edges
    filtered = cv2.bilateralFilter(gray, 5, 75, 75)
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Morphological operations to clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
    
    return cleaned
