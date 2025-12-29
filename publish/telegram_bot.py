from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def send_preview(final_video: Path, event: dict) -> None:
    """Stub: log a preview sending action.
    Replace with real Telegram Bot API integration.
    """
    logger.info("preview_sent video=%s event_id=%s", final_video, event.get("event_id"))
