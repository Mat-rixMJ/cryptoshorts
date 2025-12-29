"""
Frame Generation Engine

Generates sequence of PNG frames for video animation.
Implements sliding candle-by-candle reveal for smooth animation.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

import pandas as pd
import numpy as np

from visuals.styles import ChartStyle, get_default_style
from visuals.charts import render_candlestick_chart, add_annotation
from visuals.overlays import create_event_overlay

logger = logging.getLogger(__name__)


@dataclass
class FrameConfig:
    """Configuration for frame generation."""
    
    frames_per_event: int = 60         # Total frames to generate
    show_volume: bool = True            # Show volume bars
    show_ema: List[int] = None          # EMA periods to show ([20, 50, 200])
    highlight_event: bool = True        # Highlight event candle
    include_future: bool = True         # Include candles after event
    style: Optional[ChartStyle] = None  # Chart style
    
    def __post_init__(self):
        """Set defaults."""
        if self.show_ema is None:
            self.show_ema = [20, 50, 200]
        if self.style is None:
            self.style = get_default_style()


def generate_event_frames(
    df: pd.DataFrame,
    event_index: int,
    event_pattern: str,
    ml_score: float,
    output_dir: Path,
    config: Optional[FrameConfig] = None
) -> Tuple[int, Path]:
    """Generate frame sequence for an event.
    
    Creates animated frame sequence showing:
    1. Context window before event
    2. Event moment highlighted
    3. Post-event candles revealing gradually
    
    Args:
        df: OHLCV DataFrame with indicators
        event_index: Index of event candle
        event_pattern: Name of detected pattern
        ml_score: ML ranking score (0-1)
        output_dir: Directory to save frames
        config: FrameConfig instance
        
    Returns:
        Tuple of (num_frames_generated, output_directory)
    """
    if config is None:
        config = FrameConfig()
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Validate event index
        if event_index < 0 or event_index >= len(df):
            logger.error(f"invalid_event_index index={event_index} df_len={len(df)}")
            return 0, output_dir
        
        # Calculate context window
        context_before = max(5, event_index - 10)  # At least 5 candles before
        context_after = min(len(df) - 1, event_index + 20)  # At least 20 after if available
        
        logger.info(f"generating_frames event_index={event_index} pattern={event_pattern} "
                   f"ml_score={ml_score:.3f} output_dir={output_dir}")
        
        # Phase 1: Build context (show candles before event)
        phase1_frames = int(config.frames_per_event * 0.35)  # 35% of frames
        phase1_step = max(1, (event_index - context_before) / max(1, phase1_frames))
        
        frame_count = 0
        
        # Phase 1: Context building
        for i in range(phase1_frames):
            # Calculate end candle for this frame (gradually reveal up to event)
            frame_end_idx = int(context_before + (event_index - context_before) * (i + 1) / phase1_frames)
            frame_end_idx = min(frame_end_idx, event_index)
            
            success = _render_frame(
                df,
                context_before,
                frame_end_idx,
                event_index,
                event_pattern,
                ml_score,
                output_dir,
                frame_count,
                config,
                phase="context"
            )
            
            if success:
                frame_count += 1
        
        # Phase 2: Event highlight (hold on event, show context)
        phase2_frames = int(config.frames_per_event * 0.20)  # 20% of frames
        for i in range(phase2_frames):
            success = _render_frame(
                df,
                context_before,
                event_index,
                event_index,
                event_pattern,
                ml_score,
                output_dir,
                frame_count,
                config,
                phase="event"
            )
            
            if success:
                frame_count += 1
        
        # Phase 3: Future reveal (gradually show post-event candles)
        phase3_frames = int(config.frames_per_event * 0.45)  # 45% of frames
        
        if config.include_future and context_after > event_index:
            for i in range(phase3_frames):
                # Gradually reveal future candles
                frame_end_idx = int(event_index + (context_after - event_index) * (i + 1) / phase3_frames)
                frame_end_idx = min(frame_end_idx, context_after)
                
                success = _render_frame(
                    df,
                    context_before,
                    frame_end_idx,
                    event_index,
                    event_pattern,
                    ml_score,
                    output_dir,
                    frame_count,
                    config,
                    phase="future"
                )
                
                if success:
                    frame_count += 1
        else:
            # If no future candles, hold on event
            for i in range(phase3_frames):
                success = _render_frame(
                    df,
                    context_before,
                    event_index,
                    event_index,
                    event_pattern,
                    ml_score,
                    output_dir,
                    frame_count,
                    config,
                    phase="future"
                )
                
                if success:
                    frame_count += 1
        
        logger.info(f"frames_generation_complete frames={frame_count} pattern={event_pattern}")
        return frame_count, output_dir
        
    except Exception as e:
        logger.error(f"frame_generation_failed event_index={event_index} error={e}")
        return 0, output_dir


def _render_frame(
    df: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    event_idx: int,
    pattern: str,
    ml_score: float,
    output_dir: Path,
    frame_num: int,
    config: FrameConfig,
    phase: str = "unknown"
) -> bool:
    """Render a single frame.
    
    Args:
        df: Full OHLCV DataFrame
        start_idx: Start index for window
        end_idx: End index for window (inclusive)
        event_idx: Index of event candle
        pattern: Pattern name
        ml_score: ML score
        output_dir: Output directory
        frame_num: Frame number (for ordering)
        config: FrameConfig
        phase: Current phase (context/event/future)
        
    Returns:
        True if successful
    """
    try:
        # Extract window
        window_df = df.iloc[start_idx:end_idx+1].copy()
        
        if len(window_df) < 1:
            return False
        
        # Adjust event_idx to window coordinates
        window_event_idx = event_idx - start_idx if event_idx >= start_idx else None
        
        # Create title with pattern and score
        title = f"{pattern} | ML Score: {ml_score:.3f}"
        
        # Frame filename (zero-padded)
        frame_path = output_dir / f"{frame_num:04d}.png"
        
        # Render chart
        success = render_candlestick_chart(
            window_df,
            frame_path,
            title=title,
            show_volume=config.show_volume,
            show_ema=config.show_ema,
            style=config.style,
            highlight_index=window_event_idx if config.highlight_event else None
        )
        
        if success:
            logger.debug(f"frame_rendered frame={frame_num:04d} pattern={pattern} phase={phase}")
        
        return success
        
    except Exception as e:
        logger.error(f"frame_render_failed frame_num={frame_num} error={e}")
        return False


def generate_multi_event_frames(
    df: pd.DataFrame,
    ranked_events: List[Dict],
    base_output_dir: Path,
    config: Optional[FrameConfig] = None,
    max_events: Optional[int] = None
) -> Dict[str, Tuple[int, Path]]:
    """Generate frames for multiple events.
    
    Args:
        df: OHLCV DataFrame
        ranked_events: List of event dicts with:
            - event_index: int
            - pattern: str
            - ml_score: float
            - event_id: str (optional, auto-generated if missing)
        base_output_dir: Base output directory
        config: FrameConfig instance
        max_events: Maximum events to process (None = all)
        
    Returns:
        Dict mapping event_id -> (num_frames, output_dir)
    """
    if config is None:
        config = FrameConfig()
    
    results = {}
    
    for i, event in enumerate(ranked_events):
        if max_events and i >= max_events:
            break
        
        # Get or generate event ID
        event_id = event.get("event_id", f"event_{event['event_index']:03d}_{event['pattern'][:3]}")
        
        event_dir = base_output_dir / event_id
        
        num_frames, output_dir = generate_event_frames(
            df,
            event["event_index"],
            event["pattern"],
            event["ml_score"],
            event_dir,
            config
        )
        
        results[event_id] = (num_frames, output_dir)
        
        logger.info(f"event_processed event_id={event_id} frames={num_frames}")
    
    return results


def generate_frames_for_event(df: pd.DataFrame, event: Dict, output_base: Path = Path("visuals/frames"), config: Optional[FrameConfig] = None) -> Path:
    """Adapter: generate frames for a single event and return the frames directory.

    Expects event dict with keys: event_index, pattern, ml_score, optional event_id.
    """
    if config is None:
        config = FrameConfig()
    event_id = event.get("event_id", f"event_{event['event_index']:03d}_{event['pattern'][:3]}")
    event_dir = Path(output_base) / event_id
    generate_event_frames(
        df,
        event["event_index"],
        event["pattern"],
        float(event.get("ml_score", 0.0)),
        event_dir,
        config,
    )
    return event_dir
