"""
Example Usage: Pattern Detection (Phase 3)

Demonstrates how to:
1. Load feature-rich data from Phase 2
2. Run pattern detection
3. Filter and analyze detected events
"""

import json
import logging
from pathlib import Path

import pandas as pd

# Phase 2 imports
from analysis.indicators import calculate_indicators
from analysis.features import calculate_features
from analysis.utils import combine_and_clean

# Phase 3 imports
from analysis.patterns import (
    detect_patterns,
    events_to_dataframe,
    filter_events_by_confidence,
    get_pattern_summary,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def prepare_data() -> pd.DataFrame:
    """Load and prepare data with indicators and features (Phase 1 + 2)."""
    
    # Load clean OHLCV data
    csv_path = Path("data/raw/BTC_USDT_1h.csv")
    logger.info(f"Loading data from {csv_path}")
    
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    logger.info(f"Loaded {len(df)} rows")
    
    # Calculate indicators
    logger.info("Calculating indicators...")
    indicators_df = calculate_indicators(df)
    
    # Calculate features
    df_with_indicators = pd.concat([df, indicators_df], axis=1)
    features_df = calculate_features(df_with_indicators)
    
    # Combine everything
    logger.info("Combining data...")
    final_df = combine_and_clean(
        ohlcv=df,
        indicators=indicators_df,
        features=features_df,
        drop_na=True
    )
    
    logger.info(f"Data prepared: {final_df.shape}")
    return final_df


def main():
    """Main execution flow for pattern detection."""
    
    print("=" * 70)
    print("PHASE 3: PATTERN DETECTION")
    print("=" * 70)
    
    # Step 1: Prepare data
    df = prepare_data()
    
    # Step 2: Configure pattern detection
    pattern_config = {
        "ema": True,
        "rsi": True,
        "breakout": True,
        "volume": True,
        "structure": True,
    }
    
    # Step 3: Detect patterns
    logger.info("Running pattern detection...")
    events = detect_patterns(df, config=pattern_config, symbol="BTC/USDT")
    
    # Step 4: Display summary
    print("\n" + "=" * 70)
    print("DETECTION SUMMARY")
    print("=" * 70)
    print(f"Total events detected: {len(events)}")
    
    summary = get_pattern_summary(events)
    print("\nPattern counts:")
    for pattern, count in sorted(summary.items(), key=lambda x: -x[1]):
        print(f"  {pattern:.<50} {count:>3}")
    
    # Step 5: Show high-confidence events
    high_conf_events = filter_events_by_confidence(events, min_confidence=0.8)
    
    print("\n" + "=" * 70)
    print(f"HIGH CONFIDENCE EVENTS (>= 0.8): {len(high_conf_events)}")
    print("=" * 70)
    
    if high_conf_events:
        for i, event in enumerate(high_conf_events[:5], 1):
            print(f"\n{i}. {event['pattern']}")
            print(f"   Timestamp: {event['timestamp']}")
            print(f"   Index: {event['index']}")
            print(f"   Confidence: {event['confidence']:.3f}")
            print(f"   Details: {json.dumps(event['details'], indent=6)}")
    
    # Step 6: Convert to DataFrame for analysis
    events_df = events_to_dataframe(events)
    
    print("\n" + "=" * 70)
    print("EVENTS DATAFRAME (First 10 rows)")
    print("=" * 70)
    print(events_df.head(10).to_string())
    
    # Step 7: Export examples
    print("\n" + "=" * 70)
    print("SAMPLE EVENT STRUCTURE")
    print("=" * 70)
    if events:
        print(json.dumps(events[0], indent=2, default=str))
    
    # Optional: Save events to JSON
    # output_path = Path("data/processed/detected_events.json")
    # output_path.parent.mkdir(parents=True, exist_ok=True)
    # with output_path.open("w") as f:
    #     json.dump(events, f, indent=2, default=str)
    # logger.info(f"Events saved to {output_path}")
    
    return events, events_df


if __name__ == "__main__":
    detected_events, events_dataframe = main()
