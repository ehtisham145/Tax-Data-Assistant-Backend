import sqlite3
import logging
from config import SQLITE_DB_PATH

logger = logging.getLogger(__name__)

def get_connection():
    """Get SQLite database connection."""
    return sqlite3.connect(SQLITE_DB_PATH)
def init_db():
    """Create users and conversations tables if they don't exist."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                session_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES users(session_id)
            )
        """)
        
        conn.commit()
        logger.info("✅ Database initialized successfully!")
    except sqlite3.Error as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    finally:
        conn.close()

def save_message(session_id: str, role: str, message: str):
    """Save a single chat message to DB."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (session_id, role, message) VALUES (?, ?, ?)",
            (session_id, role, message)
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"❌ Error saving message: {e}")
    finally:
        conn.close()

def get_conversation_history(session_id: str):
    """Fetch full chat history for a session from DB."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, message, created_at FROM conversations WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        )
        return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching history: {e}")
        return []
    finally:
        conn.close()

def insert_user(session_id: str, name: str, email: str) -> bool:
    """Insert new user. Returns True if inserted, False if email exists."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute("SELECT name FROM users WHERE email = ?", (email,))
        existing = cursor.fetchone()

        if existing:
            return False, existing[0]  # Already registered

        cursor.execute(
            "INSERT INTO users (session_id, name, email) VALUES (?, ?, ?)",
            (session_id, name, email)
        )
        conn.commit()
        return True, name

    except sqlite3.Error as e:
        logger.error(f"❌ Error inserting user: {e}")
        raise
    finally:
        conn.close()

def get_user_by_session(session_id: str):
    """Fetch user by session_id. Returns (name, email) or None."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, email FROM users WHERE session_id = ?", (session_id,)
        )
        return cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching user: {e}")
        raise
    finally:
        conn.close()

def get_all_users():
    """Fetch all registered users."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, name, email, created_at FROM users")
        return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"❌ Error fetching all users: {e}")
        raise
    finally:
        conn.close()