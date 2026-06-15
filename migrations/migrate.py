import logging
from sqlalchemy import text
from database_setup.connections import engine
from sqlalchemy.exc import SQLAlchemyError

#----------------Setting your Logs----------------
logger=logging.getLogger(__name__)

"""We will use text feature of sql alchemy for wiriting sql queries"""

#-------------Tracking Table Function------------
def _ensure_migrations_table(conn):
    """The underscore (_) prefix in _ensure_migrations_table marks it as an internal helper function 
    meant for "Staff Only" use within the file.This function acts as an "attendance register"
    by creating the schema_migrations table if it does not already exist.
    The table tracks which database updates (migrations) have already been applied so they don't 
    run twice and break the system.It records essential details for every update, 
    including a unique version number, a description, and the exact timestamp it was applied Using
    the underscore convention keeps the code clean and prevents internal functions from
    being accidentally imported into other files."""

    conn.execute(text(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ))


#-------Function for Checking Applied Migrations----------------------------
def _get_applied_versions(conn)->set[int]:
    """This function fetch all the migrations from the schema table which has been alredy applied this 
    function is private we can just use this function inside this file"""
    result = conn.execute((text("""SELECT version FROM schema_migrations""")))
    return {row[0] for row in result}    



#----------Define your Migrations List---------------------------------------

MIGRATIONS = [
   (1, "add phone_number column to users table", """
        ALTER TABLE users ADD COLUMN phone TEXT NOT NULL DEFAULT '';
    """),
]

#------Final Migration Function-----------------------------------------------
#------Final Migration Function-----------------------------------------------
def migrate() -> None:
    try:
        logger.info("Starting database migrations...")

        with engine.connect() as conn:
            with conn.begin():
                _ensure_migrations_table(conn)
                applied = _get_applied_versions(conn)
                pending = [m for m in MIGRATIONS if m[0] not in applied]

                if not pending:
                    logger.info("No pending migrations - database is up to date")
                    return

                # SMART CHECK: Fresh install tabhi maana jayega jab applied khali ho 
                # AUR database mein users table bhi na bana ho.
                is_fresh_install = len(applied) == 0 and not _tables_exist(conn)

                for version, description, sql in pending:
                    if not is_fresh_install:
                        logger.info(f"Applying migration {version}: {description}")
                        conn.execute(text(sql))
                    else:
                        logger.info(f"Skipping migration {version} (fresh install, structure will be handled by init_db)")
                    
                    # Record the migration as tracked/applied
                    conn.execute(
                        text("INSERT INTO schema_migrations (version, description) VALUES (:v, :d)"),
                        {"v": version, "d": description},
                    )
                    logger.info(f"Migration {version} marked as applied")

        logger.info("Database migration completed successfully")

    except SQLAlchemyError as e:
        logger.critical(f"Database migration failed (DB error): {e}", exc_info=True)
        raise RuntimeError("Database migration failed. Application cannot start.") from e
    except Exception as e:
        logger.critical(f"Unexpected error during migration: {e}", exc_info=True)
        raise RuntimeError("Database migration failed. Application cannot start.") from e


def _tables_exist(conn) -> bool:
    """Check if any application tables already exist (i.e. init_db already ran)."""
    result = conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    ))
    return result.first() is not None