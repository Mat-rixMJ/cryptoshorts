"""
Event Ranking and Scoring Module

Scores detected events using trained ML model.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import pandas as pd

from analysis.ml.dataset import encode_pattern

logger = logging.getLogger(__name__)


def prepare_events_for_scoring(
    events: List[dict],
    df: pd.DataFrame,
    feature_cols: List[str],
) -> pd.DataFrame:
    """Prepare events for ML scoring by extracting features.
    
    Args:
        events: List of detected events
        df: DataFrame with features (clean column names without "feat_" prefix)
        feature_cols: List of feature column names from create_event_dataset
                     (these have "feat_" prefix like ["feat_atr", "feat_ema_20"])
        
    Returns:
        DataFrame with event features ready for scoring
    """
    rows = []
    
    for event in events:
        idx = event.get("index")
        
        if idx not in df.index:
            logger.debug(f"skipping_event_scoring invalid_index={idx}")
            continue
        
        # Build feature row
        row = {
            "event_index": idx,
            "pattern": event.get("pattern"),
            "timestamp": event.get("timestamp"),
            "confidence": event.get("confidence", 0.0),
        }
        
        # Add features - feature_cols have "feat_" prefix like "feat_atr"
        # We need to strip that to access the actual dataframe columns
        for feat_col in feature_cols:
            if feat_col == "pattern_encoded":
                # Special case: pattern_encoded comes from the pattern name
                row["pattern_encoded"] = encode_pattern(event.get("pattern", ""))
            elif feat_col.startswith("feat_"):
                # Strip "feat_" prefix to get original column name  
                clean_col = feat_col[5:]  # Remove "feat_" prefix
                if clean_col in df.columns:
                    row[feat_col] = df.loc[idx, clean_col]
            else:
                # Just in case, handle case where it's not prefixed
                if feat_col in df.columns:
                    row[feat_col] = df.loc[idx, feat_col]
        
        rows.append(row)
    
    scoring_df = pd.DataFrame(rows)
    logger.info(f"events_prepared_for_scoring count={len(scoring_df)}")
    
    return scoring_df


def score_events(
    model,
    scoring_df: pd.DataFrame,
    feature_cols: List[str],
) -> pd.DataFrame:
    """Score events using trained model.
    
    Args:
        model: Trained regression model
        scoring_df: DataFrame with event features
        feature_cols: List of feature column names (including "pattern_encoded", with "feat_" prefix on others)
        
    Returns:
        DataFrame with ml_score added
    """
    # Model was trained on feature_cols (which already includes "pattern_encoded")
    # No need to add it separately
    model_feature_cols = feature_cols
    
    # Verify that all required columns exist
    missing_cols = [col for col in model_feature_cols if col not in scoring_df.columns]
    if missing_cols:
        logger.warning(f"missing_features_in_scoring missing={missing_cols}")
        # Fill missing columns with 0
        for col in missing_cols:
            scoring_df[col] = 0.0
    
    # Prepare feature matrix - ensure same column order and names as during training
    X_scoring = scoring_df[model_feature_cols].fillna(0)
    
    # Get raw predictions (expected future return %)
    raw_scores = model.predict(X_scoring)
    
    # Normalize to 0-1 range (sigmoid normalization)
    # Handle extremely negative/positive returns
    ml_scores = 1 / (1 + np.exp(-raw_scores / 5))  # Scaled by 5 for reasonable range
    
    scoring_df = scoring_df.copy()
    scoring_df["ml_score"] = np.clip(ml_scores, 0.0, 1.0)
    scoring_df["expected_move_pct"] = raw_scores
    
    logger.info(f"events_scored count={len(scoring_df)} "
               f"score_range=[{scoring_df['ml_score'].min():.3f}, {scoring_df['ml_score'].max():.3f}]")
    
    return scoring_df


def rank_events(
    scored_df: pd.DataFrame,
    min_score: float = 0.65,
    max_events_per_pattern: Optional[int] = None,
) -> pd.DataFrame:
    """Rank and filter events by ML score.
    
    Args:
        scored_df: DataFrame with ml_score column
        min_score: Minimum score threshold for video selection
        max_events_per_pattern: Max events to keep per pattern type (optional)
        
    Returns:
        Ranked and filtered DataFrame
    """
    # Sort by score descending
    ranked = scored_df.sort_values("ml_score", ascending=False).reset_index(drop=True)
    
    # Add rank column
    ranked["rank"] = range(1, len(ranked) + 1)
    
    # Filter by minimum score
    filtered = ranked[ranked["ml_score"] >= min_score].copy()
    
    removed_by_score = len(ranked) - len(filtered)
    if removed_by_score > 0:
        logger.info(f"events_filtered_by_score removed={removed_by_score} min_score={min_score}")
    
    # Filter by max per pattern if specified
    if max_events_per_pattern:
        filtered = filtered.groupby("pattern").head(max_events_per_pattern).reset_index(drop=True)
        logger.info(f"events_filtered_by_pattern max_per_pattern={max_events_per_pattern}")
    
    # Add video readiness flag
    filtered["ready_for_video"] = (filtered["ml_score"] >= min_score).astype(bool)
    
    logger.info(f"events_ranked total={len(ranked)} accepted={len(filtered)}")
    
    return filtered


def get_ranking_summary(ranked_df: pd.DataFrame) -> dict:
    """Get summary statistics of ranked events.
    
    Args:
        ranked_df: Ranked DataFrame
        
    Returns:
        Summary dict
    """
    return {
        "total_events": len(ranked_df),
        "avg_score": round(ranked_df["ml_score"].mean(), 4),
        "std_score": round(ranked_df["ml_score"].std(), 4),
        "top_pattern": ranked_df["pattern"].value_counts().index[0] if len(ranked_df) > 0 else None,
        "patterns_count": ranked_df["pattern"].nunique(),
        "top_5_scores": ranked_df["ml_score"].nlargest(5).tolist(),
    }
