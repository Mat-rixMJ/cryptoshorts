"""
Validation and Testing for Chart Frame Generation

Verifies:
1. Frame output integrity (PNG files valid)
2. Frame ordering (zero-padded sequence)
3. Frame count matches configuration
4. Chart dimensions match specification (900x1600)
5. Module imports and basic functionality
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple
import sys

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def validate_frame_files(
    output_dir: Path,
    expected_count: int = None
) -> Dict[str, any]:
    """Validate generated frame files.
    
    Checks:
    - PNG files exist and are readable
    - Files follow naming convention (0001.png, 0002.png, etc.)
    - Files are ordered correctly
    - File sizes reasonable (not empty)
    
    Args:
        output_dir: Directory containing frames
        expected_count: Expected number of frames (None = don't check)
        
    Returns:
        Dict with validation results
    """
    output_dir = Path(output_dir)
    
    if not output_dir.exists():
        return {
            "valid": False,
            "error": f"output_directory_not_found: {output_dir}",
            "frame_count": 0,
            "files": []
        }
    
    # Get PNG files
    png_files = sorted(list(output_dir.glob("*.png")))
    
    results = {
        "valid": True,
        "frame_count": len(png_files),
        "files": [],
        "issues": []
    }
    
    if len(png_files) == 0:
        results["valid"] = False
        results["issues"].append("no_png_files_found")
        return results
    
    # Check expected count
    if expected_count and len(png_files) != expected_count:
        results["issues"].append(
            f"frame_count_mismatch: expected={expected_count} actual={len(png_files)}"
        )
    
    # Validate each file
    for i, png_file in enumerate(png_files):
        file_info = {
            "name": png_file.name,
            "size_bytes": png_file.stat().st_size,
            "sequence_number": None,
            "valid": True
        }
        
        # Check naming convention
        try:
            seq_num = int(png_file.stem)
            file_info["sequence_number"] = seq_num
            
            # Check sequence ordering
            if seq_num != i + 1:
                results["issues"].append(
                    f"sequence_error: file {png_file.name} has number {seq_num} but expected {i+1}"
                )
        except ValueError:
            file_info["valid"] = False
            results["issues"].append(f"invalid_filename: {png_file.name}")
        
        # Check file size (PNG header is minimum ~60 bytes)
        if file_info["size_bytes"] < 60:
            file_info["valid"] = False
            results["issues"].append(f"file_too_small: {png_file.name} ({file_info['size_bytes']} bytes)")
        
        results["files"].append(file_info)
    
    if results["issues"]:
        results["valid"] = False
    
    return results


def validate_png_dimensions(
    png_path: Path,
    expected_width: int = 900,
    expected_height: int = 1600
) -> Dict[str, any]:
    """Validate PNG dimensions.
    
    Args:
        png_path: Path to PNG file
        expected_width: Expected width in pixels
        expected_height: Expected height in pixels
        
    Returns:
        Dict with dimension validation
    """
    try:
        import struct
        
        png_path = Path(png_path)
        
        with open(png_path, 'rb') as f:
            # PNG signature
            sig = f.read(8)
            if sig != b'\x89PNG\r\n\x1a\n':
                return {
                    "valid": False,
                    "error": "not_a_valid_png_file"
                }
            
            # IHDR chunk
            size_bytes = f.read(4)
            chunk_type = f.read(4)
            
            if chunk_type != b'IHDR':
                return {
                    "valid": False,
                    "error": "invalid_png_structure"
                }
            
            width_bytes = f.read(4)
            height_bytes = f.read(4)
            
            width = struct.unpack('>I', width_bytes)[0]
            height = struct.unpack('>I', height_bytes)[0]
            
            result = {
                "valid": True,
                "width": width,
                "height": height,
                "expected_width": expected_width,
                "expected_height": expected_height,
                "matches": width == expected_width and height == expected_height
            }
            
            if not result["matches"]:
                result["valid"] = False
            
            return result
            
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


def validate_module_imports() -> Dict[str, any]:
    """Validate module imports and basic functionality.
    
    Returns:
        Dict with import validation results
    """
    results = {
        "valid": True,
        "modules": {}
    }
    
    # Test styles import
    try:
        from visuals import ChartStyle, get_default_style
        style = get_default_style()
        assert style is not None
        results["modules"]["styles"] = "ok"
    except Exception as e:
        results["modules"]["styles"] = f"failed: {e}"
        results["valid"] = False
    
    # Test charts import
    try:
        from visuals import render_candlestick_chart
        assert callable(render_candlestick_chart)
        results["modules"]["charts"] = "ok"
    except Exception as e:
        results["modules"]["charts"] = f"failed: {e}"
        results["valid"] = False
    
    # Test overlays import
    try:
        from visuals import EventOverlay, create_event_overlay
        assert callable(create_event_overlay)
        results["modules"]["overlays"] = "ok"
    except Exception as e:
        results["modules"]["overlays"] = f"failed: {e}"
        results["valid"] = False
    
    # Test frames import
    try:
        from visuals import FrameConfig, generate_event_frames
        config = FrameConfig()
        assert config.frames_per_event == 60
        results["modules"]["frames"] = "ok"
    except Exception as e:
        results["modules"]["frames"] = f"failed: {e}"
        results["valid"] = False
    
    return results


def validate_dataframe_structure(df: pd.DataFrame) -> Dict[str, any]:
    """Validate Phase 2 DataFrame structure.
    
    Expected columns:
        - OHLCV: open, high, low, close, volume
        - Indicators: ema_20, ema_50, ema_200
    """
    required_cols = ["open", "high", "low", "close", "volume"]
    optional_cols = ["ema_20", "ema_50", "ema_200"]
    
    results = {
        "valid": True,
        "shape": df.shape,
        "required_columns": {},
        "optional_columns": {},
        "missing": []
    }
    
    # Check required columns
    for col in required_cols:
        if col in df.columns:
            results["required_columns"][col] = "present"
        else:
            results["required_columns"][col] = "missing"
            results["missing"].append(col)
            results["valid"] = False
    
    # Check optional columns
    for col in optional_cols:
        if col in df.columns:
            results["optional_columns"][col] = "present"
        else:
            results["optional_columns"][col] = "missing"
    
    return results


def run_validation_suite() -> Dict[str, any]:
    """Run complete validation suite.
    
    Returns:
        Dict with all validation results
    """
    logger.info("=== Phase 5 Validation Suite ===")
    
    results = {
        "module_imports": validate_module_imports(),
    }
    
    # Test module imports first
    if not results["module_imports"]["valid"]:
        logger.error("module_import_validation_failed")
        for module, status in results["module_imports"]["modules"].items():
            logger.error(f"  {module}: {status}")
        return results
    
    logger.info("module_imports: OK")
    
    # Validate sample DataFrame
    logger.info("validating_dataframe_structure...")
    df = _create_sample_dataframe()
    results["dataframe"] = validate_dataframe_structure(df)
    
    if results["dataframe"]["missing"]:
        logger.error(f"missing_columns: {results['dataframe']['missing']}")
    else:
        logger.info("dataframe_structure: OK")
    
    # Try rendering a sample frame
    logger.info("testing_frame_rendering...")
    test_dir = Path("visuals/test_frames")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        from visuals import FrameConfig, generate_event_frames, get_default_style
        
        config = FrameConfig(
            frames_per_event=3,  # Minimal for testing
            show_volume=True,
            show_ema=[20, 50, 200],
            style=get_default_style()
        )
        
        num_frames, output_dir = generate_event_frames(
            df,
            event_index=50,
            event_pattern="TEST_PATTERN",
            ml_score=0.75,
            output_dir=test_dir,
            config=config
        )
        
        results["test_render"] = {
            "valid": num_frames > 0,
            "frames_generated": num_frames,
            "output_dir": str(output_dir)
        }
        
        logger.info(f"test_render: {num_frames} frames generated")
        
        # Validate generated frames
        if num_frames > 0:
            results["frame_validation"] = validate_frame_files(output_dir, expected_count=num_frames)
            
            if results["frame_validation"]["valid"]:
                logger.info("frame_files: OK")
            else:
                logger.error(f"frame_validation_issues: {results['frame_validation']['issues']}")
            
            # Check dimensions of first frame
            first_frame = list(output_dir.glob("*.png"))[0]
            results["frame_dimensions"] = validate_png_dimensions(first_frame)
            
            if results["frame_dimensions"]["valid"]:
                logger.info(f"frame_dimensions: {results['frame_dimensions']['width']}x{results['frame_dimensions']['height']}")
            else:
                logger.error(f"dimension_error: {results['frame_dimensions'].get('error', 'unknown')}")
        
    except Exception as e:
        logger.error(f"test_render_failed: {e}")
        results["test_render"] = {
            "valid": False,
            "error": str(e)
        }
    
    return results


def _create_sample_dataframe(num_rows: int = 100) -> pd.DataFrame:
    """Create sample OHLCV DataFrame for testing."""
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
    
    df["ema_20"] = df["close"].ewm(span=20).mean()
    df["ema_50"] = df["close"].ewm(span=50).mean()
    df["ema_200"] = df["close"].ewm(span=200).mean()
    
    df.set_index("timestamp", inplace=True)
    
    return df


if __name__ == "__main__":
    validation_results = run_validation_suite()
    
    # Summary
    logger.info("\n=== Validation Summary ===")
    all_valid = all(
        v.get("valid", False) if isinstance(v, dict) else True
        for v in validation_results.values()
    )
    
    if all_valid:
        logger.info("✓ All validations passed")
        sys.exit(0)
    else:
        logger.error("✗ Some validations failed")
        sys.exit(1)
