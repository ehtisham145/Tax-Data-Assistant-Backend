import logging
from sqlalchemy.exc import SQLAlchemyError
from database_setup.connections import engine, Base, check_db_connection
from database_setup.models import User, Conversation, Feedback  # noqa: F401 - ensures models are registered on Base

logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Create all tables defined on Base if they don't already exist.
    Safe to call multiple times - does not drop or alter existing tables.
    """
    if not check_db_connection():
        raise RuntimeError("Cannot initialize database - connection check failed")

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


