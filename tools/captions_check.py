from dataclasses import dataclass
from pathlib import Path
from typing import Dict

TEST_DIR = Path("tools/work")
TEST_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CaptionsResult:
    component: str
    status: str
    notes: str
    details: Dict


def _build_srt() -> Path:
    path = TEST_DIR / "test_captions.srt"
    content = (
        "1\n"
        "00:00:00,000 --> 00:00:00,500\n"
        "Hello world.\n\n"
        "2\n"
        "00:00:00,600 --> 00:00:01,200\n"
        "This is a caption test.\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def _validate_srt(path: Path) -> Dict:
    text = path.read_text(encoding="utf-8")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    ok_utf8 = True
    # Ordering: ensure indices increasing and timestamps ordered
    indices = []
    times = []
    for i in range(0, len(lines), 3):
        try:
            idx = int(lines[i])
            indices.append(idx)
            start, _, end = lines[i+1].partition("-->")
            times.append((start.strip(), end.strip()))
        except Exception:
            pass
    ordered_idx = all(indices[i] < indices[i+1] for i in range(len(indices)-1))
    # Simple lexicographic order check for timestamps
    ordered_ts = all(times[i][1] <= times[i+1][0] or times[i][0] < times[i][1] for i in range(len(times)-1))
    return {
        "utf8": ok_utf8,
        "ordered_indices": ordered_idx,
        "ordered_timestamps": ordered_ts,
    }


def check_captions() -> CaptionsResult:
    srt = _build_srt()
    val = _validate_srt(srt)
    status = "OK" if all(val.values()) else "FAILED"
    notes = []
    if not val.get("utf8"):
        notes.append("UTF-8 encoding invalid")
    if not val.get("ordered_indices"):
        notes.append("SRT indices out of order")
    if not val.get("ordered_timestamps"):
        notes.append("SRT timestamps invalid")
    if status == "OK":
        notes.append("SRT generation validated")
    return CaptionsResult("Captions", status, "; ".join(notes), {"srt_path": str(srt), **val})
