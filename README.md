# Fantasy Football Draft Board OCR

A sophisticated OCR system for extracting player information from fantasy football draft boards using computer vision, color-based position detection, and intelligent player matching.

## 🚀 Features

- **Color-Based Position Detection**: Uses manual calibration to detect player positions from sticker colors
- **Advanced OCR**: Extracts player names, teams, positions, and bye weeks from draft board cells
- **Intelligent Player Matching**: Combines fuzzy string matching with draft position logic
- **No Duplicate Tracking**: Ensures each player is only matched once across the entire board
- **Multiple Output Formats**: CSV, JSON, and visual overlays
- **High Accuracy**: Achieves 100% success rate on test boards

## 🎯 How It Works

### 1. **Color-Based Position Detection**
The system uses manually calibrated color profiles to detect player positions:
- **QB**: Orange stickers
- **RB**: Brown/red stickers  
- **WR**: Blue stickers
- **TE**: Red stickers
- **K**: Grey stickers
- **DST**: Green stickers

### 2. **Position-Filtered Player Matching**
When a color position is detected, the system:
- Filters the player database to only include players of that position
- Reduces search space by 67-94% (e.g., 172 WR candidates instead of 518 total)
- Applies a significant confidence bonus for position matches

### 3. **Draft Position Logic**
Uses snake draft pattern to validate matches:
- Row 1: Picks 1-10 (left to right)
- Row 2: Picks 11-20 (right to left, snake pattern)
- Continues pattern for all rows
- Matches players based on expected draft position ranges

### 4. **Fuzzy String Matching**
Handles poor OCR text using:
- Token set ratio matching for player names
- Team abbreviation normalization
- Bye week extraction and validation
- Confidence scoring based on multiple factors

## 📁 Project Structure

```
draftboard_ocr/
├── src/                          # Core modules
│   ├── preprocess.py             # Image preprocessing and enhancement
│   ├── grid.py                   # Grid cell extraction
│   ├── ocr_cell.py               # OCR and color detection
│   ├── reconcile.py              # Player matching and reconciliation
│   ├── emit.py                   # Output generation
│   ├── espn_uploader.py          # ESPN Fantasy Football integration
│   ├── color_calibration.py      # Color profile framework
│   ├── manual_color_calibration.py # Manual color calibration
│   └── color_visualization.py    # Visual analysis tools
├── templates/                    # Web interface templates
│   └── index.html                # Main web interface
├── static/                       # Web assets
│   ├── script.js                 # Frontend JavaScript
│   ├── style.css                 # Frontend CSS
│   └── uploads/                  # Temporary web uploads
├── data/                         # Input data
│   ├── draftboard.png            # Draft board image
│   ├── formattemplate.png        # Format reference image
│   ├── top500_playernames.csv    # Player database
│   └── positional_color_examples/ # Color calibration images
├── uploads/                      # User uploaded images (web interface)
├── web_output/                   # Web interface processing output
├── full_board_out/               # CLI processing output
├── app.py                        # Main Flask web application
├── start_web.py                  # Web startup script (auto-opens browser)
├── run_full_board.py             # CLI execution script
├── ProjectPlan.txt               # Detailed project documentation
├── README.md                     # This file
├── requirements.txt              # Python dependencies
└── .gitignore                    # Git ignore patterns
```

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd draftboard_ocr
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare your data:**
   - Place your draft board image as `data/draftboard.png`
   - Ensure `data/top500_playernames.csv` contains your player database
   - Add color calibration images to `data/positional_color_examples/`

## 🎮 Usage

### Web Interface (Recommended)

**Option 1: Direct launch (no auto-browser)**
```bash
python3 app.py
```

**Option 2: Startup script (auto-opens browser)**
```bash
python3 start_web.py
```

This will:
1. Start the web server on http://localhost:5001
2. Open your browser automatically (start_web.py only)
3. Provide an interactive interface for:
   - Uploading your draft board image
   - Cropping the image to focus on the board
   - Calibrating colors by clicking on each position
   - Processing and viewing results
   - Downloading results in multiple formats
   - Uploading results to ESPN Fantasy Football

### Command Line Interface
```bash
python3 run_full_board.py
```

This will:
1. Load and preprocess the draft board image
2. Extract all grid cells
3. Run OCR with color-based position detection
4. Match players using position-filtered reconciliation
5. Generate outputs in `full_board_out/`

### Output Files

**CLI Output** (`full_board_out/` directory):
- **`board.csv`**: Complete data in CSV format
- **`rows.txt`**: Row-major draft format
- **`cols.txt`**: Column-major format
- **`overlay.png`**: Visual overlay with all matches
- **`board.json`**: Detailed JSON data

**Web Interface Output** (`web_output/results/` directory):
- **`board.csv`**: Complete data in CSV format
- **`board.json`**: Detailed JSON data
- **`overlay.png`**: Visual overlay with all matches
- **`cells/`**: Individual cell images for manual correction

### Color Calibration
To calibrate for different sticker colors:

1. **Take example images** of each position color
2. **Save as** `qb.png`, `rb.png`, `wr.png`, `te.png`, `k.png`, `dst.png`
3. **Place in** `data/positional_color_examples/`
4. **Run the system** - it will automatically calibrate

## 📊 Performance Results

### Test Results (160-cell board)
- **Success Rate**: 100% (160/160 cells)
- **Position Detection**: 100% accuracy
- **Player Matching**: 100% accuracy
- **Processing Time**: ~30 seconds for full board

### Color Filtering Impact
- **WR**: 172 candidates (67% reduction)
- **RB**: 144 candidates (72% reduction)  
- **QB**: ~50 candidates (90% reduction)
- **TE**: ~30 candidates (94% reduction)

## 🔧 Configuration

### Confidence Thresholds
- **Default**: 40.0 (lowered from 80.0 for better coverage)
- **Adjust in**: `run_full_board.py` line 58

### Color Calibration
- **Tolerance**: Adjustable in `manual_color_calibration.py`
- **Sample Analysis**: Uses 5th-95th percentiles with tolerance

### OCR Settings
- **PSM Mode**: 7 (single uniform block of text)
- **Character Whitelisting**: Position-specific for better accuracy

## 🎨 Color Detection System

### Manual Calibration Process
1. **Sample Collection**: Analyzes example images for each position
2. **HSV Range Calculation**: Uses percentiles to handle outliers
3. **Tolerance Addition**: Adds buffer for lighting variations
4. **Profile Storage**: Saves calibrated ranges for reuse

### Dominant Color Extraction
- **K-means Clustering**: Finds most frequent non-white color
- **Noise Filtering**: Ignores text, glare, and edges
- **Background Focus**: Targets solid card background colors

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **OpenCV** for computer vision capabilities
- **Tesseract** for OCR functionality
- **RapidFuzz** for fuzzy string matching
- **Scikit-learn** for color clustering algorithms

---

**Note**: This system is optimized for fantasy football draft boards with color-coded position stickers. For other formats, color calibration may be required.
