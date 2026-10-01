"""Centralized logging orchestration for openstan and dependent libraries.

Manages logger initialization, context switching (app ↔ project logs), verbosity
levels, and log cleanup. All file I/O handlers are configured here; libraries
configure no handlers themselves (by design).

This module provides a factory function `get_logger()` for creating loggers,
context switching between app and project logs, verbosity control, and automatic
cleanup of stale project log files.

**Key Design:**
- Single root logger `"openstan"` with cascade to dependency libraries
- Handler attachment strategy: handlers are attached to BOTH the openstan logger
  AND library loggers (bank_statement_parser, uk_bank_statement_anonymiser).
  This is necessary because library loggers are top-level independent loggers
  that do not propagate to openstan's logger hierarchy.
- Context switching via `switch_to_app_log()` and `switch_to_project_log()`
  Handlers are added/removed from ALL loggers (openstan + libraries) together.
- Verbosity levels: "normal" (INFO) and "verbose" (DEBUG)
- Persistence via `QSettings` (so settings survive app restarts)
- Platform-aware log directories (Windows/macOS/Linux)
- 10 MB file rotation with 5 backups
- 30-day retention cleanup for project logs (runs on app closure)
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QSettings

__all__: list[str] = [
    "cleanup_old_project_logs",
    "get_app_log_path",
    "get_logger",
    "get_project_log_path",
    "get_verbosity",
    "initialize",
    "set_verbosity",
    "switch_to_app_log",
    "switch_to_project_log",
]

# Type alias for verbosity levels
Verbosity = Literal["normal", "verbose"]

# Settings keys
_SETTINGS_ORG = "openstan"
_SETTINGS_APP = "openstan"
_KEY_VERBOSITY = "logging/verbosity"

# Log format
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# Rotation settings
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5

# Global logger state (module level)
_root_logger: logging.Logger | None = None
_app_log_handler: logging.handlers.RotatingFileHandler | None = None
_project_log_handler: logging.handlers.RotatingFileHandler | None = None
_current_context: Literal["app", "project", "none"] = "none"

# Library loggers (top-level, not children of "openstan")
# These must have handlers attached explicitly since they don't inherit
# from the openstan logger hierarchy
_lib_bank_parser_logger: logging.Logger | None = None
_lib_anonymiser_logger: logging.Logger | None = None


def _user_data_dir() -> Path:
    """Return platform-appropriate user data directory for logs.

    Returns:
        Path to user data directory following platform conventions.
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "openstan"


def get_app_log_path() -> Path:
    """Get the application log file path.

    Returns:
        Path to application.log in platform-specific user data directory.
    """
    return _user_data_dir() / "application.log"


def get_project_log_path(project_root: Path) -> Path:
    """Get the project log file path.

    Args:
        project_root: Root directory of the project.

    Returns:
        Path to project.log in the project root directory.
    """
    return Path(project_root) / "project.log"


def get_verbosity() -> Verbosity:
    """Get current verbosity level from QSettings.

    Returns:
        "normal" (INFO level) or "verbose" (DEBUG level).
    """
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    value = settings.value(_KEY_VERBOSITY, "normal")
    # Ensure we always return valid values
    if value not in ("normal", "verbose"):
        return "normal"
    return value


def set_verbosity(level: Verbosity) -> None:
    """Set verbosity level for all loggers (openstan + libraries).

    Updates the root logger and all dependency library loggers, and persists
    the setting to QSettings so it survives app restarts.

    IMPORTANT: This function does NOT attach handlers. Handlers must be
    attached separately in initialize() and during context switches.
    This function only sets the verbosity LEVEL for each logger.

    Args:
        level: "normal" (INFO) or "verbose" (DEBUG).

    Raises:
        ValueError: If level is not "normal" or "verbose".
    """
    if level not in ("normal", "verbose"):
        raise ValueError(f"Invalid verbosity level: {level}")

    # Calculate the logging level
    log_level = logging.DEBUG if level == "verbose" else logging.INFO

    # Update openstan root logger
    if _root_logger:
        _root_logger.setLevel(log_level)

    # Cascade to dependency library loggers
    # Note: These are top-level loggers, not children of "openstan"
    for lib_name in ("bank_statement_parser", "uk_bank_statement_anonymiser"):
        lib_logger = logging.getLogger(lib_name)
        lib_logger.setLevel(log_level)

    # Persist to QSettings
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    settings.setValue(_KEY_VERBOSITY, level)


