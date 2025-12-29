"""
Phase-6: Video Assembly Engine

Converts ordered PNG frame sequences into mobile-optimized vertical MP4 videos.

- Deterministic output
- Smooth playback
- Shorts-first (9:16, 1080x1920)
- FFmpeg does the heavy lifting; Python orchestrates

Usage (CLI):
    python -m video.assemble --frames visuals/frames/EVENT_123 --out video/base/EVENT_123.mp4 --fps 30
"""
from __future__ import annotations

import logging
import re
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import VideoConfig, load_config
from .ffmpeg_utils import (
    build_sequence_to_mp4_cmd,
    ensure_ffmpeg_available,
)

logger = logging.getLogger(__name__)


NUMERIC_PNG_RE = re.compile(r"^(\d{4})\.png$")


def _scan_frames(frames_dir: Path) -> Tuple[int, List[Path]]:
    """Scan and validate frame files in frames_dir.

    Returns number of frames and the sorted list of frame paths.
    Fails fast if directory missing or empty.
    """
    frames_dir = Path(frames_dir)
    if not frames_dir.exists() or not frames_dir.is_dir():
        raise FileNotFoundError(f"Frames directory not found: {frames_dir}")

    frames = [p for p in frames_dir.iterdir() if p.is_file() and NUMERIC_PNG_RE.match(p.name)]
    if not frames:
        raise FileNotFoundError(f"No PNG frames found in {frames_dir} (expected 0001.png .. 00NN.png)")

    frames.sort(key=lambda p: int(p.stem))
    return len(frames), frames


def _validate_contiguous(frames: List[Path]) -> None:
    """Ensure frames are contiguous increasing numbers starting from the first frame's index.

    Accepts sequences starting at 0000 or 0001 (or any index) as long as numbering
    increases by 1 with no gaps.
    """
    if not frames:
        return
    start = int(frames[0].stem)
    for offset, p in enumerate(frames):
        n = int(p.stem)
        expected = start + offset
        if n != expected:
            raise ValueError(
                f"Frame numbering not contiguous: expected {expected:04d}.png but found {p.name}"
            )


def assemble_video(
    frames_dir: Path,
    output_path: Path,
    fps: Optional[int] = None,
    config: Optional[VideoConfig] = None,
) -> Dict[str, object]:
    """Assemble a video from a directory of PNG frames using FFmpeg.

    Args:
        frames_dir: Directory containing ordered PNGs (0001.png .. 00NN.png)
        output_path: Output MP4 path (parent will be created)
        fps: Override frames-per-second (24 or 30 recommended)
        config: VideoConfig overrides

    Returns:
        Dict with metadata: {event_id, frame_count, fps, output, size_bytes, seconds, ffmpeg_ms}
    """
    cfg = config or VideoConfig()
    if fps is not None:
        cfg = VideoConfig(**{**cfg.to_dict(), "fps": int(fps)})

    ensure_ffmpeg_available()

    event_id = Path(frames_dir).name

    # Scan + validate
    total_frames, frame_list = _scan_frames(frames_dir)
    if cfg.verify_contiguous_frames:
        _validate_contiguous(frame_list)

    # Cap duration to Shorts limit
    max_frames = min(total_frames, cfg.hard_cap_seconds * cfg.fps)

    # Prepare filesystem
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build FFmpeg command
    # Determine starting frame number for ffmpeg image2 demuxer
    start_number = int(frame_list[0].stem)

    cmd = build_sequence_to_mp4_cmd(
        frames_dir=Path(frames_dir),
        output_path=output_path,
        frames_count=total_frames,
        cfg=cfg,
        fps=cfg.fps,
        start_number=start_number,
    )

    # Execute
    start = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    if proc.returncode != 0:
        logger.error("ffmpeg_failed event=%s code=%s", event_id, proc.returncode)
        if proc.stdout:
            logger.error("ffmpeg_stdout:\n%s", proc.stdout)
        if proc.stderr:
            logger.error("ffmpeg_stderr:\n%s", proc.stderr)
        raise RuntimeError(f"FFmpeg failed for {event_id} (exit {proc.returncode})")

    # Collect stats
    size_bytes = output_path.stat().st_size if output_path.exists() else 0
    seconds = min(total_frames / cfg.fps, cfg.hard_cap_seconds)

    result = {
        "event_id": event_id,
        "frame_count": total_frames,
        "fps": cfg.fps,
        "output": str(output_path),
        "size_bytes": size_bytes,
        "seconds": seconds,
        "ffmpeg_ms": elapsed_ms,
    }

    logger.info(
        "video_assembled event=%s frames=%d fps=%d size=%dB dur=%.2fs time=%dms",
        event_id, total_frames, cfg.fps, size_bytes, seconds, elapsed_ms,
    )

    return result


def _infer_default_output(frames_dir: Path) -> Path:
    event_id = Path(frames_dir).name
    return Path("video") / "base" / f"{event_id}.mp4"


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    parser = argparse.ArgumentParser(description="Assemble PNG frames into a vertical MP4 video")
    parser.add_argument("--frames", required=True, help="Directory with 0001.png .. 00NN.png")
    parser.add_argument("--out", required=False, help="Output MP4 path (default: video/base/{EVENT_ID}.mp4)")
    parser.add_argument("--fps", type=int, default=None, help="Output frames per second (24 or 30)")
    parser.add_argument("--config", default=None, help="Optional JSON config path")

    args = parser.parse_args()
    frames_dir = Path(args.frames)
    out_path = Path(args.out) if args.out else _infer_default_output(frames_dir)

    cfg = load_config(Path(args.config)) if args.config else VideoConfig()

    info = assemble_video(frames_dir, out_path, fps=args.fps, config=cfg)
    print(
        f"Assembled {info['event_id']} → {info['output']}\n"
        f"Frames={info['frame_count']} FPS={info['fps']} Duration={info['seconds']:.2f}s Size={info['size_bytes']}B"
    )


def assemble_video_for_event(frames_dir: Path, event_id: str, fps: int = 30, config: Optional[VideoConfig] = None) -> Path:
    """Adapter: assemble video and return output path for the given event id.

    Output: video/base/{event_id}.mp4
    """
    out = Path("video") / "base" / f"{event_id}.mp4"
    assemble_video(frames_dir, out, fps=fps, config=config)
    return out
