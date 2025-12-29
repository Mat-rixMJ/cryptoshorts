"""
Event Overlays

Visual overlay system for highlighting events, patterns, and movements.
Provides reusable components for annotating charts with pattern information.
"""

import logging
from typing import Optional, Dict, Any

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from visuals.styles import ChartStyle, get_default_style

logger = logging.getLogger(__name__)


class EventOverlay:
    """Visual overlay for event information.
    
    Handles adding visual elements to chart:
    - Event marker (vertical line)
    - Direction arrow (up/down)
    - Pattern name annotation
    - ML score annotation
    """
    
    def __init__(self, style: Optional[ChartStyle] = None):
        """Initialize overlay.
        
        Args:
            style: ChartStyle instance (uses default if None)
        """
        self.style = style or get_default_style()
    
    def add_event_marker(
        self,
        ax: plt.Axes,
        event_index: int,
        event_price: float,
        pattern_name: str,
        ml_score: float = None
    ) -> None:
        """Add event marker with pattern information.
        
        Args:
            ax: Matplotlib axes
            event_index: Index of event candle
            event_price: Price at event (typically close price)
            pattern_name: Name of detected pattern
            ml_score: ML ranking score (0-1)
        """
        ylim = ax.get_ylim()
        
        # Vertical line marking the event
        ax.axvline(
            x=event_index,
            color=self.style.colors["event_marker"],
            linewidth=2.0,
            alpha=0.8,
            linestyle="--",
            zorder=5
        )
        
        # Highlight zone around event
        rect = patches.Rectangle(
            (event_index - 0.4, ylim[0]),
            0.8,
            ylim[1] - ylim[0],
            facecolor=self.style.colors["event_highlight"],
            edgecolor=self.style.colors["event_marker"],
            linewidth=1.5,
            alpha=0.25,
            zorder=1
        )
        ax.add_patch(rect)
        
        # Event candle circle
        ax.plot(
            [event_index],
            [event_price],
            marker="o",
            markersize=10,
            color=self.style.colors["event_marker"],
            markeredgecolor=self.style.colors["text"],
            markeredgewidth=1,
            zorder=6
        )
        
        # Pattern annotation
        annotation_text = f"{pattern_name}"
        if ml_score is not None:
            annotation_text += f"\nScore: {ml_score:.3f}"
        
        ax.annotate(
            annotation_text,
            xy=(event_index, event_price),
            xytext=(20, 20),
            textcoords="offset points",
            fontsize=11,
            color=self.style.colors["text"],
            fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.7",
                facecolor=self.style.colors["background"],
                edgecolor=self.style.colors["event_marker"],
                linewidth=2,
                alpha=0.95
            ),
            arrowprops=dict(
                arrowstyle="->",
                color=self.style.colors["event_marker"],
                lw=2,
                connectionstyle="arc3,rad=0.3"
            ),
            zorder=10
        )
    
    def add_direction_arrow(
        self,
        ax: plt.Axes,
        event_index: int,
        from_price: float,
        to_price: float,
        magnitude_pct: float = None
    ) -> None:
        """Add arrow showing price movement direction.
        
        Args:
            ax: Matplotlib axes
            event_index: Index of event
            from_price: Starting price
            to_price: Ending price
            magnitude_pct: Percentage move (for annotation)
        """
        is_up = to_price > from_price
        arrow_color = self.style.colors["candle_up"] if is_up else self.style.colors["candle_down"]
        arrow_symbol = "↑" if is_up else "↓"
        
        # Arrow annotation
        y_pos = max(from_price, to_price) + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.05
        
        arrow_text = arrow_symbol
        if magnitude_pct is not None:
            arrow_text += f" {abs(magnitude_pct):.2f}%"
        
        ax.annotate(
            arrow_text,
            xy=(event_index, y_pos),
            fontsize=16,
            color=arrow_color,
            fontweight="bold",
            ha="center",
            va="bottom",
            zorder=8
        )
    
    def add_support_resistance(
        self,
        ax: plt.Axes,
        level_price: float,
        level_type: str = "Support",
        alpha: float = 0.5
    ) -> None:
        """Add support/resistance level line.
        
        Args:
            ax: Matplotlib axes
            level_price: Price level
            level_type: "Support" or "Resistance"
            alpha: Line transparency
        """
        color = self.style.colors["ema_50"] if level_type == "Support" else self.style.colors["ema_20"]
        
        ax.axhline(
            y=level_price,
            color=color,
            linewidth=1.5,
            alpha=alpha,
            linestyle=":",
            zorder=3
        )
        
        # Level label
        ax.text(
            ax.get_xlim()[1] * 0.95,
            level_price,
            f" {level_type}",
            fontsize=9,
            color=color,
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor=self.style.colors["background"],
                edgecolor=color,
                linewidth=1,
                alpha=0.8
            )
        )
    
    def add_volume_spike_indicator(
        self,
        ax: plt.Axes,
        index: int,
        is_spike: bool
    ) -> None:
        """Add indicator for volume spike.
        
        Args:
            ax: Matplotlib axes
            index: Candle index
            is_spike: Whether volume is spiking
        """
        if not is_spike:
            return
        
        ylim = ax.get_ylim()
        mid_y = ylim[0] + (ylim[1] - ylim[0]) * 0.95
        
        # Spike indicator symbol
        ax.text(
            index,
            mid_y,
            "↕",
            fontsize=14,
            color=self.style.colors["candle_up"],
            ha="center",
            va="center",
            fontweight="bold",
            alpha=0.8,
            zorder=7
        )
    
    def add_pattern_context_box(
        self,
        ax: plt.Axes,
        start_index: int,
        end_index: int,
        context_info: str = None
    ) -> None:
        """Add context box around event window.
        
        Args:
            ax: Matplotlib axes
            start_index: Window start
            end_index: Window end
            context_info: Optional info text
        """
        ylim = ax.get_ylim()
        
        # Context box
        rect = patches.Rectangle(
            (start_index - 0.5, ylim[0]),
            end_index - start_index + 1,
            ylim[1] - ylim[0],
            facecolor=self.style.colors["event_highlight"],
            edgecolor=self.style.colors["event_marker"],
            linewidth=1,
            alpha=0.15,
            linestyle="--",
            zorder=0
        )
        ax.add_patch(rect)
        
        # Info text (if provided)
        if context_info:
            mid_x = (start_index + end_index) / 2
            ax.text(
                mid_x,
                ylim[1] * 0.98,
                context_info,
                fontsize=9,
                color=self.style.colors["text"],
                ha="center",
                va="top",
                style="italic",
                alpha=0.7
            )


def create_event_overlay(style: Optional[ChartStyle] = None) -> EventOverlay:
    """Create event overlay instance.
    
    Args:
        style: Optional ChartStyle instance
        
    Returns:
        EventOverlay instance
    """
    return EventOverlay(style)
