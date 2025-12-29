"""
RSI Pattern Detectors

Detects patterns related to Relative Strength Index.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def detect_rsi_oversold_bounce(df: pd.DataFrame, idx: int, threshold: float = 30) -> Optional[dict]:
    """Detect RSI oversold bounce (<30 and rising).
    
    Args:
        df: DataFrame with RSI column
        idx: Current index to check
        threshold: Oversold threshold (default 30)
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < 2 or "rsi" not in df.columns:
        return None
    
    # Check: was oversold, now rising
    prev_oversold = df.loc[idx - 1, "rsi"] < threshold
    curr_rising = df.loc[idx, "rsi"] > df.loc[idx - 1, "rsi"]
    still_near_oversold = df.loc[idx, "rsi"] < threshold + 10  # Within 10 points of threshold
    
    if prev_oversold and curr_rising and still_near_oversold:
        # Confidence based on momentum of bounce
        rsi_change = df.loc[idx, "rsi"] - df.loc[idx - 2, "rsi"]
        confidence = min(0.6 + (rsi_change / 20), 0.95)
        
        return {
            "pattern": "RSI_OVERSOLD_BOUNCE",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [max(0, idx - 10), min(len(df) - 1, idx + 10)],
            "details": {
                "rsi_value": round(df.loc[idx, "rsi"], 2),
                "rsi_change": round(rsi_change, 2),
                "threshold": threshold,
            }
        }
    
    return None


def detect_rsi_overbought_rejection(df: pd.DataFrame, idx: int, threshold: float = 70) -> Optional[dict]:
    """Detect RSI overbought rejection (>70 and falling).
    
    Args:
        df: DataFrame with RSI column
        idx: Current index to check
        threshold: Overbought threshold (default 70)
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < 2 or "rsi" not in df.columns:
        return None
    
    # Check: was overbought, now falling
    prev_overbought = df.loc[idx - 1, "rsi"] > threshold
    curr_falling = df.loc[idx, "rsi"] < df.loc[idx - 1, "rsi"]
    still_near_overbought = df.loc[idx, "rsi"] > threshold - 10
    
    if prev_overbought and curr_falling and still_near_overbought:
        rsi_change = df.loc[idx - 2, "rsi"] - df.loc[idx, "rsi"]
        confidence = min(0.6 + (rsi_change / 20), 0.95)
        
        return {
            "pattern": "RSI_OVERBOUGHT_REJECTION",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [max(0, idx - 10), min(len(df) - 1, idx + 10)],
            "details": {
                "rsi_value": round(df.loc[idx, "rsi"], 2),
                "rsi_change": round(rsi_change, 2),
                "threshold": threshold,
            }
        }
    
    return None


def detect_rsi_bullish_divergence(df: pd.DataFrame, idx: int, lookback: int = 20) -> Optional[dict]:
    """Detect simple RSI bullish divergence (price makes lower low, RSI makes higher low).
    
    Args:
        df: DataFrame with close and RSI columns
        idx: Current index to check
        lookback: Period to look back for divergence
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < lookback or "rsi" not in df.columns:
        return None
    
    # Find recent low in price and RSI
    window_start = max(0, idx - lookback)
    price_window = df.loc[window_start:idx, "close"]
    rsi_window = df.loc[window_start:idx, "rsi"]
    
    if len(price_window) < 5 or len(rsi_window) < 5:
        return None
    
    # Find the lowest price point in window (excluding current)
    prev_price_low_idx = price_window.iloc[:-1].idxmin()
    curr_price = df.loc[idx, "close"]
    prev_price_low = df.loc[prev_price_low_idx, "close"]
    
    # Check if current price is lower than previous low
    if curr_price >= prev_price_low:
        return None
    
    # Check if RSI is higher than it was at previous low
    prev_rsi_at_low = df.loc[prev_price_low_idx, "rsi"]
    curr_rsi = df.loc[idx, "rsi"]
    
    if curr_rsi > prev_rsi_at_low:
        # Divergence detected
        price_diff_pct = ((prev_price_low - curr_price) / curr_price) * 100
        rsi_diff = curr_rsi - prev_rsi_at_low
        
        confidence = min(0.65 + (rsi_diff / 50), 0.90)
        
        return {
            "pattern": "RSI_BULLISH_DIVERGENCE",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [window_start, idx],
            "details": {
                "curr_rsi": round(curr_rsi, 2),
                "prev_rsi": round(prev_rsi_at_low, 2),
                "rsi_diff": round(rsi_diff, 2),
                "price_diff_pct": round(price_diff_pct, 2),
                "prev_low_index": int(prev_price_low_idx),
            }
        }
    
    return None


def detect_rsi_bearish_divergence(df: pd.DataFrame, idx: int, lookback: int = 20) -> Optional[dict]:
    """Detect simple RSI bearish divergence (price makes higher high, RSI makes lower high).
    
    Args:
        df: DataFrame with close and RSI columns
        idx: Current index to check
        lookback: Period to look back for divergence
        
    Returns:
        Event dict if pattern detected, None otherwise
    """
    if idx < lookback or "rsi" not in df.columns:
        return None
    
    window_start = max(0, idx - lookback)
    price_window = df.loc[window_start:idx, "close"]
    rsi_window = df.loc[window_start:idx, "rsi"]
    
    if len(price_window) < 5 or len(rsi_window) < 5:
        return None
    
    # Find the highest price point in window (excluding current)
    prev_price_high_idx = price_window.iloc[:-1].idxmax()
    curr_price = df.loc[idx, "close"]
    prev_price_high = df.loc[prev_price_high_idx, "close"]
    
    # Check if current price is higher than previous high
    if curr_price <= prev_price_high:
        return None
    
    # Check if RSI is lower than it was at previous high
    prev_rsi_at_high = df.loc[prev_price_high_idx, "rsi"]
    curr_rsi = df.loc[idx, "rsi"]
    
    if curr_rsi < prev_rsi_at_high:
        price_diff_pct = ((curr_price - prev_price_high) / prev_price_high) * 100
        rsi_diff = prev_rsi_at_high - curr_rsi
        
        confidence = min(0.65 + (rsi_diff / 50), 0.90)
        
        return {
            "pattern": "RSI_BEARISH_DIVERGENCE",
            "index": idx,
            "timestamp": df.loc[idx, "timestamp"],
            "confidence": round(confidence, 3),
            "window": [window_start, idx],
            "details": {
                "curr_rsi": round(curr_rsi, 2),
                "prev_rsi": round(prev_rsi_at_high, 2),
                "rsi_diff": round(rsi_diff, 2),
                "price_diff_pct": round(price_diff_pct, 2),
                "prev_high_index": int(prev_price_high_idx),
            }
        }
    
    return None


def detect_rsi_patterns(df: pd.DataFrame) -> List[dict]:
    """Detect all RSI-related patterns in the DataFrame.
    
    Args:
        df: DataFrame with OHLCV and RSI data
        
    Returns:
        List of detected pattern events
    """
    events = []
    
    for idx in df.index:
        # Oversold bounce
        event = detect_rsi_oversold_bounce(df, idx)
        if event:
            events.append(event)
        
        # Overbought rejection
        event = detect_rsi_overbought_rejection(df, idx)
        if event:
            events.append(event)
        
        # Bullish divergence
        event = detect_rsi_bullish_divergence(df, idx, lookback=20)
        if event:
            events.append(event)
        
        # Bearish divergence
        event = detect_rsi_bearish_divergence(df, idx, lookback=20)
        if event:
            events.append(event)
    
    logger.info(f"rsi_patterns_detected count={len(events)}")
    return events
