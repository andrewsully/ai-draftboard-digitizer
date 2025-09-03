import cv2
import numpy as np
import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
from pathlib import Path

@dataclass
class ColorProfile:
    """Color profile for a position group."""
    position: str
    hsv_ranges: List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]
    confidence: float = 1.0

class ManualColorCalibrator:
    """Manual color calibration using example images."""
    
    def __init__(self, examples_dir: str = "data/positional_color_examples"):
        self.examples_dir = examples_dir
        self.profiles = {}
        self.color_samples = {}
    
    def analyze_example_images(self):
        """Deprecated: UI now provides color profiles directly. No-op for compatibility."""
        print("[manual_color_calibration] analyze_example_images is deprecated and ignored (using UI-provided profiles).")
        return self.profiles
    
    def _analyze_position_image(self, position: str, image_path: str):
        """Analyze a single position example image."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Could not load {image_path}")
            return
        
        # Convert to HSV
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Extract all HSV values
        hsv_values = []
        for y in range(hsv_image.shape[0]):
            for x in range(hsv_image.shape[1]):
                h, s, v = hsv_image[y, x]
                # Filter out very dark or very light pixels (likely background)
                if v > 30 and v < 250 and s > 20:
                    hsv_values.append((h, s, v))
        
        if not hsv_values:
            print(f"No valid color samples found in {image_path}")
            return
        
        # Calculate statistics
        h_values = [h for h, s, v in hsv_values]
        s_values = [s for h, s, v in hsv_values]
        v_values = [v for h, s, v in hsv_values]
        
        # Calculate ranges with percentiles to handle outliers
        h_min, h_max = np.percentile(h_values, [5, 95])
        s_min, s_max = np.percentile(s_values, [5, 95])
        v_min, v_max = np.percentile(v_values, [5, 95])
        
        # Add data-driven tolerance (agnostic to which position uses which color)
        # Expand ranges proportionally to observed spread with sensible floors.
        h_spread = max(1, int(h_max - h_min))
        s_spread = max(1, int(s_max - s_min))
        v_spread = max(1, int(v_max - v_min))

        # Proportional pads (percent of spread) with minimum absolute pads
        h_pad = max(8, int(0.20 * h_spread))   # hue range 0-180
        s_pad = max(20, int(0.20 * s_spread))  # saturation 0-255
        v_pad = max(20, int(0.20 * v_spread))  # value 0-255

        h_min = max(0, int(h_min - h_pad))
        h_max = min(180, int(h_max + h_pad))
        s_min = max(0, int(s_min - s_pad))
        s_max = min(255, int(s_max + s_pad))
        v_min = max(0, int(v_min - v_pad))
        v_max = min(255, int(v_max + v_pad))
        
        # Store the profile
        self.profiles[position] = ColorProfile(
            position=position,
            hsv_ranges=[((h_min, s_min, v_min), (h_max, s_max, v_max))]
        )
        
        # Store samples for visualization
        self.color_samples[position] = hsv_values
        
        print(f"  {position} color range:")
        print(f"    Hue: {h_min}-{h_max}")
        print(f"    Saturation: {s_min}-{s_max}")
        print(f"    Value: {v_min}-{v_max}")
        print(f"    Sample count: {len(hsv_values)}")
    
    def detect_position_from_color(self, hsv: Tuple[float, float, float]) -> Tuple[str, float]:
        """
        Detect position from HSV color using calibrated profiles.
        
        Args:
            hsv: HSV color values (H, S, V)
        
        Returns:
            Tuple of (position, confidence)
        """
        h, s, v = hsv
        best_match = None
        best_confidence = 0.0
        
        for pos, profile in self.profiles.items():
            for lower, upper in profile.hsv_ranges:
                # Check if color falls within this range
                if self._color_in_range(hsv, lower, upper):
                    confidence = self._calculate_confidence(hsv, lower, upper) * profile.confidence
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = pos
        
        return best_match, best_confidence
    
    def _color_in_range(self, hsv: Tuple[float, float, float], 
                       lower: Tuple[int, int, int], 
                       upper: Tuple[int, int, int]) -> bool:
        """Check if HSV color is within the given range."""
        h, s, v = hsv
        lh, ls, lv = lower
        uh, us, uv = upper
        
        # Handle hue wrap-around (red spans 0-10 and 170-180)
        if lh > uh:  # Wrap-around case
            h_in_range = (h >= lh) or (h <= uh)
        else:
            h_in_range = lh <= h <= uh
        
        return h_in_range and ls <= s <= us and lv <= v <= uv
    
    def _calculate_confidence(self, hsv: Tuple[float, float, float], 
                            lower: Tuple[int, int, int], 
                            upper: Tuple[int, int, int]) -> float:
        """Calculate confidence based on how well the color fits the range."""
        h, s, v = hsv
        lh, ls, lv = lower
        uh, us, uv = upper
        
        # Calculate distance from center of range
        h_center = (lh + uh) / 2
        s_center = (ls + us) / 2
        v_center = (lv + uv) / 2
        
        # Handle hue wrap-around
        if lh > uh:
            h_center = ((lh + uh + 180) % 360) / 2
        
        h_dist = min(abs(h - h_center), abs(h - h_center + 180), abs(h - h_center - 180))
        s_dist = abs(s - s_center)
        v_dist = abs(v - v_center)
        
        # Normalize distances
        h_norm = h_dist / 90.0  # Max hue distance
        s_norm = s_dist / 255.0  # Max saturation distance
        v_norm = v_dist / 255.0  # Max value distance
        
        # Calculate confidence (higher = better fit)
        confidence = 1.0 - (h_norm + s_norm + v_norm) / 3.0
        return max(0.0, confidence)
    
    def save_profiles(self, output_file: str = "manual_color_profiles.json"):
        """Save the calibrated profiles to a file."""
        data = {}
        for pos, profile in self.profiles.items():
            data[pos] = {
                'hsv_ranges': profile.hsv_ranges,
                'confidence': profile.confidence
            }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved manual color profiles to {output_file}")
    
    def visualize_color_spectrum(self, output_file: str = "position_color_spectrum.png"):
        """Create a visualization of the color spectrum for each position."""
        if not self.color_samples:
            print("No color samples to visualize")
            return
        
        # Create figure with subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Color mapping for positions
        position_colors = {
            'QB': 'orange',
            'RB': 'brown', 
            'WR': 'blue',
            'TE': 'red',
            'K': 'gray',
            'DST': 'green'
        }
        
        # Plot 1: Hue distribution
        ax1.set_title('Hue Distribution by Position')
        ax1.set_xlabel('Hue (0-180)')
        ax1.set_ylabel('Frequency')
        
        for position, samples in self.color_samples.items():
            h_values = [h for h, s, v in samples]
            ax1.hist(h_values, bins=30, alpha=0.7, label=position, 
                    color=position_colors.get(position, 'black'))
        
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Saturation vs Value
        ax2.set_title('Saturation vs Value by Position')
        ax2.set_xlabel('Saturation')
        ax2.set_ylabel('Value')
        
        for position, samples in self.color_samples.items():
            s_values = [s for h, s, v in samples]
            v_values = [v for h, s, v in samples]
            ax2.scatter(s_values, v_values, alpha=0.6, label=position,
                       color=position_colors.get(position, 'black'), s=10)
        
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Hue vs Saturation
        ax3.set_title('Hue vs Saturation by Position')
        ax3.set_xlabel('Hue')
        ax3.set_ylabel('Saturation')
        
        for position, samples in self.color_samples.items():
            h_values = [h for h, s, v in samples]
            s_values = [s for h, s, v in samples]
            ax3.scatter(h_values, s_values, alpha=0.6, label=position,
                       color=position_colors.get(position, 'black'), s=10)
        
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Color ranges summary
        ax4.set_title('Color Ranges Summary')
        ax4.set_xlabel('Position')
        ax4.set_ylabel('Hue Range')
        
        positions = list(self.profiles.keys())
        hue_ranges = []
        hue_centers = []
        
        for pos in positions:
            if pos in self.profiles:
                profile = self.profiles[pos]
                for lower, upper in profile.hsv_ranges:
                    h_min, h_max = lower[0], upper[0]
                    hue_ranges.append((h_min, h_max))
                    hue_centers.append((h_min + h_max) / 2)
        
        # Create horizontal bars showing hue ranges
        y_pos = range(len(positions))
        for i, pos in enumerate(positions):
            if i < len(hue_ranges):
                h_min, h_max = hue_ranges[i]
                ax4.barh(i, h_max - h_min, left=h_min, 
                        color=position_colors.get(pos, 'gray'), alpha=0.7)
                ax4.text(hue_centers[i], i, pos, ha='center', va='center', fontweight='bold')
        
        ax4.set_yticks(y_pos)
        ax4.set_yticklabels(positions)
        ax4.set_xlim(0, 180)
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Color spectrum visualization saved to {output_file}")
        
        # Print summary
        print("\nColor Range Summary:")
        print("=" * 50)
        for pos in positions:
            if pos in self.profiles:
                profile = self.profiles[pos]
                for lower, upper in profile.hsv_ranges:
                    h_min, h_max = lower[0], upper[0]
                    print(f"{pos:3s}: Hue {h_min:3d}-{h_max:3d} ({h_max-h_min:3d} range)")

def calibrate_from_examples():
    """Main function to calibrate colors from example images."""
    calibrator = ManualColorCalibrator()
    
    # Analyze example images
    profiles = calibrator.analyze_example_images()
    
    # Save profiles
    calibrator.save_profiles()
    
    # Create visualization (disabled)
    # calibrator.visualize_color_spectrum()
    
    return calibrator

if __name__ == "__main__":
    calibrate_from_examples()
