"""
Explainability Module

Provides interpretable explanations for event rankings.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def get_feature_importance(
    model,
    feature_names: List[str],
    top_k: int = 10,
) -> Dict[str, float]:
    """Get top-K important features from trained model.
    
    Args:
        model: Trained model
        feature_names: List of feature names
        top_k: Number of top features to return
        
    Returns:
        Dict mapping feature names to importance scores
    """
    importances = model.feature_importances_
    
    # Create importance dict
    feature_importance = {
        name: round(float(imp), 4)
        for name, imp in zip(feature_names, importances)
        if name != "event_index"  # Skip non-feature columns
    }
    
    # Sort and take top-K
    sorted_importance = dict(
        sorted(feature_importance.items(), key=lambda x: -x[1])[:top_k]
    )
    
    logger.info(f"feature_importance_extracted top_{top_k}={list(sorted_importance.keys())}")
    
    return sorted_importance


def explain_event(
    event_row: pd.Series,
    feature_importance: Dict[str, float],
    feature_cols: List[str],
    top_k: int = 5,
) -> dict:
    """Generate explanation for a single event's ranking.
    
    Args:
        event_row: Row from ranked DataFrame
        feature_importance: Dict of global feature importances
        feature_cols: List of feature columns (clean names)
        top_k: Number of top contributing features to return
        
    Returns:
        Explanation dict
    """
    explanation = {
        "event_index": int(event_row.get("event_index", -1)),
        "pattern": event_row.get("pattern"),
        "ml_score": round(float(event_row.get("ml_score", 0)), 4),
        "rule_confidence": round(float(event_row.get("confidence", 0)), 4),
        "expected_move_pct": round(float(event_row.get("expected_move_pct", 0)), 3),
    }
    
    # Extract feature values for this event (feature_cols are clean names)
    event_features = {}
    for col in feature_cols:
        if col in event_row.index:
            value = event_row[col]
            if pd.notna(value):
                event_features[col] = round(float(value), 3)
    
    # Get top contributing features
    top_contributing = []
    for feat_name, importance in sorted(
        feature_importance.items(), key=lambda x: -x[1]
    )[:top_k]:
        # feat_name is already clean (no feat_ prefix from get_feature_importance)
        if feat_name in event_features:
            top_contributing.append({
                "feature": feat_name,
                "value": event_features[feat_name],
                "importance": importance,
            })
    
    explanation["top_contributing_features"] = top_contributing
    
    return explanation


def explain_ranking_distribution(
    ranked_df: pd.DataFrame,
    feature_importance: Dict[str, float],
) -> dict:
    """Explain the overall ranking distribution.
    
    Args:
        ranked_df: Ranked events DataFrame
        feature_importance: Global feature importances
        
    Returns:
        Distribution explanation dict
    """
    explanation = {
        "total_events": len(ranked_df),
        "score_statistics": {
            "mean": round(ranked_df["ml_score"].mean(), 4),
            "median": round(ranked_df["ml_score"].median(), 4),
            "std": round(ranked_df["ml_score"].std(), 4),
            "min": round(ranked_df["ml_score"].min(), 4),
            "max": round(ranked_df["ml_score"].max(), 4),
        },
        "pattern_distribution": ranked_df["pattern"].value_counts().to_dict(),
        "top_10_features": dict(
            sorted(feature_importance.items(), key=lambda x: -x[1])[:10]
        ),
    }
    
    return explanation


def get_event_explanation_table(
    ranked_df: pd.DataFrame,
    feature_importance: Dict[str, float],
    feature_cols: List[str],
    num_events: int = 5,
) -> pd.DataFrame:
    """Create explanation table for top-ranked events.
    
    Args:
        ranked_df: Ranked events DataFrame
        feature_importance: Global feature importances
        feature_cols: List of feature columns
        num_events: Number of top events to explain
        
    Returns:
        Explanation DataFrame
    """
    explanations = []
    
    for idx, row in ranked_df.head(num_events).iterrows():
        exp = explain_event(row, feature_importance, feature_cols, top_k=3)
        
        # Flatten for DataFrame
        flat_exp = {
            "rank": idx + 1,
            "event_index": exp["event_index"],
            "pattern": exp["pattern"],
            "ml_score": exp["ml_score"],
            "expected_move_pct": exp["expected_move_pct"],
        }
        
        # Add top contributing features
        for i, contrib in enumerate(exp["top_contributing_features"][:3]):
            flat_exp[f"feat_{i+1}_name"] = contrib["feature"]
            flat_exp[f"feat_{i+1}_value"] = contrib["value"]
            flat_exp[f"feat_{i+1}_importance"] = contrib["importance"]
        
        explanations.append(flat_exp)
    
    return pd.DataFrame(explanations)
