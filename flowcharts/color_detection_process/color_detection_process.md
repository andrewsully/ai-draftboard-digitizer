# Color Detection Process Flowchart

```mermaid
flowchart TD
    A["User uploads draft board image"] --> B["User crops the board"]
    B --> C["User chooses color detection method"]
    
    C --> D["Manual Color Selection<br/>'Pick Color' buttons"]
    C --> E["Auto-Generate Colors<br/>'Detect Colors Automatically'"]
    
    D --> D1["User clicks 'Pick Color' for position<br/>(QB, RB, WR, TE, K, DST)"]
    D1 --> D2["User clicks specific pixel on image"]
    D2 --> D3["System samples exact RGB/HSV<br/>from that pixel"]
    D3 --> D4["Color stored as profile<br/>for that position"]
    D4 --> D5{"All 6 positions<br/>selected?"}
    D5 -->|No| D1
    D5 -->|Yes| F["Proceed to board processing"]
    
    E --> E1["Tier 1: Smart OCR-based Detection"]
    E1 --> E2["System performs OCR on all cells<br/>to find position text + player names"]
    E2 --> E3["For each recognized position<br/>(QB, RB, etc.), collect HSV samples<br/>from cells containing that position"]
    E3 --> E4["Calculate HSV color ranges<br/>using percentiles and padding"]
    E4 --> E5{"Successfully detected<br/>≥ 3 positions?"}
    
    E5 -->|Yes| E6["Use OCR-derived color profiles<br/>(High confidence: 1.0)"]
    E6 --> F
    
    E5 -->|No| E7["Tier 2: K-means Clustering Fallback"]
    E7 --> E8["Apply K-means clustering<br/>with 6 clusters to entire image"]
    E8 --> E9["Filter pixels by saturation/value<br/>(Remove background/white pixels)"]
    E9 --> E10["Sort clusters by size<br/>(largest to smallest)"]
    E10 --> E11["Assign clusters to positions<br/>in order: WR→RB→QB→TE→DST→K"]
    E11 --> E12["Generate color profiles<br/>(Lower confidence: 0.5)"]
    E12 --> F
    
    F --> G["User can refine colors manually<br/>or proceed to processing"]
    G --> H["System processes entire board<br/>using established color profiles"]
    
    style D fill:#1976d2,color:#fff
    style E fill:#7b1fa2,color:#fff
    style E1 fill:#388e3c,color:#fff
    style E7 fill:#f57c00,color:#fff
    style F fill:#2e7d32,color:#fff
```

## Process Overview

This flowchart shows the two-tier color detection system:

### Manual Color Selection (Blue Path)
- Direct pixel sampling by user interaction
- Full user control over color selection
- No algorithmic processing involved

### Auto-Generate Colors (Purple Path)
- **Tier 1 (Green)**: Smart OCR-based detection using actual draft board content
- **Tier 2 (Orange)**: K-means clustering fallback when OCR fails
- Graceful degradation ensures system always works

### Key Features
- High confidence (1.0) for OCR-derived profiles
- Lower confidence (0.5) for K-means fallback
- Users can always refine auto-detected colors manually
