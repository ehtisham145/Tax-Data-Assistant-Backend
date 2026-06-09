import sqlite3
from database.connections import get_db
import logging
logger = logging.getLogger(__name__)

def save_message(session_id: str, role: str, message: str) -> bool:
    """
    Save a chat message. Returns True on success, raises on failure.
    Caller must handle errors — silent failure removed intentionally.
    """
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO conversations (session_id, role, message) VALUES (?, ?, ?)",
                (session_id, role, message),
            )
        return True
    except sqlite3.Error as e:
        logger.error(f"❌ Error saving message for session [{session_id}]: {e}")
        raise

def get_conversation_history(session_id: str, limit: int = 50) -> list:
    """
    Fetch recent chat history for a session.
    `limit` prevents memory overload on long conversations.
    """
    try:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT role, message, created_at
                FROM conversations
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
            return [tuple(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching history for session [{session_id}]: {e}")
        return []

