from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from .logger import get_logger

logger = get_logger(__name__)


def load_csv(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["timestamp"], infer_datetime_format=True)
    return df


def append_new_rows(existing: Optional[pd.DataFrame], incoming: pd.DataFrame) -> pd.DataFrame:
    if existing is None:
        return incoming
    merged = pd.concat([existing, incoming], ignore_index=True)
    merged = merged.drop_duplicates(subset=["timestamp"], keep="last")
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    return merged


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("file_saved path=%s rows=%s", path, len(df))
