"""
Voice script generator for Phase-7.

Generates short, educational narration from event metadata.
Rules:
- Past tense
- Clear and neutral tone
- Avoid hype or advice
- 5–12 seconds target length
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class EventMeta:
    event_id: str
    coin: str
    pattern_name: str
    direction: str  # 'bullish' or 'bearish'
    move_pct: float
    timeframe: str  # e.g., '4 hours'


def generate_voice_script(meta: EventMeta, add_disclaimer: bool = True) -> str:
    """Generate an educational narration script for the event.

    Example output:
        "Bitcoin broke resistance after an EMA crossover.\n"
        "Price moved up by nine percent within four hours.\n"
        "Educational content using historical data."
    """
    coin = meta.coin.strip()
    pattern = meta.pattern_name.strip()
    direction = meta.direction.strip().lower()
    pct = abs(meta.move_pct)
    timeframe = meta.timeframe.strip()

    # Direction phrasing
    if direction == "bullish":
        dir_phrase = "moved up"
    elif direction == "bearish":
        dir_phrase = "moved down"
    else:
        dir_phrase = "changed"

    # Pattern phrasing (past tense, simple)
    pattern_line = f"{coin} showed a {pattern.lower()} pattern."

    # Movement
    move_line = f"Price {dir_phrase} by {pct:.0f} percent within {timeframe}."

    # Optional context (avoid advice, use neutral tone)
    context_line = "This event was identified using historical indicators."

    lines = [pattern_line, move_line, context_line]

    if add_disclaimer:
        lines.append("Educational content using historical data.")

    return "\n".join(lines)


def generate_script(event: dict, add_disclaimer: bool = True) -> str:
    """Adapter: build EventMeta from event dict and generate narration script.

    Expects keys: event_id, pattern, expected_move_pct (optional), direction (optional), timeframe (optional)
    """
    event_id = event.get("event_id", "event")
    coin = event.get("symbol", "BTC").split("/")[0]
    pattern = event.get("pattern", "Pattern")
    move_pct = float(event.get("expected_move_pct", 2.0))
    timeframe = event.get("timeframe", "1h")
    # Simple direction heuristic
    direction = event.get("direction") or ("bullish" if move_pct >= 0 else "bearish")
    meta = EventMeta(event_id=event_id, coin=coin, pattern_name=pattern, direction=direction, move_pct=abs(move_pct), timeframe=timeframe)
    return generate_voice_script(meta, add_disclaimer=add_disclaimer)
