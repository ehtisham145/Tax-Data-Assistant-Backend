import sqlite3
from utils.config import SQLITE_DB_PATH

def migrate():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("DROP TABLE IF EXISTS feedback")
    conn.execute("""
        CREATE TABLE feedback (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   TEXT,
            user_message TEXT NOT NULL,
            bot_response TEXT NOT NULL,
            rating       TEXT NOT NULL CHECK(rating IN ('thumbs_up', 'thumbs_down')),
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.commit()
    conn.close()
    print("Migration done!")