"""
ML Model Creation and Management

Handles model instantiation, saving, and loading.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Literal, Optional, Union

import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

logger = logging.getLogger(__name__)


def create_model(
    model_type: Literal["random_forest", "gradient_boosting"] = "random_forest",
    **kwargs
) -> Union[RandomForestRegressor, GradientBoostingRegressor]:
    """Create a regression model for event ranking.
    
    Args:
        model_type: Type of model to create
        **kwargs: Additional parameters for the model
        
    Returns:
        Unfitted model instance
    """
    random_state = 42  # Deterministic
    
    if model_type == "random_forest":
        # Default params optimized for time-series event ranking
        return RandomForestRegressor(
            n_estimators=kwargs.get("n_estimators", 100),
            max_depth=kwargs.get("max_depth", 15),
            min_samples_split=kwargs.get("min_samples_split", 5),
            min_samples_leaf=kwargs.get("min_samples_leaf", 2),
            max_features=kwargs.get("max_features", "sqrt"),
            n_jobs=-1,  # Use all CPUs
            random_state=random_state,
            verbose=kwargs.get("verbose", 0),
        )
    
    elif model_type == "gradient_boosting":
        return GradientBoostingRegressor(
            n_estimators=kwargs.get("n_estimators", 100),
            learning_rate=kwargs.get("learning_rate", 0.1),
            max_depth=kwargs.get("max_depth", 5),
            min_samples_split=kwargs.get("min_samples_split", 5),
            min_samples_leaf=kwargs.get("min_samples_leaf", 2),
            random_state=random_state,
            verbose=kwargs.get("verbose", 0),
        )
    
    else:
        raise ValueError(f"Unknown model_type: {model_type}")


def save_model(
    model: Union[RandomForestRegressor, GradientBoostingRegressor],
    path: Path,
    metadata: Optional[dict] = None,
) -> None:
    """Save trained model to disk using pickle.
    
    Args:
        model: Trained model instance
        path: Path to save model to
        metadata: Optional metadata dict to save alongside model
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with path.open("wb") as f:
        pickle.dump(model, f)
    
    logger.info(f"model_saved path={path}")
    
    # Save metadata if provided
    if metadata:
        metadata_path = path.parent / f"{path.stem}_metadata.pkl"
        with metadata_path.open("wb") as f:
            pickle.dump(metadata, f)
        logger.info(f"model_metadata_saved path={metadata_path}")


def load_model(path: Path) -> Union[RandomForestRegressor, GradientBoostingRegressor]:
    """Load trained model from disk.
    
    Args:
        path: Path to model file
        
    Returns:
        Loaded model instance
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    
    with path.open("rb") as f:
        model = pickle.load(f)
    
    logger.info(f"model_loaded path={path}")
    return model


def load_model_metadata(path: Path) -> Optional[dict]:
    """Load model metadata.
    
    Args:
        path: Path to model file (metadata file derived from this)
        
    Returns:
        Metadata dict or None if not found
    """
    path = Path(path)
    metadata_path = path.parent / f"{path.stem}_metadata.pkl"
    
    if not metadata_path.exists():
        return None
    
    with metadata_path.open("rb") as f:
        metadata = pickle.load(f)
    
    logger.info(f"model_metadata_loaded path={metadata_path}")
    return metadata


def get_feature_importance(
    model: Union[RandomForestRegressor, GradientBoostingRegressor],
    feature_names: list[str],
) -> dict[str, float]:
    """Extract feature importance from trained model.
    
    Args:
        model: Trained model
        feature_names: Names of features
        
    Returns:
        Dict mapping feature names to importance scores
    """
    importances = model.feature_importances_
    
    feature_importance = {
        name: round(float(importance), 4)
        for name, importance in zip(feature_names, importances)
    }
    
    # Sort by importance
    feature_importance = dict(
        sorted(feature_importance.items(), key=lambda x: -x[1])
    )
    
    logger.info(f"feature_importance_extracted top_5={list(feature_importance.items())[:5]}")
    
    return feature_importance
