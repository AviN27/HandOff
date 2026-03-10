"""Local file storage for screenshots (replaces Cloud Storage)."""

import logging
import os
from pathlib import Path
from datetime import datetime

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _ensure_dir(path: Path) -> None:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


async def upload_screenshot(
    session_id: str, step: int, image_bytes: bytes
) -> str | None:
    """Save a screenshot to the local filesystem.

    Returns the local file path or None on failure.
    """
    try:
        base_dir = Path(settings.LOCAL_SCREENSHOT_DIR) / session_id
        _ensure_dir(base_dir)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"step_{step:03d}_{timestamp}.png"
        filepath = base_dir / filename

        filepath.write_bytes(image_bytes)
        logger.info(f"Screenshot saved locally: {filepath}")
        return str(filepath)
    except Exception as e:
        logger.error(f"Screenshot save failed: {e}")
        return None
