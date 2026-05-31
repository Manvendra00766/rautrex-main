from database.connection import engine
from core.logger import logger
from sqlalchemy import text

async def run_db_vacuum():
    """
    Runs SQLite database checkpointing and vacuuming to optimize disk usage and indexing trees.
    For SQLite: checkpoints WAL journal files and performs a full VACUUM.
    For PostgreSQL: runs standard VACUUM.
    """
    dialect = engine.dialect.name
    logger.info(f"[DBMaintenance] Starting database optimization. Dialect: {dialect}")
    
    try:
        # SQLite's VACUUM or PRAGMA statements cannot run inside a multi-statement transaction,
        # but SQLAlchemy's engine.connect() allows us to run them. We use conn.execution_options(isolation_level="AUTOCOMMIT")
        # to ensure they execute outside of a transaction context.
        async with engine.connect() as conn:
            # Set autocommit to run statements like VACUUM that cannot run in transactions
            conn = conn.execution_options(isolation_level="AUTOCOMMIT")
            
            if dialect == "sqlite":
                logger.info("[DBMaintenance] Checkpointing WAL journal and truncating...")
                await conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
                logger.info("[DBMaintenance] Running SQLite VACUUM to shrink .db size...")
                await conn.execute(text("VACUUM;"))
                logger.info("[DBMaintenance] SQLite database optimized and defragmented.")
            elif dialect == "postgresql":
                logger.info("[DBMaintenance] Running PostgreSQL VACUUM...")
                await conn.execute(text("VACUUM;"))
                logger.info("[DBMaintenance] PostgreSQL database vacuum completed.")
            else:
                logger.info(f"[DBMaintenance] No specific maintenance tasks defined for dialect: {dialect}")
                
        logger.info("[DBMaintenance] Database maintenance task completed successfully.")
        return True
    except Exception as e:
        logger.error(f"[DBMaintenance] Error executing database maintenance: {e}")
        return False
