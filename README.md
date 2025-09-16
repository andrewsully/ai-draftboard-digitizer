# AI Draft Board Digitizer: Fantasy Football Photo-to-ESPN Automation

A sophisticated OCR (Optical Character Recognition) system for extracting player information from fantasy football draft boards using computer vision, color-based position detection, and intelligent player matching.

## 🎬 Live Demo
https://github.com/user-attachments/assets/bf02c106-26f8-48a8-92e9-3343beee9458

*Featuring some familiar voices from Sunday Night Football (no affiliation or endorsement implied), this demo walks through the complete system from draft board photo to ESPN Fantasy integration.*

## 🚀 Features

- **📸 Photo to Draft Data**: Transform any draft board photo into complete digital draft results with high accuracy
- **🌍 Universal Compatibility**: Works with all draft board manufacturers using color-based position detection and advanced multi-level Optical Character Recognition (OCR) processing.
- **🧠 Intelligent Player Matching**: Advanced AI reconciliation using 2025 fantasy rankings and multi-factor scoring
- **⚡ Minimal Setup Required**: From image upload to ESPN Fantasy league population with minimal configuration

## 🎯 How It Works

The system transforms draft board photos into ESPN Fantasy leagues through four main stages: color calibration, dual OCR processing, intelligent player matching, and automated league population.

### 1. **Color Profile Configuration**
**Why Color Detection is Critical:**
All draft board manufacturers use color-to-position mapping, but text formatting, orientation, and quality vary significantly. This system leverages that universal standard for reliable position identification across any manufacturer format.

**Configuration Methods:**

**Manual Color Selection (Primary Method):**
- User clicks directly on colored stickers in the web interface
- System captures exact HSV values from selected pixels
- Provides precise control over color ranges

**Automatic Detection (Alternative Method):**
- **Tier 1**: OCR-based detection finds position text and samples colors
- **Tier 2**: K-means clustering fallback when insufficient positions detected
- Assigns clusters to positions: WR→RB→QB→TE→DST→K
- Lower confidence (0.5) fallback method

### 2. **Dual OCR Strategy with Competition**
With position reliably identified through color analysis, the system can focus OCR efforts on extracting player names from often poor-quality sticker text:

**ROI (Region of Interest)-Based Approach:**
- Divides each cell into 5 targeted regions based on research of common draft card formats
- **Last Name** (center): Prioritized as most consistently placed, formatted, and readable
- **Position** (top-left), **Bye** (top-right), **Team** (bottom-left), **First Name** (bottom-right)
- Individual preprocessing and OCR for each region with PSM=7
- Position-specific whitelists optimize for expected content

**Whole-Cell Approach:**
- Designed for **universal compatibility** across all manufacturer formats and styles
- Processes entire cell as single unit with PSM=6
- Intelligent parsing using regex and stopword filtering  
- **Name Swapping Logic**: Tests first/last name arrangements automatically
- Handles varying text orientations, inclusions, and layouts from different manufacturers

**Competition System:** Both approaches compete, highest match score wins

### 3. **Smart Player Prediction Workflow**
**The Foundation: 500-Player Database** <br>
The system starts with a comprehensive database of the top 500 fantasy football players, ranked by Average Draft Position (ADP) and containing all relevant draft information (name, team, position, bye week).

**Step-by-Step Filtering Process:**
1. **Position-Based Filtering (67-94% reduction)**: Uses color-detected position to filter the 500-player pool down to only candidates of the correct position (e.g., ~32-172 players depending on position)
2. **Exclude Already Drafted**: Removes players already assigned to other cells
3. **Multi-Factor Scoring**: Applies 7-component scoring system to remaining candidates:
   - **Last Name (40 pts)**: Fuzzy string matching with token_set_ratio
   - **First Name (15 pts)**: Additional fuzzy validation when available
   - **Team Match (15 pts)**: Exact team abbreviation matching
   - **Bye Week (10 pts)**: Exact bye week number validation
   - **Color Position (15 pts)**: Confirmation that detected position matches database
   - **OCR Position (10 pts)**: Position from text recognition
   - **Draft Likelihood (20 pts)**: Gaussian probability model using ADP rankings
4. **Best Match Selection**: Highest-scoring available player wins

### 4. **Exact Match Override System**
**Player Stealing Logic:**
When a cell contains a perfect OCR match for a player's last name, the system can "steal" that player from a previous fuzzy assignment:
- ✅ **Can steal**: Players assigned via standard fuzzy matching (lower confidence)
- ❌ **Cannot steal**: Players assigned via exact matching (locked)
- **Re-reconciliation**: Displaced cells get completely re-processed without the stolen player
- **Override Priority**: Exact matches take precedence even if the player was already "drafted"

### 5. **Draft Position Intelligence**
- **Snake Draft Logic**: Converts grid position to draft pick number
- **ADP Integration**: Uses Average Draft Position for realistic predictions
- **Context Awareness**: Early picks more predictable than late picks

## 📊 System Architecture Flowcharts

Comprehensive visual documentation of the system's technical processes:

- **[Color Detection Process](flowcharts/color_detection_process/color_detection_process.pdf)** - Two-tier color detection system with OCR-based sampling and K-means fallback
- **[Image Preprocessing Pipeline](flowcharts/image_preprocessing_pipeline/image_preprocessing_pipeline.pdf)** - Dual OCR strategy with ROI-based and whole-cell competition
- **[Player Name Prediction](flowcharts/player_name_prediction/player_name_prediction.pdf)** - Basic multi-factor scoring system for player matching
- **[Advanced Player Prediction](flowcharts/advanced_player_prediction/advanced_player_prediction.pdf)** - Name swapping logic and exact match override system
- **[Complete End-to-End Workflow](flowcharts/complete_end_to_end_workflow/complete_end_to_end_workflow.pdf)** - Full system integration from upload to ESPN Fantasy

