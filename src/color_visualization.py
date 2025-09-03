import cv2
import numpy as np
import os
from typing import List, Tuple, Dict
from manual_color_calibration import ManualColorCalibrator
from preprocess import normalize_board
from grid import cells_from_rectified
from ocr_cell import mean_hsv

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
    k = 3
    _, labels, centers = cv2.kmeans(
        pixels, k, None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0),
        10, cv2.KMEANS_RANDOM_CENTERS
    )
    
    # Choose the cluster with the most members
    counts = np.bincount(labels.flatten())
    dominant = centers[np.argmax(counts)]
    
    return tuple(map(float, dominant))

class ColorVisualizer:
    """Visualize color-based position predictions on the draft board."""
    
    def __init__(self):
        self.calibrator = ManualColorCalibrator()
        self.calibrator.analyze_example_images()
        
        # Color mapping for visualization
        self.position_colors = {
            'QB': (0, 165, 255),    # Orange in BGR
            'RB': (0, 0, 255),      # Red in BGR
            'WR': (255, 0, 0),      # Blue in BGR
            'TE': (255, 0, 255),    # Magenta in BGR
            'K': (128, 128, 128),   # Gray in BGR
            'DST': (0, 255, 0),     # Green in BGR
        }
    
    def create_position_overlay(self, image_path: str, output_path: str = "color_position_overlay.png"):
        """Create an overlay showing predicted positions for each cell."""
        print("Creating color position overlay...")
        
        # Load and preprocess image
        rectified_image = normalize_board(image_path, "color_viz_out")
        cells = cells_from_rectified(rectified_image, output_dir="color_viz_out")
        
        # Create a copy for visualization
        overlay_image = rectified_image.copy()
        
        # Process each cell
        position_counts = {}
        cell_predictions = []
        
        for i, (row, col, x, y, w, h) in enumerate(cells):
            cell_img = rectified_image[y:y+h, x:x+w]
            
            # Use dominant non-white color instead of fixed corner sampling
            hsv = dominant_nonwhite_hsv(cell_img)
            
            # Predict position
            predicted_pos, confidence = self.calibrator.detect_position_from_color(hsv)
            
            # Store prediction
            cell_predictions.append({
                'cell_id': i,
                'row': row,
                'col': col,
                'x': x,
                'y': y,
                'w': w,
                'h': h,
                'predicted_position': predicted_pos,
                'confidence': confidence,
                'hsv': hsv
            })
            
            # Count positions
            if predicted_pos:
                position_counts[predicted_pos] = position_counts.get(predicted_pos, 0) + 1
            
            # Draw on overlay
            self._draw_cell_prediction(overlay_image, x, y, w, h, predicted_pos, confidence, i)
        
        # Save the overlay
        cv2.imwrite(output_path, overlay_image)
        print(f"Color position overlay saved to: {output_path}")
        
        # Print summary
        print(f"\nPosition Distribution:")
        for pos, count in sorted(position_counts.items()):
            print(f"  {pos}: {count} cells")
        
        return cell_predictions, overlay_image
    
    def _draw_cell_prediction(self, image, x, y, w, h, position, confidence, cell_id):
        """Draw position prediction on a cell."""
        if not position:
            # No prediction - draw gray border
            cv2.rectangle(image, (x, y), (x + w, y + h), (128, 128, 128), 2)
            cv2.putText(image, f"None", (x + 5, y + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
            return
        
        # Get color for position
        color = self.position_colors.get(position, (255, 255, 255))
        
        # Draw colored border
        border_thickness = max(1, int(confidence * 3))  # Thicker border for higher confidence
        cv2.rectangle(image, (x, y), (x + w, y + h), color, border_thickness)
        
        # Draw position label
        label = f"{position}"
        if confidence < 0.7:
            label += "?"
        
        # Calculate text position (top-left of cell)
        text_x = x + 5
        text_y = y + 20
        
        # Draw background for text
        (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(image, (text_x - 2, text_y - text_height - 2), 
                     (text_x + text_width + 2, text_y + 2), (0, 0, 0), -1)
        
        # Draw text
        cv2.putText(image, label, (text_x, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Draw confidence score (smaller, bottom-right)
        conf_text = f"{confidence:.1f}"
        conf_x = x + w - 30
        conf_y = y + h - 5
        
        cv2.putText(image, conf_text, (conf_x, conf_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    def create_detailed_analysis(self, image_path: str, output_dir: str = "color_analysis_detailed"):
        """Create detailed analysis with individual cell images and predictions."""
        print("Creating detailed color analysis...")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Get predictions
        cell_predictions, overlay_image = self.create_position_overlay(
            image_path, os.path.join(output_dir, "overlay.png")
        )
        
        # Create summary report
        self._create_summary_report(cell_predictions, output_dir)
        
        # Create individual cell images with predictions
        self._create_cell_images(image_path, cell_predictions, output_dir)
        
        print(f"Detailed analysis saved to: {output_dir}/")
    
    def _create_summary_report(self, cell_predictions, output_dir):
        """Create a text summary of all predictions."""
        report_path = os.path.join(output_dir, "color_predictions_report.txt")
        
        with open(report_path, 'w') as f:
            f.write("Color-Based Position Predictions Report\n")
            f.write("=" * 50 + "\n\n")
            
            # Summary statistics
            position_counts = {}
            confidence_ranges = {'high': 0, 'medium': 0, 'low': 0, 'none': 0}
            
            for pred in cell_predictions:
                pos = pred['predicted_position']
                conf = pred['confidence']
                
                if pos:
                    position_counts[pos] = position_counts.get(pos, 0) + 1
                    
                    if conf > 0.8:
                        confidence_ranges['high'] += 1
                    elif conf > 0.6:
                        confidence_ranges['medium'] += 1
                    else:
                        confidence_ranges['low'] += 1
                else:
                    confidence_ranges['none'] += 1
            
            f.write("Position Distribution:\n")
            for pos, count in sorted(position_counts.items()):
                f.write(f"  {pos}: {count} cells\n")
            
            f.write(f"\nConfidence Distribution:\n")
            f.write(f"  High (>0.8): {confidence_ranges['high']} cells\n")
            f.write(f"  Medium (0.6-0.8): {confidence_ranges['medium']} cells\n")
            f.write(f"  Low (<0.6): {confidence_ranges['low']} cells\n")
            f.write(f"  No prediction: {confidence_ranges['none']} cells\n")
            
            f.write(f"\nDetailed Cell Predictions:\n")
            f.write("-" * 50 + "\n")
            
            for pred in cell_predictions:
                f.write(f"Cell {pred['cell_id']:3d} (R{pred['row']}, C{pred['col']}): ")
                if pred['predicted_position']:
                    f.write(f"{pred['predicted_position']} (conf: {pred['confidence']:.2f})")
                else:
                    f.write("No prediction")
                f.write(f" [HSV: {pred['hsv']}]\n")
    
    def _create_cell_images(self, image_path, cell_predictions, output_dir):
        """Create individual cell images with predictions."""
        rectified_image = normalize_board(image_path, "temp")
        
        for pred in cell_predictions[:20]:  # Limit to first 20 for space
            x, y, w, h = pred['x'], pred['y'], pred['w'], pred['h']
            cell_img = rectified_image[y:y+h, x:x+w]
            
            # Add prediction info to cell image
            position = pred['predicted_position']
            confidence = pred['confidence']
            
            # Create labeled image
            labeled_img = cell_img.copy()
            
            if position:
                color = self.position_colors.get(position, (255, 255, 255))
                cv2.rectangle(labeled_img, (0, 0), (w, h), color, 3)
                
                # Add text
                label = f"{position} ({confidence:.2f})"
                cv2.putText(labeled_img, label, (5, 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            else:
                cv2.rectangle(labeled_img, (0, 0), (w, h), (128, 128, 128), 3)
                cv2.putText(labeled_img, "None", (5, 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 2)
            
            # Save cell image
            cell_filename = f"cell_{pred['cell_id']:03d}_R{pred['row']}_C{pred['col']}_{position or 'None'}.png"
            cv2.imwrite(os.path.join(output_dir, cell_filename), labeled_img)

def visualize_color_predictions(image_path: str = "data/draftboard.png"):
    """Main function to create color prediction visualizations."""
    visualizer = ColorVisualizer()
    
    # Create overlay
    cell_predictions, overlay_image = visualizer.create_position_overlay(image_path)
    
    # Create detailed analysis
    visualizer.create_detailed_analysis(image_path)
    
    return cell_predictions, overlay_image

if __name__ == "__main__":
    visualize_color_predictions()