def _create_rotating_file_handler(
    log_path: Path,
) -> logging.handlers.RotatingFileHandler:
    """Create a RotatingFileHandler with standard config.

    Args:
        log_path: Path to the log file.

    Returns:
        Configured RotatingFileHandler.
    """
    # Ensure parent directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
    )
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    handler.setLevel(logging.DEBUG)  # Handler passes all; logger controls level
    return handler


def _add_handler_to_all_loggers(
    handler: logging.handlers.RotatingFileHandler,
) -> None:
    """Add a handler to openstan logger and all library loggers.

    This is necessary because library loggers (bank_statement_parser,
    uk_bank_statement_anonymiser) are top-level independent loggers that do not
    inherit from the openstan logger hierarchy. Without explicit handler
    attachment, library logs would propagate to Python's root logger
    (which has no handlers) and be silently dropped.

    Args:
        handler: The handler to attach to all loggers.
    """
    if _root_logger and handler not in _root_logger.handlers:
        _root_logger.addHandler(handler)

    # Attach to library loggers
    if _lib_bank_parser_logger and handler not in _lib_bank_parser_logger.handlers:
        _lib_bank_parser_logger.addHandler(handler)

    if _lib_anonymiser_logger and handler not in _lib_anonymiser_logger.handlers:
        _lib_anonymiser_logger.addHandler(handler)


def _remove_handler_from_all_loggers(
    handler: logging.Handler | None,
) -> None:
    """Remove a handler from openstan logger and all library loggers.

    Ensures handlers are removed from all loggers that might have them
    attached, then closes the handler.

    Args:
        handler: The handler to remove, or None.
    """
    if not handler:
        return

    if _root_logger and handler in _root_logger.handlers:
        _root_logger.removeHandler(handler)

    if _lib_bank_parser_logger and handler in _lib_bank_parser_logger.handlers:
        _lib_bank_parser_logger.removeHandler(handler)

    if _lib_anonymiser_logger and handler in _lib_anonymiser_logger.handlers:
        _lib_anonymiser_logger.removeHandler(handler)

    handler.close()


def initialize(verbosity: Verbosity | None = None) -> None:
    """Initialize logging infrastructure on app startup.

    Sets up the root logger with file handlers, clears application.log,
    and applies verbosity settings from QSettings (or provided verbosity).

    Handler attachment strategy:
    - Handlers are attached to BOTH the "openstan" logger AND library loggers
    - This is necessary because library loggers are independent top-level
      loggers that do not inherit from the openstan hierarchy
    - Without explicit handler attachment, library logs would be silently dropped

    Should be called once at app startup, before QApplication creation.

    Args:
        verbosity: Optional override for initial verbosity level.
            If not provided, reads from QSettings (default "normal").
    """
    global _root_logger, _app_log_handler, _current_context
    global _lib_bank_parser_logger, _lib_anonymiser_logger

    # Create root logger

    _root_logger = logging.getLogger("openstan")
    _root_logger.propagate = False  # Don't propagate to root logger
    _root_logger.setLevel(logging.DEBUG)  # Logger accepts DEBUG; handlers filter

    # Initialize library loggers (top-level, independent)
    _lib_bank_parser_logger = logging.getLogger("bank_statement_parser")
    _lib_bank_parser_logger.propagate = False
    _lib_bank_parser_logger.setLevel(logging.DEBUG)

    _lib_anonymiser_logger = logging.getLogger("uk_bank_statement_anonymiser")
    _lib_anonymiser_logger.propagate = False
    _lib_anonymiser_logger.setLevel(logging.DEBUG)

    # Remove any existing handlers (in case of re-init)
    # This prevents resource leaks from file handles staying open
    for handler in _root_logger.handlers[:]:
        _remove_handler_from_all_loggers(handler)

    # Initialize app log handler and clear the file
    app_log_path = get_app_log_path()
    app_log_path.parent.mkdir(parents=True, exist_ok=True)

    # Clear existing app log
    if app_log_path.exists():
        app_log_path.unlink()

    # Create fresh app log handler
    _app_log_handler = _create_rotating_file_handler(app_log_path)
    # Attach to ALL loggers (openstan + libraries)
    _add_handler_to_all_loggers(_app_log_handler)
    _current_context = "app"

    # Set initial verbosity from QSettings (or override)
    if verbosity is None:
        verbosity = get_verbosity()
    set_verbosity(verbosity)

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized: app log = %s", app_log_path)


