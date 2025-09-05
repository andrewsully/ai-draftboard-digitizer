# Image Preprocessing and OCR Pipeline

```mermaid
flowchart TD
    A["Raw Draft Board Image"] --> B["Board-Level Preprocessing<br/>(normalize_board)"]
    
    B --> B1["Convert BGR → HSV"]
    B1 --> B2["Apply CLAHE to V channel<br/>(clipLimit=2.0, tileSize=8x8)"]
    B2 --> B3["Convert HSV → BGR"]
    B3 --> B4["Bilateral Filter Denoising<br/>(d=9, sigmaColor=75, sigmaSpace=75)"]
    B4 --> B5["Save rectified.png"]
    
    B5 --> C["Grid Extraction<br/>(cells_from_rectified)"]
    C --> C1["Calculate precise cell boundaries<br/>(16 rows × 10 cols default)"]
    C1 --> C2["Extract individual cell images<br/>using integer boundaries"]
    C2 --> C3["Save cell images: r{row}_c{col}.png"]
    
    C3 --> D["Dual OCR Strategy<br/>(Both approaches run in parallel)"]
    
    D --> D_ROI["ROI-Based Approach<br/>(read_cell)"]
    D --> D_WHOLE["Whole-Cell Approach<br/>(read_cell_whole)"]
    
    D_ROI --> D1["Define ROI Regions"]
    D1 --> D1a["Position ROI: top-left 35% × 25%"]
    D1 --> D1b["Bye ROI: top-right 35% × 25%"]
    D1 --> D1c["Last Name ROI: center 80% × 40%"]
    D1 --> D1d["Team ROI: bottom-left 35% × 25%"]
    D1 --> D1e["First Name ROI: bottom-right 35% × 25%"]
    
    D1a --> E_ROI["ROI OCR Preprocessing<br/>(neutral_otsu per ROI)"]
    D1b --> E_ROI
    D1c --> E_ROI
    D1d --> E_ROI
    D1e --> E_ROI
    
    D_WHOLE --> E_WHOLE["Whole-Cell Preprocessing<br/>(neutral_otsu on full cell)"]
    
    E_ROI --> E1_ROI["Convert BGR → Grayscale<br/>(per ROI)"]
    E1_ROI --> E2_ROI["Apply CLAHE Enhancement<br/>(clipLimit=2.2, tileSize=20x20)"]
    E2_ROI --> E3_ROI["Gaussian Blur + Unsharp Masking"]
    E3_ROI --> E4_ROI["Otsu Thresholding + Morphological Ops"]
    E4_ROI --> F_ROI["ROI-Specific OCR Execution"]
    
    F_ROI --> F1["Position OCR<br/>(PSM=7, whitelist='QBWRTEDSTK')"]
    F_ROI --> F2["Bye OCR<br/>(PSM=7, whitelist='BYE 0123456789')"]
    F_ROI --> F3["Last Name OCR<br/>(PSM=7, no whitelist)"]
    F_ROI --> F4["Team OCR<br/>(PSM=7, no whitelist)"]
    F_ROI --> F5["First Name OCR<br/>(PSM=7, no whitelist)"]
    
    E_WHOLE --> E1_WHOLE["Convert BGR → Grayscale<br/>(full cell)"]
    E1_WHOLE --> E2_WHOLE["Apply CLAHE Enhancement"]
    E2_WHOLE --> E3_WHOLE["Gaussian Blur + Unsharp Masking"]
    E3_WHOLE --> E4_WHOLE["Otsu Thresholding + Morphological Ops"]
    E4_WHOLE --> F_WHOLE["Whole-Cell OCR Execution<br/>(PSM=6, get tokens with confidence)"]
    
    F_WHOLE --> F6["Parse all text tokens"]
    F6 --> F7["Regex-based field extraction<br/>(BYE, positions, teams)"]
    F7 --> F8["Intelligent name parsing<br/>(longest non-stopword token)"]
    F8 --> F9["Optional first/last name swapping"]
    
    F1 --> G_ROI["ROI Text Post-Processing"]
    F2 --> G_ROI
    F3 --> G_ROI
    F4 --> G_ROI
    F5 --> G_ROI
    
    F9 --> G_WHOLE["Whole-Cell Text Results"]
    
    G_ROI --> J["Reconciliation & Competition"]
    G_WHOLE --> J
    
    J --> J1["Run reconciliation on both results"]
    J1 --> J2["Test name swapping on whole-cell result"]
    J2 --> J3["Compare match scores"]
    J3 --> J4["Select best performing approach"]
    
    J4 --> H["Color Analysis<br/>(dominant_nonwhite_hsv)"]
    
    H --> H1["Filter out white/background pixels<br/>(V>30, V<250, S>20)"]
    H1 --> H2["K-means clustering<br/>(k=3 clusters)"]
    H2 --> H3["Select dominant cluster<br/>(largest pixel count)"]
    H3 --> H4["Extract HSV color values"]
    
    H4 --> I["Final Cell Results"]
    I --> I1["OCR text fields<br/>(pos, bye, last, team, first)"]
    I --> I2["Color-based position prediction"]
    I --> I3["Confidence scores"]
    
    style B fill:#2196f3,color:#fff
    style C fill:#4caf50,color:#fff
    style D fill:#ff9800,color:#fff
    style D_ROI fill:#e91e63,color:#fff
    style D_WHOLE fill:#673ab7,color:#fff
    style E_ROI fill:#9c27b0,color:#fff
    style E_WHOLE fill:#3f51b5,color:#fff
    style F_ROI fill:#f44336,color:#fff
    style F_WHOLE fill:#2196f3,color:#fff
    style G_ROI fill:#795548,color:#fff
    style G_WHOLE fill:#4caf50,color:#fff
    style J fill:#ff5722,color:#fff
    style H fill:#607d8b,color:#fff
    style I fill:#009688,color:#fff
```

