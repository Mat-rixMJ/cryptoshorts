"""
Local TTS via Piper (preferred) to generate WAV, then normalize and speed-adjust.

Requirements:
- Piper installed locally and accessible (PATH or provided exe path).
- Voice model (.onnx) path provided in config.
- FFmpeg installed for audio processing (atempo, loudnorm).
"""
from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path
from typing import Optional, Dict
import logging

from .config import AudioConfig, load_audio_config

logger = logging.getLogger(__name__)


def _ensure_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("FFmpeg not found in PATH. Please install ffmpeg.")
    return exe


def _ensure_piper(cfg: AudioConfig) -> str:
    exe = cfg.piper_exe or shutil.which("piper")
    if not exe:
        raise RuntimeError("Piper TTS not found. Set AudioConfig.piper_exe or add to PATH.")
    return exe


def _wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
        return frames / float(rate or 1)


def synthesize_wav(text: str, out_wav: Path, cfg: AudioConfig) -> Dict[str, object]:
    """Run Piper TTS to synthesize narration to WAV.

    Args:
        text: Narration text
        out_wav: Destination wav path
        cfg: AudioConfig (must include piper_model)

    Returns:
        Dict with {path, raw_seconds}
    """
    ffmpeg = _ensure_ffmpeg()
    piper = _ensure_piper(cfg)

    if not cfg.piper_model:
        raise RuntimeError("AudioConfig.piper_model is required for Piper TTS.")

    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    # Call Piper: feed text via stdin, output wav to -f or --output_file
    # Common CLI: piper -m <model.onnx> -f <out.wav>
    cmd = [piper, "-m", str(cfg.piper_model), "-f", str(out_wav)]
    logger.info("piper_synthesize -> %s", out_wav)
    proc = subprocess.run(cmd, input=text, text=True, capture_output=True)
    if proc.returncode != 0:
        logger.error("piper_failed code=%s stderr=%s", proc.returncode, proc.stderr)
        raise RuntimeError("Piper TTS synthesis failed")

    raw_seconds = _wav_duration_seconds(out_wav)
    logger.info("piper_audio raw_duration=%.2fs", raw_seconds)

    return {"path": str(out_wav), "raw_seconds": raw_seconds}


def adjust_speed_and_normalize(in_wav: Path, out_wav: Path, cfg: AudioConfig) -> Dict[str, object]:
    """Use FFmpeg to apply atempo and loudnorm to the narration audio.

    - atempo for speed (speech_speed 0.5–2.0)
    - loudnorm for consistent loudness
    """
    ffmpeg = _ensure_ffmpeg()

    speed = max(min(cfg.speech_speed, 2.0), 0.5)
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    # Apply atempo then loudnorm
    af = f"atempo={speed},loudnorm=I=-16:LRA=11:TP=-1.5"

    cmd = [
        ffmpeg, "-hide_banner", "-y" if cfg.overwrite else "-n",
        "-i", str(in_wav),
        "-af", af,
        "-ar", "44100",
        str(out_wav),
    ]

    logger.info("ffmpeg_normalize -> %s", out_wav)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("ffmpeg_audio_failed code=%s stderr=%s", proc.returncode, proc.stderr)
        raise RuntimeError("FFmpeg audio processing failed")

    seconds = _wav_duration_seconds(out_wav)
    logger.info("voice_final duration=%.2fs", seconds)

    return {"path": str(out_wav), "seconds": seconds}


def generate_voice(script: str, event_id: str, cfg: Optional[AudioConfig] = None) -> Optional[Path]:
    """Adapter: synthesize and normalize voice for an event; return normalized WAV path or None if disabled/unavailable.

    - Auto-load AudioConfig from audio/audio_config.json if cfg is None
    - Respect cfg.enabled flag
    - If Piper not found, log and return None
    """
    cfg = cfg or load_audio_config()
    if not cfg.enabled:
        logger.warning("voiceover_disabled")
        return None

    work_dir = Path("work") / event_id
    raw = work_dir / "voice_raw.wav"
    norm = work_dir / "voice_norm.wav"

    try:
        synthesize_wav(script, raw, cfg)
    except Exception as e:
        logger.warning("piper_unavailable_or_failed err=%s", e)
        return None

    if cfg.normalize_audio:
        adjust_speed_and_normalize(raw, norm, cfg)
        return norm
    else:
        return raw
