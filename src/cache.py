from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import pandas as pd

from .logger import get_logger

logger = get_logger(__name__)


def load_if_fresh(path: Path, ttl_minutes: int) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    age_seconds = time.time() - path.stat().st_mtime
    if age_seconds <= ttl_minutes * 60:
        logger.info("cache_hit path=%s age_seconds=%.1f", path, age_seconds)
        return pd.read_csv(path, parse_dates=["timestamp"], infer_datetime_format=True)
    logger.info("cache_stale path=%s age_seconds=%.1f", path, age_seconds)
    return None


def write_cache(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("cache_write path=%s rows=%s", path, len(df))
