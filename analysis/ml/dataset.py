"""
Event Dataset Creation Module

Creates event-level feature datasets for ML training.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# Patterns for encoding
PATTERN_ENCODING = {
    "EMA_CROSS_BULLISH": 1,
    "EMA_CROSS_BEARISH": 2,
    "PRICE_CROSS_EMA_BULLISH": 3,
    "EMA_TREND_ALIGNMENT": 4,
    "RSI_OVERSOLD_BOUNCE": 5,
    "RSI_OVERBOUGHT_REJECTION": 6,
    "RSI_BULLISH_DIVERGENCE": 7,
    "RSI_BEARISH_DIVERGENCE": 8,
    "RESISTANCE_BREAKOUT": 9,
    "SUPPORT_BREAKDOWN": 10,
    "FAKE_BREAKOUT": 11,
    "VOLUME_SPIKE": 12,
    "HIGH_VOLUME_BREAKOUT_BULLISH": 13,
    "HIGH_VOLUME_BREAKOUT_BEARISH": 14,
    "LOW_VOLUME_FAKE_MOVE": 15,
    "HIGHER_HIGH_HIGHER_LOW": 16,
    "LOWER_HIGH_LOWER_LOW": 17,
    "RANGE_COMPRESSION": 18,
}


def encode_pattern(pattern_name: str) -> int:
    """Encode pattern name to numeric value.
    
    Args:
        pattern_name: Name of the pattern
        
    Returns:
        Numeric encoding (default 0 for unknown)
    """
    return PATTERN_ENCODING.get(pattern_name, 0)


def get_feature_columns(df: pd.DataFrame) -> List[str]:
    """Extract feature column names from DataFrame.
    
    Excludes timestamp and OHLCV columns, includes all numeric features.
    
    Args:
        df: DataFrame with features
        
    Returns:
        List of feature column names
    """
    exclude_cols = {"timestamp", "open", "high", "low", "close", "volume"}
    
    feature_cols = [
        col for col in df.columns
        if col not in exclude_cols
        and pd.api.types.is_numeric_dtype(df[col])
    ]
    
    return sorted(feature_cols)


def create_event_dataset(
    df: pd.DataFrame,
    events: List[dict],
    include_future_return: bool = True,
) -> Tuple[pd.DataFrame, List[str]]:
    """Create event-level dataset for ML training.
    
    For each event, extracts features at the event index and creates
    a row in the output dataset.
    
    Args:
        df: Full DataFrame with indicators and features
        events: List of detected events with index field
        include_future_return: Whether to include future_return label
        
    Returns:
        Tuple of (event_dataset, feature_column_names)
    """
    feature_cols = get_feature_columns(df)
    
    rows = []
    
    for event in events:
        idx = event.get("index")
        
        # Skip invalid indexes
        if idx is None or idx not in df.index:
            logger.debug(f"skipping_event invalid_index={idx}")
            continue
        
        # Build row from event and features
        row = {
            "event_index": idx,
            "pattern": event.get("pattern"),
            "pattern_encoded": encode_pattern(event.get("pattern", "")),
            "confidence": event.get("confidence", 0.0),
        }
        
        # Add feature values at event index
        for col in feature_cols:
            if col in df.columns:
                row[f"feat_{col}"] = df.loc[idx, col]
        
        # Add optional future return label
        if include_future_return and "future_return" in event:
            row["future_return"] = event["future_return"]
        
        rows.append(row)
    
    dataset = pd.DataFrame(rows)
    
    logger.info(f"event_dataset_created rows={len(dataset)} features={len(feature_cols)}")
    
    # Return the actual feature column names from the dataset
    # These are: "pattern_encoded", "feat_atr", "feat_ema_20", ..., "feat_vwap"
    # Exclude metadata columns and label columns
    exclude_from_features = {"event_index", "pattern", "confidence", "future_return", "feat_future_return"}
    feature_column_names = [col for col in dataset.columns 
                           if col not in exclude_from_features]
    
    return dataset, feature_column_names


def handle_missing_features(
    dataset: pd.DataFrame,
    feature_cols: List[str],
    strategy: str = "drop",
) -> pd.DataFrame:
    """Handle missing values in feature dataset.
    
    Args:
        dataset: Event dataset with potential NaN values
        feature_cols: List of feature columns
        strategy: "drop" (remove rows) or "fill" (forward fill)
        
    Returns:
        Cleaned dataset
    """
    before = len(dataset)
    
    if strategy == "drop":
        cleaned = dataset.dropna(subset=feature_cols)
    elif strategy == "fill":
        cleaned = dataset.fillna(method="ffill").dropna(subset=feature_cols)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    after = len(cleaned)
    removed = before - after
    
    if removed > 0:
        logger.info(f"missing_features_handled strategy={strategy} removed={removed}")
    
    return cleaned


def validate_event_dataset(
    dataset: pd.DataFrame,
    feature_cols: List[str],
) -> bool:
    """Validate event dataset for training readiness.
    
    Args:
        dataset: Event dataset
        feature_cols: List of feature columns
        
    Returns:
        True if valid, False otherwise
    """
    if dataset.empty:
        logger.error("dataset_empty")
        return False
    
    missing_cols = [col for col in feature_cols if col not in dataset.columns]
    if missing_cols:
        logger.error(f"dataset_missing_columns cols={missing_cols}")
        return False
    
    nan_count = dataset[feature_cols].isna().sum().sum()
    if nan_count > 0:
        logger.warning(f"dataset_contains_nan count={nan_count}")
    
    logger.info(f"dataset_validated rows={len(dataset)} cols={len(feature_cols)}")
    return True
