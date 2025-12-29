from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
import yaml


@dataclass
class IngestionConfig:
    exchange: str
    symbols: List[str]
    timeframe: str
    candle_limit: int
    data_dir: Path
    cache_ttl_minutes: int = 10
    fill_missing: str = "drop"  # options: drop, ffill

    @staticmethod
    def from_dict(config: dict, base_path: Optional[Path] = None) -> "IngestionConfig":
        base = base_path or Path.cwd()
        data_dir = base / Path(config.get("data_dir", "data"))
        symbols = list(config.get("symbols", []))
        if not symbols:
            raise ValueError("Config must include at least one symbol under 'symbols'.")
        return IngestionConfig(
            exchange=str(config.get("exchange", "binance")),
            symbols=symbols,
            timeframe=str(config.get("timeframe", "1h")),
            candle_limit=int(config.get("candle_limit", 500)),
            data_dir=data_dir,
            cache_ttl_minutes=int(config.get("cache_ttl_minutes", 10)),
            fill_missing=str(config.get("fill_missing", "drop")),
        )

    @staticmethod
    def from_yaml(path: Path) -> "IngestionConfig":
        with Path(path).open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return IngestionConfig.from_dict(data, base_path=Path(path).parent)

    def raw_path(self, symbol: str, timeframe: str) -> Path:
        safe_symbol = symbol.replace("/", "_")
        return self.data_dir / "raw" / f"{safe_symbol}_{timeframe}.csv"

    def cache_path(self, symbol: str, timeframe: str) -> Path:
        safe_symbol = symbol.replace("/", "_")
        return self.data_dir / "cache" / f"{safe_symbol}_{timeframe}.csv"

    def processed_path(self, symbol: str, timeframe: str) -> Path:
        safe_symbol = symbol.replace("/", "_")
        return self.data_dir / "processed" / f"{safe_symbol}_{timeframe}.csv"

    def ensure_dirs(self) -> None:
        for sub in ("raw", "cache", "processed"):
            (self.data_dir / sub).mkdir(parents=True, exist_ok=True)


DEFAULT_CONFIG = IngestionConfig(
    exchange="binance",
    symbols=["BTC/USDT"],
    timeframe="1h",
    candle_limit=500,
    data_dir=Path("data"),
)
