"""
Chart Styling System

Defines reusable visual styles optimized for vertical mobile video.
All colors and dimensions chosen for clarity on small screens.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from dataclasses import dataclass
from typing import Tuple, Dict, Any

# Color Palette (High Contrast, Mobile-Friendly)
COLORS = {
    "background": "#0a0e27",      # Dark navy background
    "grid": "#1a1f3a",             # Subtle grid
    "text": "#ffffff",              # White text
    "candle_up": "#00ff41",         # Bright green (bullish)
    "candle_down": "#ff0041",       # Bright red (bearish)
    "wick_up": "#00dd33",           # Green wick
    "wick_down": "#dd0033",         # Red wick
    "volume_up": "#00ff4144",       # Green volume (transparent)
    "volume_down": "#ff004144",     # Red volume (transparent)
    "ema_20": "#64b5f6",            # Light blue
    "ema_50": "#ffa726",            # Orange
    "ema_200": "#ba68c8",           # Purple
    "event_highlight": "#ffff0022", # Yellow highlight (transparent)
    "event_marker": "#ffff00",      # Bright yellow
}

# Typography
FONTS = {
    "title": {"size": 16, "weight": "bold", "family": "monospace"},
    "label": {"size": 12, "weight": "normal", "family": "monospace"},
    "small": {"size": 10, "weight": "normal", "family": "monospace"},
    "annotation": {"size": 11, "weight": "bold", "family": "monospace"},
}

# Dimensions (optimized for 9:16 vertical video)
DIMENSIONS = {
    "width": 9,          # 9 inches width
    "height": 16,        # 16 inches height (9:16 aspect ratio)
    "dpi": 100,          # 100 DPI = 900x1600 pixels
    "margin_left": 0.8,  # Inch
    "margin_right": 0.3,
    "margin_top": 0.5,
    "margin_bottom": 0.8,
}

# Line Widths
LINEWIDTHS = {
    "candle_edge": 0.5,      # Candlestick edges
    "wick": 0.4,              # Wick lines
    "ema": 1.5,               # EMA lines
    "event_marker": 2.0,      # Event vertical line
    "grid": 0.3,              # Grid lines
}

# Candle Sizing
CANDLE_CONFIG = {
    "width": 0.6,             # Candle body width (in candle units)
    "wick_width": 0.2,        # Wick width (in candle units)
    "edge_width": 0.5,        # Border width
}


@dataclass
class ChartStyle:
    """Chart styling configuration."""
    
    width: float = DIMENSIONS["width"]
    height: float = DIMENSIONS["height"]
    dpi: int = DIMENSIONS["dpi"]
    colors: Dict[str, str] = None
    fonts: Dict[str, Dict[str, Any]] = None
    linewidths: Dict[str, float] = None
    
    def __post_init__(self):
        """Set defaults."""
        if self.colors is None:
            self.colors = COLORS.copy()
        if self.fonts is None:
            self.fonts = FONTS.copy()
        if self.linewidths is None:
            self.linewidths = LINEWIDTHS.copy()
    
    @property
    def figure_size(self) -> Tuple[float, float]:
        """Get figure size tuple."""
        return (self.width, self.height)
    
    @property
    def resolution_px(self) -> Tuple[int, int]:
        """Get resolution in pixels."""
        return (int(self.width * self.dpi), int(self.height * self.dpi))
    
    def apply_to_figure(self, fig: plt.Figure, ax: plt.Axes) -> None:
        """Apply style to matplotlib figure and axes.
        
        Args:
            fig: Matplotlib figure
            ax: Matplotlib axes
        """
        # Background colors
        fig.patch.set_facecolor(self.colors["background"])
        ax.set_facecolor(self.colors["background"])
        
        # Grid
        ax.grid(True, color=self.colors["grid"], linestyle="-", linewidth=self.linewidths["grid"])
        ax.set_axisbelow(True)
        
        # Spine colors
        for spine in ax.spines.values():
            spine.set_color(self.colors["text"])
            spine.set_linewidth(1)
        
        # Tick colors
        ax.tick_params(colors=self.colors["text"], labelsize=self.fonts["label"]["size"])
        
        # Label colors
        ax.xaxis.label.set_color(self.colors["text"])
        ax.yaxis.label.set_color(self.colors["text"])
    
    def get_color_for_movement(self, is_up: bool) -> Tuple[str, str]:
        """Get colors for up/down movement.
        
        Args:
            is_up: Whether movement is upward
            
        Returns:
            Tuple of (candle_color, wick_color)
        """
        if is_up:
            return self.colors["candle_up"], self.colors["wick_up"]
        else:
            return self.colors["candle_down"], self.colors["wick_down"]


def get_default_style() -> ChartStyle:
    """Get default chart style for vertical mobile video.
    
    Returns:
        Configured ChartStyle instance
    """
    return ChartStyle()


def apply_title_style(ax: plt.Axes, text: str, style: ChartStyle = None) -> None:
    """Apply title styling to axes.
    
    Args:
        ax: Matplotlib axes
        text: Title text
        style: ChartStyle instance (uses default if None)
    """
    if style is None:
        style = get_default_style()
    
    ax.set_title(
        text,
        color=style.colors["text"],
        fontsize=style.fonts["title"]["size"],
        fontweight=style.fonts["title"]["weight"],
        fontfamily=style.fonts["title"]["family"],
        pad=20
    )


def apply_label_style(text_obj: plt.Text, style: ChartStyle = None) -> None:
    """Apply label styling to text object.
    
    Args:
        text_obj: Matplotlib text object
        style: ChartStyle instance
    """
    if style is None:
        style = get_default_style()
    
    text_obj.set_color(style.colors["text"])
    text_obj.set_fontsize(style.fonts["label"]["size"])
    text_obj.set_fontfamily(style.fonts["label"]["family"])


def apply_annotation_style(text_obj: plt.Text, style: ChartStyle = None) -> None:
    """Apply annotation styling to text object.
    
    Args:
        text_obj: Matplotlib text object
        style: ChartStyle instance
    """
    if style is None:
        style = get_default_style()
    
    text_obj.set_color(style.colors["text"])
    text_obj.set_fontsize(style.fonts["annotation"]["size"])
    text_obj.set_fontweight(style.fonts["annotation"]["weight"])
    text_obj.set_fontfamily(style.fonts["annotation"]["family"])
    text_obj.set_bbox(dict(
        boxstyle="round,pad=0.5",
        facecolor=style.colors["background"],
        edgecolor=style.colors["text"],
        linewidth=1,
        alpha=0.9
    ))
