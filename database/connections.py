import sqlite3
from utils.config import SQLITE_DB_PATH
from contextlib import contextmanager

# ─── Connection Pool (Thread-safe) ──────────────────────────────────────────
def get_connection():
    """Get a thread-safe SQLite connection with WAL mode for concurrency."""
    conn = sqlite3.connect(
        SQLITE_DB_PATH,
        check_same_thread=False, # FastAPI multi-thread support
        timeout=10 
    )
    
    conn.row_factory = sqlite3.Row  # Dict-style row access
    conn.execute("PRAGMA journal_mode=WAL")    # Better concurrent reads/writes
    conn.execute("PRAGMA foreign_keys=ON")     # Enforce FK constraints
    conn.execute("PRAGMA synchronous=NORMAL")  # Balance speed vs safety
    return conn


"""What does the Context Manager does It actually opens your db connection 
and close it when work has done"""
@contextmanager
def get_db():
    """Context manager — auto-closes connection, auto-rollback on error."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()