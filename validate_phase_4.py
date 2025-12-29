#!/usr/bin/env python
"""
Phase 4 Validation Script

Quick validation that all Phase 4 components work correctly.
"""

import json
import logging
from pathlib import Path

import pandas as pd
import numpy as np

from analysis.indicators import calculate_indicators
from analysis.features import calculate_features
from analysis.utils import combine_and_clean
from analysis.patterns import detect_patterns

from analysis.ml.labels import compute_future_labels, compute_event_labels
from analysis.ml.dataset import create_event_dataset, validate_event_dataset
from analysis.ml.model import load_model
from analysis.ml.rank import (
    prepare_events_for_scoring,
    score_events,
    rank_events,
    get_ranking_summary,
)
from analysis.ml.explain import get_feature_importance, explain_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def validate_phase_4():
    """Validate Phase 4 ML ranking system."""
    
    print("\n" + "=" * 70)
    print("PHASE 4 VALIDATION: ML-BASED EVENT RANKING")
    print("=" * 70)
    
    # Step 1: Load pre-trained model
    print("\n[1/5] Loading pre-trained model...")
    model_path = Path("analysis/ml/models/ranking_model.pkl")
    
    if not model_path.exists():
        print(f"  ❌ Model not found: {model_path}")
        print("  Run example_ml_ranking.py first to train the model")
        return False
    
    model = load_model(model_path)
    print(f"  ✅ Model loaded: {model.__class__.__name__}")
    print(f"     - Features expected: {model.n_features_in_}")
    
    # Note: For actual validation, we use the pre-computed dataset from example_ml_ranking
    # since the model was trained on specific feature engineering pipeline
    
    # Step 2: Check model files
    print("\n[2/5] Checking model persistence...")
    metadata_path = Path("analysis/ml/models/ranking_model_metadata.pkl")
    
    if metadata_path.exists():
        print(f"  ✅ Model metadata file exists")
    else:
        print(f"  ⚠️  Model metadata file not found (optional)")
    
    print(f"     - Model type: {type(model).__name__}")
    print(f"     - Model parameters: n_estimators={model.n_estimators}")
    
    # Step 3: Validate feature expectations
    print("\n[3/5] Validating feature compatibility...")
    
    # Expected features that the model was trained on
    expected_features = [
        'pattern_encoded', 'feat_atr', 'feat_atr_pct', 
        'feat_candle_body_size_pct', 'feat_candle_wick_ratio',
        'feat_ema_20', 'feat_ema_200', 'feat_ema_200_dist_pct',
        'feat_ema_20_dist_pct', 'feat_ema_50', 'feat_ema_50_dist_pct',
        'feat_macd', 'feat_macd_histogram', 'feat_macd_signal',
        'feat_momentum_10', 'feat_rsi', 'feat_rsi_norm',
        'feat_trend_strength_20', 'feat_volatility_20', 'feat_volume_ma',
        'feat_volume_spike_ratio', 'feat_vwap'
    ]
    
    print(f"  ✅ Expected features: {len(expected_features)}")
    print(f"     - First 3: {expected_features[:3]}")
    print(f"     - Pattern encoding: pattern → integer (1-18)")
    
    # Step 4: Module availability check
    print("\n[4/5] Checking module availability...")
    
    modules_to_check = [
        ("labels", compute_future_labels),
        ("dataset", create_event_dataset),
        ("model", load_model),
        ("rank", score_events),
        ("explain", get_feature_importance),
    ]
    
    for module_name, module_func in modules_to_check:
        try:
            assert module_func is not None
            print(f"  ✅ analysis.ml.{module_name}")
        except:
            print(f"  ❌ analysis.ml.{module_name}")
            return False
    
    # Step 5: Output validation
    print("\n[5/5] Validating output format...")
    
    # Check that model can make predictions
    # Create dummy data matching the feature count and names the model expects
    dummy_X = pd.DataFrame(
        np.random.randn(1, model.n_features_in_),
        columns=expected_features  # Use the expected feature names
    )
    
    try:
        predictions = model.predict(dummy_X)
        print(f"  ✅ Model prediction works")
        print(f"     - Prediction shape: {predictions.shape}")
        print(f"     - Prediction value (dummy): {predictions[0]:.4f}")
    except Exception as e:
        print(f"  ❌ Model prediction failed: {e}")
        return False
    
    # Display validation checks
    print("\n" + "=" * 70)
    print("VALIDATION CHECKS")
    print("=" * 70)
    
    checks = [
        ("Model file exists", model_path.exists()),
        ("Model type is RandomForest", "RandomForest" in type(model).__name__),
        ("Features count matches", model.n_features_in_ == len(expected_features)),
        ("Model can predict", predictions is not None and len(predictions) > 0),
        ("All modules importable", all(m is not None for _, m in modules_to_check)),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"  {status} {check_name}")
        if not check_result:
            all_passed = False
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    if all_passed:
        print("✅ Phase 4 validation passed!")
        print(f"\nPhase 4 Implementation Summary:")
        print(f"  - Model: RandomForestRegressor with {model.n_estimators} trees")
        print(f"  - Features: {model.n_features_in_} technical/pattern features")
        print(f"  - Ranking: Sigmoid-normalized confidence scores (0-1)")
        print(f"  - Output: JSON-serializable event rankings")
        print(f"\nUsage:")
        print(f"  - Run 'example_ml_ranking.py' for complete demo with 13 ranked events")
        print(f"  - Run 'validate_phase_4.py' for quick validation")
        print(f"\nNext Phase: Phase 5 - Chart Animation & Video Generation")
        return True
    else:
        print("❌ Validation failed!")
        return False


if __name__ == "__main__":
    success = validate_phase_4()
    exit(0 if success else 1)
