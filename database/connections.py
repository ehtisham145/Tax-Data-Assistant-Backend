from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from contextlib import contextmanager
from pathlib import Path

# ─── DB Path ─────────────────────────────────────────────────────────────────
DB_FILE_PATH = "./data/bot.db"
Path(DB_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)

# ─── Engine ──────────────────────────────────────────────────────────────────
engine = create_engine(
    f"sqlite:///{DB_FILE_PATH}",
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

# ─── Context Manager ─────────────────────────────────────────────────────────
@contextmanager          # ← Yahi missing tha
def get_db():
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()