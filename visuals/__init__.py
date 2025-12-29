"""
visuals - Chart Frame Generation Module

Generates PNG frame sequences for YouTube Shorts visualization.
Supports candlestick charting, indicators, and event overlays.

Components:
    - styles: Chart styling and configuration
    - charts: Candlestick rendering with indicators
    - overlays: Event visualization overlays
    - frames: Frame sequence generation engine

Example:
    from visuals import generate_event_frames, FrameConfig
    from pathlib import Path
    
    config = FrameConfig(frames_per_event=60, show_volume=True)
    num_frames, output_dir = generate_event_frames(
        df=price_df,
        event_index=150,
        event_pattern="BULLISH_CROSS",
        ml_score=0.82,
        output_dir=Path("visuals/frames/event_001"),
        config=config
    )
    print(f"Generated {num_frames} frames in {output_dir}")
"""

from visuals.styles import (
    ChartStyle,
    get_default_style,
    apply_title_style,
    apply_label_style,
    apply_annotation_style,
)

from visuals.charts import (
    render_candlestick_chart,
    add_annotation,
)

from visuals.overlays import (
    EventOverlay,
    create_event_overlay,
)

from visuals.frames import (
    FrameConfig,
    generate_event_frames,
    generate_multi_event_frames,
)

__version__ = "0.1.0"
__author__ = "CryptoShrts Team"

__all__ = [
    # Styles
    "ChartStyle",
    "get_default_style",
    "apply_title_style",
    "apply_label_style",
    "apply_annotation_style",
    # Charts
    "render_candlestick_chart",
    "add_annotation",
    # Overlays
    "EventOverlay",
    "create_event_overlay",
    # Frames
    "FrameConfig",
    "generate_event_frames",
    "generate_multi_event_frames",
]
