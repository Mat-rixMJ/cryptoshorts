"""
Example Usage: ML-Based Event Ranking (Phase 4)

Demonstrates how to:
1. Generate future-based labels
2. Create event-level dataset
3. Train ranking model
4. Score and rank events
5. Explain rankings
"""

import json
import logging
from pathlib import Path

import pandas as pd
import numpy as np

# Phase 2-3 imports
from analysis.indicators import calculate_indicators
from analysis.features import calculate_features
from analysis.utils import combine_and_clean
from analysis.patterns import detect_patterns, get_pattern_summary

# Phase 4 ML imports
from analysis.ml.labels import compute_future_labels, compute_event_labels
from analysis.ml.dataset import create_event_dataset, validate_event_dataset
from analysis.ml.model import create_model, save_model
from analysis.ml.train import time_aware_split, prepare_training_data, train_model
from analysis.ml.rank import (
    prepare_events_for_scoring,
    score_events,
    rank_events,
    get_ranking_summary,
)
from analysis.ml.explain import (
    explain_ranking_distribution,
    get_event_explanation_table,
    get_feature_importance,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def prepare_data_with_patterns() -> tuple[pd.DataFrame, list[dict]]:
    """Load data and detect patterns (Phase 1-3)."""
    
    # Load clean OHLCV data
    csv_path = Path("data/raw/BTC_USDT_1h.csv")
    logger.info(f"Loading data from {csv_path}")
    
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    
    # Calculate indicators
    logger.info("Calculating indicators...")
    indicators_df = calculate_indicators(df)
    
    # Calculate features
    df_with_indicators = pd.concat([df, indicators_df], axis=1)
    features_df = calculate_features(df_with_indicators)
    
    # Combine everything
    logger.info("Combining data...")
    final_df = combine_and_clean(
        ohlcv=df,
        indicators=indicators_df,
        features=features_df,
        drop_na=True
    )
    
    # Detect patterns
    logger.info("Detecting patterns...")
    events = detect_patterns(final_df, symbol="BTC/USDT")
    
    logger.info(f"Data prepared: {final_df.shape}, Events: {len(events)}")
    return final_df, events


def main():
    """Main execution flow for ML event ranking."""
    
    print("=" * 70)
    print("PHASE 4: ML-BASED EVENT RANKING")
    print("=" * 70)
    
    # Step 1: Prepare data with patterns
    df, events = prepare_data_with_patterns()
    
    # Step 2: Compute future labels
    logger.info("Computing future labels...")
    lookahead = 10
    df_labeled = compute_future_labels(df, lookahead_candles=lookahead)
    
    # Add labels to events
    events_labeled = compute_event_labels(df_labeled, events, lookahead_candles=lookahead)
    print(f"\nEvents with labels: {len(events_labeled)}")
    
    # Step 3: Create event dataset
    logger.info("Creating event dataset...")
    event_dataset, feature_cols = create_event_dataset(df_labeled, events_labeled)
    
    # Validate dataset
    is_valid = validate_event_dataset(event_dataset, feature_cols)
    if not is_valid:
        logger.error("Event dataset validation failed!")
        return
    
    # Step 4: Prepare training data
    X, y = prepare_training_data(event_dataset, feature_cols)
    
    # Time-aware split
    X_train, X_test, y_train, y_test = time_aware_split(X, y, test_size=0.2)
    
    # Step 5: Create and train model
    logger.info("Training ranking model...")
    model = create_model(model_type="random_forest", n_estimators=50)
    
    train_metrics = train_model(model, X_train, y_train, X_test, y_test)
    
    print("\n" + "=" * 70)
    print("MODEL TRAINING RESULTS")
    print("=" * 70)
    for metric, value in train_metrics.items():
        print(f"  {metric:.<40} {value}")
    
    # Step 6: Score all events
    logger.info("Scoring events...")
    scoring_df = prepare_events_for_scoring(events_labeled, df_labeled, feature_cols)
    scored_df = score_events(model, scoring_df, feature_cols)
    
    # Step 7: Rank events
    logger.info("Ranking events...")
    ranked_df = rank_events(scored_df, min_score=0.65, max_events_per_pattern=5)
    
    print("\n" + "=" * 70)
    print("RANKING SUMMARY")
    print("=" * 70)
    summary = get_ranking_summary(ranked_df)
    for key, value in summary.items():
        if key != "top_5_scores":
            print(f"  {key:.<40} {value}")
    
    # Step 8: Explainability
    logger.info("Generating explanations...")
    feature_importance = get_feature_importance(model, feature_cols, top_k=10)
    
    print("\n" + "=" * 70)
    print("TOP 10 IMPORTANT FEATURES")
    print("=" * 70)
    for i, (feat, imp) in enumerate(feature_importance.items(), 1):
        print(f"  {i:2d}. {feat:.<45} {imp:.4f}")
    
    # Step 9: Explain distribution
    dist_explanation = explain_ranking_distribution(ranked_df, feature_importance)
    
    print("\n" + "=" * 70)
    print("RANKING DISTRIBUTION")
    print("=" * 70)
    for key, value in dist_explanation["score_statistics"].items():
        print(f"  {key:.<40} {value}")
    
    # Step 10: Top events explanation table
    print("\n" + "=" * 70)
    print("TOP 5 EVENTS DETAILED EXPLANATION")
    print("=" * 70)
    explain_table = get_event_explanation_table(
        ranked_df, feature_importance, feature_cols, num_events=5
    )
    print(explain_table.to_string(index=False))
    
    # Step 11: Show sample ranked event
    if len(ranked_df) > 0:
        print("\n" + "=" * 70)
        print("SAMPLE RANKED EVENT")
        print("=" * 70)
        top_event = ranked_df.iloc[0]
        print(json.dumps({
            "event_index": int(top_event["event_index"]),
            "pattern": top_event["pattern"],
            "timestamp": str(top_event["timestamp"]),
            "rule_confidence": round(top_event["confidence"], 3),
            "ml_score": round(top_event["ml_score"], 3),
            "expected_move_pct": round(top_event["expected_move_pct"], 3),
            "rank": int(top_event["rank"]),
            "ready_for_video": bool(top_event["ready_for_video"]),
        }, indent=2))
    
    # Step 12: Save model
    model_path = Path("analysis/ml/models/ranking_model.pkl")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    save_model(model, model_path, metadata={
        "feature_cols": feature_cols,
        "model_type": "random_forest",
        "lookahead_candles": lookahead,
    })
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total detected events:       {len(events_labeled)}")
    print(f"High-quality ranked events:  {len(ranked_df)}")
    print(f"Ready for video:             {ranked_df['ready_for_video'].sum()}")
    print(f"Model saved to:              {model_path}")
    
    return model, ranked_df, feature_importance


if __name__ == "__main__":
    model_trained, events_ranked, importances = main()
