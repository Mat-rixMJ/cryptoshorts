from __future__ import annotations

from typing import Tuple

import pandas as pd

from .logger import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

_TIMEFRAME_FREQ = {
    "1m": "1T",
    "5m": "5T",
    "15m": "15T",
    "1h": "1H",
    "4h": "4H",
    "1d": "1D",
}


def validate_schema(df: pd.DataFrame) -> pd.DataFrame:
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Input data missing columns: {missing_cols}")
    return df[REQUIRED_COLUMNS].copy()


def validate_values(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Drop rows with impossible price/volume relationships."""
    before = len(df)
    mask = (
        df["high"].ge(df[["open", "close"]].max(axis=1))
        & df["low"].le(df[["open", "close"]].min(axis=1))
        & df["volume"].ge(0)
    )
    cleaned = df[mask].dropna()
    dropped = before - len(cleaned)
    if dropped:
        logger.warning("validation_drop rows=%s", dropped)
    return cleaned, dropped


def clean_duplicates_and_sort(df: pd.DataFrame) -> pd.DataFrame:
    # Drop exact duplicates on timestamp
    df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    return df.reset_index(drop=True)


def ensure_uniform_cadence(df: pd.DataFrame, timeframe: str, fill_missing: str = "drop") -> pd.DataFrame:
    freq = _TIMEFRAME_FREQ.get(timeframe)
    if not freq:
        raise ValueError(f"Unsupported timeframe '{timeframe}'.")
    df = df.set_index("timestamp").sort_index()
    full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq=freq, tz="UTC")
    reindexed = df.reindex(full_index)

    missing = reindexed["open"].isna().sum()
    if missing:
        logger.warning("missing_candles count=%s", int(missing))
        if fill_missing == "ffill":
            reindexed = reindexed.ffill()
        elif fill_missing == "drop":
            reindexed = reindexed.dropna()
        else:
            raise ValueError("fill_missing must be 'drop' or 'ffill'")
    reindexed = reindexed.reset_index().rename(columns={"index": "timestamp"})
    return reindexed


def validate_ohlcv(df: pd.DataFrame, timeframe: str, fill_missing: str = "drop") -> pd.DataFrame:
    df = validate_schema(df)
    df, _ = validate_values(df)
    df = clean_duplicates_and_sort(df)
    df = ensure_uniform_cadence(df, timeframe=timeframe, fill_missing=fill_missing)
    return df
