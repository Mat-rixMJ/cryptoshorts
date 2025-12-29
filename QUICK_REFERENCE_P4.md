# Phase 4 Quick Reference

## Run the Demo

```bash
python example_ml_ranking.py
```

**Output:** 13 ranked events, model metrics, feature importance, explanations

## Quick Validation

```bash
python validate_phase_4.py
```

**Output:** Verification that all Phase 4 components work

## Module Overview

| Module     | Purpose                           | Key Function                                  |
| ---------- | --------------------------------- | --------------------------------------------- |
| labels.py  | Generate future-based labels      | `compute_future_labels()`                     |
| dataset.py | Create ML-ready dataset           | `create_event_dataset()`                      |
| model.py   | Model instantiation & persistence | `create_model()`, `load_model()`              |
| train.py   | Training pipeline                 | `train_model()`, `time_aware_split()`         |
| rank.py    | Score and rank events             | `score_events()`, `rank_events()`             |
| explain.py | Generate explanations             | `get_feature_importance()`, `explain_event()` |

## Key Statistics

**Data:**

- 714 price candles (1-hour BTC)
- 703 detected patterns
- 685 labeled events (97%)
- 22 technical features

**Model:**

- RandomForestRegressor (50 trees)
- 548 training / 137 validation split
- Validation Spearman: 0.44

**Output:**

- 13 high-quality ranked events
- Confidence range: 0.65-0.70
- 7 unique patterns represented

## Top Features (by importance)

1. VWAP (14.5%)
2. EMA-20 (9.5%)
3. EMA-200 (7.7%)
4. EMA-50 (5.4%)
5. Volume MA (5.4%)

## Output Format

```json
{
  "event_index": 63,
  "pattern": "PRICE_CROSS_EMA_BULLISH",
  "timestamp": "2025-12-02 09:00:00",
  "rule_confidence": 0.95,
  "ml_score": 0.703,
  "expected_move_pct": 4.31,
  "rank": 1,
  "ready_for_video": true
}
```

## Common Tasks

### Load pre-trained model

```python
from analysis.ml.model import load_model
model = load_model("analysis/ml/models/ranking_model.pkl")
```

### Score new events

```python
from analysis.ml.rank import prepare_events_for_scoring, score_events

scoring_df = prepare_events_for_scoring(events, df, feature_cols)
scored_df = score_events(model, scoring_df, feature_cols)
```

### Get feature importance

```python
from analysis.ml.explain import get_feature_importance

importance = get_feature_importance(model, feature_cols, top_k=10)
for feat, score in importance.items():
    print(f"{feat}: {score:.4f}")
```

### Explain a ranked event

```python
from analysis.ml.explain import explain_event

explanation = explain_event(event_row, importance, feature_cols)
print(explanation['top_contributing_features'])
```

## Architecture

```
Phases 1-3 Output (Events + Features)
           ↓
    compute_future_labels()
           ↓
    compute_event_labels()
           ↓
    create_event_dataset()
           ↓
    prepare_training_data()
           ↓
    train_model()
           ↓
    score_events()
           ↓
    rank_events()
           ↓
    Phase 5 Input (Ranked Events)
```

## Model Capabilities

✅ **Time-Aware Training** - No future leakage
✅ **Deterministic** - Reproducible results
✅ **Interpretable** - Feature importance & explanations
✅ **Persistent** - Save/load trained models
✅ **Configurable** - Adjustable thresholds & limits
✅ **JSON Output** - Easy integration with downstream systems
✅ **Production Ready** - Error handling & logging

## Next Steps

Phase 5 will use these ranked events for:

- Chart animation highlighting patterns
- Video generation with ML insights
- Social media content creation
- Performance tracking

---

See PHASE_4_COMPLETE.md for full details
