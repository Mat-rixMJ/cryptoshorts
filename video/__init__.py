"""
Video assembly engine (Phase-6) for CryptoShrts.

Converts ordered PNG frames into mobile-ready vertical MP4 videos.

Public API:
    - VideoConfig: configuration dataclass
    - assemble_video(frames_dir, output_path, fps=None, config=None)
"""
from .config import VideoConfig, load_config
from .assemble import assemble_video
from .ffmpeg_utils import build_sequence_to_mp4_cmd

__all__ = [
    "VideoConfig",
    "load_config",
    "assemble_video",
    "build_sequence_to_mp4_cmd",
]
