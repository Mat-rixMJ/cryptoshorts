"""
Base Chart Rendering

Renders candlestick charts with optional indicators using matplotlib.
Optimized for mobile vertical video layout.
"""

import logging
from pathlib import Path
from typing import Optional, List, Tuple

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.collections import PatchCollection

from visuals.styles import ChartStyle, get_default_style, apply_title_style, CANDLE_CONFIG, LINEWIDTHS

logger = logging.getLogger(__name__)


def render_candlestick_chart(
    df: pd.DataFrame,
    save_path: Path,
    title: str = "Price Action",
    show_volume: bool = True,
    show_ema: Optional[List[int]] = None,
    style: Optional[ChartStyle] = None,
    highlight_index: Optional[int] = None,
) -> bool:
    """Render candlestick chart with optional indicators.
    
    Args:
        df: OHLCV DataFrame with columns [open, high, low, close, volume, ema_20, ema_50, ema_200]
        save_path: Path to save PNG frame
        title: Chart title
        show_volume: Whether to show volume bars
        show_ema: List of EMA periods to show (e.g., [20, 50, 200])
        style: ChartStyle instance (uses default if None)
        highlight_index: Index to highlight with event marker
        
    Returns:
        True if successful, False otherwise
    """
    if style is None:
        style = get_default_style()
    
    try:
        # Create figure and axes
        fig, ax_price = plt.subplots(
            figsize=style.figure_size,
            dpi=style.dpi,
            facecolor=style.colors["background"]
        )
        
        # Apply base styling
        style.apply_to_figure(fig, ax_price)
        
        # Set up price subplot
        ax_price.set_ylabel("Price (USD)", color=style.colors["text"], fontsize=11)
        
        # Render candlesticks
        _render_candlesticks(df, ax_price, style)
        
        # Render volume bars (if requested)
        if show_volume:
            ax_volume = ax_price.twinx()
            _render_volume(df, ax_volume, style)
            ax_volume.set_ylabel("Volume", color=style.colors["text"], fontsize=10)
        
        # Render EMAs (if requested)
        if show_ema:
            _render_emas(df, ax_price, show_ema, style)
        
        # Highlight event candle (if requested)
        if highlight_index is not None:
            _highlight_event_candle(df, ax_price, highlight_index, style)
        
        # Apply title
        apply_title_style(ax_price, title, style)
        
        # Adjust layout to prevent label cutoff
        plt.tight_layout()
        
        # Save figure
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(
            save_path,
            facecolor=style.colors["background"],
            edgecolor="none",
            bbox_inches="tight",
            pad_inches=0.1,
            dpi=style.dpi
        )
        
        plt.close(fig)
        logger.debug(f"chart_rendered path={save_path}")
        return True
        
    except Exception as e:
        logger.error(f"chart_rendering_failed error={e}")
        plt.close("all")
        return False


