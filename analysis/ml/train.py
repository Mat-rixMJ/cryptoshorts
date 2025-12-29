"""
Model Training Pipeline

Handles training, validation, and evaluation of ranking models.
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error

logger = logging.getLogger(__name__)


def time_aware_split(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split data respecting time ordering (no future leakage).
    
    Uses chronological split: earlier data for training, later for validation.
    
    Args:
        X: Feature matrix with event_index column
        y: Target values
        test_size: Proportion of data to use for validation
        
    Returns:
        Tuple of (X_train, X_test, y_train, y_test)
    """
    # Sort by event_index to ensure time ordering
    if "event_index" in X.columns:
        X = X.sort_values("event_index").reset_index(drop=True)
        y = y.loc[X.index]
    
    # Calculate split point
    split_point = int(len(X) * (1 - test_size))
    
    X_train = X.iloc[:split_point]
    X_test = X.iloc[split_point:]
    y_train = y.iloc[:split_point]
    y_test = y.iloc[split_point:]
    
    logger.info(f"time_aware_split train={len(X_train)} test={len(X_test)}")
    
    return X_train, X_test, y_train, y_test


def prepare_training_data(
    dataset: pd.DataFrame,
    feature_cols: list[str],
) -> Tuple[pd.DataFrame, pd.Series]:
    """Prepare features and target from event dataset.
    
    Args:
        dataset: Event dataset with features and target
        feature_cols: List of feature column names (already includes "pattern_encoded")
        
    Returns:
        Tuple of (X, y) ready for training
    """
    # Separate features and target
    # feature_cols already includes "pattern_encoded", so don't add it twice
    X = dataset[["event_index"] + feature_cols].copy()
    y = dataset["future_return"].copy()
    
    # Handle any remaining NaN in features
    X = X.fillna(X.mean(numeric_only=True))
    
    logger.info(f"training_data_prepared X={X.shape} y={y.shape}")
    
    return X, y


def train_model(
    model,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: Optional[pd.DataFrame] = None,
    y_val: Optional[pd.Series] = None,
) -> dict:
    """Train model on training data.
    
    Args:
        model: Unfitted model instance
        X_train: Training features
        y_train: Training targets
        X_val: Optional validation features
        y_val: Optional validation targets
        
    Returns:
        Dict with training metrics
    """
    logger.info(f"training_start model={model.__class__.__name__}")
    
    # Remove event_index from features for actual training
    feature_cols = [col for col in X_train.columns if col != "event_index"]
    X_train_features = X_train[feature_cols]
    
    # Train model
    model.fit(X_train_features, y_train)
    
    # Evaluate on training set
    y_train_pred = model.predict(X_train_features)
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
    train_mae = mean_absolute_error(y_train, y_train_pred)
    
    metrics = {
        "train_rmse": round(train_rmse, 4),
        "train_mae": round(train_mae, 4),
    }
    
    # Evaluate on validation set if provided
    if X_val is not None and y_val is not None:
        X_val_features = X_val[feature_cols]
        y_val_pred = model.predict(X_val_features)
        val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
        val_mae = mean_absolute_error(y_val, y_val_pred)
        
        # Ranking quality: Spearman correlation
        from scipy.stats import spearmanr
        corr, _ = spearmanr(y_val, y_val_pred)
        
        metrics["val_rmse"] = round(val_rmse, 4)
        metrics["val_mae"] = round(val_mae, 4)
        metrics["spearman_corr"] = round(float(corr), 4)
    
    logger.info(f"training_complete metrics={metrics}")
    
    return metrics


def evaluate_model(
    model,
    X: pd.DataFrame,
    y: pd.Series,
) -> dict:
    """Evaluate model on a dataset.
    
    Args:
        model: Trained model
        X: Feature matrix
        y: Target values
        
    Returns:
        Dict with evaluation metrics
    """
    feature_cols = [col for col in X.columns if col != "event_index"]
    X_features = X[feature_cols]
    
    y_pred = model.predict(X_features)
    
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    mae = mean_absolute_error(y, y_pred)
    
    # Ranking correlation
    from scipy.stats import spearmanr
    corr, p_value = spearmanr(y, y_pred)
    
    metrics = {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "spearman_correlation": round(float(corr), 4),
        "spearman_pvalue": round(float(p_value), 6),
        "sample_count": len(y),
    }
    
    logger.info(f"model_evaluation metrics={metrics}")
    
    return metrics


# Optional import for ranking metrics
try:
    from scipy.stats import spearmanr
except ImportError:
    logger.warning("scipy not available, ranking metrics will be skipped")
