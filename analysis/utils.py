"""
Utility Functions for Data Validation and Integration

Provides validation, cleaning, and combination utilities for indicator/feature data.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def validate_dataframe(df: pd.DataFrame, name: str = "dataframe") -> None:
    """Validate DataFrame for common data quality issues.
    
    Checks for:
    - NaN values
    - Infinite values
    - Empty DataFrame
    
    Args:
        df: DataFrame to validate
        name: Name for logging purposes
        
    Raises:
        ValueError: If validation fails
    """
    if df.empty:
        raise ValueError(f"{name} is empty")
    
    # Check for NaN
    nan_count = df.isna().sum().sum()
    if nan_count > 0:
        nan_cols = df.columns[df.isna().any()].tolist()
        logger.warning(f"{name} contains {nan_count} NaN values in columns: {nan_cols}")
    
    # Check for infinite values
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    inf_count = np.isinf(df[numeric_cols]).sum().sum()
    if inf_count > 0:
        inf_cols = numeric_cols[np.isinf(df[numeric_cols]).any()].tolist()
        raise ValueError(f"{name} contains {inf_count} infinite values in columns: {inf_cols}")
    
    logger.info(f"{name}_validated shape={df.shape} nan_count={nan_count}")


def check_column_collisions(dfs: list[pd.DataFrame]) -> list[str]:
    """Check for duplicate column names across multiple DataFrames.
    
    Args:
        dfs: List of DataFrames to check
        
    Returns:
        List of duplicate column names
    """
    all_columns = []
    for df in dfs:
        all_columns.extend(df.columns.tolist())
    
    duplicates = [col for col in set(all_columns) if all_columns.count(col) > 1]
    
    if duplicates:
        logger.warning(f"column_collisions_detected columns={duplicates}")
    
    return duplicates


def replace_inf_with_nan(df: pd.DataFrame) -> pd.DataFrame:
    """Replace infinite values with NaN for safe removal.
    
    Args:
        df: DataFrame to clean
        
    Returns:
        DataFrame with inf replaced by NaN
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df_clean = df.copy()
    df_clean[numeric_cols] = df_clean[numeric_cols].replace([np.inf, -np.inf], np.nan)
    return df_clean


def drop_na_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows containing any NaN values.
    
    Args:
        df: DataFrame to clean
        
    Returns:
        DataFrame with NaN rows removed
    """
    rows_before = len(df)
    df_clean = df.dropna()
    rows_after = len(df_clean)
    rows_dropped = rows_before - rows_after
    
    if rows_dropped > 0:
        logger.info(f"nan_rows_dropped count={rows_dropped} remaining={rows_after}")
    
    return df_clean


def combine_and_clean(
    ohlcv: pd.DataFrame,
    indicators: pd.DataFrame,
    features: pd.DataFrame,
    drop_na: bool = True
) -> pd.DataFrame:
    """Combine OHLCV, indicators, and features into one clean DataFrame.
    
    Args:
        ohlcv: Original OHLCV data
        indicators: Calculated indicators
        features: Calculated features
        drop_na: Whether to drop rows with NaN values
        
    Returns:
        Combined and cleaned DataFrame
    """
    logger.info("combining_dataframes ohlcv_shape=%s indicators_shape=%s features_shape=%s",
                ohlcv.shape, indicators.shape, features.shape)
    
    # Check for column collisions
    collisions = check_column_collisions([ohlcv, indicators, features])
    if collisions:
        logger.warning(f"Column collisions detected: {collisions}. Later DataFrames will overwrite.")
    
    # Combine all DataFrames
    combined = pd.concat([ohlcv, indicators, features], axis=1)
    
    # Replace infinite values with NaN
    combined = replace_inf_with_nan(combined)
    
    # Drop NaN rows if requested
    if drop_na:
        combined = drop_na_rows(combined)
    
    # Ensure timestamp ordering
    if "timestamp" in combined.columns:
        combined = combined.sort_values("timestamp").reset_index(drop=True)
    
    # Final validation
    try:
        validate_dataframe(combined, name="combined_dataframe")
    except ValueError as e:
        logger.error(f"combined_dataframe_validation_failed: {e}")
        if drop_na:
            raise
    
    logger.info(f"dataframe_combined_successfully final_shape={combined.shape} columns={len(combined.columns)}")
    return combined


def get_feature_summary(df: pd.DataFrame) -> dict:
    """Get summary statistics about the feature-rich DataFrame.
    
    Args:
        df: DataFrame to summarize
        
    Returns:
        Dict with summary information
    """
    return {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "numeric_columns": len(df.select_dtypes(include=[np.number]).columns),
        "nan_count": int(df.isna().sum().sum()),
        "memory_usage_mb": float(df.memory_usage(deep=True).sum() / 1024 / 1024),
        "columns": df.columns.tolist(),
    }
