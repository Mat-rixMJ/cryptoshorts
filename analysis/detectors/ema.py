"""
EMA Pattern Detectors

Detects patterns related to Exponential Moving Averages.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def detect_ema_cross_bullish(df: pd.DataFrame, idx: int, fast: int = 20, slow: int = 50) -> Optional[dict]:
    """Detect bullish EMA crossover (fast crosses above slow).
    
    Args:
        df: DataFrame with EMA columns
        idx: Current index to check
        fast: Fast EMA period
        slow: Slow EMA period
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < 1:
        return None
    
    fast_col = f"ema_{fast}"
    slow_col = f"ema_{slow}"
    
    if fast_col not in df.columns or slow_col not in df.columns:
        return None
    
    # Check crossover: was below, now above
    prev_below = df.loc[idx - 1, fast_col] <= df.loc[idx - 1, slow_col]
    curr_above = df.loc[idx, fast_col] > df.loc[idx, slow_col]
    
    if prev_below and curr_above:
        # Calculate confidence based on separation and volume
        separation = ((df.loc[idx, fast_col] - df.loc[idx, slow_col]) / df.loc[idx, slow_col]) * 100
        confidence = min(0.5 + abs(separation) * 2, 1.0)  # Base 0.5, up to 1.0
        
        return {
            "pattern": "EMA_CROSS_BULLISH",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [max(0, idx - 10), min(len(df) - 1, idx + 10)],
            "details": {
                "ema_fast": fast,
                "ema_slow": slow,
                "separation_pct": round(separation, 3),
            }
        }
    
    return None


def detect_ema_cross_bearish(df: pd.DataFrame, idx: int, fast: int = 20, slow: int = 50) -> Optional[dict]:
    """Detect bearish EMA crossover (fast crosses below slow).
    
    Args:
        df: DataFrame with EMA columns
        idx: Current index to check
        fast: Fast EMA period
        slow: Slow EMA period
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < 1:
        return None
    
    fast_col = f"ema_{fast}"
    slow_col = f"ema_{slow}"
    
    if fast_col not in df.columns or slow_col not in df.columns:
        return None
    
    # Check crossover: was above, now below
    prev_above = df.loc[idx - 1, fast_col] >= df.loc[idx - 1, slow_col]
    curr_below = df.loc[idx, fast_col] < df.loc[idx, slow_col]
    
    if prev_above and curr_below:
        separation = ((df.loc[idx, slow_col] - df.loc[idx, fast_col]) / df.loc[idx, slow_col]) * 100
        confidence = min(0.5 + abs(separation) * 2, 1.0)
        
        return {
            "pattern": "EMA_CROSS_BEARISH",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [max(0, idx - 10), min(len(df) - 1, idx + 10)],
            "details": {
                "ema_fast": fast,
                "ema_slow": slow,
                "separation_pct": round(separation, 3),
            }
        }
    
    return None


def detect_price_cross_ema(df: pd.DataFrame, idx: int, period: int = 20) -> Optional[dict]:
    """Detect price crossing above EMA (bullish signal).
    
    Args:
        df: DataFrame with close and EMA columns
        idx: Current index to check
        period: EMA period to check against
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < 1:
        return None
    
    ema_col = f"ema_{period}"
    
    if ema_col not in df.columns:
        return None
    
    # Price crosses above EMA
    prev_below = df.loc[idx - 1, "close"] <= df.loc[idx - 1, ema_col]
    curr_above = df.loc[idx, "close"] > df.loc[idx, ema_col]
    
    if prev_below and curr_above:
        distance = ((df.loc[idx, "close"] - df.loc[idx, ema_col]) / df.loc[idx, ema_col]) * 100
        confidence = min(0.6 + abs(distance) * 3, 0.95)
        
        return {
            "pattern": "PRICE_CROSS_EMA_BULLISH",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [max(0, idx - 5), min(len(df) - 1, idx + 5)],
            "details": {
                "ema_period": period,
                "distance_pct": round(distance, 3),
            }
        }
    
    return None


def detect_ema_trend_alignment(df: pd.DataFrame, idx: int) -> Optional[dict]:
    """Detect bullish EMA trend alignment (EMA20 > EMA50 > EMA200).
    
    Args:
        df: DataFrame with EMA columns
        idx: Current index to check
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < 1:
        return None
    
    required_cols = ["ema_20", "ema_50", "ema_200"]
    if not all(col in df.columns for col in required_cols):
        return None
    
    # Check alignment at current index
    curr_aligned = (
        df.loc[idx, "ema_20"] > df.loc[idx, "ema_50"] > df.loc[idx, "ema_200"]
    )
    
    # Check if alignment just formed (wasn't aligned before)
    prev_aligned = (
        df.loc[idx - 1, "ema_20"] > df.loc[idx - 1, "ema_50"] > df.loc[idx - 1, "ema_200"]
    )
    
    if curr_aligned and not prev_aligned:
        # Calculate strength of alignment
        spread_20_50 = ((df.loc[idx, "ema_20"] - df.loc[idx, "ema_50"]) / df.loc[idx, "ema_50"]) * 100
        spread_50_200 = ((df.loc[idx, "ema_50"] - df.loc[idx, "ema_200"]) / df.loc[idx, "ema_200"]) * 100
        
        confidence = min(0.7 + (spread_20_50 + spread_50_200), 0.95)
        
        return {
            "pattern": "EMA_TREND_ALIGNMENT",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [max(0, idx - 20), min(len(df) - 1, idx + 20)],
            "details": {
                "spread_20_50_pct": round(spread_20_50, 3),
                "spread_50_200_pct": round(spread_50_200, 3),
            }
        }
    
    return None


def detect_ema_patterns(df: pd.DataFrame) -> List[dict]:
    """Detect all EMA-related patterns in the DataFrame.
    
    Args:
        df: DataFrame with OHLCV and EMA data
        
    Returns:
        List of detected pattern events
    """
    events = []
    
    for idx in df.index:
        # EMA crossovers
        event = detect_ema_cross_bullish(df, idx, fast=20, slow=50)
        if event:
            events.append(event)
        
        event = detect_ema_cross_bearish(df, idx, fast=20, slow=50)
        if event:
            events.append(event)
        
        # Price crossing EMA
        event = detect_price_cross_ema(df, idx, period=20)
        if event:
            events.append(event)
        
        # Trend alignment
        event = detect_ema_trend_alignment(df, idx)
        if event:
            events.append(event)
    
    logger.info(f"ema_patterns_detected count={len(events)}")
    return events
