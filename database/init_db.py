from database.connections import get_db
import logging
logger=logging.getLogger(__name__)
import sqlite3

# ─── Init ────────────────────────────────────────────────────────────────────

def init_db():
    """Create tables and indexes if they don't exist."""
    try:
        with get_db() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                session_id TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                email      TEXT UNIQUE NOT NULL,
                is_admin   INTEGER DEFAULT 0,    -- 0 = normal, 1 = admin
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role       TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    message    TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES users(session_id) ON DELETE CASCADE
                );

                -- Performance indexes
                CREATE INDEX IF NOT EXISTS idx_users_email
                    ON users(email);

                CREATE INDEX IF NOT EXISTS idx_conversations_session_created
                    ON conversations(session_id, created_at);
            """)
        logger.info("✅ Database initialized successfully!")
    except sqlite3.Error as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

