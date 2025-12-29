import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

TEST_DIR = Path("tools/work/test_video")
TEST_DIR.mkdir(parents=True, exist_ok=True)


def _run(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return 1, "", str(e)


def _ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def _ffprobe_info(video_path: Path) -> Dict:
    info = {"resolution": None, "duration": None}
    if not _ffprobe_available():
        return info
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=0",
        str(video_path)
    ]
    code, out, err = _run(cmd)
    if code != 0:
        return info
    width = None
    height = None
    duration = None
    for line in out.splitlines():
        if line.startswith("width="):
            try:
                width = int(line.split("=")[1])
            except Exception:
                pass
        if line.startswith("height="):
            try:
                height = int(line.split("=")[1])
            except Exception:
                pass
        if line.startswith("duration="):
            try:
                duration = float(line.split("=")[1])
            except Exception:
                pass
    info["resolution"] = (width, height) if width and height else None
    info["duration"] = duration
    return info


def generate_dummy_frames() -> Tuple[bool, str]:
    # Use ffmpeg color source to create a few PNG frames (no real content)
    frames_dir = TEST_DIR / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    # Generate 30 frames at 30 fps (~1s)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1",
        "-vf", "fps=30",
        str(frames_dir / "frame_%04d.png"),
    ]
    code, out, err = _run(cmd)
    if code != 0:
        return False, f"ffmpeg color->png failed: {err.strip()}"
    return True, str(frames_dir)


def assemble_test_video(frames_dir: Path) -> Tuple[bool, str]:
    out_video = TEST_DIR / "test_short.mp4"
    if out_video.exists():
        try:
            out_video.unlink()
        except Exception:
            pass
    # Assemble at fixed fps, encode libx264, 1080x1920, yuv420p
    cmd = [
        "ffmpeg", "-y",
        "-r", "30",
        "-start_number", "0001",
        "-i", str(frames_dir / "frame_%04d.png"),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_video)
    ]
    code, out, err = _run(cmd)
    if code != 0:
        return False, f"ffmpeg seq->mp4 failed: {err.strip()}"
    return True, str(out_video)


@dataclass
class VideoResult:
    component: str
    status: str
    notes: str
    details: Dict


def check_video() -> VideoResult:
    ok_frames, frames_info = generate_dummy_frames()
    if not ok_frames:
        return VideoResult("Video", "FAILED", frames_info, {"frames": None})

    ok_video, video_info = assemble_test_video(Path(frames_info))
    if not ok_video:
        return VideoResult("Video", "FAILED", video_info, {"video": None})

    info = _ffprobe_info(Path(video_info))
    res_ok = info.get("resolution") == (1080, 1920)
    dur_ok = (info.get("duration") or 0.0) < 60.0

    status = "OK" if (res_ok and dur_ok) else "FAILED"
    notes = []
    if not res_ok:
        notes.append(f"Resolution invalid: {info.get('resolution')}")
    if not dur_ok:
        notes.append(f"Duration too long: {info.get('duration')}")
    if status == "OK":
        notes.append("Image sequence → MP4 validated")

    return VideoResult(
        component="Video",
        status=status,
        notes="; ".join(notes) if notes else "",
        details={
            "video_path": video_info,
            "resolution": info.get("resolution"),
            "duration": info.get("duration"),
        },
    )
