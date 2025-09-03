import cv2
import numpy as np
import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ColorProfile:
    """Color profile for a position group."""
    position: str
    hsv_ranges: List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]  # List of (lower, upper) HSV ranges
    confidence: float = 1.0

class ColorCalibrator:
    """Color calibration system for position detection."""
    
    def __init__(self, calibration_file: str = "color_profiles.json"):
        self.calibration_file = calibration_file
        self.profiles = self._load_default_profiles()
        self._load_calibration()
    
    def _load_default_profiles(self) -> Dict[str, ColorProfile]:
        """Load default color profiles."""
        return {
            "QB": ColorProfile("QB", [
                ((10, 100, 100), (25, 255, 255)),  # Orange
                ((0, 100, 100), (10, 255, 255))    # Red-orange
            ]),
            "RB": ColorProfile("RB", [
                ((0, 50, 50), (20, 255, 200)),     # Brown/red-brown
                ((10, 50, 50), (25, 255, 200))     # Orange-brown
            ]),
            "WR": ColorProfile("WR", [
                ((100, 100, 100), (130, 255, 255)), # Blue
                ((110, 100, 100), (140, 255, 255))  # Blue-green
            ]),
            "TE": ColorProfile("TE", [
                ((0, 100, 100), (10, 255, 255)),    # Red
                ((170, 100, 100), (180, 255, 255))  # Red (wrap-around)
            ]),
            "K": ColorProfile("K", [
                ((0, 0, 100), (180, 50, 200)),      # Grey/white
                ((0, 0, 50), (180, 30, 150))        # Dark grey
            ]),
            "DST": ColorProfile("DST", [
                ((35, 100, 100), (85, 255, 255)),   # Green
                ((40, 100, 100), (80, 255, 255))    # Green-blue
            ])
        }
    
    def _load_calibration(self):
        """Load calibrated color profiles from file."""
        if os.path.exists(self.calibration_file):
            try:
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)
                    for pos, profile_data in data.items():
                        if pos in self.profiles:
                            self.profiles[pos].hsv_ranges = profile_data['hsv_ranges']
                            self.profiles[pos].confidence = profile_data.get('confidence', 1.0)
                print(f"Loaded calibrated color profiles from {self.calibration_file}")
            except Exception as e:
                print(f"Error loading calibration: {e}")
    
    def save_calibration(self):
        """Save calibrated color profiles to file."""
        data = {}
        for pos, profile in self.profiles.items():
            data[pos] = {
                'hsv_ranges': profile.hsv_ranges,
                'confidence': profile.confidence
            }
        
        with open(self.calibration_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved calibrated color profiles to {self.calibration_file}")
    
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
    
    def calibrate_from_samples(self, samples: Dict[str, List[Tuple[float, float, float]]]):
        """
        Calibrate color profiles from sample HSV values.
        
        Args:
            samples: Dictionary mapping positions to lists of HSV samples
        """
        for pos, hsv_samples in samples.items():
            if pos not in self.profiles:
                continue
            
            if len(hsv_samples) < 3:
                print(f"Warning: Not enough samples for {pos} ({len(hsv_samples)} samples)")
                continue
            
            # Calculate HSV ranges from samples
            h_values = [h for h, s, v in hsv_samples]
            s_values = [s for h, s, v in hsv_samples]
            v_values = [v for h, s, v in hsv_samples]
            
            # Calculate ranges with some tolerance
            h_tolerance = 10
            s_tolerance = 30
            v_tolerance = 30
            
            h_min, h_max = min(h_values), max(h_values)
            s_min, s_max = min(s_values), max(s_values)
            v_min, v_max = min(v_values), max(v_values)
            
            # Expand ranges with tolerance
            h_min = max(0, h_min - h_tolerance)
            h_max = min(180, h_max + h_tolerance)
            s_min = max(0, s_min - s_tolerance)
            s_max = min(255, s_max + s_tolerance)
            v_min = max(0, v_min - v_tolerance)
            v_max = min(255, v_max + v_tolerance)
            
            # Update profile
            self.profiles[pos].hsv_ranges = [((int(h_min), int(s_min), int(v_min)), 
                                            (int(h_max), int(s_max), int(v_max)))]
            
            print(f"Calibrated {pos}: H({h_min:.0f}-{h_max:.0f}), S({s_min:.0f}-{s_max:.0f}), V({v_min:.0f}-{v_max:.0f})")
        
        # Save calibration
        self.save_calibration()

def create_color_calibration_tool():
    """Create a tool for manually calibrating colors."""
    print("Color Calibration Tool")
    print("=" * 40)
    print("This tool helps you calibrate color detection for your specific draft board.")
    print("You'll need to provide HSV samples for each position group.")
    print()
    
    calibrator = ColorCalibrator()
    
    # Example usage
    print("Example usage:")
    print("samples = {")
    print("    'QB': [(15, 200, 200), (20, 220, 220), (18, 210, 210)],")
    print("    'RB': [(12, 150, 150), (18, 180, 180), (15, 160, 160)],")
    print("    'WR': [(110, 200, 200), (120, 220, 220), (115, 210, 210)],")
    print("    # ... more samples")
    print("}")
    print("calibrator.calibrate_from_samples(samples)")
    
    return calibrator
