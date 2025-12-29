import pandas as pd
import pytest

from src.config import IngestionConfig
from src.ingestion import DataIngestion
from src.validation import validate_ohlcv


def test_validation_drops_invalid_rows():
    data = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"], utc=True),
            "open": [100, 100],
            "high": [110, 90],  # second row invalid
            "low": [90, 95],
            "close": [105, 102],
            "volume": [1.0, -5.0],
        }
    )
    clean = validate_ohlcv(data, timeframe="1h", fill_missing="drop")
    assert len(clean) == 1
    assert clean.iloc[0]["open"] == 100


def test_csv_fallback(tmp_path):
    cfg = IngestionConfig(
        exchange="binance",
        symbols=["BTC/USDT"],
        timeframe="1h",
        candle_limit=10,
        data_dir=tmp_path / "data",
        cache_ttl_minutes=1,
    )
    cfg.ensure_dirs()
    raw_path = cfg.raw_path("BTC/USDT", "1h")

    sample = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z"], utc=True),
            "open": [100],
            "high": [110],
            "low": [90],
            "close": [105],
            "volume": [1.0],
        }
    )
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(raw_path, index=False)

    ingestion = DataIngestion(cfg)

    # Force API failure by monkeypatching the fetch method
    def fail_fetch(*_args, **_kwargs):
        raise RuntimeError("forced failure")

    ingestion._fetch_with_fallback = fail_fetch  # type: ignore

    df = ingestion.load_symbol("BTC/USDT")
    assert len(df) == 1
    assert df.iloc[0]["close"] == 105


def test_api_fetch_is_used(monkeypatch, tmp_path):
    cfg = IngestionConfig(
        exchange="binance",
        symbols=["BTC/USDT"],
        timeframe="1h",
        candle_limit=10,
        data_dir=tmp_path / "data",
        cache_ttl_minutes=1,
    )
    ingestion = DataIngestion(cfg)

    called = {}

    def fake_fetch(symbol, timeframe, limit, exchange_id):
        called["ok"] = True
        return pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z"], utc=True),
                "open": [1],
                "high": [2],
                "low": [0.5],
                "close": [1.5],
                "volume": [10],
            }
        )

    monkeypatch.setattr("src.ingestion.fetch_ohlcv", fake_fetch)

    df = ingestion.load_symbol("BTC/USDT")
    assert called.get("ok") is True
    assert len(df) == 1
    assert df.iloc[0]["volume"] == 10
