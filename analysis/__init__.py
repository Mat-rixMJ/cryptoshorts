"""
Technical Analysis & Feature Engineering Module

Provides indicator calculation, feature engineering, and pattern detection for OHLCV data.
"""

from .indicators import calculate_indicators
from .features import calculate_features
from .utils import validate_dataframe, combine_and_clean
from .patterns import (
    detect_patterns,
    events_to_dataframe,
    filter_events_by_confidence,
    filter_events_by_pattern,
)

__all__ = [
    "calculate_indicators",
    "calculate_features",
    "validate_dataframe",
    "combine_and_clean",
    "detect_patterns",
    "events_to_dataframe",
    "filter_events_by_confidence",
    "filter_events_by_pattern",
]
