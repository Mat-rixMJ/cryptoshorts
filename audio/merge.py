"""
FFmpeg merge: mux narration WAV into silent vertical MP4.

- Maps video and audio streams, encodes audio (AAC), keeps shortest.
- Produces final MP4.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict
import logging

from .config import AudioConfig

logger = logging.getLogger(__name__)


def _ensure_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("FFmpeg not found in PATH. Please install ffmpeg.")
    return exe


def mux_audio_video(silent_mp4: Path, narration_wav: Path, out_mp4: Path, cfg: AudioConfig) -> Dict[str, str]:
    ffmpeg = _ensure_ffmpeg()

    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    # Build command; include audio only if it exists
    cmd = [ffmpeg, "-hide_banner", "-y" if cfg.overwrite else "-n", "-i", str(silent_mp4)]
    if Path(narration_wav).exists():
        cmd += ["-i", str(narration_wav)]
        cmd += [
            "-c:v", "copy",
            "-c:a", cfg.audio_codec,
            "-b:a", cfg.audio_bitrate,
            "-shortest",
            str(out_mp4),
        ]
    else:
        # No audio available, output video-only
        cmd += [
            "-c:v", "copy",
            str(out_mp4),
        ]

    logger.info("ffmpeg_mux -> %s", out_mp4)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("ffmpeg_mux_failed code=%s stderr=%s", proc.returncode, proc.stderr)
        raise RuntimeError("FFmpeg muxing failed")

    return {"path": str(out_mp4)}


def mux_with_soft_subtitles(video_mp4: Path, narration_wav: Path, srt_path: Path, out_mp4: Path, cfg: AudioConfig) -> Dict[str, str]:
    ffmpeg = _ensure_ffmpeg()
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg, "-hide_banner", "-y" if cfg.overwrite else "-n",
        "-i", str(video_mp4),
        "-i", str(narration_wav),
        "-i", str(srt_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-map", "2:s:0",
        "-c:v", "copy",
        "-c:a", cfg.audio_codec,
        "-b:a", cfg.audio_bitrate,
        "-c:s", "mov_text",
        "-metadata:s:s:0", f"language={cfg.subtitle_language}",
        "-shortest",
        str(out_mp4),
    ]

    logger.info("ffmpeg_mux_softsubs -> %s", out_mp4)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("ffmpeg_softsubs_failed code=%s stderr=%s", proc.returncode, proc.stderr)
        raise RuntimeError("FFmpeg soft subtitle muxing failed")

    return {"path": str(out_mp4)}


def mux_with_burned_subtitles(video_mp4: Path, narration_wav: Path, srt_path: Path, out_mp4: Path, cfg: AudioConfig) -> Dict[str, str]:
    ffmpeg = _ensure_ffmpeg()
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    # Burn subtitles into video via subtitles filter; re-encode video.
    # Use force_style for readability on mobile.
    srt_posix = str(srt_path).replace("\\", "/")
    force_style = "FontSize=36,Outline=2,Alignment=2"  # bottom-center

    inputs = [ffmpeg, "-hide_banner", "-y" if cfg.overwrite else "-n", "-i", str(video_mp4)]
    maps = []
    # Include audio if available
    if Path(narration_wav).exists():
        inputs += ["-i", str(narration_wav)]
        maps = ["-map", "[v]", "-map", "1:a:0"]
    else:
        maps = ["-map", "[v]"]

    filter_complex = f"[0:v]subtitles='{srt_posix}:force_style={force_style}'[v]"
    cmd = inputs + [
        "-filter_complex", filter_complex,
        *maps,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-c:a", cfg.audio_codec,
        "-b:a", cfg.audio_bitrate,
        "-shortest",
        str(out_mp4),
    ]

    logger.info("ffmpeg_mux_burnsubs -> %s", out_mp4)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("ffmpeg_burnsubs_failed code=%s stderr=%s", proc.returncode, proc.stderr)
        raise RuntimeError("FFmpeg burned subtitle muxing failed")

    return {"path": str(out_mp4)}


def merge_audio_video(video_path: Path, audio_path: Path, captions_path: Path, event_id: str, cfg: AudioConfig | None = None, burn_captions: bool = True) -> Path:
    """Adapter: merge audio and video; captions kept as external SRT file.

    Returns final MP4 path.
    """
    cfg = cfg or AudioConfig()
    final = Path("video") / "final" / f"{event_id}.mp4"
    # Decide burn vs external based on explicit flag; keep external SRT either way
    if burn_captions and Path(captions_path).exists():
        # Burn subtitles visually; include audio if available, else produce silent video
        mux_with_burned_subtitles(video_path, audio_path, captions_path, final, cfg)
    else:
        # Soft subtitle embedding if requested via cfg.subtitle_mode; else audio-only mux
        if cfg.subtitle_mode == "soft" and Path(captions_path).exists():
            mux_with_soft_subtitles(video_path, audio_path, captions_path, final, cfg)
        else:
            mux_audio_video(video_path, audio_path, final, cfg)
    return final
