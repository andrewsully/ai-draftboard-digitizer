# Player Name Prediction and Reconciliation Process

```mermaid
flowchart TD
    A["OCR Results from Cell<br/>(ROI or Whole-Cell winner)"] --> B["Extract OCR Data Fields"]
    
    B --> B1["Last Name (primary)"]
    B --> B2["First Name"]
    B --> B3["Team Abbreviation"]
    B --> B4["Bye Week Number"]
    B --> B5["OCR Position Text"]
    B --> B6["Color-Based Position"]
    
    B1 --> C["Load Player Database<br/>(top500_playernames.csv)"]
    B2 --> C
    B3 --> C
    B4 --> C
    B5 --> C
    B6 --> C
    
    C --> D["Calculate Draft Context"]
    D --> D1["Convert grid position to draft pick<br/>(Snake draft logic: row, col → pick #)"]
    D1 --> D2["Determine expected player rank<br/>based on draft position"]
    
    D2 --> E["Apply Position Filters"]
    E --> E1{"Color position<br/>available?"}
    E1 -->|Yes| E2["Filter candidates by position<br/>(QB, RB, WR, TE, K, DST)"]
    E1 -->|No| E3["Use all players as candidates"]
    E2 --> F["Multi-Factor Scoring System"]
    E3 --> F
    
    F --> F1["Score Component 1: Last Name<br/>Fuzzy string matching (0-40 pts)"]
    F --> F2["Score Component 2: First Name<br/>Fuzzy string matching (0-15 pts)"]
    F --> F3["Score Component 3: Team Match<br/>Exact team abbreviation (0-15 pts)"]
    F --> F4["Score Component 4: Bye Week<br/>Exact bye week number (0-10 pts)"]
    F --> F5["Score Component 5: Color Position<br/>Position from color analysis (0-15 pts)"]
    F --> F6["Score Component 6: OCR Position<br/>Position from OCR text (0-10 pts)"]
    F --> F7["Score Component 7: Draft Likelihood<br/>Gaussian probability model (0-20 pts)"]
    
    F1 --> G["Calculate Total Score<br/>(Maximum: 125 points)"]
    F2 --> G
    F3 --> G
    F4 --> G
    F5 --> G
    F6 --> G
    F7 --> G
    
    G --> H["Filter Used Players<br/>(Prevent duplicates)"]
    H --> H1["Check player identity against<br/>used_players set"]
    H1 --> H2["Skip already drafted players"]
    
    H2 --> I["Rank All Candidates<br/>(Sort by total score)"]
    I --> I1["Select highest scoring candidate"]
    I1 --> I2["Get detailed score breakdown"]
    
    I2 --> J["Confidence Threshold Check"]
    J --> J1{"Score ≥ 45.0<br/>(confidence threshold)?"}
    
    J1 -->|Yes| K1["HIGH CONFIDENCE MATCH"]
    J1 -->|No| K2["LOW CONFIDENCE - USE OCR"]
    
    K1 --> K1a["Use database player data"]
    K1a --> K1b["Full name from CSV"]
    K1a --> K1c["Team from CSV"]
    K1a --> K1d["Position from CSV"]
    K1a --> K1e["Bye week from CSV"]
    K1a --> K1f["Mark as 'csv' source"]
    
    K2 --> K2a["Use raw OCR data"]
    K2a --> K2b["Combine OCR first + last"]
    K2a --> K2c["Use OCR team (if available)"]
    K2a --> K2d["Use color position or OCR position"]
    K2a --> K2e["Use OCR bye week"]
    K2a --> K2f["Mark as 'ocr' source"]
    
    K1f --> L["Final Player Result"]
    K2f --> L
    
    L --> L1["Player identity with confidence"]
    L --> L2["Source attribution (csv/ocr)"]
    L --> L3["Match score and breakdown"]
    L --> L4["Draft position analysis"]
    L --> L5["Raw OCR data preserved"]
    
    L5 --> M["Add to used_players set<br/>(Prevent future duplicates)"]
    M --> N["Return Complete Player Record"]
    
    style A fill:#2196f3,color:#fff
    style C fill:#4caf50,color:#fff
    style D fill:#ff9800,color:#fff
    style E fill:#9c27b0,color:#fff
    style F fill:#f44336,color:#fff
    style G fill:#795548,color:#fff
    style H fill:#607d8b,color:#fff
    style I fill:#3f51b5,color:#fff
    style J fill:#e91e63,color:#fff
    style K1 fill:#4caf50,color:#fff
    style K2 fill:#ff5722,color:#fff
    style L fill:#009688,color:#fff
    style M fill:#673ab7,color:#fff
    style N fill:#1976d2,color:#fff
```

## Process Overview

This flowchart details the sophisticated player name prediction and reconciliation system:

### 🔵 OCR Input Processing
- Receives winning OCR results from dual-strategy pipeline
- Extracts all available text fields and color-based position

### 🟢 Database Integration
- Loads comprehensive player database (top500_playernames.csv)
- Handles special cases like DST teams and free agents
- Maintains player rankings for draft likelihood calculations

### 🟠 Draft Context Analysis
- Converts grid position to actual draft pick using snake draft logic
- Calculates expected player rank based on draft position
- Provides context for draft likelihood scoring

### 🟣 Intelligent Filtering
- Uses color-based position detection for strong filtering
- Reduces candidate pool to relevant position players
- Maintains full candidate pool when color data unavailable

### 🔴 Multi-Factor Scoring System (7 Components)
1. **Last Name (40%)**: Fuzzy string matching using token_set_ratio
2. **First Name (15%)**: Additional fuzzy matching when available
3. **Team Match (15%)**: Exact team abbreviation matching
4. **Bye Week (10%)**: Exact bye week number matching
5. **Color Position (15%)**: Position from color analysis
6. **OCR Position (10%)**: Position from OCR text recognition
7. **Draft Likelihood (20%)**: Gaussian probability model based on ADP

### 🟤 Duplicate Prevention
- Maintains used_players set with unique player identities
- Prevents same player from being drafted multiple times
- Uses composite identity: (first, last, team, pos, bye)

### 🔵 Ranking and Selection
- Sorts all candidates by total score
- Selects highest scoring available player
- Provides detailed score breakdown for transparency

### 🔴 Confidence-Based Decision
- **High Confidence (≥45 points)**: Use database player data
- **Low Confidence (<45 points)**: Fall back to raw OCR data
- Maintains data quality while handling edge cases

### 🟢 Comprehensive Output
- Complete player record with all metadata
- Source attribution for traceability
- Match confidence and score breakdown
- Draft position analysis and raw OCR preservation

## Key Features

- **Fuzzy Matching**: Handles OCR errors and name variations
- **Draft Intelligence**: Uses ADP rankings and draft position context
- **Multi-Modal Validation**: Combines text, color, and positional data
- **Graceful Degradation**: Falls back to OCR when matching fails
- **Duplicate Prevention**: Sophisticated identity tracking
- **Transparency**: Detailed scoring breakdown for debugging