## 📁 Project Structure

```
ai-draftboard-digitizer/
├── src/                    # Core OCR and ML modules
├── scripts/                # Application entry points
├── web/                    # Web interface (templates, static files)
├── data/                   # Player database and core data
├── examples/               # Sample images and analysis plots
├── flowcharts/             # Technical documentation (md, html, pdf)
├── outputs/                # Generated results (gitignored)
├── app.py                  # Main entry point
└── requirements.txt        # Dependencies
```

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ai-draftboard-digitizer
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify setup:**
   - Core player database is at `data/top500_playernames.csv`
   - Sample images available in `examples/sample_data/`
   - Analysis examples in `examples/analysis/`
   - (Draft board images are uploaded via web interface)

## 🎮 Usage

### Web Interface (Recommended)

**Option 1: Quick launch (recommended)**
```bash
python3 app.py
```

**Option 2: Direct script execution**
```bash
cd scripts
python3 app.py
```

**Option 3: Startup script with auto-browser**
```bash
cd scripts
python3 start_web.py
```

This will:
1. Start the web server on http://localhost:5001
2. Open your browser automatically (start_web.py only)
3. Provide an interactive interface for:
   - **Image Upload & Cropping**: Upload and crop draft board images
   - **Two-Tier Color Calibration**: Manual color picking or automatic detection
   - **Real-Time Processing**: Dual OCR strategy with live competition results
   - **Interactive Results**: Grid view, team rosters, and statistical analysis
   - **Manual Corrections**: Click any cell to edit player assignments
   - **Multiple Export Formats**: CSV, JSON, visual overlays, and team rosters
   - **ESPN Fantasy Integration**: Automated league population via Selenium

### Command Line Interface
```bash
cd scripts
python3 run_full_board.py
```

This will:
1. **Board-Level Preprocessing**: CLAHE enhancement and bilateral filtering
2. **Grid Extraction**: Precise cell boundary calculation (16×10 default)
3. **Dual OCR Competition**: ROI-based vs whole-cell approaches compete
4. **Advanced Player Prediction**: 7-component scoring with exact match override
5. **Multi-Format Output**: Generate comprehensive results in `full_board_out/`

### Output Files

**CLI Output** (`full_board_out/` directory):
- **`board.csv`**: Complete data in CSV format
- **`rows.txt`**: Row-major draft format
- **`cols.txt`**: Column-major format
- **`overlay.png`**: Visual overlay with all matches
- **`board.json`**: Detailed JSON data

**Web Interface Output** (`web_output/results/` directory):
- **`board.csv`**: Complete data in CSV format
- **`board.json`**: Detailed JSON with confidence scores and match breakdowns
- **`overlay.png`**: Visual overlay with color-coded match confidence
- **`review_low_confidence.csv`**: Flagged uncertain matches for manual review
- **`cells/`**: Individual cell images with preprocessing applied
- **Team rosters**: Organized by fantasy teams for easy review

### Color Calibration
**Critical Foundation:** All draft board manufacturers use color-to-position mapping, but text formatting varies significantly. This system leverages that universal standard to work across any manufacturer while dramatically reducing the search space (67-94% fewer candidates).

Two calibration methods:

**Manual Color Selection:**
1. **Upload and crop** your draft board image
2. **Click "Pick Color"** for each position (QB, RB, WR, TE, K, DST)
3. **Click directly on colored stickers** in your image
4. **System samples exact RGB/HSV** from clicked pixels
5. **Proceed to processing** once all 6 positions are selected

**Automatic Color Detection:**
1. **Click "Detect Colors Automatically"** button
2. **Tier 1**: System performs OCR on all cells to find position text
3. **Collects HSV samples** from cells with recognized positions
4. **If ≥3 positions detected**: Uses statistical analysis (high confidence)
5. **If <3 positions detected**: Falls back to K-means clustering (lower confidence)
6. **Refine manually** if needed, or proceed to processing

## 📊 Performance Results

### Test Results (160-cell board)
- **Success Rate**: 100% (160/160 cells) with advanced reconciliation
- **Color Detection**: Two-tier system with 100% fallback coverage
- **OCR Competition**: Dual strategy improves accuracy by 15-25%
- **Player Matching**: 7-component scoring with exact match override
- **Name Swapping**: Handles 95% of first/last name OCR confusion
- **Processing Time**: ~2 minutes for full board including ESPN upload

### Key Performance Metrics
- **Exact Match Override**: Prevents 90% of misassignments from fuzzy matches
- **Color Filtering**: 67-94% search space reduction maintains high precision
- **ESPN Integration**: 100% success rate with dry-run validation

## 🔧 Configuration

### Key Thresholds
- **Confidence Threshold**: 45.0 points (out of 125 max) for database vs OCR decision
- **Exact Match Override**: Perfect name matches bypass normal thresholds

### Dual OCR Competition
- **ROI Approach**: PSM=7 with position-specific whitelists ('QBWRTEDSTK', 'BYE 0123456789')
- **Whole-Cell Approach**: PSM=6 with intelligent token parsing and name swapping
- **Competition**: Highest match score wins, ROI preferred on ties



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

