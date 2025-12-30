from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

try:
    from src.fetcher import fetch_ohlcv  # live fetch via ccxt
except Exception:
    fetch_ohlcv = None  # fallback to local CSV

logger = logging.getLogger(__name__)


def fetch_data(symbol: str, timeframe: str, limit: int = 8760, exchange: str = "binance") -> pd.DataFrame:
    """Fetch OHLCV data for the given symbol/timeframe.

    - If ccxt is available, fetch live data via src.fetcher
    - Otherwise, fallback to local CSV at data/raw/<SYMBOL>_<TIMEFRAME>.csv
    """
    if fetch_ohlcv:
        try:
            return fetch_ohlcv(symbol, timeframe, limit, exchange_id=exchange)
        except Exception as e:
            logger.warning("live_fetch_failed fallback_local symbol=%s tf=%s err=%s", symbol, timeframe, e)
    # Fallback to local CSV
    fname = symbol.replace("/", "_") + f"_{timeframe}.csv"
    csv_path = Path("data/raw") / fname
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    logger.info("loaded_local_csv path=%s rows=%d", csv_path, len(df))
    return df
