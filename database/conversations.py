import sqlite3
from database.connections import get_db
import logging

logger = logging.getLogger(__name__)



def save_message(session_id: str, role: str, message: str) -> None:
    """Save a single message to conversations table."""
    try:
        with get_db() as conn:
            # User ensure karo pehle - warna foreign key fail hoga
            conn.execute(
                """
                INSERT OR IGNORE INTO users (session_id, created_at)
                VALUES (?, CURRENT_TIMESTAMP)
                """,
                (session_id,),
            )
            conn.execute(
                """
                INSERT INTO conversations (session_id, role, message)
                VALUES (?, ?, ?)
                """,
                (session_id, role, message),
            )
        logger.info(f"✅ Message saved for session: {session_id} | role: {role}")
    except sqlite3.Error as e:
        logger.error(f"❌ Error saving message [{session_id}]: {e}")
        raise e 


def get_conversation_history(session_id: str) -> list:
    """Get full conversation history for a session ordered by time."""
    try:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT role, message, created_at
                FROM conversations
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (session_id,),
            ).fetchall()
            return [tuple(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching history [{session_id}]: {e}")
        raise


def delete_conversation(session_id: str) -> None:
    """Delete all messages for a session."""
    try:
        with get_db() as conn:
            conn.execute(
                "DELETE FROM conversations WHERE session_id = ?",
                (session_id,),
            )
        logger.info(f"✅ Conversation deleted for session: {session_id}")
    except sqlite3.Error as e:
        logger.error(f"❌ Error deleting conversation [{session_id}]: {e}")
        raise