## Pipeline Overview

This flowchart details the complete image preprocessing and OCR pipeline:

### 🔵 Board-Level Preprocessing
- CLAHE contrast enhancement on HSV V-channel
- Bilateral filtering for noise reduction
- Saves enhanced board as `rectified.png`

### 🟢 Grid Extraction
- Calculates precise cell boundaries (16×10 default)
- Extracts individual cell images with no gaps/overlaps
- Saves cells as `r{row}_c{col}.png`

### 🟠 Dual OCR Strategy
The system runs **both approaches in parallel** for maximum accuracy:

#### 🔴 ROI-Based Approach (read_cell)
- Divides each cell into 5 regions for targeted OCR:
  - **Position**: Top-left corner (35% × 25%)
  - **Bye Week**: Top-right corner (35% × 25%)
  - **Last Name**: Center region (80% × 40%)
  - **Team**: Bottom-left corner (35% × 25%)
  - **First Name**: Bottom-right corner (35% × 25%)
- Each ROI gets individual `neutral_otsu` preprocessing
- Uses PSM=7 with position-specific whitelists
- Parallel processing of all 5 ROIs

#### 🟣 Whole-Cell Approach (read_cell_whole)
- Processes entire cell as single unit
- Single `neutral_otsu` preprocessing on full cell
- Uses PSM=6 to get tokens with confidence scores
- Intelligent parsing using regex and stopword filtering
- Finds longest non-stopword token as last name
- Tests first/last name swapping for better matches

### 🟠 Reconciliation & Competition
- Both approaches run reconciliation against player database
- System tests name swapping on whole-cell results
- Compares match scores between approaches
- **Automatically selects the best performing result**

### 🔵 Color Analysis
- K-means clustering on non-background pixels
- Dominant color extraction for position prediction
- HSV color space analysis

### 🟢 Final Results
- Combined OCR text fields
- Color-based position predictions
- Confidence scoring for validation
