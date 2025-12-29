# Analysis ML Module - Event Ranking System

Event-based machine learning ranking system for scoring detected trading patterns by their likelihood of producing significant post-event price movement.

## Quick Start

```python
from analysis.ml.labels import compute_future_labels, compute_event_labels
from analysis.ml.dataset import create_event_dataset, validate_event_dataset
from analysis.ml.model import create_model, save_model
from analysis.ml.train import time_aware_split, prepare_training_data, train_model
from analysis.ml.rank import prepare_events_for_scoring, score_events, rank_events
from analysis.ml.explain import get_feature_importance, explain_event

# Prepare data (df with features, events list with patterns)
df_labeled = compute_future_labels(df, lookahead_candles=10)
events_labeled = compute_event_labels(df_labeled, events)

# Create dataset
event_dataset, feature_cols = create_event_dataset(df_labeled, events_labeled)

# Train model
X, y = prepare_training_data(event_dataset, feature_cols)
X_train, X_test, y_train, y_test = time_aware_split(X, y, test_size=0.2)

model = create_model(model_type="random_forest", n_estimators=50)
metrics = train_model(model, X_train, y_train, X_test, y_test)

# Score and rank events
scoring_df = prepare_events_for_scoring(events_labeled, df_labeled, feature_cols)
scored_df = score_events(model, scoring_df, feature_cols)
ranked_df = rank_events(scored_df, min_score=0.65, max_events_per_pattern=5)

# Explain rankings
feature_importance = get_feature_importance(model, feature_cols, top_k=10)
explanation = explain_event(ranked_df.iloc[0], feature_importance, feature_cols)
```

## Module Architecture

### 1. Labels Module (`labels.py`)

Generate binary labels from future price movement.

```python
compute_future_labels(df, lookahead_candles=10) → df with 'future_return' column
compute_event_labels(df, events) → events with 'future_return' field
```

**Use case:** Create training targets from future price data
**Time awareness:** No future leakage - labels computed from forward-looking prices

### 2. Dataset Module (`dataset.py`)

Transform events into ML-ready feature rows.

```python
create_event_dataset(df, events, include_future_return=True) → (dataset_df, feature_cols)
validate_event_dataset(dataset, feature_cols) → bool
get_feature_columns(df) → list of feature column names
encode_pattern(pattern_name) → int (1-18)
```

**Features generated:** 22 technical indicators + 1 pattern encoding
**Output shape:** (n*events, 25) with columns: event_index, pattern, pattern_encoded, confidence, feat*\*, future_return

### 3. Model Module (`model.py`)

Create, train, save, and load ML models.

```python
create_model(model_type="random_forest", n_estimators=50) → model
save_model(model, path) → None
load_model(path) → model
get_feature_importance(model, feature_names) → dict
```

**Supported models:**

- RandomForestRegressor (default) - Fast, robust, interpretable
- GradientBoostingRegressor - Slightly better performance, slower

### 4. Train Module (`train.py`)

Training pipeline with time-aware validation split.

```python
prepare_training_data(dataset, feature_cols) → (X, y)
time_aware_split(X, y, test_size=0.2) → (X_train, X_test, y_train, y_test)
train_model(model, X_train, y_train, X_val, y_val) → metrics_dict
evaluate_model(model, X, y) → metrics_dict
```

**Time awareness:** Chronological split ensures no future data in training set

### 5. Rank Module (`rank.py`)

Score events and generate ranked lists.

```python
prepare_events_for_scoring(events, df, feature_cols) → scoring_df
score_events(model, scoring_df, feature_cols) → scored_df with ml_score
rank_events(scored_df, min_score=0.65, max_events_per_pattern=5) → ranked_df
get_ranking_summary(ranked_df) → dict with statistics
```

**Output fields:**

- `ml_score`: Confidence (0-1) from sigmoid-normalized model output
- `expected_move_pct`: Raw model prediction (% price movement)
- `rank`: Position in sorted ranking
- `ready_for_video`: Boolean indicating content-readiness

### 6. Explain Module (`explain.py`)

Generate interpretable explanations for rankings.

```python
get_feature_importance(model, feature_names, top_k=10) → dict
explain_event(event_row, feature_importance, feature_cols, top_k=5) → explanation_dict
explain_ranking_distribution(ranked_df) → statistics_dict
get_event_explanation_table(ranked_df, feature_importance, feature_cols) → formatted_table
```

## Data Flow

