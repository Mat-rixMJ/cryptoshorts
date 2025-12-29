import json
import os
import wave
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


TEST_DIR = Path("tools/work")
TEST_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_CONFIG = {
    "enabled": True,
    "piper_exe": "C:/path/to/piper.exe",
    "piper_model": "C:/path/to/en_US-lessac-high.onnx",
    "speech_speed": 1.0,
    "normalize_audio": True,
    "subtitle_mode": "burn",  # burn | soft | external
    "subtitle_language": "en"
}


def _run(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return 1, "", str(e)


def _wav_duration_seconds(path: Path) -> float:
    try:
        with wave.open(str(path), 'rb') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            return frames / float(rate) if rate else 0.0
    except Exception:
        return 0.0


@dataclass
class AudioResult:
    component: str
    status: str
    notes: str
    details: Dict


def _read_audio_config(cfg_path: Path) -> Optional[Dict]:
    try:
        with cfg_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def ensure_sample_config(audio_dir: Path) -> None:
    audio_dir.mkdir(parents=True, exist_ok=True)
    sample_path = audio_dir / "audio_config.sample.json"
    if not sample_path.exists():
        with sample_path.open('w', encoding='utf-8') as f:
            json.dump(SAMPLE_CONFIG, f, indent=2)


def _validate_paths(cfg: Dict) -> Tuple[bool, str]:
    exe = cfg.get("piper_exe")
    model = cfg.get("piper_model")
    if not exe:
        return False, "piper_exe missing in audio_config.json"
    if not model:
        return False, "piper_model missing in audio_config.json"
    if not Path(exe).exists():
        return False, f"piper executable not found: {exe}"
    if not Path(model).exists():
        return False, f"piper model not found: {model}"
    return True, "paths valid"


def run_tts_test(cfg: Dict) -> Tuple[bool, str, float]:
    out_wav = TEST_DIR / "tts_test.wav"
    if out_wav.exists():
        try:
            out_wav.unlink()
        except Exception:
            pass
    exe = cfg.get("piper_exe")
    model = cfg.get("piper_model")
    text = "Hello from the pre-flight check."
    cmd = [exe, "-m", model, "-f", str(out_wav), "-t", text]
    code, out, err = _run(cmd)
    if code != 0:
        return False, f"piper run failed: {err.strip()}", 0.0
    dur = _wav_duration_seconds(out_wav)
    if dur <= 0.01:
        return False, "Generated WAV is zero length", dur
    return True, str(out_wav), dur


def check_audio() -> AudioResult:
    audio_dir = Path("audio")
    ensure_sample_config(audio_dir)
    cfg_path = audio_dir / "audio_config.json"
    has_cfg = cfg_path.exists()
    cfg = _read_audio_config(cfg_path) if has_cfg else None

    status = "OK"
    notes = []
    details = {
        "config_present": has_cfg,
        "paths_valid": False,
        "tts_test": None,
        "wav_duration": 0.0,
    }

    if not has_cfg:
        status = "FAILED"
        notes.append("audio_config.json missing. Created audio_config.sample.json. Configure Piper to enable audio.")
        return AudioResult("Audio/TTS", status, "; ".join(notes), details)

    ok_paths, msg = _validate_paths(cfg)
    details["paths_valid"] = ok_paths
    if not ok_paths:
        status = "FAILED"
        notes.append(msg)
        notes.append("Install Piper and model; update audio/audio_config.json.")
        return AudioResult("Audio/TTS", status, "; ".join(notes), details)

    # Try a test synthesis
    ok_tts, info, dur = run_tts_test(cfg)
    details["tts_test"] = info
    details["wav_duration"] = dur
    if not ok_tts:
        status = "FAILED"
        notes.append(info)
    else:
        notes.append(f"TTS ok ({dur:.2f}s)")

    return AudioResult("Audio/TTS", status, "; ".join(notes), details)
