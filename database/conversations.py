import sqlite3
from database.connections import get_db
import logging
logger = logging.getLogger(__name__)

def save_message(session_id: str, role: str, message: str):
    with get_db() as conn:
        # Pehle check karo session exist karta hai ya nahi
        user = conn.execute(
            "SELECT 1 FROM users WHERE session_id = ?", (session_id,)
        ).fetchone()

        if not user:
            logger.warning(f"⚠️ Session {session_id} not in DB yet — skipping save")
            return  # silently skip, crash mat karo

        conn.execute(
            "INSERT INTO conversations (session_id, role, message) VALUES (?, ?, ?)",
            (session_id, role, message),
        )
        conn.commit()

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