def _render_candlesticks(
    df: pd.DataFrame,
    ax: plt.Axes,
    style: ChartStyle
) -> None:
    """Render candlestick candles.
    
    Args:
        df: OHLCV DataFrame
        ax: Matplotlib axes
        style: ChartStyle instance
    """
    width = CANDLE_CONFIG["width"]
    wick_width = CANDLE_CONFIG["wick_width"]
    
    for i, (idx, row) in enumerate(df.iterrows()):
        o = row["open"]
        h = row["high"]
        l = row["low"]
        c = row["close"]
        
        # Determine if candle is up or down
        is_up = c >= o
        candle_color, wick_color = style.get_color_for_movement(is_up)
        
        # Draw wick (high-low line)
        ax.plot(
            [i, i],
            [l, h],
            color=wick_color,
            linewidth=LINEWIDTHS["wick"],
            solid_capstyle="round"
        )
        
        # Draw candle body (open-close)
        candle_low = min(o, c)
        candle_high = max(o, c)
        
        rect = patches.Rectangle(
            (i - width / 2, candle_low),
            width,
            candle_high - candle_low,
            linewidth=LINEWIDTHS["candle_edge"],
            edgecolor=candle_color,
            facecolor=candle_color if is_up else style.colors["background"],
            alpha=1.0
        )
        ax.add_patch(rect)
    
    # Set x-axis limits and labels
    ax.set_xlim(-1, len(df))
    ax.set_xticks(range(0, len(df), max(1, len(df) // 6)))
    ax.set_xticklabels([df.index[i].strftime("%H:%M") if hasattr(df.index[i], "strftime") 
                         else str(df.index[i])[-5:] 
                         for i in ax.get_xticks() if i < len(df)])
    
    # Set y-axis limits with padding
    price_min = df["low"].min()
    price_max = df["high"].max()
    price_range = price_max - price_min
    ax.set_ylim(price_min - price_range * 0.05, price_max + price_range * 0.05)


def _render_volume(
    df: pd.DataFrame,
    ax: plt.Axes,
    style: ChartStyle
) -> None:
    """Render volume bars.
    
    Args:
        df: OHLCV DataFrame with volume column
        ax: Volume axes (twin of price axes)
        style: ChartStyle instance
    """
    if "volume" not in df.columns:
        return
    
    width = CANDLE_CONFIG["width"]
    
    for i, (idx, row) in enumerate(df.iterrows()):
        is_up = row["close"] >= row["open"]
        color = style.colors["volume_up"] if is_up else style.colors["volume_down"]
        
        ax.bar(i, row["volume"], width=width, color=color, edgecolor="none", alpha=0.5)
    
    # Set volume y-axis limits
    max_volume = df["volume"].max()
    ax.set_ylim(0, max_volume * 3)  # 3x padding for visibility
    ax.set_yticks([])  # Hide volume ticks
    
    # Style volume axes
    ax.spines["right"].set_color(style.colors["text"])
    ax.spines["left"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.tick_params(axis="y", colors=style.colors["text"])


def _render_emas(
    df: pd.DataFrame,
    ax: plt.Axes,
    periods: List[int],
    style: ChartStyle
) -> None:
    """Render EMA lines.
    
    Args:
        df: DataFrame with EMA columns (ema_20, ema_50, ema_200, etc.)
        ax: Price axes
        periods: List of EMA periods to display
        style: ChartStyle instance
    """
    ema_colors = {
        20: style.colors["ema_20"],
        50: style.colors["ema_50"],
        200: style.colors["ema_200"],
    }
    
    for period in periods:
        col_name = f"ema_{period}"
        if col_name in df.columns:
            ax.plot(
                range(len(df)),
                df[col_name],
                color=ema_colors.get(period, "#888888"),
                linewidth=LINEWIDTHS["ema"],
                label=f"EMA{period}",
                alpha=0.8
            )
    
    # Add legend if any EMAs were plotted
    if any(f"ema_{p}" in df.columns for p in periods):
        ax.legend(
            loc="upper left",
            fontsize=9,
            labelcolor=style.colors["text"],
            framealpha=0.9,
            facecolor=style.colors["background"],
            edgecolor=style.colors["grid"]
        )


def _highlight_event_candle(
    df: pd.DataFrame,
    ax: plt.Axes,
    index: int,
    style: ChartStyle
) -> None:
    """Highlight event candle with vertical marker.
    
    Args:
        df: OHLCV DataFrame
        ax: Price axes
        index: Index of event candle
        style: ChartStyle instance
    """
    if index < 0 or index >= len(df):
        return
    
    # Get y-axis limits
    ylim = ax.get_ylim()
    
    # Draw vertical line at event
    ax.axvline(
        x=index,
        color=style.colors["event_marker"],
        linewidth=LINEWIDTHS["event_marker"],
        alpha=0.7,
        linestyle="--"
    )
    
    # Draw highlight box around event candle
    rect = patches.Rectangle(
        (index - 0.5, ylim[0]),
        1,
        ylim[1] - ylim[0],
        facecolor=style.colors["event_highlight"],
        edgecolor=style.colors["event_marker"],
        linewidth=1,
        alpha=0.3,
        zorder=-1
    )
    ax.add_patch(rect)


def add_annotation(
    ax: plt.Axes,
    x: float,
    y: float,
    text: str,
    style: Optional[ChartStyle] = None,
    arrow: bool = False
) -> None:
    """Add text annotation to chart.
    
    Args:
        ax: Matplotlib axes
        x: X position
        y: Y position
        text: Annotation text
        style: ChartStyle instance
        arrow: Whether to add arrow
    """
    if style is None:
        style = get_default_style()
    
    annotation = ax.annotate(
        text,
        xy=(x, y),
        xytext=(10, 10),
        textcoords="offset points",
        fontsize=style.fonts["annotation"]["size"],
        color=style.colors["text"],
        fontweight=style.fonts["annotation"]["weight"],
        bbox=dict(
            boxstyle="round,pad=0.5",
            facecolor=style.colors["background"],
            edgecolor=style.colors["event_marker"],
            linewidth=1.5,
            alpha=0.95
        ),
        arrowprops=dict(
            arrowstyle="->",
            color=style.colors["event_marker"],
            lw=1.5
        ) if arrow else None
    )
    
    return annotation
