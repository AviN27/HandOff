"""Firestore integration for session and task state."""

import logging
from datetime import datetime
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_firestore_client = None


def _get_client():
    global _firestore_client
    if not settings.USE_FIRESTORE:
        return None
    if _firestore_client is None:
        try:
            from google.cloud import firestore
            _firestore_client = firestore.AsyncClient(
                project=settings.GOOGLE_CLOUD_PROJECT
            )
        except Exception as e:
            logger.warning(f"Firestore unavailable: {e}")
    return _firestore_client


async def create_session(session_id: str, task: str, start_url: str) -> dict | None:
    """Create a new session document in Firestore."""
    client = _get_client()
    if not client:
        logger.debug("Skipping session creation — no Firestore client")
        return None

    try:
        doc_ref = client.collection(settings.FIRESTORE_COLLECTION).document(session_id)
        session_data = {
            "session_id": session_id,
            "task": task,
            "start_url": start_url,
            "status": "created",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "steps": [],
            "summary": "",
        }
        await doc_ref.set(session_data)
        logger.info(f"Session created in Firestore: {session_id}")
        return session_data
    except Exception as e:
        logger.error(f"Firestore create session error: {e}")
        return None


async def update_session_state(
    session_id: str, status: str, detail: str = ""
) -> None:
    """Update session status in Firestore."""
    client = _get_client()
    if not client:
        return

    try:
        doc_ref = client.collection(settings.FIRESTORE_COLLECTION).document(session_id)
        await doc_ref.update({
            "status": status,
            "summary": detail,
            "updated_at": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.error(f"Firestore update error: {e}")


async def get_session(session_id: str) -> dict | None:
    """Retrieve a session from Firestore."""
    client = _get_client()
    if not client:
        return None

    try:
        doc_ref = client.collection(settings.FIRESTORE_COLLECTION).document(session_id)
        doc = await doc_ref.get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"Firestore get session error: {e}")
        return None


async def list_sessions(limit: int = 20) -> list[dict]:
    """List recent sessions from Firestore."""
    client = _get_client()
    if not client:
        return []

    try:
        query = (
            client.collection(settings.FIRESTORE_COLLECTION)
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
        )
        docs = query.stream()
        sessions = []
        async for doc in docs:
            sessions.append(doc.to_dict())
        return sessions
    except Exception as e:
        logger.error(f"Firestore list sessions error: {e}")
        return []
