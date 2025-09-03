import cv2
import numpy as np
import os
from typing import List, Tuple

def cells_from_rectified(img, rows=16, cols=10, output_dir="out"):
    """
    Split the rectified board into a grid of cells using precise integer
    boundaries so all pixels are covered without gaps or overlaps.
    
    Args:
        img: Rectified board image
        rows: Number of rows (default 16)
        cols: Number of columns (default 10)
        output_dir: Directory to save cell images
    
    Returns:
        List of cell ROIs: [(row, col, x, y, w, h), ...]
    """
    H, W = img.shape[:2]

    # Compute exact boundaries via rounding; covers full extent [0, H] and [0, W]
    row_bounds = [int(round(i * H / rows)) for i in range(rows + 1)]
    col_bounds = [int(round(i * W / cols)) for i in range(cols + 1)]

    # Enforce monotonicity and final bounds just in case of rounding artifacts
    row_bounds[0], row_bounds[-1] = 0, H
    col_bounds[0], col_bounds[-1] = 0, W

    cells = []
    cells_dir = os.path.join(output_dir, "cells")
    os.makedirs(cells_dir, exist_ok=True)

    for r in range(rows):
        y0, y1 = row_bounds[r], row_bounds[r + 1]
        h = max(0, y1 - y0)
        for c in range(cols):
            x0, x1 = col_bounds[c], col_bounds[c + 1]
            w = max(0, x1 - x0)

            # Crop the cell
            cell_img = img[y0:y1, x0:x1]

            # Save cell image for debugging
            cell_filename = f"r{r}_c{c}.png"
            cv2.imwrite(os.path.join(cells_dir, cell_filename), cell_img)

            cells.append((r, c, x0, y0, w, h))

    return cells

def find_grid_boundaries(img, rows=16, cols=10):
    """
    Find grid boundaries using projection profiles (refined approach).
    
    Args:
        img: Rectified board image
        rows: Number of rows
        cols: Number of columns
    
    Returns:
        Tuple of (row_boundaries, col_boundaries)
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply Sobel filters to find edges
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    
    # Calculate gradient magnitude
    gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
    
    # Project onto x and y axes
    vertical_projection = np.sum(gradient_magnitude, axis=0)
    horizontal_projection = np.sum(gradient_magnitude, axis=1)
    
    # Find peaks in projections (these correspond to grid lines)
    col_boundaries = find_peaks(vertical_projection, cols + 1)
    row_boundaries = find_peaks(horizontal_projection, rows + 1)
    
    return row_boundaries, col_boundaries

def find_peaks(projection, num_peaks):
    """
    Find the strongest peaks in a projection profile.
    
    Args:
        projection: 1D array of projection values
        num_peaks: Number of peaks to find
    
    Returns:
        List of peak positions
    """
    # Apply smoothing to reduce noise
    smoothed = np.convolve(projection, np.ones(5)/5, mode='same')
    
    # Find local maxima
    peaks = []
    for i in range(1, len(smoothed) - 1):
        if smoothed[i] > smoothed[i-1] and smoothed[i] > smoothed[i+1]:
            peaks.append((i, smoothed[i]))
    
    # Sort by peak strength and take the strongest
    peaks.sort(key=lambda x: x[1], reverse=True)
    
    # Take the top peaks and sort by position
    top_peaks = sorted([p[0] for p in peaks[:num_peaks]])
    
    return top_peaks

def cells_from_boundaries(img, row_boundaries, col_boundaries, output_dir="out"):
    """
    Create cells based on detected boundaries.
    
    Args:
        img: Rectified board image
        row_boundaries: List of row boundary positions
        col_boundaries: List of column boundary positions
        output_dir: Directory to save cell images
    
    Returns:
        List of cell ROIs: [(row, col, x, y, w, h), ...]
    """
    cells = []
    cells_dir = os.path.join(output_dir, "cells")
    os.makedirs(cells_dir, exist_ok=True)
    
    for r in range(len(row_boundaries) - 1):
        for c in range(len(col_boundaries) - 1):
            x = col_boundaries[c]
            y = row_boundaries[r]
            w = col_boundaries[c + 1] - x
            h = row_boundaries[r + 1] - y
            
            # Crop the cell
            cell_img = img[y:y+h, x:x+w]
            
            # Save cell image for debugging
            cell_filename = f"r{r}_c{c}.png"
            cv2.imwrite(os.path.join(cells_dir, cell_filename), cell_img)
            
            cells.append((r, c, x, y, w, h))
    
    return cells
