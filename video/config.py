"""
Phase-6 Configuration for Video Assembly Engine.

Defines default configuration and helpers to load/merge user overrides.
No I/O beyond simple local file reading is performed.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import json


@dataclass
class VideoConfig:
    """Config values for assembling videos from PNG frames.

    All values are chosen for mobile-first (YouTube Shorts) delivery while
    preserving determinism and compatibility.
    """

    # Output video
    resolution: Tuple[int, int] = (1080, 1920)  # (width, height)
    fps: int = 30
    video_codec: str = "libx264"
    crf: int = 18
    preset: str = "fast"
    pix_fmt: str = "yuv420p"

    # Behavior
    overwrite: bool = True  # Allow overwriting output files
    verify_contiguous_frames: bool = True  # Require 0001..00NN without gaps

    # Effects (disabled by default)
    add_zoom: bool = False
    zoom_strength: float = 0.03  # 3% total zoom over full duration
    add_fade: bool = False
    fade_duration_sec: float = 0.35
    motion_smoothing: bool = False  # minterpolate

    # Trimming safety: Shorts must be <= 60s
    hard_cap_seconds: int = 60

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_config(path: Optional[Path]) -> VideoConfig:
    """Load config from a JSON file (optional). Falls back to defaults.

    Args:
        path: Path to a JSON file with overrides or None
    """
    base = VideoConfig()
    if not path:
        return base

    p = Path(path)
    if not p.exists():
        return base

    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Shallow merge of simple types
    merged = base.to_dict()
    for k, v in data.items():
        if k in merged:
            merged[k] = v

    return VideoConfig(**merged)
