"""
Pattern Detection Orchestration

Main module for detecting and aggregating all market patterns.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import pandas as pd

from .detectors import (
    detect_ema_patterns,
    detect_rsi_patterns,
    detect_breakout_patterns,
    detect_volume_patterns,
    detect_structure_patterns,
)

logger = logging.getLogger(__name__)


def remove_duplicate_events(events: List[dict]) -> List[dict]:
    """Remove duplicate events at the same index and pattern type.
    
    Args:
        events: List of detected events
        
    Returns:
        Deduplicated list of events
    """
    seen = set()
    unique_events = []
    
    for event in events:
        key = (event["pattern"], event["index"])
        if key not in seen:
            seen.add(key)
            unique_events.append(event)
    
    dropped = len(events) - len(unique_events)
    if dropped > 0:
        logger.info(f"duplicate_events_removed count={dropped}")
    
    return unique_events


def validate_events(events: List[dict], df: pd.DataFrame) -> List[dict]:
    """Validate events have valid indexes and timestamps.
    
    Args:
        events: List of detected events
        df: Source DataFrame
        
    Returns:
        List of valid events
    """
    valid_events = []
    
    for event in events:
        idx = event.get("index")
        
        # Check index is valid
        if idx is None or idx not in df.index:
            logger.warning(f"invalid_event_index pattern={event.get('pattern')} index={idx}")
            continue
        
        # Check timestamp exists
        if "timestamp" not in df.columns:
            logger.warning("timestamp_column_missing in DataFrame")
            continue
        
        valid_events.append(event)
    
    invalid_count = len(events) - len(valid_events)
    if invalid_count > 0:
        logger.warning(f"invalid_events_removed count={invalid_count}")
    
    return valid_events


def sort_events(events: List[dict]) -> List[dict]:
    """Sort events by timestamp and index.
    
    Args:
        events: List of detected events
        
    Returns:
        Sorted list of events
    """
    return sorted(events, key=lambda e: (e["timestamp"], e["index"]))


def get_pattern_summary(events: List[dict]) -> Dict[str, int]:
    """Get count of events by pattern type.
    
    Args:
        events: List of detected events
        
    Returns:
        Dict mapping pattern names to counts
    """
    summary = {}
    for event in events:
        pattern = event.get("pattern", "UNKNOWN")
        summary[pattern] = summary.get(pattern, 0) + 1
    return summary


def detect_patterns(
    df: pd.DataFrame,
    config: Optional[Dict[str, bool]] = None,
    symbol: Optional[str] = None
) -> List[dict]:
    """Detect all enabled patterns in the DataFrame.
    
    This is the main entry point for pattern detection. It runs all enabled
    detectors, aggregates results, removes duplicates, validates, and sorts.
    
    Args:
        df: DataFrame with OHLCV, indicators, and features
        config: Configuration dict to enable/disable pattern types
                Example: {"ema": True, "rsi": True, "breakout": True, "volume": True, "structure": False}
        symbol: Optional symbol name to include in events
        
    Returns:
        List of detected pattern events, sorted by timestamp
    """
    if config is None:
        config = {
            "ema": True,
            "rsi": True,
            "breakout": True,
            "volume": True,
            "structure": True,
        }
    
    logger.info(f"pattern_detection_started rows={len(df)} config={config}")
    
    all_events = []
    
    # Run enabled detectors
    if config.get("ema", True):
        events = detect_ema_patterns(df)
        all_events.extend(events)
    
    if config.get("rsi", True):
        events = detect_rsi_patterns(df)
        all_events.extend(events)
    
    if config.get("breakout", True):
        events = detect_breakout_patterns(df)
        all_events.extend(events)
    
    if config.get("volume", True):
        events = detect_volume_patterns(df)
        all_events.extend(events)
    
    if config.get("structure", True):
        events = detect_structure_patterns(df)
        all_events.extend(events)
    
    # Add symbol if provided
    if symbol:
        for event in all_events:
            event["symbol"] = symbol
    
    # Deduplicate
    all_events = remove_duplicate_events(all_events)
    
    # Validate
    all_events = validate_events(all_events, df)
    
    # Sort by timestamp
    all_events = sort_events(all_events)
    
    # Log summary
    summary = get_pattern_summary(all_events)
    logger.info(f"pattern_detection_complete total_events={len(all_events)}")
    for pattern, count in sorted(summary.items()):
        logger.info(f"  {pattern}: {count}")
    
    return all_events


def events_to_dataframe(events: List[dict]) -> pd.DataFrame:
    """Convert list of events to a structured DataFrame.
    
    Args:
        events: List of detected events
        
    Returns:
        DataFrame with event data
    """
    if not events:
        return pd.DataFrame()
    
    # Flatten events for DataFrame
    rows = []
    for event in events:
        row = {
            "pattern": event.get("pattern"),
            "index": event.get("index"),
            "timestamp": event.get("timestamp"),
            "confidence": event.get("confidence"),
            "window_start": event.get("window", [None, None])[0],
            "window_end": event.get("window", [None, None])[1],
            "symbol": event.get("symbol"),
        }
        # Add flattened details
        details = event.get("details", {})
        for key, value in details.items():
            row[f"detail_{key}"] = value
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    logger.info(f"events_converted_to_dataframe shape={df.shape}")
    return df


def filter_events_by_confidence(events: List[dict], min_confidence: float = 0.7) -> List[dict]:
    """Filter events by minimum confidence threshold.
    
    Args:
        events: List of detected events
        min_confidence: Minimum confidence score (0.0 to 1.0)
        
    Returns:
        Filtered list of events
    """
    filtered = [e for e in events if e.get("confidence", 0) >= min_confidence]
    removed = len(events) - len(filtered)
    
    if removed > 0:
        logger.info(f"events_filtered_by_confidence removed={removed} min_conf={min_confidence}")
    
    return filtered


def filter_events_by_pattern(events: List[dict], patterns: List[str]) -> List[dict]:
    """Filter events by pattern type.
    
    Args:
        events: List of detected events
        patterns: List of pattern names to keep
        
    Returns:
        Filtered list of events
    """
    filtered = [e for e in events if e.get("pattern") in patterns]
    logger.info(f"events_filtered_by_pattern kept={len(filtered)} patterns={patterns}")
    return filtered
