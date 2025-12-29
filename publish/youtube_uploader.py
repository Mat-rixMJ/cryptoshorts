from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def upload_video(final_video: Path, event: dict) -> None:
    """Stub: log upload action.
    Replace with YouTube Data API integration.
    """
    logger.info("upload_stub video=%s event_id=%s", final_video, event.get("event_id"))
