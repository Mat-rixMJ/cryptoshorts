"""
Optional effect helpers for building FFmpeg filter snippets.

These functions only return strings for integration into a larger filtergraph
and are intentionally minimal. The defaults are conservative and disabled by
config unless explicitly turned on.
"""
from __future__ import annotations

from typing import Optional


def zoom_filter(total_frames: int, total_zoom: float) -> str:
    """Return a subtle zoompan filter.

    Args:
        total_frames: Number of frames in the final clip
        total_zoom: Total zoom factor above 1.0 over the whole clip
    """
    if total_frames <= 0 or total_zoom <= 0:
        return ""
    per_frame = min(total_zoom / total_frames, 0.002)
    return (
        "zoompan="
        "z='min(zoom+%.6f,1+%.6f)':"
        "d=1:"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)'"
    ) % (per_frame, total_zoom)


def fade_filters(total_frames: int, fps: int, fade_seconds: float) -> str:
    """Return fade in/out filters for the clip.

    Fades are symmetrical, clamped for very short clips.
    """
    if fade_seconds <= 0:
        return ""
    total_duration = max(total_frames / max(fps, 1), 0.0001)
    fd = min(fade_seconds, total_duration / 3)
    fade_out_start = max(total_duration - fd, 0)
    return f"fade=t=in:st=0:d={fd},fade=t=out:st={fade_out_start}:d={fd}"


def smoothing_filter(target_fps: int) -> str:
    """Return minterpolate for motion smoothing to target_fps.

    Disabled by default; use sparingly to avoid artifacts.
    """
    return f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
