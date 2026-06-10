import sqlite3
from database.connections import get_db
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def insert_user(session_id: str, name: str, email: str) -> tuple[bool, str]:
    try:
        with get_db() as conn:
            # Pehle check karo email exist karta hai ya nahi
            existing = conn.execute(
                "SELECT session_id, name FROM users WHERE email = ?", (email,)
            ).fetchone()

            if existing:
                old_session_id = existing["session_id"]

                if old_session_id != session_id:
                    # ✅ Pehle purani conversations delete karo (FK issue fix)
                    conn.execute(
                        "DELETE FROM conversations WHERE session_id = ?",
                        (old_session_id,),
                    )
                    # Phir naya session_id update karo
                    conn.execute(
                        "UPDATE users SET session_id = ? WHERE email = ?",
                        (session_id, email),
                    )
                    logger.info(f"🔄 Session updated for: {email}")

                return False, existing["name"]

            # Naya user — insert karo
            conn.execute(
                "INSERT INTO users (session_id, name, email) VALUES (?, ?, ?)",
                (session_id, name, email),
            )
            return True, name

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