```
Phases 1-3 Output
├── df (714 rows, 27 cols)
│   └── OHLCV, indicators, features
└── events (703 detected patterns)
    └── timestamp, pattern, confidence, index

        ↓ compute_future_labels()

df_labeled (714 rows, with future_return)

        ↓ compute_event_labels()

events_labeled (events with future_return)

        ↓ create_event_dataset()

event_dataset (685 rows, 25 cols)
├── event_index, pattern, pattern_encoded
├── confidence
├── feat_atr, feat_ema_20, ... (22 features)
└── future_return (label)

        ↓ prepare_training_data()

X (685 rows, 23 cols), y (685 values)
├── event_index, pattern_encoded, feat_*

        ↓ time_aware_split()

X_train (548), X_test (137)
y_train (548), y_test (137)

        ↓ train_model()

Trained RandomForest model + metrics

        ↓ prepare_events_for_scoring() + score_events()

scored_df (685 rows)
├── event metadata
├── model features
├── ml_score (0-1 confidence)
└── expected_move_pct

        ↓ rank_events()

ranked_df (13 rows, filtered & sorted)
├── High-quality events only
└── ready_for_video = true

Phase 5 Input
└── JSON with ranked events
```

## Configuration

### Model Selection

```python
# Use Random Forest (default)
model = create_model(model_type="random_forest", n_estimators=50)

# Use Gradient Boosting (slower, potentially better)
model = create_model(model_type="gradient_boosting",
                     n_estimators=50,
                     learning_rate=0.1,
                     max_depth=5)
```

### Ranking Filters

```python
ranked_df = rank_events(
    scored_df,
    min_score=0.65,              # Only keep events with ml_score ≥ 0.65
    max_events_per_pattern=5     # Max 5 events per pattern type
)
```

### Future Label Window

```python
df_labeled = compute_future_labels(
    df,
    lookahead_candles=10  # Predict 10-candle future movement (default)
)
```

## Output Format

### Ranked Event JSON

```json
{
  "event_index": 63,
  "pattern": "PRICE_CROSS_EMA_BULLISH",
  "timestamp": "2025-12-02 09:00:00+00:00",
  "rule_confidence": 0.95,
  "ml_score": 0.703,
  "expected_move_pct": 4.307,
  "rank": 1,
  "ready_for_video": true
}
```

### Feature Importance

```json
{
  "feat_vwap": 0.1451,
  "feat_ema_20": 0.0950,
  "feat_ema_200": 0.0770,
  ...
}
```

### Event Explanation

```python
{
  "event_index": 63,
  "pattern": "PRICE_CROSS_EMA_BULLISH",
  "ml_score": 0.703,
  "rule_confidence": 0.95,
  "expected_move_pct": 4.307,
  "top_contributing_features": [
    {"feature": "feat_vwap", "value": 88107.961, "importance": 0.1451},
    {"feature": "feat_ema_20", "value": 86629.194, "importance": 0.0950},
    {"feature": "feat_ema_200", "value": 70826.342, "importance": 0.0770}
  ]
}
```

## Key Design Principles

### 1. **Deterministic**

- All operations use `random_state=42`
- Identical training data → identical model
- Reproducible rankings across runs

### 2. **Time-Aware**

- Chronological train/test split prevents future leakage
- Historical events for training, recent events for validation
- Realistic performance estimation

### 3. **Explainable**

- Feature importance ranking
- Per-event top contributing features
- Distribution analysis of rankings

### 4. **Scalable**

- CPU-only computation
- Efficient DataFrame operations
- Batch processing ready

### 5. **Production-Ready**

- Comprehensive error handling
- Detailed logging at each step
- Model serialization/deserialization
- JSON-serializable output

## Performance Metrics

For the example BTC dataset (714 candles, 703 events):

```
Training: 548 events
Validation: 137 events

Model: RandomForestRegressor (50 trees)

Metrics:
  Train RMSE: 0.2929
  Val RMSE:   0.8475
  Train MAE:  0.1772
  Val MAE:    0.5897
  Spearman:   0.4391 (ranking correlation)

Output:
  Total events ranked: 13 (min_score ≥ 0.65)
  Score range: [0.6502, 0.7030]
  Ready for Phase 5: 13 events
```

## Logging

All modules use Python's `logging` module. Configure as needed:

```python
import logging

# Show debug messages
logging.basicConfig(level=logging.DEBUG)

# Show only warnings and errors
logging.basicConfig(level=logging.WARNING)
```

## Error Handling

All modules include error handling for:

- Missing or invalid data
- Index misalignment
- Feature/column naming issues
- Model persistence failures

Warnings are logged but execution continues when non-critical.

## Dependencies

- pandas >= 1.0
- numpy >= 1.18
- scikit-learn >= 0.24
- scipy >= 1.5
- joblib >= 1.0 (for model persistence)

## Testing

Run the example script to validate:

```bash
python example_ml_ranking.py
```

Expected output:

- Model trained with validation metrics
- 13-685 events ranked (configurable)
- Feature importance ranking
- Event explanations
- Model saved to `analysis/ml/models/ranking_model.pkl`

## Next Steps (Phase 5)

Use ranked events for:

- **Chart Animation**: Highlight patterns and expected movement
- **Video Generation**: Create educational content about specific events
- **Content Curation**: Select events for social media posts
- **Performance Analysis**: Track actual vs predicted movement

---

**Module Version:** 1.0  
**Status:** Production Ready ✅  
**Last Updated:** 2025-12-29
