import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Tuple


def _run(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return 1, "", str(e)


@dataclass
class FFmpegResult:
    component: str
    status: str
    notes: str
    details: Dict


def detect_ffmpeg() -> Tuple[bool, str]:
    path = shutil.which("ffmpeg")
    if not path:
        return False, "ffmpeg not found in PATH"
    code, out, err = _run(["ffmpeg", "-version"])
    if code != 0:
        return False, f"ffmpeg -version failed: {err.strip()}"
    first_line = out.splitlines()[0] if out else ""
    return True, first_line


def check_codecs() -> Dict:
    encoders = {"libx264": False, "aac": False, "h264_nvenc": False}
    code, out, err = _run(["ffmpeg", "-encoders"])
    if code == 0:
        for line in out.splitlines():
            if "libx264" in line:
                encoders["libx264"] = True
            if "aac" in line and "Audio" in out:
                encoders["aac"] = True
            if "h264_nvenc" in line:
                encoders["h264_nvenc"] = True
    return encoders


def check_ffprobe() -> bool:
    path = shutil.which("ffprobe")
    if not path:
        return False
    code, out, err = _run(["ffprobe", "-version"])
    return code == 0


def check_ffmpeg(min_version_major: int = 4) -> FFmpegResult:
    ok, ver_line = detect_ffmpeg()
    if not ok:
        return FFmpegResult(
            component="FFmpeg",
            status="MISSING",
            notes=ver_line,
            details={"ffmpeg": None},
        )

    codecs = check_codecs()
    ffprobe_ok = check_ffprobe()

    # Parse version major
    vmaj = None
    try:
        # Example: ffmpeg version 6.1.1 ...
        parts = ver_line.split()
        for i, p in enumerate(parts):
            if p.lower() == "version" and i + 1 < len(parts):
                vmaj = int(parts[i + 1].split(".")[0])
                break
    except Exception:
        vmaj = None

    status = "OK"
    notes = []
    if vmaj is None or vmaj < min_version_major:
        status = "FAILED"
        notes.append(f"ffmpeg version too old or unknown: {ver_line}")
    if not codecs.get("libx264"):
        status = "FAILED"
        notes.append("libx264 encoder missing")
    if not codecs.get("aac"):
        status = "FAILED"
        notes.append("aac encoder missing")
    if not ffprobe_ok:
        notes.append("ffprobe missing (warning)")

    if status != "OK":
        notes.append("Install FFmpeg with libx264/aac. Windows: scoop/chocolatey; Linux: distro packages.")

    return FFmpegResult(
        component="FFmpeg",
        status=status,
        notes="; ".join(notes) if notes else ver_line,
        details={
            "version_line": ver_line,
            "codecs": codecs,
            "ffprobe": ffprobe_ok,
        },
    )
