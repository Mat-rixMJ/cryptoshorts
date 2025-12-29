"""
Deterministic captions (SRT) from narration text.

Two modes:
- deterministic: split text into readable lines, allocate timings evenly across total duration
- whisper: optional future mode stub (not implemented)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List
import math

from .config import AudioConfig
from .tts import _wav_duration_seconds


@dataclass
class CaptionSegment:
    index: int
    start: float
    end: float
    text: str


def _format_ts(seconds: float) -> str:
    s = max(seconds, 0.0)
    hours = int(s // 3600)
    s -= hours * 3600
    minutes = int(s // 60)
    s -= minutes * 60
    secs = int(s)
    ms = int(round((s - secs) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _split_text(text: str, max_chars: int, max_lines_per_caption: int) -> List[str]:
    # Simple split by sentences and commas first
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    parts: List[str] = []
    for sent in sentences:
        if len(sent) <= max_chars:
            parts.append(sent)
        else:
            # fallback: split by commas or spaces
            chunks = re.split(r",\s+|\s+", sent)
            cur = ""
            for ch in chunks:
                nxt = (cur + " " + ch).strip()
                if len(nxt) <= max_chars:
                    cur = nxt
                else:
                    if cur:
                        parts.append(cur)
                    cur = ch
            if cur:
                parts.append(cur)
    # Merge small parts to fit lines per caption
    merged: List[str] = []
    i = 0
    while i < len(parts):
        block = parts[i]
        lines = 1
        j = i + 1
        while j < len(parts) and lines < max_lines_per_caption:
            candidate = block + "\n" + parts[j]
            if len(candidate) <= max_chars * max_lines_per_caption:
                block = candidate
                lines += 1
                j += 1
            else:
                break
        merged.append(block)
        i = j
    return merged


def build_captions(text: str, total_seconds: float, cfg: AudioConfig) -> List[CaptionSegment]:
    if cfg.caption_mode == "whisper":
        # Future: use whisper.cpp alignment results
        raise NotImplementedError("Whisper caption mode not implemented in this offline build.")

    max_chars = cfg.caption_line_max_chars
    max_lines = cfg.max_lines_per_caption

    blocks = _split_text(text, max_chars=max_chars, max_lines_per_caption=max_lines)
    if not blocks:
        return []

    # Allocate time per block evenly, last block ends exactly at total_seconds
    n = len(blocks)
    per = total_seconds / n if n else total_seconds
    segments: List[CaptionSegment] = []
    cur = 0.0
    for idx, b in enumerate(blocks, start=1):
        start = cur
        end = per * idx
        # enforce minimal durations
        dur = end - start
        if dur < 0.8:
            end = start + 0.8
        segments.append(CaptionSegment(index=idx, start=start, end=min(end, total_seconds), text=b))
        cur = end
    # Adjust last end
    if segments:
        segments[-1].end = max(segments[-1].end, min(total_seconds, segments[-1].start + 1.2))
    return segments


def write_srt(segments: List[CaptionSegment], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    for seg in segments:
        lines.append(str(seg.index))
        lines.append(f"{_format_ts(seg.start)} --> {_format_ts(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def generate_captions(script: str, event_id: str, cfg: AudioConfig | None = None) -> Path:
    """Adapter: generate SRT captions for an event using voice duration."""
    cfg = cfg or AudioConfig()
    norm_wav = Path("work") / event_id / "voice_norm.wav"
    duration = _wav_duration_seconds(norm_wav) if norm_wav.exists() else max(6.0, len(script.split()) / 2.5)
    segments = build_captions(script, total_seconds=duration, cfg=cfg)
    srt_path = Path("work") / event_id / "captions.srt"
    write_srt(segments, srt_path)
    return srt_path
