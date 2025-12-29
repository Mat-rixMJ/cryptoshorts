"""
Technical Indicator Calculation Module

Computes standard technical indicators using pandas-ta and custom implementations.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = "close") -> pd.Series:
    """Calculate Relative Strength Index (RSI).
    
    RSI measures momentum on a 0-100 scale. Values above 70 indicate overbought,
    below 30 indicate oversold conditions.
    
    Args:
        df: DataFrame with OHLCV data
        period: Lookback period for RSI calculation
        column: Price column to use
        
    Returns:
        Series with RSI values
    """
    try:
        import pandas_ta as ta
        rsi = ta.rsi(df[column], length=period)
        logger.info(f"rsi_calculated period={period}")
        return rsi
    except ImportError:
        # Fallback implementation
        delta = df[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        logger.info(f"rsi_calculated period={period} method=fallback")
        return rsi


def calculate_ema(df: pd.DataFrame, periods: list[int], column: str = "close") -> pd.DataFrame:
    """Calculate Exponential Moving Averages.
    
    EMA gives more weight to recent prices, making it more responsive than SMA.
    
    Args:
        df: DataFrame with OHLCV data
        periods: List of EMA periods to calculate
        column: Price column to use
        
    Returns:
        DataFrame with EMA columns named 'ema_{period}'
    """
    result = pd.DataFrame(index=df.index)
    
    for period in periods:
        ema = df[column].ewm(span=period, adjust=False).mean()
        result[f"ema_{period}"] = ema
        logger.info(f"ema_calculated period={period}")
    
    return result


def calculate_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = "close"
) -> pd.DataFrame:
    """Calculate MACD (Moving Average Convergence Divergence).
    
    MACD shows the relationship between two EMAs. The signal line is an EMA of MACD.
    Histogram shows the difference between MACD and signal.
    
    Args:
        df: DataFrame with OHLCV data
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period
        column: Price column to use
        
    Returns:
        DataFrame with columns: macd, macd_signal, macd_histogram
    """
    try:
        import pandas_ta as ta
        macd_result = ta.macd(df[column], fast=fast, slow=slow, signal=signal)
        result = pd.DataFrame(index=df.index)
        result["macd"] = macd_result[f"MACD_{fast}_{slow}_{signal}"]
        result["macd_signal"] = macd_result[f"MACDs_{fast}_{slow}_{signal}"]
        result["macd_histogram"] = macd_result[f"MACDh_{fast}_{slow}_{signal}"]
        logger.info(f"macd_calculated fast={fast} slow={slow} signal={signal}")
        return result
    except ImportError:
        # Fallback implementation
        ema_fast = df[column].ewm(span=fast, adjust=False).mean()
        ema_slow = df[column].ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_histogram = macd - macd_signal
        
        result = pd.DataFrame(index=df.index)
        result["macd"] = macd
        result["macd_signal"] = macd_signal
        result["macd_histogram"] = macd_histogram
        logger.info(f"macd_calculated fast={fast} slow={slow} signal={signal} method=fallback")
        return result


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR).
    
    ATR measures volatility by calculating the average of true ranges.
    Higher ATR indicates higher volatility.
    
    Args:
        df: DataFrame with OHLCV data (must have high, low, close)
        period: Lookback period
        
    Returns:
        Series with ATR values
    """
    try:
        import pandas_ta as ta
        atr = ta.atr(df["high"], df["low"], df["close"], length=period)
        logger.info(f"atr_calculated period={period}")
        return atr
    except ImportError:
        # Fallback implementation
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        logger.info(f"atr_calculated period={period} method=fallback")
        return atr


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Calculate Volume Weighted Average Price (VWAP).
    
    VWAP is the average price weighted by volume. It resets daily but for
    intraday data without date boundaries, we calculate cumulative VWAP.
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        Series with VWAP values
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    
    # For intraday: cumulative VWAP
    vwap = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
    logger.info("vwap_calculated")
    return vwap


def calculate_volume_ma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate Volume Moving Average.
    
    Simple moving average of volume to identify volume trends and spikes.
    
    Args:
        df: DataFrame with OHLCV data
        period: Lookback period
        
    Returns:
        Series with volume MA values
    """
    volume_ma = df["volume"].rolling(window=period).mean()
    logger.info(f"volume_ma_calculated period={period}")
    return volume_ma


def calculate_indicators(
    df: pd.DataFrame,
    config: Optional[dict] = None
) -> pd.DataFrame:
    """Calculate all enabled technical indicators.
    
    Args:
        df: DataFrame with OHLCV data
        config: Configuration dict specifying which indicators to calculate
                Example: {"rsi": True, "ema": [20, 50, 200], "macd": True}
                
    Returns:
        DataFrame with all calculated indicators
    """
    if config is None:
        config = {
            "rsi": True,
            "ema": [20, 50, 200],
            "macd": True,
            "atr": True,
            "vwap": True,
            "volume_ma": True,
        }
    
    result = pd.DataFrame(index=df.index)
    
    # RSI
    if config.get("rsi"):
        result["rsi"] = calculate_rsi(df)
    
    # EMA
    if "ema" in config and config["ema"]:
        ema_periods = config["ema"] if isinstance(config["ema"], list) else [20, 50, 200]
        ema_df = calculate_ema(df, periods=ema_periods)
        result = pd.concat([result, ema_df], axis=1)
    
    # MACD
    if config.get("macd"):
        macd_df = calculate_macd(df)
        result = pd.concat([result, macd_df], axis=1)
    
    # ATR
    if config.get("atr"):
        result["atr"] = calculate_atr(df)
    
    # VWAP
    if config.get("vwap"):
        result["vwap"] = calculate_vwap(df)
    
    # Volume MA
    if config.get("volume_ma"):
        result["volume_ma"] = calculate_volume_ma(df)
    
    logger.info(f"indicators_calculated total_columns={len(result.columns)}")
    return result


def add_indicators(df: pd.DataFrame, config: Optional[dict] = None) -> pd.DataFrame:
    """Wrapper: append indicator columns to the input DataFrame.

    Returns a new DataFrame with indicators concatenated.
    """
    ind = calculate_indicators(df, config=config)
    return pd.concat([df, ind], axis=1)
