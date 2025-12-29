"""
Breakout Pattern Detectors

Detects price breakouts above resistance or below support.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def detect_resistance_breakout(df: pd.DataFrame, idx: int, lookback: int = 20) -> Optional[dict]:
    """Detect breakout above recent resistance level.
    
    Args:
        df: DataFrame with OHLC data
        idx: Current index to check
        lookback: Period to calculate resistance
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < lookback:
        return None
    
    # Calculate recent resistance (highest high in lookback period)
    window_start = max(0, idx - lookback)
    recent_resistance = df.loc[window_start:idx - 1, "high"].max()
    
    # Check if current close breaks above resistance
    curr_close = df.loc[idx, "close"]
    
    if curr_close > recent_resistance:
        # Calculate strength of breakout
        breakout_pct = ((curr_close - recent_resistance) / recent_resistance) * 100
        
        # Volume confirmation (if available)
        volume_conf = 0.0
        if "volume_spike_ratio" in df.columns:
            volume_conf = min(df.loc[idx, "volume_spike_ratio"] / 2, 0.3)
        
        confidence = min(0.6 + abs(breakout_pct) * 5 + volume_conf, 0.95)
        
        return {
            "pattern": "RESISTANCE_BREAKOUT",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [window_start, min(len(df) - 1, idx + 10)],
            "details": {
                "resistance_level": round(recent_resistance, 2),
                "breakout_pct": round(breakout_pct, 3),
                "lookback_periods": lookback,
            }
        }
    
    return None


def detect_support_breakdown(df: pd.DataFrame, idx: int, lookback: int = 20) -> Optional[dict]:
    """Detect breakdown below recent support level.
    
    Args:
        df: DataFrame with OHLC data
        idx: Current index to check
        lookback: Period to calculate support
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < lookback:
        return None
    
    # Calculate recent support (lowest low in lookback period)
    window_start = max(0, idx - lookback)
    recent_support = df.loc[window_start:idx - 1, "low"].min()
    
    # Check if current close breaks below support
    curr_close = df.loc[idx, "close"]
    
    if curr_close < recent_support:
        breakdown_pct = ((recent_support - curr_close) / recent_support) * 100
        
        # Volume confirmation
        volume_conf = 0.0
        if "volume_spike_ratio" in df.columns:
            volume_conf = min(df.loc[idx, "volume_spike_ratio"] / 2, 0.3)
        
        confidence = min(0.6 + abs(breakdown_pct) * 5 + volume_conf, 0.95)
        
        return {
            "pattern": "SUPPORT_BREAKDOWN",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [window_start, min(len(df) - 1, idx + 10)],
            "details": {
                "support_level": round(recent_support, 2),
                "breakdown_pct": round(breakdown_pct, 3),
                "lookback_periods": lookback,
            }
        }
    
    return None


def detect_fake_breakout(df: pd.DataFrame, idx: int, lookback: int = 20) -> Optional[dict]:
    """Detect fake breakout (break above resistance followed by quick rejection).
    
    Args:
        df: DataFrame with OHLC data
        idx: Current index to check
        lookback: Period to calculate resistance
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < lookback + 3:  # Need extra candles for rejection
        return None
    
    # Check if 2-3 candles ago there was a breakout
    check_idx = idx - 2
    window_start = max(0, check_idx - lookback)
    
    # Resistance before breakout
    resistance = df.loc[window_start:check_idx - 1, "high"].max()
    
    # Did we break above?
    broke_above = df.loc[check_idx, "close"] > resistance
    
    # Did we reject back below?
    curr_below = df.loc[idx, "close"] < resistance
    
    if broke_above and curr_below:
        rejection_pct = ((df.loc[check_idx, "close"] - df.loc[idx, "close"]) / df.loc[check_idx, "close"]) * 100
        
        confidence = min(0.65 + abs(rejection_pct) * 3, 0.90)
        
        return {
            "pattern": "FAKE_BREAKOUT",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [window_start, idx],
            "details": {
                "resistance_level": round(resistance, 2),
                "breakout_index": int(check_idx),
                "rejection_pct": round(rejection_pct, 3),
            }
        }
    
    return None


def detect_breakout_patterns(df: pd.DataFrame) -> List[dict]:
    """Detect all breakout-related patterns in the DataFrame.
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        List of detected pattern events
    """
    events = []
    
    for idx in df.index:
        # Resistance breakout
        event = detect_resistance_breakout(df, idx, lookback=20)
        if event:
            events.append(event)
        
        # Support breakdown
        event = detect_support_breakdown(df, idx, lookback=20)
        if event:
            events.append(event)
        
        # Fake breakout
        event = detect_fake_breakout(df, idx, lookback=20)
        if event:
            events.append(event)
    
    logger.info(f"breakout_patterns_detected count={len(events)}")
    return events
