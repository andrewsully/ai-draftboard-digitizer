# Advanced Player Name Prediction with Name Swapping and Exact Match Override

```mermaid
flowchart TD
    A["Dual OCR Results<br/>(ROI + Whole-Cell)"] --> B["Standard Reconciliation"]
    
    B --> B1["Run reconciliation on ROI result"]
    B --> B2["Run reconciliation on Whole-Cell result"]
    
    B1 --> C["ROI Result Ready"]
    B2 --> D["Name Swapping Logic<br/>(Whole-Cell Only)"]
    
    D --> D1["Create swapped OCR data<br/>(first ↔ last names)"]
    D1 --> D2["Run reconciliation on swapped version"]
    D2 --> D3{"Swapped score ><br/>original score?"}
    D3 -->|Yes| D4["Use swapped result"]
    D3 -->|No| D5["Keep original result"]
    D4 --> E["Whole-Cell Result Ready"]
    D5 --> E
    
    C --> F["Competition: ROI vs Whole-Cell"]
    E --> F
    F --> F1{"Which has higher<br/>match score?"}
    F1 -->|Whole-Cell| G1["Select Whole-Cell Winner"]
    F1 -->|ROI (or tie)| G2["Select ROI Winner"]
    
    G1 --> H["Preliminary Player Assignment"]
    G2 --> H
    
    H --> I["Exact Match Override System"]
    I --> I1["Check for exact last name matches<br/>(include already-used players)"]
    I1 --> I2["Find candidates with normalized<br/>last name = OCR last name"]
    I2 --> I3{"Exact match<br/>candidates found?"}
    
    I3 -->|No| J["Standard Assignment"]
    I3 -->|Yes| K["Exact Match Processing"]
    
    K --> K1["Get highest-scoring exact match"]
    K1 --> K2["Check if player already assigned"]
    K2 --> K3{"Player assigned to<br/>another cell?"}
    
    K3 -->|No| K4["Direct assignment<br/>(player available)"]
    K3 -->|Yes| K5["Check assignment type"]
    K5 --> K6{"Previous assignment<br/>was exact match?"}
    
    K6 -->|Yes| K7["LOCKED - Cannot steal<br/>(use standard assignment)"]
    K6 -->|No| K8["STEAL PLAYER<br/>(override non-exact assignment)"]
    
    K8 --> K8a["Remove player from previous cell"]
    K8a --> K8b["Assign exact match to current cell"]
    K8b --> K8c["Mark as 'exact' assignment"]
    K8c --> K8d["Recompute displaced cell<br/>(without stolen player)"]
    K8d --> K8e["Run full reconciliation on displaced cell"]
    
    K4 --> L["Final Assignment Complete"]
    K7 --> J
    K8e --> L
    J --> L
    
    L --> L1["Update tracking systems"]
    L1 --> L1a["Add to used_players set"]
    L1 --> L1b["Update assignments_by_identity"]
    L1 --> L1c["Update identity_by_cell mapping"]
    
    L1c --> M["Player Locked In"]
    M --> M1["Player identity with source"]
    M --> M2["Assignment type (exact/standard)"]
    M --> M3["Match confidence and breakdown"]
    M --> M4["Override reason (if applicable)"]
    
    M4 --> N["Complete Player Record"]
    
    style A fill:#2196f3,color:#fff
    style B fill:#4caf50,color:#fff
    style D fill:#ff9800,color:#fff
    style F fill:#9c27b0,color:#fff
    style H fill:#f44336,color:#fff
    style I fill:#795548,color:#fff
    style K fill:#607d8b,color:#fff
    style K8 fill:#e91e63,color:#fff
    style L fill:#3f51b5,color:#fff
    style M fill:#009688,color:#fff
    style N fill:#1976d2,color:#fff
```

## Advanced Player Prediction Features

### 🔵 Dual OCR Input
- Receives both ROI and whole-cell OCR results
- Each result includes all extracted fields (names, team, position, bye)

### 🟢 Standard Reconciliation
- Runs multi-factor scoring on both OCR approaches
- Uses 7-component scoring system (125 max points)
- Filters by color position and availability

### 🟠 Name Swapping Logic (Whole-Cell Only)
- **Automatic first/last name testing**: Creates swapped version of whole-cell OCR
- **Score comparison**: Tests if `(last, first)` performs better than `(first, last)`
- **Best result selection**: Uses higher-scoring name arrangement
- **OCR error handling**: Compensates for common name field confusion

### 🟣 Competition System
- **Head-to-head scoring**: ROI result vs whole-cell result (possibly swapped)
- **Tie-breaking**: ROI wins on equal scores (preference for targeted approach)
- **Winner selection**: Highest match score determines preliminary assignment

### 🔴 Preliminary Assignment
- **Confidence thresholding**: 45+ points uses database, <45 uses OCR
- **Standard duplicate prevention**: Respects used_players set
- **Initial player selection**: Best available match

### 🟤 Exact Match Override System
This is the **most sophisticated feature**:

#### **Exact Match Detection**
- **Normalized comparison**: `normalize_name(OCR_last) == normalize_name(player.last)`
- **Include used players**: Searches ALL players, even already-drafted ones
- **High-confidence override**: Exact matches bypass normal confidence thresholds

#### **Player Stealing Logic**
- **Assignment tracking**: System tracks how each player was assigned
- **Exact vs Standard**: Distinguishes between exact matches and fuzzy matches
- **Stealing rules**:
  - ✅ **Can steal**: Player assigned via standard (fuzzy) matching
  - ❌ **Cannot steal**: Player assigned via exact matching (locked)
  
#### **Reassignment Process**
1. **Remove** player from previous cell assignment
2. **Assign** exact match to current cell with 'exact' flag
3. **Recompute** displaced cell without the stolen player
4. **Full reconciliation** on displaced cell to find new best match

### 🔵 Advanced Tracking Systems
- **`used_players` set**: Prevents basic duplicates
- **`assignments_by_identity`**: Tracks assignment type (exact/standard)
- **`identity_by_cell`**: Maps cells to player identities
- **Assignment metadata**: Stores override reasons and confidence

### 🟢 Final Player Record
- **Complete identity**: All player metadata with source attribution
- **Assignment type**: Standard, exact, or stolen
- **Override tracking**: Reason for any special handling
- **Confidence metrics**: Match scores and breakdown
- **Audit trail**: Raw OCR data and decision process

## Key Intelligence Features

### **Name Confusion Handling**
- Automatically tests first/last name swaps on whole-cell OCR
- Handles common OCR parsing errors where names get reversed
- Improves accuracy when cell layout doesn't match ROI assumptions

### **Exact Match Priority**
- Perfect last name matches get special treatment
- Can override lower-confidence assignments elsewhere
- Prevents high-confidence exact matches from being lost to fuzzy matches

### **Smart Player Locking**
- Exact matches are "locked" and cannot be stolen
- Standard matches can be displaced by exact matches
- Prevents cascading reassignments and ensures stability

### **Graceful Reassignment**
- Displaced cells get full re-reconciliation
- System ensures every cell gets best available match
- No cells are left without assignments due to stealing

This system represents one of the most sophisticated draft board analysis engines ever built, combining fuzzy matching, exact matching, name swapping, player stealing, and intelligent reassignment in a single coherent pipeline!
