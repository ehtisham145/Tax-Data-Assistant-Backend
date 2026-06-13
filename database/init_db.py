import logging
from database.connections import engine,Base

logger = logging.getLogger(__name__)

def init_db() -> None:
    """Create all tables if they don't exist in a production-safe manner."""
    try:
        logger.info("Starting database initialization...")
        
        # Tables create karna
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Database initialized successfully!")
    except Exception as e:
        logger.critical(f"❌ Database initialization failed: {str(e)}", exc_info=True)
        raise RuntimeError("Database initialization failed. Application cannot start.") from e