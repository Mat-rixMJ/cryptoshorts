"""
Market Structure Pattern Detectors

Detects higher highs, lower lows, and structural patterns.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def detect_higher_high_higher_low(df: pd.DataFrame, idx: int, lookback: int = 10) -> Optional[dict]:
    """Detect bullish market structure (higher high + higher low).
    
    Args:
        df: DataFrame with OHLC data
        idx: Current index to check
        lookback: Period to look back for comparison
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < lookback + 5:
        return None
    
    # Find recent swing high and low in lookback window
    window_start = max(0, idx - lookback)
    window_end = idx - 3  # Exclude last few candles
    
    if window_end <= window_start:
        return None
    
    prev_high = df.loc[window_start:window_end, "high"].max()
    prev_low = df.loc[window_start:window_end, "low"].min()
    
    # Check current formation
    curr_high = df.loc[idx - 2:idx, "high"].max()
    curr_low = df.loc[idx - 2:idx, "low"].min()
    
    # Higher high and higher low
    if curr_high > prev_high and curr_low > prev_low:
        high_increase = ((curr_high - prev_high) / prev_high) * 100
        low_increase = ((curr_low - prev_low) / prev_low) * 100
        
        confidence = min(0.7 + (high_increase + low_increase) * 0.5, 0.95)
        
        return {
            "pattern": "HIGHER_HIGH_HIGHER_LOW",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [window_start, idx],
            "details": {
                "prev_high": round(prev_high, 2),
                "curr_high": round(curr_high, 2),
                "prev_low": round(prev_low, 2),
                "curr_low": round(curr_low, 2),
                "high_increase_pct": round(high_increase, 3),
                "low_increase_pct": round(low_increase, 3),
            }
        }
    
    return None


def detect_lower_high_lower_low(df: pd.DataFrame, idx: int, lookback: int = 10) -> Optional[dict]:
    """Detect bearish market structure (lower high + lower low).
    
    Args:
        df: DataFrame with OHLC data
        idx: Current index to check
        lookback: Period to look back for comparison
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < lookback + 5:
        return None
    
    window_start = max(0, idx - lookback)
    window_end = idx - 3
    
    if window_end <= window_start:
        return None
    
    prev_high = df.loc[window_start:window_end, "high"].max()
    prev_low = df.loc[window_start:window_end, "low"].min()
    
    curr_high = df.loc[idx - 2:idx, "high"].max()
    curr_low = df.loc[idx - 2:idx, "low"].min()
    
    # Lower high and lower low
    if curr_high < prev_high and curr_low < prev_low:
        high_decrease = ((prev_high - curr_high) / prev_high) * 100
        low_decrease = ((prev_low - curr_low) / prev_low) * 100
        
        confidence = min(0.7 + (high_decrease + low_decrease) * 0.5, 0.95)
        
        return {
            "pattern": "LOWER_HIGH_LOWER_LOW",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [window_start, idx],
            "details": {
                "prev_high": round(prev_high, 2),
                "curr_high": round(curr_high, 2),
                "prev_low": round(prev_low, 2),
                "curr_low": round(curr_low, 2),
                "high_decrease_pct": round(high_decrease, 3),
                "low_decrease_pct": round(low_decrease, 3),
            }
        }
    
    return None


def detect_range_compression(df: pd.DataFrame, idx: int, lookback: int = 20) -> Optional[dict]:
    """Detect range compression / volatility squeeze.
    
    Identifies when price range is contracting, often preceding a breakout.
    
    Args:
        df: DataFrame with OHLC data
        idx: Current index to check
        lookback: Period to calculate compression
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < lookback + 10 or "atr" not in df.columns:
        return None
    
    # Compare recent ATR to historical ATR
    recent_atr = df.loc[idx - 5:idx, "atr"].mean()
    historical_atr = df.loc[idx - lookback:idx - 6, "atr"].mean()
    
    if historical_atr == 0:
        return None
    
    compression_ratio = recent_atr / historical_atr
    
    # Compression detected if recent ATR is significantly lower
    if compression_ratio < 0.7:  # Recent volatility is < 70% of historical
        confidence = min(0.65 + (0.7 - compression_ratio) * 2, 0.90)
        
        return {
            "pattern": "RANGE_COMPRESSION",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [max(0, idx - lookback), min(len(df) - 1, idx + 10)],
            "details": {
                "compression_ratio": round(compression_ratio, 3),
                "recent_atr": round(recent_atr, 2),
                "historical_atr": round(historical_atr, 2),
            }
        }
    
    return None


def detect_structure_patterns(df: pd.DataFrame) -> List[dict]:
    """Detect all market structure patterns in the DataFrame.
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        List of detected pattern events
    """
    events = []
    
    for idx in df.index:
        # Higher high, higher low
        event = detect_higher_high_higher_low(df, idx, lookback=10)
        if event:
            events.append(event)
        
        # Lower high, lower low
        event = detect_lower_high_lower_low(df, idx, lookback=10)
        if event:
            events.append(event)
        
        # Range compression
        event = detect_range_compression(df, idx, lookback=20)
        if event:
            events.append(event)
    
    logger.info(f"structure_patterns_detected count={len(events)}")
    return events
