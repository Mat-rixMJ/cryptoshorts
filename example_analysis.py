"""
Example Usage: Indicator Calculation & Feature Engineering

Demonstrates how to:
1. Load clean OHLCV data from CSV
2. Calculate technical indicators
3. Calculate derived features
4. Combine into ML-ready DataFrame
"""

import logging
from pathlib import Path

import pandas as pd

from analysis.indicators import calculate_indicators
from analysis.features import calculate_features
from analysis.utils import combine_and_clean, get_feature_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def main():
    """Main execution flow for indicator and feature calculation."""
    
    # Step 1: Load clean OHLCV data
    csv_path = Path("data/raw/BTC_USDT_1h.csv")
    logger.info(f"Loading data from {csv_path}")
    
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    logger.info(f"Loaded {len(df)} rows with columns: {df.columns.tolist()}")
    
    # Step 2: Configure indicators
    indicator_config = {
        "rsi": True,
        "ema": [20, 50, 200],
        "macd": True,
        "atr": True,
        "vwap": True,
        "volume_ma": True,
    }
    
    # Step 3: Calculate indicators
    logger.info("Calculating technical indicators...")
    indicators_df = calculate_indicators(df, config=indicator_config)
    logger.info(f"Indicators calculated: {indicators_df.columns.tolist()}")
    
    # Step 4: Calculate features
    logger.info("Calculating derived features...")
    
    # Combine OHLCV with indicators for feature calculation
    df_with_indicators = pd.concat([df, indicators_df], axis=1)
    features_df = calculate_features(df_with_indicators)
    logger.info(f"Features calculated: {features_df.columns.tolist()}")
    
    # Step 5: Combine everything
    logger.info("Combining OHLCV, indicators, and features...")
    final_df = combine_and_clean(
        ohlcv=df,
        indicators=indicators_df,
        features=features_df,
        drop_na=True
    )
    
    # Step 6: Summary
    summary = get_feature_summary(final_df)
    logger.info("=" * 60)
    logger.info("FINAL DATAFRAME SUMMARY")
    logger.info("=" * 60)
    for key, value in summary.items():
        if key != "columns":
            logger.info(f"{key}: {value}")
    
    # Step 7: Display sample
    print("\n" + "=" * 60)
    print("SAMPLE OUTPUT (First 5 rows)")
    print("=" * 60)
    print(final_df.head())
    
    print("\n" + "=" * 60)
    print("SAMPLE OUTPUT (Last 5 rows)")
    print("=" * 60)
    print(final_df.tail())
    
    print("\n" + "=" * 60)
    print("COLUMN LIST")
    print("=" * 60)
    for i, col in enumerate(final_df.columns, 1):
        print(f"{i:2d}. {col}")
    
    # Optional: Save to processed directory
    # output_path = Path("data/processed/BTC_USDT_1h_features.csv")
    # output_path.parent.mkdir(parents=True, exist_ok=True)
    # final_df.to_csv(output_path, index=False)
    # logger.info(f"Saved feature-rich data to {output_path}")
    
    return final_df


if __name__ == "__main__":
    result_df = main()
