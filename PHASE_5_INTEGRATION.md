# PHASE 5 INTEGRATION GUIDE

## System Overview

```
PHASE 1: DATA INGESTION
    ↓ Raw market data (OHLCV)

PHASE 2: INDICATORS & FEATURES
    ↓ 27 feature columns (OHLCV + indicators + metrics)

PHASE 3: PATTERN DETECTION
    ↓ Identified patterns with timestamps

PHASE 4: ML RANKING
    ↓ Ranked events (index + pattern + ml_score)

PHASE 5: CHART FRAME GENERATION ← YOU ARE HERE
    ↓ PNG frame sequences (0001.png, 0002.png, ...)

PHASE 6: VIDEO STITCHING
    ↓ FFmpeg video generation + audio synthesis

OUTPUT: YouTube Shorts MP4 videos
```

---

## Data Flow Through Phase 5

### Input from Phase 2

```
Phase 2 Output: DataFrame with OHLCV + Indicators
┌─────────────────────────────────┐
│ timestamp | open | high | low   │
│ close | volume | ema_20 | ema_50│
│ ema_200 | ... (27 cols total)   │
│ 714 rows (hourly data)          │
└─────────────────────────────────┘
          ↓ PHASE 5
```

### Input from Phase 4

```
Phase 4 Output: Ranked Events
┌──────────────────────────────────┐
│ [                                │
│   {                              │
│     "event_index": 150,          │
│     "pattern": "GOLDEN_CROSS",   │
│     "ml_score": 0.87,            │
│     "context_window": [140, 160] │
│   },                             │
│   ...                            │
│ ]                                │
└──────────────────────────────────┘
          ↓ PHASE 5
```

### Phase 5 Processing

```
PHASE 5 ALGORITHM:
1. Load DataFrame (OHLCV + indicators)
2. For each ranked event:
   a. Extract context window (start_idx → end_idx)
   b. Create 60 frames in 3 phases:
      - Phase 1 (35%): Pre-event candles reveal
      - Phase 2 (20%): Event moment highlight
      - Phase 3 (45%): Post-event candles reveal
   c. Render candlestick + volume + EMAs + overlay
   d. Save as PNG sequence (0001.png → 0060.png)
3. Output frame directory per event
```

### Output to Phase 6

```
Phase 5 Output: Frame Sequences
┌────────────────────────────────┐
│ visuals/frames/                │
│ ├── event_001_GOLDEN_CROSS/    │
│ │   ├── 0001.png               │
│ │   ├── 0002.png               │
│ │   └── 0060.png               │
│ ├── event_002_BULLISH_ENGULFING│
│ │   └── ...                    │
│ └── ...                        │
└────────────────────────────────┘
          ↓ PHASE 6
      FFmpeg stitching
      + audio synthesis
      + captions
          ↓
    YouTube Shorts videos
```

---

## Module Usage in Phase 5

### Initialization

```python
from visuals import (
    ChartStyle,
    render_candlestick_chart,
    EventOverlay,
    FrameConfig,
    generate_event_frames
)
import pandas as pd
from pathlib import Path
```

### Data Loading

```python
# Load Phase 2 output
df = pd.read_csv("phase2_output.csv", index_col="timestamp")
print(f"DataFrame shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")

# Load Phase 4 output
import json
with open("phase4_output.json") as f:
    events = json.load(f)
print(f"Events: {len(events)}")
```

### Style Configuration

```python
# Get default mobile-optimized style
style = ChartStyle()
# Verify dimensions
assert style.figure_size == (9, 16)      # inches
assert style.resolution_px == (900, 1600) # pixels
assert style.dpi == 100
```

### Frame Generation

```python
# Configure frame generation
config = FrameConfig(
    frames_per_event=60,
    show_volume=True,
    show_ema=[20, 50, 200],
    highlight_event=True,
    style=style
)

# Generate frames for each event
for event in events[:10]:
    num_frames, output_dir = generate_event_frames(
        df=df,
        event_index=event["event_index"],
        event_pattern=event["pattern"],
        ml_score=event["ml_score"],
        output_dir=Path(f"visuals/frames/{event['event_id']}"),
        config=config
    )
    print(f"✓ {event['event_id']}: {num_frames} frames")
```

---

## Typical Workflow

### Step 1: Prepare Inputs

```python
# Ensure Phase 2 & 4 outputs are available
import pandas as pd
import json

df = pd.read_csv("phase2_output.csv")
with open("phase4_output.json") as f:
    events = json.load(f)

assert len(df) > 0, "DataFrame is empty"
assert len(events) > 0, "No events to process"
```

### Step 2: Configure

```python
from visuals import FrameConfig, get_default_style

config = FrameConfig(
    frames_per_event=60,      # Total frames per event
    show_volume=True,         # Include volume bars
    show_ema=[20, 50, 200],   # Include these EMAs
    highlight_event=True,     # Highlight event candle
    style=get_default_style() # Mobile-optimized styling
)
```

