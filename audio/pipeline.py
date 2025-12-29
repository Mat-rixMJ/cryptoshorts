from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from .config import AudioConfig, load_config
from .scripts import EventMeta, generate_voice_script
from .tts import synthesize_wav, adjust_speed_and_normalize
from .captions import build_captions, write_srt
from .merge import mux_audio_video

logger = logging.getLogger(__name__)


def assemble_voiceover_video(
    event: EventMeta,
    silent_mp4: Path,
    out_mp4: Path,
    work_dir: Path,
    cfg: AudioConfig | None = None,
) -> Dict[str, str]:
    """End-to-end pipeline: TTS -> normalize -> captions -> mux.

    Returns paths for {voice_raw, voice_norm, captions, final_mp4}.
    """
    cfg = cfg or AudioConfig()

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1) Script
    script = generate_voice_script(event, add_disclaimer=cfg.add_disclaimer)
    logger.info("voice_script chars=%d", len(script))

    # 2) Synthesize raw WAV
    raw_wav = work_dir / "voice_raw.wav"
    tts_info = synthesize_wav(script, raw_wav, cfg)

    # 3) Normalize + speed adjust
    norm_wav = work_dir / "voice_norm.wav"
    norm_info = adjust_speed_and_normalize(raw_wav, norm_wav, cfg)

    # 4) Captions (deterministic) based on final audio duration
    captions = build_captions(script, total_seconds=norm_info["seconds"], cfg=cfg)
    srt_path = work_dir / "captions.srt"
    write_srt(captions, srt_path)

    # 5) Mux with video
    final = mux_audio_video(silent_mp4, norm_wav, out_mp4, cfg)

    return {
        "voice_raw": str(raw_wav),
        "voice_norm": str(norm_wav),
        "captions": str(srt_path),
        "final_mp4": final["path"],
    }
