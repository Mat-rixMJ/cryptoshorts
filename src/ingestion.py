from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from .cache import load_if_fresh, write_cache
from .config import IngestionConfig
from .fetcher import fetch_ohlcv
from .logger import get_logger
from .storage import append_new_rows, load_csv, save_csv
from .validation import validate_ohlcv

logger = get_logger(__name__)


class DataIngestion:
    def __init__(self, config: IngestionConfig):
        self.config = config
        self.config.ensure_dirs()

    def load_symbol(
        self, symbol: str, timeframe: Optional[str] = None, limit: Optional[int] = None
    ) -> pd.DataFrame:
        tf = timeframe or self.config.timeframe
        limit = limit or self.config.candle_limit

        cache_path = self.config.cache_path(symbol, tf)
        cached = load_if_fresh(cache_path, ttl_minutes=self.config.cache_ttl_minutes)
        if cached is not None:
            logger.info("returning_cached symbol=%s timeframe=%s", symbol, tf)
            return validate_ohlcv(cached, timeframe=tf, fill_missing=self.config.fill_missing)

        raw_path = self.config.raw_path(symbol, tf)
        existing = load_csv(raw_path)

        fetched = self._fetch_with_fallback(symbol, tf, limit)
        merged = append_new_rows(existing, fetched)

        clean = validate_ohlcv(merged, timeframe=tf, fill_missing=self.config.fill_missing)

        save_csv(clean, raw_path)
        write_cache(clean, cache_path)
        return clean

    def _fetch_with_fallback(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        try:
            return fetch_ohlcv(symbol, timeframe=timeframe, limit=limit, exchange_id=self.config.exchange)
        except Exception as api_exc:
            logger.error("api_fetch_failed symbol=%s error=%s", symbol, api_exc)
            raw_path = self.config.raw_path(symbol, timeframe)
            fallback = load_csv(raw_path)
            if fallback is None:
                raise RuntimeError(
                    f"API fetch failed and no local CSV fallback found for {symbol} {timeframe}"
                ) from api_exc
            logger.info("fallback_csv_load path=%s", raw_path)
            return fallback


def example_usage() -> pd.DataFrame:
    cfg = IngestionConfig.from_yaml(Path("config.yaml"))
    ingestion = DataIngestion(cfg)
    df = ingestion.load_symbol(cfg.symbols[0])
    return df.head()
