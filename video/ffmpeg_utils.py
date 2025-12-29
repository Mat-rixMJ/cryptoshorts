"""
FFmpeg command builders for Phase-6 Video Assembly.

- Image sequence -> H.264 MP4
- Scaling, padding to 9:16 safely (no stretching)
- Optional effects assembled via filterchains
- Deterministic parameters for mobile (YouTube Shorts)

All functions return argument lists suitable for subprocess.run without shell=True.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from .config import VideoConfig


def ensure_ffmpeg_available() -> str:
    """Return the ffmpeg executable path if available in PATH, else raise.
    """
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("FFmpeg not found in PATH. Please install ffmpeg and ensure it is accessible.")
    return exe


def input_pattern_for_sequence(frames_dir: Path, pad: int = 4) -> str:
    """Return printf-style pattern for image2 demuxer: %04d.png.

    Args:
        frames_dir: Directory containing 0001.png, 0002.png, ...
        pad: Zero-padding width (default 4)
    """
    frames_dir = Path(frames_dir)
    return str(frames_dir / ("%0" + str(pad) + "d.png"))


def build_scale_pad_filter(size: Tuple[int, int]) -> str:
    """Build a safe scale+pad filter to fit content into target size without stretching.

    This preserves aspect ratio, first scaling down to fit within the target frame,
    then padding to exact dimensions centered.

    Example result:
        "scale=w=1080:h=1920:force_original_aspect_ratio=decrease,
         pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black"
    """
    w, h = size
    return (
        f"scale=w={w}:h={h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black"
    )


def build_effect_filters(
    size: Tuple[int, int],
    cfg: VideoConfig,
    frames: int,
    fps: int,
) -> str:
    """Assemble optional effect filters (zoom, fade, smoothing).

    Filters are chained in a deterministic order and are disabled by default.
    """
    chains: List[str] = []

    # Slow zoom (Ken Burns-like). Keep subtle; apply after scale/pad.
    # Implement via zoompan with tiny incremental zoom over total frames.
    # Note: zoompan generates frames; we'll keep d=1 to map input->output frames.
    if cfg.add_zoom and cfg.zoom_strength > 0:
        # Target zoom per frame to reach (1 + zoom_strength) at the end
        per_frame = cfg.zoom_strength / max(frames, 1)
        # Cap per-frame to avoid jumps
        per_frame = min(per_frame, 0.002)
        chains.append(
            "zoompan=z='min(zoom+%.6f,1+%.6f)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        )
        chains[-1] = chains[-1] % (per_frame, cfg.zoom_strength)

    # Fade in/out at the start/end of the clip
    if cfg.add_fade and cfg.fade_duration_sec > 0:
        total_duration = max(frames / max(fps, 1), 0.0001)
        fd = min(cfg.fade_duration_sec, total_duration / 3)
        fade_out_start = max(total_duration - fd, 0)
        chains.append(f"fade=t=in:st=0:d={fd}")
        chains.append(f"fade=t=out:st={fade_out_start}:d={fd}")

    # Motion smoothing via minterpolate to target fps (kept subtle by default off)
    if cfg.motion_smoothing:
        chains.append(f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")

    # Always enforce final pixel format for broad compatibility
    chains.append("format=yuv420p,setsar=1")

    return ",".join(chains)


def build_filter_chain(size: Tuple[int, int], cfg: VideoConfig, frames: int, fps: int) -> str:
    """Compose the full filtergraph: scale/pad -> effects -> format.

    Returns a single filtergraph string suitable for `-vf`.
    """
    parts = [build_scale_pad_filter(size)]
    effects = build_effect_filters(size, cfg, frames, fps)
    if effects:
        parts.append(effects)
    return ",".join(parts)


def max_frames_for_cap(cfg: VideoConfig, fps: int) -> int:
    """Maximum frames allowed to respect Shorts duration cap."""
    return max(int(cfg.hard_cap_seconds * max(fps, 1)), 1)


def build_sequence_to_mp4_cmd(
    frames_dir: Path,
    output_path: Path,
    frames_count: int,
    cfg: VideoConfig,
    fps: Optional[int] = None,
    pad: int = 4,
    start_number: int = 1,
) -> List[str]:
    """Build the ffmpeg command to convert an image sequence to an MP4.

    Args:
        frames_dir: Directory with %0{pad}d.png images starting at 1
        output_path: Destination MP4 path
        frames_count: Number of frames detected
        cfg: Video configuration
        fps: Override FPS (defaults to cfg.fps)
        pad: Zero-padding width for image sequence
    """
    ffmpeg = ensure_ffmpeg_available()
    fps = int(fps or cfg.fps)
    w, h = cfg.resolution

    # Enforce duration cap
    max_frames = min(frames_count, max_frames_for_cap(cfg, fps))

    vf = build_filter_chain((w, h), cfg, max_frames, fps)

    in_pattern = input_pattern_for_sequence(frames_dir, pad)

    args: List[str] = [
        ffmpeg,
        "-hide_banner",
        "-stats",
        "-y" if cfg.overwrite else "-n",
        # Set input framerate to map N images -> N/fps seconds deterministically
        "-framerate", str(fps),
        "-start_number", str(int(start_number)),
        "-i", in_pattern,
        # Video filters for aspect-correct vertical output
        "-vf", vf,
        # Encoding params
        "-c:v", cfg.video_codec,
        "-pix_fmt", cfg.pix_fmt,
        "-preset", cfg.preset,
        "-crf", str(cfg.crf),
        # Constant frame rate output
        "-r", str(fps),
        # Trim to max Frames (<= 60s)
        "-frames:v", str(max_frames),
        str(output_path),
    ]
    return args