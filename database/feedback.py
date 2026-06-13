import sqlite3
import logging
from database.connections import get_db

logger = logging.getLogger(__name__)

import sqlite3
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

def get_all_feedback(limit: int = 50, offset: int = 0) -> tuple:
    """Get feedback items with pagination and the total global count."""
    try:
        with get_db() as conn:
            # 1. Get total count of all feedback in the table
            total_count = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]

            # 2. Get the paginated rows
            rows = conn.execute(
                """
                SELECT session_id, user_message, bot_response, rating, created_at
                FROM feedback
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
            
            feedback_records = [tuple(r) for r in rows]
            
            # Return both as a tuple
            return feedback_records, total_count
            
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching feedback: {e}")
        raise

def get_feedback_stats() -> dict:
    """Get total thumbs up and thumbs down counts."""
    try:
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN rating = 'thumbs_up' THEN 1 ELSE 0 END) as thumbs_up,
                    SUM(CASE WHEN rating = 'thumbs_down' THEN 1 ELSE 0 END) as thumbs_down
                FROM feedback
                """,
            ).fetchone()
            return {
                "total": row[0],
                "thumbs_up": row[1],
                "thumbs_down": row[2],
            }
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching feedback stats: {e}")
        raise