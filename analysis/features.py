"""
Feature Engineering Module

Creates derived numerical features from OHLCV and indicator data for ML readiness.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_ema_distance(df: pd.DataFrame, ema_periods: list[int]) -> pd.DataFrame:
    """Calculate percentage distance from price to each EMA.
    
    Positive values mean price is above EMA (bullish), negative below (bearish).
    
    Args:
        df: DataFrame with 'close' and 'ema_{period}' columns
        ema_periods: List of EMA periods to calculate distance for
        
    Returns:
        DataFrame with columns 'ema_{period}_dist_pct'
    """
    result = pd.DataFrame(index=df.index)
    
    for period in ema_periods:
        ema_col = f"ema_{period}"
        if ema_col in df.columns:
            distance = ((df["close"] - df[ema_col]) / df[ema_col]) * 100
            result[f"ema_{period}_dist_pct"] = distance
            logger.debug(f"ema_distance_calculated period={period}")
    
    logger.info(f"ema_distance_features calculated count={len(result.columns)}")
    return result


def calculate_rsi_normalized(df: pd.DataFrame) -> pd.Series:
    """Normalize RSI to 0-1 range for ML compatibility.
    
    RSI is already 0-100, this scales it to 0-1.
    
    Args:
        df: DataFrame with 'rsi' column
        
    Returns:
        Series with normalized RSI (0-1)
    """
    if "rsi" not in df.columns:
        return pd.Series(index=df.index, dtype=float)
    
    rsi_norm = df["rsi"] / 100.0
    logger.info("rsi_normalized")
    return rsi_norm


def calculate_volume_spike_ratio(df: pd.DataFrame) -> pd.Series:
    """Calculate volume spike ratio: current volume / volume MA.
    
    Values > 1 indicate above-average volume, < 1 below-average.
    
    Args:
        df: DataFrame with 'volume' and 'volume_ma' columns
        
    Returns:
        Series with volume spike ratios
    """
    if "volume_ma" not in df.columns:
        return pd.Series(index=df.index, dtype=float)
    
    # Avoid division by zero
    volume_spike = df["volume"] / df["volume_ma"].replace(0, np.nan)
    logger.info("volume_spike_ratio_calculated")
    return volume_spike


def calculate_candle_body_size(df: pd.DataFrame) -> pd.Series:
    """Calculate candle body size as % of close price.
    
    Larger bodies indicate stronger directional moves.
    
    Args:
        df: DataFrame with 'open' and 'close' columns
        
    Returns:
        Series with body size percentage
    """
    body_size = ((df["close"] - df["open"]).abs() / df["close"]) * 100
    logger.info("candle_body_size_calculated")
    return body_size


def calculate_candle_wick_ratio(df: pd.DataFrame) -> pd.Series:
    """Calculate wick ratio: total wick length / body length.
    
    Higher values indicate more rejection and indecision.
    
    Args:
        df: DataFrame with OHLC columns
        
    Returns:
        Series with wick ratios
    """
    body = (df["close"] - df["open"]).abs()
    total_range = df["high"] - df["low"]
    wick = total_range - body
    
    # Avoid division by zero
    wick_ratio = wick / body.replace(0, np.nan)
    # Cap extreme values
    wick_ratio = wick_ratio.clip(upper=100)
    
    logger.info("candle_wick_ratio_calculated")
    return wick_ratio


def calculate_volatility(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate rolling volatility as standard deviation of returns.
    
    Higher values indicate more price instability.
    
    Args:
        df: DataFrame with 'close' column
        period: Lookback period for volatility calculation
        
    Returns:
        Series with volatility values
    """
    returns = df["close"].pct_change()
    volatility = returns.rolling(window=period).std() * 100  # Convert to percentage
    logger.info(f"volatility_calculated period={period}")
    return volatility


def calculate_trend_strength(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate trend strength using linear regression slope.
    
    Positive values indicate uptrend, negative downtrend.
    Magnitude indicates strength.
    
    Args:
        df: DataFrame with 'close' column
        period: Lookback period
        
    Returns:
        Series with trend strength values
    """
    def rolling_slope(series):
        x = np.arange(len(series))
        if len(series) < 2 or series.isna().all():
            return np.nan
        # Simple linear regression slope
        slope = np.polyfit(x, series, 1)[0]
        return slope
    
    trend = df["close"].rolling(window=period).apply(rolling_slope, raw=False)
    # Normalize by price
    trend_strength = (trend / df["close"]) * 100
    logger.info(f"trend_strength_calculated period={period}")
    return trend_strength


def calculate_price_momentum(df: pd.DataFrame, period: int = 10) -> pd.Series:
    """Calculate price momentum as percentage change over period.
    
    Args:
        df: DataFrame with 'close' column
        period: Lookback period
        
    Returns:
        Series with momentum values
    """
    momentum = df["close"].pct_change(periods=period) * 100
    logger.info(f"price_momentum_calculated period={period}")
    return momentum


def calculate_atr_percent(df: pd.DataFrame) -> pd.Series:
    """Calculate ATR as percentage of price for normalization.
    
    Args:
        df: DataFrame with 'atr' and 'close' columns
        
    Returns:
        Series with ATR percentage
    """
    if "atr" not in df.columns:
        return pd.Series(index=df.index, dtype=float)
    
    atr_pct = (df["atr"] / df["close"]) * 100
    logger.info("atr_percent_calculated")
    return atr_pct


def calculate_features(
    df: pd.DataFrame,
    config: Optional[dict] = None
) -> pd.DataFrame:
    """Calculate all derived features from OHLCV and indicator data.
    
    Args:
        df: DataFrame with OHLCV and indicator columns
        config: Configuration dict (currently uses defaults)
        
    Returns:
        DataFrame with all calculated features
    """
    result = pd.DataFrame(index=df.index)
    
    # EMA distance features
    ema_periods = [20, 50, 200]
    if any(f"ema_{p}" in df.columns for p in ema_periods):
        ema_dist = calculate_ema_distance(df, ema_periods)
        result = pd.concat([result, ema_dist], axis=1)
    
    # RSI normalized
    if "rsi" in df.columns:
        result["rsi_norm"] = calculate_rsi_normalized(df)
    
    # Volume features
    if "volume_ma" in df.columns:
        result["volume_spike_ratio"] = calculate_volume_spike_ratio(df)
    
    # Candle features
    result["candle_body_size_pct"] = calculate_candle_body_size(df)
    result["candle_wick_ratio"] = calculate_candle_wick_ratio(df)
    
    # Volatility
    result["volatility_20"] = calculate_volatility(df, period=20)
    
    # Trend strength
    result["trend_strength_20"] = calculate_trend_strength(df, period=20)
    
    # Momentum
    result["momentum_10"] = calculate_price_momentum(df, period=10)
    
    # ATR percentage
    if "atr" in df.columns:
        result["atr_pct"] = calculate_atr_percent(df)
    
    logger.info(f"features_calculated total_columns={len(result.columns)}")
    return result


def add_features(df: pd.DataFrame, config: Optional[dict] = None) -> pd.DataFrame:
    """Wrapper: append derived feature columns to the input DataFrame.

    Returns a new DataFrame with features concatenated.
    """
    feats = calculate_features(df, config=config)
    return pd.concat([df, feats], axis=1)
