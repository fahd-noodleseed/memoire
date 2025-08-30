"""
Logging configuration for Memoire.

This module provides a centralized, robust logging setup.
Key principles:
1.  **Simplicity**: No queues or listeners. Handlers are attached directly
    to the root logger. This avoids race conditions during initialization.
2.  **Centralized Config**: `setup_logging` is the single source of truth.
    It configures the root logger.
3.  **Safe `get_logger`**: `get_logger(name)` simply returns a logger instance.
    It does no configuration itself. All loggers inherit configuration from
    the root logger, so it's safe to call at any point in the code, even
    at the module level.
"""
import logging
import logging.handlers
import os
import sys
import atexit
from pathlib import Path
from datetime import datetime

# --- Globals ---
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# --- Filters ---
class LoggerNameFilter(logging.Filter):
    """Passes records whose names start with a specified prefix."""
    def __init__(self, name_prefix):
        super().__init__()
        self.name_prefix = name_prefix

    def filter(self, record):
        return record.name.startswith(self.name_prefix)

class ExcludeNameFilter(logging.Filter):
    """Passes records whose names DO NOT start with specified prefixes."""
    def __init__(self, prefixes_to_exclude):
        super().__init__()
        self.prefixes_to_exclude = tuple(prefixes_to_exclude)

    def filter(self, record):
        return not record.name.startswith(self.prefixes_to_exclude)

# --- Setup ---
def setup_logging():
    """
    Set up logging configuration. This is the single source of truth for logging.
    It should be called only once at application startup.
    """
    # Set log level to DEBUG
    log_level = logging.DEBUG
    log_level_str = 'DEBUG'

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers to prevent duplication
    root_logger.handlers = []

    # Base formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- Define Handlers ---

    # 1. App File Handler (for memoire.app.*)
    app_file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log",
        maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    app_file_handler.setFormatter(formatter)
    app_file_handler.addFilter(LoggerNameFilter('memoire.app'))

    # 2. MCP File Handler (for memoire.mcp.*)
    mcp_file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / f"mcp_{datetime.now().strftime('%Y%m%d')}.log",
        maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    mcp_file_handler.setFormatter(formatter)
    mcp_file_handler.addFilter(LoggerNameFilter('memoire.mcp'))

    # 3. System File Handler (for everything else)
    system_file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / f"system_{datetime.now().strftime('%Y%m%d')}.log",
        maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    system_file_handler.setFormatter(formatter)
    # Exclude logs that are already being captured by app and mcp handlers
    system_file_handler.addFilter(ExcludeNameFilter(['memoire.app', 'memoire.mcp']))

    # 4. Console Handler (for critical errors)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)

    # --- Add Handlers to Root Logger ---
    root_logger.addHandler(app_file_handler)
    root_logger.addHandler(mcp_file_handler)
    root_logger.addHandler(system_file_handler)
    root_logger.addHandler(console_handler)

    # --- Log Startup ---
    startup_logger = get_logger('memoire.app')
    startup_logger.info("=" * 80)
    startup_logger.info(f"Logging initialized. Level: {log_level_str}. Root level: {logging.getLevelName(root_logger.level)}")
    startup_logger.info(f"App logs:    {app_file_handler.baseFilename}")
    startup_logger.info(f"MCP logs:    {mcp_file_handler.baseFilename}")
    startup_logger.info(f"System logs: {system_file_handler.baseFilename}")
    startup_logger.info("=" * 80)

    # Register shutdown hook for a clean exit
    atexit.register(logging.shutdown)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    This is a simple pass-through to logging.getLogger(). It does no
    configuration. The returned logger will inherit its settings from the
    root logger configured in `setup_logging`. It is safe to be called
    at the module level.
    """
    return logging.getLogger(name)

# --- Example Usage ---
if __name__ == '__main__':
    # Example of how to use the new logging setup
    setup_logging()

    # Get loggers
    main_logger = get_logger('memoire.app.main')
    mcp_logger = get_logger('memoire.mcp.server')
    other_logger = get_logger('some_other_library')
    main_debug_logger = get_logger('memoire.app.debug')

    # Log messages
    main_logger.info("This is an info message for the main app.")
    main_logger.warning("This is a warning message for the main app.")
    mcp_logger.info("This is an info message for MCP.")
    mcp_logger.debug("This should NOT appear unless log level is DEBUG.")
    other_logger.info("This is from another library and will go to system.log.")
    main_debug_logger.debug("This is a debug message for the app.")

    # Test error logging to console
    mcp_logger.error("This is a critical error and should appear on stderr.")

    print("Example finished. Check the log files in the 'logs' directory.")
    # atexit will call logging.shutdown() automatically
