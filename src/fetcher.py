from __future__ import annotations

import time
from typing import Optional

import pandas as pd

from .logger import get_logger

logger = get_logger(__name__)


def _load_exchange(exchange_id: str):
    try:
        import ccxt  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment specific
        raise RuntimeError("ccxt is required. Install with `pip install ccxt`." ) from exc

    try:
        exchange_cls = getattr(ccxt, exchange_id)
    except AttributeError as exc:
        raise ValueError(f"Exchange '{exchange_id}' is not supported by ccxt.") from exc
    return exchange_cls()


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    limit: int = 8760,
    exchange_id: str = "binance",
    max_retries: int = 3,
    retry_delay: float = 1.5,
    since: Optional[int] = None,
) -> pd.DataFrame:
    """Fetch OHLCV data for a symbol/timeframe.

    Retries transient ccxt errors and returns a DataFrame with standardized columns.
    """

    exchange = _load_exchange(exchange_id)
    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("fetch_start symbol=%s timeframe=%s limit=%s", symbol, timeframe, limit)
            raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit, since=since)
            logger.info("fetch_success symbol=%s rows=%s", symbol, len(raw))
            df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            return df
        except Exception as exc:  # ccxt throws generic exceptions
            last_error = exc
            logger.warning(
                "fetch_retry attempt=%s/%s symbol=%s timeframe=%s error=%s",
                attempt,
                max_retries,
                symbol,
                timeframe,
                exc,
            )
            time.sleep(retry_delay)
    raise RuntimeError(f"Failed to fetch OHLCV after {max_retries} attempts: {last_error}")
