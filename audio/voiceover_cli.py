from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .config import AudioConfig, load_config
from .scripts import EventMeta
from .pipeline import assemble_voiceover_video

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("Voiceover + Captions engine")
    p.add_argument("--silent", required=True, help="Path to silent MP4 from Phase 6")
    p.add_argument("--out", required=True, help="Output final MP4 path")
    p.add_argument("--work", required=True, help="Work dir for audio + captions")
    p.add_argument("--config", help="Optional audio config JSON override")

    # Event metadata
    p.add_argument("--coin", required=True)
    p.add_argument("--pattern", required=True)
    p.add_argument("--direction", required=True, choices=["up", "down"])
    p.add_argument("--move_pct", required=True, type=float)
    p.add_argument("--timeframe", required=True)
    return p.parse_args()


def main():
    args = parse_args()

    cfg = AudioConfig()
    if args.config:
        cfg = load_config(args.config)

    event = EventMeta(
        coin=args.coin,
        pattern_name=args.pattern,
        direction=args.direction,
        move_pct=args.move_pct,
        timeframe=args.timeframe,
    )

    results = assemble_voiceover_video(
        event=event,
        silent_mp4=Path(args.silent),
        out_mp4=Path(args.out),
        work_dir=Path(args.work),
        cfg=cfg,
    )

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