### Step 3: Generate

```python
from visuals import generate_multi_event_frames
from pathlib import Path

results = generate_multi_event_frames(
    df=df,
    ranked_events=events,
    base_output_dir=Path("visuals/frames"),
    config=config,
    max_events=10  # Process top 10
)
```

### Step 4: Verify

```python
# Check results
total_frames = 0
for event_id, (num_frames, path) in results.items():
    print(f"✓ {event_id}: {num_frames} frames")
    # Verify PNG files exist
    pngs = list(path.glob("*.png"))
    assert len(pngs) == num_frames
    total_frames += num_frames

print(f"\nTotal: {total_frames} frames generated")
```

### Step 5: Validate

```bash
# Run validation suite
python validate_phase5.py
```

### Step 6: Pass to Phase 6

```bash
# Phase 6 takes these frames and stitches into video:
# ffmpeg -framerate 30 -i "visuals/frames/event_001/%04d.png" output.mp4
```

---

## Integration Points

### With Phase 2

- **Dependency:** DataFrame with OHLCV + indicators
- **Columns Required:** open, high, low, close, volume
- **Columns Optional:** ema_20, ema_50, ema_200
- **Format:** CSV or pickle with datetime index

### With Phase 4

- **Dependency:** List of ranked events
- **Fields Required:** event_index, pattern, ml_score
- **Fields Optional:** context_window, event_id
- **Format:** JSON or Python list of dicts

### With Phase 6

- **Deliverable:** Ordered PNG sequences per event
- **Format:** visuals/frames/{event_id}/{0001-9999}.png
- **Requirements:**
  - Zero-padded 4-digit names
  - Lexicographic ordering
  - 900×1600 resolution
  - PNG lossless format

---

## Data Mapping

### Phase 2 → Phase 5

```python
# Phase 2 OHLCV columns used in Phase 5:
df["open"]     → Candlestick body calculation
df["high"]     → Wick high line
df["low"]      → Wick low line
df["close"]    → Candlestick close & color
df["volume"]   → Volume bar height

# Phase 2 Indicator columns used in Phase 5:
df["ema_20"]   → 20-period moving average
df["ema_50"]   → 50-period moving average
df["ema_200"]  → 200-period moving average
```

### Phase 4 → Phase 5

```python
# Phase 4 event dict mapping:
event["event_index"]   → x-axis position on chart
event["pattern"]       → Title in frame header
event["ml_score"]      → Score display in title
event["context_window"] → Data window for animation
```

### Phase 5 → Phase 6

```python
# Phase 5 output for Phase 6:
frames/event_001/0001.png  → Frame 1
frames/event_001/0002.png  → Frame 2
...
frames/event_001/0060.png  → Frame 60
(ready for FFmpeg input)
```

---

## Configuration for Different Scenarios

### Conservative (Few Frames)

```python
config = FrameConfig(
    frames_per_event=20,
    show_volume=False,
    show_ema=[50],  # Just 50-period
)
```

### Standard (Balanced)

```python
config = FrameConfig(
    frames_per_event=60,  # 2 seconds @ 30fps
    show_volume=True,
    show_ema=[20, 50, 200],
)
```

### Detailed (High Quality)

```python
config = FrameConfig(
    frames_per_event=120,  # 4 seconds @ 30fps
    show_volume=True,
    show_ema=[20, 50, 200],
    include_future=True,   # Full context
)
```

### Custom Styling

```python
from visuals import ChartStyle

style = ChartStyle()
style.COLORS["bullish"] = "#00ff00"      # Bright green
style.COLORS["bearish"] = "#ff0000"      # Bright red
style.LINEWIDTHS["candle_edge"] = 1.0    # Thicker

config = FrameConfig(
    frames_per_event=60,
    style=style
)
```

---

## Common Scenarios

### Scenario 1: Single Event Testing

```python
# Generate frames for one event to verify output
from visuals import generate_event_frames, FrameConfig

num_frames, path = generate_event_frames(
    df=df,
    event_index=150,
    event_pattern="GOLDEN_CROSS",
    ml_score=0.87,
    output_dir="visuals/frames/test_event",
    config=FrameConfig()
)

print(f"Generated {num_frames} frames in {path}")
# Check: ls visuals/frames/test_event/ | head -5
```

### Scenario 2: Batch Production

```python
# Generate frames for all top-ranked events
from visuals import generate_multi_event_frames

results = generate_multi_event_frames(
    df=df,
    ranked_events=events,
    base_output_dir="visuals/frames",
    max_events=None  # All events
)

print(f"Generated {sum(n for n,_ in results.values())} total frames")
```

### Scenario 3: Custom Analysis

```python
# Focus on specific patterns only
bullish_events = [e for e in events if "BULLISH" in e["pattern"]]

results = generate_multi_event_frames(
    df=df,
    ranked_events=bullish_events,
    base_output_dir="visuals/frames",
)
```

