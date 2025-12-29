"""
Example: Generate chart frames for ranked events

Demonstrates end-to-end frame generation workflow:
1. Load Phase 2 data (OHLCV with indicators)
2. Load Phase 4 data (ranked events)
3. Generate frame sequences
4. Save to visuals/frames/{event_id}/ directories
"""

import logging
from pathlib import Path
from typing import List, Dict
import json

import pandas as pd
import numpy as np

# Import frame generation API
from visuals import (
    FrameConfig,
    generate_event_frames,
    generate_multi_event_frames,
    get_default_style,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_phase2_data(filepath: Path) -> pd.DataFrame:
    """Load Phase 2 output (OHLCV with indicators).
    
    Expected columns:
        - OHLCV: open, high, low, close, volume
        - Indicators: ema_20, ema_50, ema_200, etc.
    """
    try:
        df = pd.read_csv(filepath)
        logger.info(f"loaded_phase2_data rows={len(df)} cols={df.shape[1]}")
        return df
    except FileNotFoundError:
        logger.warning(f"phase2_data_not_found using sample data")
        return generate_sample_data()


def load_phase4_data(filepath: Path) -> List[Dict]:
    """Load Phase 4 output (ranked events).
    
    Expected format:
    [
        {
            "event_index": 150,
            "event_pattern": "BULLISH_CROSS",
            "ml_score": 0.82,
            "context_window": (140, 160)
        },
        ...
    ]
    """
    try:
        with open(filepath) as f:
            events = json.load(f)
        logger.info(f"loaded_phase4_data events={len(events)}")
        return events
    except FileNotFoundError:
        logger.warning(f"phase4_data_not_found using sample events")
        return generate_sample_events()


def generate_sample_data(num_rows: int = 300) -> pd.DataFrame:
    """Generate sample OHLCV data for demonstration."""
    np.random.seed(42)
    
    dates = pd.date_range("2024-01-01", periods=num_rows, freq="1h")
    close_prices = 50000 + np.cumsum(np.random.randn(num_rows) * 100)
    
    df = pd.DataFrame({
        "timestamp": dates,
        "open": close_prices + np.random.randn(num_rows) * 50,
        "high": close_prices + np.abs(np.random.randn(num_rows) * 100),
        "low": close_prices - np.abs(np.random.randn(num_rows) * 100),
        "close": close_prices,
        "volume": np.random.randint(1000, 10000, num_rows),
    })
    
    # Calculate EMAs
    df["ema_20"] = df["close"].ewm(span=20).mean()
    df["ema_50"] = df["close"].ewm(span=50).mean()
    df["ema_200"] = df["close"].ewm(span=200).mean()
    
    df.set_index("timestamp", inplace=True)
    
    logger.info(f"generated_sample_data rows={len(df)}")
    return df


def generate_sample_events() -> List[Dict]:
    """Generate sample events for demonstration."""
    events = [
        {
            "event_index": 80,
            "pattern": "GOLDEN_CROSS",
            "ml_score": 0.87,
        },
        {
            "event_index": 150,
            "pattern": "BULLISH_ENGULFING",
            "ml_score": 0.76,
        },
        {
            "event_index": 220,
            "pattern": "BEARISH_REVERSAL",
            "ml_score": 0.69,
        },
    ]
    
    logger.info(f"generated_sample_events count={len(events)}")
    return events


def run_example(
    phase2_data: Path = None,
    phase4_data: Path = None,
    output_base_dir: Path = None,
    max_events: int = 3
):
    """Run frame generation example.
    
    Args:
        phase2_data: Path to Phase 2 CSV file
        phase4_data: Path to Phase 4 JSON file
        output_base_dir: Base output directory for frames
        max_events: Maximum events to process
    """
    
    # Setup paths
    if output_base_dir is None:
        output_base_dir = Path(__file__).parent / "frames"
    
    logger.info(f"=== Chart Frame Generation Example ===")
    logger.info(f"output_directory={output_base_dir}")
    
    # Load data
    logger.info("loading_phase2_data...")
    df = load_phase2_data(phase2_data)
    
    logger.info("loading_phase4_data...")
    events = load_phase4_data(phase4_data)
    
    # Configure frame generation
    config = FrameConfig(
        frames_per_event=60,
        show_volume=True,
        show_ema=[20, 50, 200],
        highlight_event=True,
        style=get_default_style()
    )
    
    logger.info(f"configuration frames_per_event={config.frames_per_event} "
               f"show_volume={config.show_volume} show_ema={config.show_ema}")
    
    # Generate frames for multiple events
    logger.info(f"generating_frames max_events={max_events}...")
    
    results = generate_multi_event_frames(
        df,
        [
            {
                "event_index": e["event_index"],
                "pattern": e["pattern"],
                "ml_score": e["ml_score"]
            }
            for e in events[:max_events]
        ],
        output_base_dir,
        config=config,
        max_events=max_events
    )
    
    # Print results
    logger.info(f"\n=== Frame Generation Results ===")
    total_frames = 0
    
    for event_id, (num_frames, output_dir) in results.items():
        logger.info(f"  {event_id}: {num_frames} frames")
        logger.info(f"    → {output_dir}")
        total_frames += num_frames
        
        # List generated frames
        frame_files = sorted(list(output_dir.glob("*.png")))
        if frame_files:
            logger.info(f"    frames: {frame_files[0].name} ... {frame_files[-1].name}")
    
    logger.info(f"\nTotal frames generated: {total_frames}")
    logger.info(f"Output directory: {output_base_dir}")
    
    return results


if __name__ == "__main__":
    # Run example with sample data
    run_example(max_events=3)
