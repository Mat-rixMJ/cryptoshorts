"""
Volume Pattern Detectors

Detects volume-related patterns and anomalies.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def detect_volume_spike(df: pd.DataFrame, idx: int, threshold: float = 2.0) -> Optional[dict]:
    """Detect significant volume spike vs moving average.
    
    Args:
        df: DataFrame with volume data
        idx: Current index to check
        threshold: Spike threshold (volume / volume_ma)
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if "volume_spike_ratio" not in df.columns:
        return None
    
    spike_ratio = df.loc[idx, "volume_spike_ratio"]
    
    if spike_ratio >= threshold:
        # Determine if accompanied by price move
        price_move = 0.0
        if idx > 0:
            price_move = ((df.loc[idx, "close"] - df.loc[idx - 1, "close"]) / df.loc[idx - 1, "close"]) * 100
        
        confidence = min(0.6 + (spike_ratio - threshold) * 0.1 + abs(price_move) * 0.05, 0.95)
        
        return {
            "pattern": "VOLUME_SPIKE",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [max(0, idx - 5), min(len(df) - 1, idx + 5)],
            "details": {
                "spike_ratio": round(spike_ratio, 2),
                "threshold": threshold,
                "price_change_pct": round(price_move, 3),
            }
        }
    
    return None


def detect_high_volume_breakout(df: pd.DataFrame, idx: int) -> Optional[dict]:
    """Detect breakout confirmed by high volume.
    
    Combines price breakout with volume confirmation.
    
    Args:
        df: DataFrame with OHLCV data
        idx: Current index to check
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < 20 or "volume_spike_ratio" not in df.columns:
        return None
    
    # Check if there's a significant price move
    if idx > 0:
        price_change = ((df.loc[idx, "close"] - df.loc[idx - 1, "close"]) / df.loc[idx - 1, "close"]) * 100
    else:
        return None
    
    # Require substantial price move (> 2%)
    if abs(price_change) < 2.0:
        return None
    
    # Check volume spike
    spike_ratio = df.loc[idx, "volume_spike_ratio"]
    
    if spike_ratio >= 1.5:  # Volume at least 50% above average
        direction = "BULLISH" if price_change > 0 else "BEARISH"
        
        confidence = min(0.7 + abs(price_change) * 0.02 + (spike_ratio - 1.5) * 0.1, 0.95)
        
        return {
            "pattern": f"HIGH_VOLUME_BREAKOUT_{direction}",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [max(0, idx - 10), min(len(df) - 1, idx + 10)],
            "details": {
                "price_change_pct": round(price_change, 3),
                "volume_spike_ratio": round(spike_ratio, 2),
                "direction": direction,
            }
        }
    
    return None


def detect_low_volume_fake_move(df: pd.DataFrame, idx: int) -> Optional[dict]:
    """Detect price move on unusually low volume (potentially fake).
    
    Args:
        df: DataFrame with OHLCV data
        idx: Current index to check
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < 1 or "volume_spike_ratio" not in df.columns:
        return None
    
    # Check for significant price move
    price_change = ((df.loc[idx, "close"] - df.loc[idx - 1, "close"]) / df.loc[idx - 1, "close"]) * 100
    
    if abs(price_change) < 1.5:  # Require at least 1.5% move
        return None
    
    # Check for low volume
    spike_ratio = df.loc[idx, "volume_spike_ratio"]
    
    if spike_ratio < 0.6:  # Volume below 60% of average
        confidence = min(0.65 + abs(price_change) * 0.02 + (0.6 - spike_ratio) * 0.3, 0.90)
        
        return {
            "pattern": "LOW_VOLUME_FAKE_MOVE",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [max(0, idx - 5), min(len(df) - 1, idx + 5)],
            "details": {
                "price_change_pct": round(price_change, 3),
                "volume_spike_ratio": round(spike_ratio, 2),
            }
        }
    
    return None


def detect_volume_patterns(df: pd.DataFrame) -> List[dict]:
    """Detect all volume-related patterns in the DataFrame.
    
    Args:
        df: DataFrame with OHLCV and volume data
        
    Returns:
        List of detected pattern events
    """
    events = []
    
    for idx in df.index:
        # Volume spike
        event = detect_volume_spike(df, idx, threshold=2.0)
        if event:
            events.append(event)
        
        # High volume breakout
        event = detect_high_volume_breakout(df, idx)
        if event:
            events.append(event)
        
        # Low volume fake move
        event = detect_low_volume_fake_move(df, idx)
        if event:
            events.append(event)
    
    logger.info(f"volume_patterns_detected count={len(events)}")
    return events
