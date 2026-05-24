import sys
from loguru import logger
from .config import settings

def setup_logging():
    logger.remove()
    
    # Standard format with trace IDs for observability
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    # Console handler
    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if settings.ENVIRONMENT == "development" else "INFO",
        colorize=True,
    )
    
    # File handler for error monitoring
    logger.add(
        "logs/error.log",
        format=log_format,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )

    logger.info("Structured logging initialized.")

setup_logging()
