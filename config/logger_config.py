import os
import sys

from loguru import logger

from config.constants import LOG_DIR
from src.telegram.telegram_error_handler import AsyncTelegramSink

logger.remove()

minimum_log_level = "DEBUG"

# Terminal output without tracebacks
logger.add(sys.stdout, level=minimum_log_level, backtrace=False, diagnose=False)

logger.add(
    AsyncTelegramSink(
        max_retries=6,
        cooldown=600,  # in case of the same error, we wait 10 minutes
    ),
    level="ERROR",
    format="{message}",
    backtrace=True,
    diagnose=True,
)

# Configuration of logging to a file
logger.add(
    os.path.join(LOG_DIR, "app.log"),
    rotation="500 MB",  # Rotate when file reaches 500 MB
    retention="10 days",  # Keep logs for 10 days
    compression="zip",  # Compress rotated logs
    level=minimum_log_level,
    backtrace=True,
    diagnose=True,
)

# Configuration of logging errors to a file
logger.add(
    os.path.join(LOG_DIR, "error.log"),
    rotation="100 MB",  # Rotate when file reaches 100 MB
    retention="30 days",  # Keep error logs longer
    compression="zip",
    level="ERROR",
    backtrace=True,
    diagnose=True,
)
