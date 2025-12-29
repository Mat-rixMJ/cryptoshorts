# Phase 2: Indicator Calculation & Feature Engineering

## Overview

This module transforms clean OHLCV data into indicator-rich, ML-ready DataFrames.

## Structure

```
analysis/
├── __init__.py          # Module exports
├── indicators.py        # Technical indicator calculations
├── features.py          # Derived feature engineering
└── utils.py            # Validation and integration utilities
```

## Features

### Technical Indicators (`indicators.py`)

- **RSI (14)**: Relative Strength Index for momentum
- **EMA (20, 50, 200)**: Exponential Moving Averages
- **MACD (12,26,9)**: Moving Average Convergence Divergence
- **ATR (14)**: Average True Range for volatility
- **VWAP**: Volume Weighted Average Price
- **Volume MA (20)**: Volume moving average

### Derived Features (`features.py`)

- **EMA Distance %**: Price distance from each EMA
- **RSI Normalized**: RSI scaled to 0-1
- **Volume Spike Ratio**: Current volume / volume MA
- **Candle Body Size %**: Body size as % of price
- **Candle Wick Ratio**: Wick length / body length
- **Volatility (20)**: Rolling standard deviation of returns
- **Trend Strength (20)**: Linear regression slope
- **Momentum (10)**: Price change over period
- **ATR %**: ATR as percentage of price

## Installation

```bash
pip install pandas numpy pandas-ta
```

## Quick Start

```python
import pandas as pd
from analysis import calculate_indicators, calculate_features, combine_and_clean

# Load OHLCV data
df = pd.read_csv("data/raw/BTC_USDT_1h.csv", parse_dates=["timestamp"])

# Calculate indicators
indicators = calculate_indicators(df)

# Calculate features
df_with_ind = pd.concat([df, indicators], axis=1)
features = calculate_features(df_with_ind)

# Combine everything
final_df = combine_and_clean(df, indicators, features, drop_na=True)

print(final_df.head())
```

## Configuration

Customize which indicators to calculate:

```python
config = {
    "rsi": True,
    "ema": [20, 50, 200],
    "macd": True,
    "atr": True,
    "vwap": True,
    "volume_ma": True,
}

indicators = calculate_indicators(df, config=config)
```

## Design Decisions

### pandas-ta with Fallback

- Primary: Uses `pandas-ta` for optimized calculations
- Fallback: Custom implementations if pandas-ta unavailable
- Ensures portability without hard dependency

### Clean Data Guarantee

- Replaces infinite values with NaN
- Drops rows with NaN (configurable)
- Validates for data quality issues
- Maintains timestamp ordering

### ML-Ready Output

- All numeric features
- Normalized where appropriate
- No NaN in final output
- Standardized column naming

### Modular Design

- Each indicator is a separate function
- Features can be added/removed easily
- Clear separation of concerns
- Extensive logging for debugging

## Validation

The `utils.py` module provides:

- NaN detection and removal
- Infinite value handling
- Column collision detection
- Shape and memory profiling

## Next Steps

This output is ready for:

- Pattern detection algorithms
- ML model training
- Time series forecasting
- Chart visualization
- Video generation workflows
