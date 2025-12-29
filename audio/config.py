"""
Phase-7 Audio/Caption Configuration.

All values are free/local-friendly and tuned for mobile clarity.
Adds audio_config.json auto-loading for Piper TTS and subtitle options.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Optional, Union
import json


@dataclass
class AudioConfig:
    # TTS
    tts_engine: str = "piper"            # 'piper' or 'coqui' (piper preferred)
    piper_exe: Optional[str] = None      # Path to piper executable (if not in PATH)
    piper_model: Optional[str] = None    # Path to piper voice model .onnx
    voice: str = "en_US"                 # Informational; model controls actual voice
    speech_speed: float = 1.0            # Final audio speed via ffmpeg atempo (0.5–2.0)
    normalize_audio: bool = True         # Apply loudnorm + resample
    enabled: bool = True                 # Enable/disable voice stage cleanly

    # Script
    add_disclaimer: bool = True

    # Captions
    caption_mode: str = "deterministic"  # 'deterministic' or 'whisper'
    max_lines_per_caption: int = 2
    caption_line_max_chars: int = 42

    # Merge/output
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"
    overwrite: bool = True
    # Subtitles
    subtitle_mode: str = "external"  # 'external' | 'soft' | 'burn'
    subtitle_language: str = "en"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_config(path: Optional[Path]) -> AudioConfig:
    """Load JSON config overrides; return defaults if missing.

    Backward-compatible loader; prefers explicit path provided by caller.
    """
    base = AudioConfig()
    if not path:
        return base
    p = Path(path)
    if not p.exists():
        return base
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    merged = base.to_dict()
    for k, v in data.items():
        if k in merged:
            merged[k] = v
    return AudioConfig(**merged)


def load_audio_config(path: Union[str, Path] = "audio/audio_config.json") -> AudioConfig:
    """Auto-load AudioConfig from audio/audio_config.json.

    - Safe defaults if missing
    - Maps schema fields from sample (voice, speech_speed, normalize_audio, enabled)
    """
    base = AudioConfig()
    p = Path(path)
    if not p.exists():
        return base
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return base

    merged = base.to_dict()
    # Accept both legacy and new schema keys
    key_map = {
        "piper_exe": "piper_exe",
        "piper_model": "piper_model",
        "voice": "voice",
        "speech_speed": "speech_speed",
        "normalize_audio": "normalize_audio",
        "enabled": "enabled",
        "audio_codec": "audio_codec",
        "audio_bitrate": "audio_bitrate",
        "subtitle_mode": "subtitle_mode",
        "subtitle_language": "subtitle_language",
        "add_disclaimer": "add_disclaimer",
    }
    for src, dst in key_map.items():
        if src in data:
            merged[dst] = data[src]

    return AudioConfig(**merged)
