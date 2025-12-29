import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict


def _run(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return 1, "", str(e)


@dataclass
class GPUResult:
    component: str
    status: str
    notes: str
    details: Dict


def detect_nvidia() -> Dict:
    info = {"nvidia_smi": False, "name": None, "driver": None}
    smi = shutil.which("nvidia-smi")
    if not smi:
        return info
    code, out, err = _run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"])
    if code == 0 and out.strip():
        info["nvidia_smi"] = True
        parts = out.strip().split(',')
        info["name"] = parts[0].strip()
        if len(parts) > 1:
            info["driver"] = parts[1].strip()
    return info


def detect_ffmpeg_nvenc() -> bool:
    code, out, err = _run(["ffmpeg", "-encoders"])
    if code != 0:
        return False
    return "h264_nvenc" in out


def detect_opencv_cuda() -> bool:
    try:
        import cv2
        return "CUDA" in cv2.getBuildInformation()
    except Exception:
        return False


def check_gpu() -> GPUResult:
    nvidia = detect_nvidia()
    nvenc = detect_ffmpeg_nvenc()
    cv_cuda = detect_opencv_cuda()

    notes = []
    if nvidia.get("nvidia_smi"):
        notes.append(f"NVIDIA GPU: {nvidia.get('name')} (driver {nvidia.get('driver')})")
    else:
        notes.append("No NVIDIA GPU detected (optional)")

    if nvenc:
        notes.append("FFmpeg NVENC available")
    else:
        notes.append("FFmpeg NVENC not available (optional)")

    if cv_cuda:
        notes.append("OpenCV CUDA build detected")
    else:
        notes.append("OpenCV CUDA not detected (optional)")

    return GPUResult(
        component="GPU",
        status="OK",
        notes="; ".join(notes),
        details={
            "nvidia": nvidia,
            "ffmpeg_nvenc": nvenc,
            "opencv_cuda": cv_cuda,
        },
    )
