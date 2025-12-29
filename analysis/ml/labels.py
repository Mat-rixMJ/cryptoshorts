"""
Label Generation Module

Creates future-based labels from price movement for model training.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_future_labels(
    df: pd.DataFrame,
    lookahead_candles: int = 10,
    return_column: str = "close",
) -> pd.DataFrame:
    """Compute future return labels for each candle.
    
    For each row, calculates the return from current close to future close
    within a lookahead window.
    
    Args:
        df: DataFrame with price data
        lookahead_candles: Number of candles to look ahead
        return_column: Column to use for return calculation
        
    Returns:
        DataFrame with 'future_return' column added
    """
    df = df.copy()
    
    # Shift price forward by lookahead_candles
    future_close = df[return_column].shift(-lookahead_candles)
    
    # Calculate returns
    current_close = df[return_column]
    returns = ((future_close - current_close) / current_close) * 100  # In percentage
    
    df["future_return"] = returns
    
    # Drop rows without valid future labels (last lookahead_candles)
    df_valid = df.dropna(subset=["future_return"]).copy()
    
    dropped = len(df) - len(df_valid)
    logger.info(
        f"labels_computed lookahead={lookahead_candles} "
        f"valid_rows={len(df_valid)} dropped={dropped}"
    )
    
    return df_valid


def clip_outlier_returns(
    returns: pd.Series,
    percentile_lower: float = 1.0,
    percentile_upper: float = 99.0,
) -> pd.Series:
    """Clip extreme returns to reduce model bias.
    
    Args:
        returns: Series of return values
        percentile_lower: Lower percentile threshold
        percentile_upper: Upper percentile threshold
        
    Returns:
        Clipped returns series
    """
    lower_bound = returns.quantile(percentile_lower / 100)
    upper_bound = returns.quantile(percentile_upper / 100)
    
    clipped = returns.clip(lower=lower_bound, upper=upper_bound)
    
    clipped_count = (clipped != returns).sum()
    if clipped_count > 0:
        logger.info(f"returns_clipped count={clipped_count} "
                   f"lower={lower_bound:.3f} upper={upper_bound:.3f}")
    
    return clipped


def compute_event_labels(
    df: pd.DataFrame,
    events: list[dict],
    lookahead_candles: int = 10,
) -> list[dict]:
    """Add future return labels to detected events.
    
    Args:
        df: Full DataFrame with future_return column
        events: List of detected events
        lookahead_candles: Lookahead window used for labels
        
    Returns:
        List of events with 'future_return' field added
    """
    labeled_events = []
    
    for event in events:
        idx = event.get("index")
        
        if idx is None or idx not in df.index:
            logger.warning(f"event_index_invalid index={idx}")
            continue
        
        # Get future return if available
        future_return = df.loc[idx, "future_return"]
        
        if pd.isna(future_return):
            logger.debug(f"event_future_return_na index={idx}")
            continue
        
        # Add label to event
        event_copy = event.copy()
        event_copy["future_return"] = round(future_return, 3)
        labeled_events.append(event_copy)
    
    logger.info(f"event_labels_added count={len(labeled_events)}")
    return labeled_events
