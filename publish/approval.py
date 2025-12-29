from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def wait_for_approval(event_id: str) -> bool:
    """Stub: immediately approve.
    Replace with real approval workflow or UI.
    """
    logger.info("approval_granted event_id=%s", event_id)
    return True
