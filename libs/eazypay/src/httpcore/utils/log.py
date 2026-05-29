import logging
import os
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
from httpcore.AppConstants import AppConstants

def setup_logging(log_level_str):
    """Sets up logging with rotation.
       If log_level_str == 'FILE', logs will also be written to a file (kept for 7 days).
    """

    # Default level
    log_level = logging.INFO  

    if log_level_str is None:
        print("LOG_LEVEL not found. Using default INFO.")
    else:
        try:
            if log_level_str.upper() == "FILE":  
                log_level = logging.DEBUG   # default file logging level
            else:
                log_level = getattr(logging, log_level_str.upper())
                if not isinstance(log_level, int):
                    raise AttributeError
        except AttributeError:
            print(f"Invalid log level '{log_level_str}'. Using default logging level INFO.")
            log_level = logging.INFO

    # Configure logger
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    # Remove existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # # Console Handler (always on)
    # console_handler = logging.StreamHandler()
    # console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    # logger.addHandler(console_handler)

    # File Handler (only if FILE level is set)
    if log_level_str and log_level_str.upper() == "FILE":
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)  # ensure logs folder exists
        file_handler = TimedRotatingFileHandler(
            filename=os.path.join(log_dir, "sdklogs.log"),
            when="midnight",      # rotate at midnight
            interval=1,           # every 1 day
            backupCount=7,        # keep last 7 days
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)

    return logger


# Example usage:
level = AppConstants.LOG_LEVEL if AppConstants else "INFO"
logger = setup_logging(level)

# logger.info("This is an INFO log")
# logger.error("This is an ERROR log")
# logger.debug("This is a DEBUG log")