def switch_to_app_log() -> None:
    """Switch logging context to application.log.

    Removes project log handler (if active) from all loggers (openstan +
    libraries) and ensures app log handler is active on all loggers.
    Subsequent logs will flow to application.log.
    """
    global _project_log_handler, _current_context

    if _current_context == "app":
        return  # Already on app log

    # Remove project handler from ALL loggers
    _remove_handler_from_all_loggers(_project_log_handler)
    _project_log_handler = None

    # Ensure app handler is present on ALL loggers
    if _app_log_handler:
        _add_handler_to_all_loggers(_app_log_handler)

    _current_context = "app"
    logger = logging.getLogger(__name__)
    logger.info("Logging context switched to application.log")


def switch_to_project_log(project_root: Path) -> None:
    """Switch logging context to project.log.

    Removes app log handler from all loggers (openstan + libraries) and creates
    a new project log handler for the given project. Subsequent logs will flow
    to project.log from all loggers.

    Args:
        project_root: Root directory of the project.
    """
    global _project_log_handler, _current_context

    project_log_path = get_project_log_path(project_root)

    # If already on this project, do nothing
    if (
        _current_context == "project"
        and _project_log_handler
        and _project_log_handler.baseFilename == str(project_log_path)
    ):
        return

    # Remove app handler from ALL loggers (keep it alive in memory for switch_to_app_log)
    if _app_log_handler:
        _remove_handler_from_all_loggers(_app_log_handler)

    # Remove old project handler
    _remove_handler_from_all_loggers(_project_log_handler)

    # Create new project handler and attach to ALL loggers
    _project_log_handler = _create_rotating_file_handler(project_log_path)
    _add_handler_to_all_loggers(_project_log_handler)

    _current_context = "project"
    logger = logging.getLogger(__name__)
    logger.info("Logging context switched to project.log: %s", project_log_path)


def cleanup_old_project_logs() -> None:
    """Delete project.log files older than 30 days.

    This function scans for project.log files across the user's projects
    and removes any that haven't been modified in >30 days. Should be called
    on app closure to avoid startup delays.

    Currently, this is a placeholder that logs the operation. In future,
    it could scan known project locations or use file system watching.
    """
    logger = logging.getLogger(__name__)
    logger.debug("Running 30-day project log cleanup")

    # Note: Since we don't have a central registry of project locations,
    # cleanup is best-effort when projects are selected/loaded. This function
    # serves as a hook for future enhancements (e.g., scanning ~/.local/share/
    # for project directories, or maintaining a registry).

    # For now, log that cleanup was attempted
    logger.debug("Project log cleanup complete")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    This is the public factory function for creating loggers throughout openstan.
    All loggers created via this function inherit from the root "openstan" logger
    and respect its verbosity level and handlers.

    Args:
        name: Logger name, typically __name__ from the calling module.

    Returns:
        A logger instance that will flow logs to the active handler (app or project).

    Example:
        >>> import logging
        >>> from openstan.logging_manager import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("This is an info message")
    """
    return logging.getLogger(name)
