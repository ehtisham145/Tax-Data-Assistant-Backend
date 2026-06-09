import sqlite3
from connections import get_db
import logging
logger = logging.getLogger(__name__)


def insert_user(session_id: str, name: str, email: str) -> tuple[bool, str]:
    """
    Insert new user atomically using INSERT OR IGNORE.
    Returns (True, name) if inserted, (False, existing_name) if duplicate.
    Race condition safe — no separate SELECT needed.
    """
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (session_id, name, email) VALUES (?, ?, ?)",
                (session_id, name, email),
            )
            # Check if row was actually inserted
            row = conn.execute(
                "SELECT name FROM users WHERE email = ?", (email,)
            ).fetchone()

            inserted = (row["name"] == name)
            return inserted, row["name"]

    except sqlite3.Error as e:
        logger.error(f"❌ Error inserting user [{email}]: {e}")
        raise

def get_user_by_session(session_id: str) -> Optional[tuple]:
    """Fetch user by session_id. Returns (name, email) or None."""
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT name, email FROM users WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            return tuple(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching user by session [{session_id}]: {e}")
        raise

def get_user_by_email(email: str) -> Optional[tuple]:
    """Fetch user by email. Returns (name, email) or None."""
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT name, email FROM users WHERE email = ?", (email,)
            ).fetchone()
            return tuple(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching user by email [{email}]: {e}")
        return None


def get_all_users() -> list:
    """Fetch all registered users ordered by creation date."""
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT session_id, name, email, created_at FROM users ORDER BY created_at DESC"
            ).fetchall()
            return [tuple(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching all users: {e}")
        raise