from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from contextlib import contextmanager
from utils.config import SQLITE_DB_PATH
import logging

logger = logging.getLogger(__name__)

# ─── Engine ──────────────────────────────────────────────────────────────────
engine = create_engine(
    f"sqlite:///{SQLITE_DB_PATH}",
    connect_args={
        "check_same_thread": False,
        "timeout": 30
    },
    pool_pre_ping=True,
    echo=False
)

# ─── Pragmas ─────────────────────────────────────────────────────────────────
@event.listens_for(engine, "connect")
def set_pragmas(dbapi_conn, connection_record):
    """
    Here's a quick summary in English:
    This code runs automatically every time a new SQLite connection is opened, applying three settings:
    PRAGMA journal_mode=WAL — Switches SQLite to Write-Ahead Logging mode, which allows reads and writes
    to happen concurrently instead of locking the whole database. This drastically reduces "database is locked"
    errors, which is important for a multi-request FastAPI app.PRAGMA foreign_keys=ON — SQLite doesn't enforce
    foreign key constraints by default, even if they're defined in your models. This turns enforcement on, so
    invalid foreign key references will actually raise errors.PRAGMA synchronous=NORMAL — Controls how often SQLite 
    flushes data to disk. NORMAL (combined with WAL mode) gives a good balance between performance and safety — protected
    against app crashes, with only minimal risk in the rare case of a power loss/OS crash.
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

# ─── Base ────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

# ─── Session Factory ─────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

# ─── Dependency for FastAPI routes ────────────────────────────────────────────
def get_db():
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# ─── Context manager for manual/non-FastAPI usage ─────────────────────────────
get_db_ctx = contextmanager(get_db)
"""
Use for scripts, background tasks, or admin routes not using Depends():

    with get_db_ctx() as db:
        ...
"""

# ─── Startup check ────────────────────────────────────────────────────────────
def check_db_connection() -> bool:
    """
    Verifies the database file is reachable and pragmas applied correctly.
    Call this on app startup to fail fast if the DB path is misconfigured.
    """
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        logger.info(f"Database connection verified: {SQLITE_DB_PATH}")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        return False