### Scenario 4: Quality Control

```python
# Validate all generated frames
from validate_phase5 import validate_frame_files

for event_id, (num_frames, path) in results.items():
    validation = validate_frame_files(path, expected_count=num_frames)
    if validation["valid"]:
        print(f"✓ {event_id}: All frames valid")
    else:
        print(f"✗ {event_id}: Issues detected")
        print(validation["issues"])
```

---

## Troubleshooting Phase 5

### No frames generated

```python
# Check 1: Event index in range?
assert event_index < len(df), f"Index {event_index} out of range"

# Check 2: DataFrame has required columns?
required = ["open", "high", "low", "close", "volume"]
assert all(c in df.columns for c in required), "Missing columns"

# Check 3: Output directory writable?
output_dir.mkdir(parents=True, exist_ok=True)
assert output_dir.exists(), "Cannot create output directory"
```

### Wrong frame count

```python
# Check context window calculation
# Default: 5 candles before, 20 after (or edge limit)
context_before = max(5, event_index - 10)
context_after = min(len(df) - 1, event_index + 20)
print(f"Context window: {context_before} → {context_after}")
```

### Bad dimensions

```python
# Verify style configuration
from visuals import get_default_style
style = get_default_style()
assert style.figure_size == (9, 16)
assert style.resolution_px == (900, 1600)
```

### Rendering timeout

```python
# Increase matplotlib timeout or render in smaller batches
# Split 100 events → 10 batches of 10
from itertools import islice

for batch in [events[i:i+10] for i in range(0, len(events), 10)]:
    generate_multi_event_frames(..., ranked_events=batch)
```

---

## Performance Optimization

### Parallel Processing (Future)

```python
# Events can be processed independently
from multiprocessing import Pool

def generate_frames(event):
    return generate_event_frames(df, event["event_index"], ...)

with Pool(4) as p:
    results = p.map(generate_frames, events)
```

### Caching

```python
# Cache rendered frames if regenerating
import pickle

cache_file = "frame_cache.pkl"
if cache_file exists:
    results = pickle.load(open(cache_file, "rb"))
else:
    results = generate_multi_event_frames(...)
    pickle.dump(results, open(cache_file, "wb"))
```

### Batch Size Optimization

```python
# Process events in batches to manage memory
batch_size = 5

for i in range(0, len(events), batch_size):
    batch = events[i:i+batch_size]
    results = generate_multi_event_frames(
        df=df,
        ranked_events=batch,
        base_output_dir=output_dir
    )
    # Clear memory between batches
    import gc; gc.collect()
```

---

## Monitoring & Logging

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("visuals")
logger.setLevel(logging.DEBUG)
```

### Check Progress

```python
# Monitor frame generation
import time

start = time.time()
num_frames, path = generate_event_frames(...)
elapsed = time.time() - start

print(f"Generated {num_frames} frames in {elapsed:.1f}s")
print(f"Average: {elapsed/num_frames:.2f}s per frame")
```

---

## Quality Assurance

### Before Phase 6

1. ✅ Run `python validate_phase5.py`
2. ✅ Spot-check output frames
3. ✅ Verify frame counts match config
4. ✅ Check file sizes (should be ~50KB each)
5. ✅ Validate dimensions (900×1600)

### Spot-Check Example

```bash
# Display first frame of first event
from PIL import Image

img = Image.open("visuals/frames/event_001/0001.png")
print(f"Size: {img.size}")  # Should be (900, 1600)
img.show()
```

---

## Phase 5 → Phase 6 Handoff

### What Phase 6 Expects

- ✅ Frame sequences in `visuals/frames/{event_id}/`
- ✅ Frames named `0001.png`, `0002.png`, etc.
- ✅ Frames ordered lexicographically
- ✅ Resolution exactly 900×1600
- ✅ PNG format (lossless)

### Phase 6 Takes Over

- FFmpeg: Stitch frames into video
- Audio: Synthesis from price data
- Captions: Overlay text
- Output: YouTube Shorts MP4

### Example Phase 6 Command

```bash
ffmpeg -framerate 30 \
  -i "visuals/frames/event_001/%04d.png" \
  -c:v libx264 \
  -pix_fmt yuv420p \
  -crf 18 \
  -preset slow \
  output.mp4
```

---

## Summary

**Phase 5 receives:**

- OHLCV DataFrame from Phase 2
- Ranked events from Phase 4

**Phase 5 produces:**

- PNG frame sequences per event
- Ready for video stitching in Phase 6

**Phase 5 ensures:**

- ✅ Deterministic rendering
- ✅ Mobile-optimized layout
- ✅ Proper frame ordering
- ✅ Correct specifications

**Integration:**

- Clean data pipeline
- Modular architecture
- Extensible configuration
- Production-ready code

---

**PHASE 5 INTEGRATION COMPLETE**

Ready to proceed to Phase 6: Video Stitching & Audio Synthesis
