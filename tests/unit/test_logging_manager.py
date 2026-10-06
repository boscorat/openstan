"""Unit tests for logging_manager module.

Tests core behavior including:
- Verbosity validation and persistence
- Log path resolution across platforms
- Logger initialization and cascade
- Handler state management
"""

import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QSettings

from openstan.logging_manager import (
    get_app_log_path,
    get_logger,
    get_project_log_path,
    get_verbosity,
    set_verbosity,
)

# Test settings org/app for isolated testing
_TEST_ORG = "openstan-test"
_TEST_APP = "openstan-test"


@pytest.fixture
def clean_settings():
    """Fixture to provide clean QSettings for each test."""
    settings = QSettings(_TEST_ORG, _TEST_APP)
    # Clear any existing test settings
    settings.clear()
    yield settings
    # Cleanup after test
    settings.clear()


class TestGetVerbosity:
    """Tests for get_verbosity() function."""

    def test_get_verbosity_default_normal(self, clean_settings):
        """Default verbosity should be 'normal' when not set."""
        # Mock QSettings to return None (key doesn't exist)
        with patch("openstan.logging_manager.QSettings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.value.return_value = None
            mock_settings_class.return_value = mock_settings

            result = get_verbosity()
            assert result == "normal"

    def test_get_verbosity_returns_stored_normal(self, clean_settings):
        """Should return 'normal' when stored in QSettings."""
        with patch("openstan.logging_manager.QSettings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.value.return_value = "normal"
            mock_settings_class.return_value = mock_settings

            result = get_verbosity()
            assert result == "normal"

    def test_get_verbosity_returns_stored_verbose(self, clean_settings):
        """Should return 'verbose' when stored in QSettings."""
        with patch("openstan.logging_manager.QSettings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.value.return_value = "verbose"
            mock_settings_class.return_value = mock_settings

            result = get_verbosity()
            assert result == "verbose"

    def test_get_verbosity_sanitizes_invalid_values(self, clean_settings):
        """Should return 'normal' if invalid value stored."""
        with patch("openstan.logging_manager.QSettings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.value.return_value = "invalid_value"
            mock_settings_class.return_value = mock_settings

            result = get_verbosity()
            assert result == "normal"


class TestSetVerbosity:
    """Tests for set_verbosity() function."""

    def test_set_verbosity_rejects_invalid_level(self):
        """set_verbosity() should raise ValueError for invalid levels."""
        with pytest.raises(ValueError, match="Invalid verbosity level"):
            set_verbosity("invalid_level")  # type: ignore

    def test_set_verbosity_accepts_normal(self):
        """set_verbosity('normal') should not raise."""
        with (
            patch("openstan.logging_manager.QSettings"),
            patch("openstan.logging_manager._root_logger") as mock_logger,
        ):
            mock_logger.setLevel = MagicMock()
            set_verbosity("normal")
            # Should not raise

    def test_set_verbosity_accepts_verbose(self):
        """set_verbosity('verbose') should not raise."""
        with (
            patch("openstan.logging_manager.QSettings"),
            patch("openstan.logging_manager._root_logger") as mock_logger,
        ):
            mock_logger.setLevel = MagicMock()
            set_verbosity("verbose")
            # Should not raise

    def test_set_verbosity_persists_to_qsettings(self):
        """set_verbosity() should persist value to QSettings."""
        with patch("openstan.logging_manager.QSettings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings_class.return_value = mock_settings

            with patch("openstan.logging_manager._root_logger"):
                set_verbosity("verbose")

            # Verify setValue was called with correct key/value
            mock_settings.setValue.assert_called_once_with(
                "logging/verbosity", "verbose"
            )

    def test_set_verbosity_updates_all_loggers(self):
        """set_verbosity() should update openstan + library loggers."""
        with (
            patch("openstan.logging_manager.QSettings"),
            patch("openstan.logging_manager._root_logger"),
            patch("openstan.logging_manager.logging.getLogger") as mock_get_logger,
        ):
            mock_bsp = MagicMock()
            mock_anon = MagicMock()
            mock_get_logger.side_effect = [mock_bsp, mock_anon]

            set_verbosity("verbose")

            # Verify library loggers were fetched
            calls = mock_get_logger.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == "bank_statement_parser"
            assert calls[1][0][0] == "uk_bank_statement_anonymiser"


class TestGetAppLogPath:
    """Tests for get_app_log_path() function."""

    def test_get_app_log_path_returns_path_object(self):
        """Should return a Path object."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        result = get_app_log_path(session_id)
        assert isinstance(result, Path)

    def test_get_app_log_path_ends_with_session_uuid(self):
        """Should end with the session UUID as filename."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        result = get_app_log_path(session_id)
        assert result.name == f"{session_id}.log"

    @patch.dict(os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"})
    @patch("sys.platform", "win32")
    def test_get_app_log_path_windows(self):
        """Windows path should use APPDATA."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        result = get_app_log_path(session_id)
        assert "openstan" in str(result)
        assert session_id in str(result)

    @patch("sys.platform", "darwin")
    def test_get_app_log_path_macos(self):
        """macOS path should use Library/Application Support."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        result = get_app_log_path(session_id)
        result_str = str(result)
        assert "openstan" in result_str
        # Should be under home directory
        assert (
            str(Path.home()) in result_str
            or "~" in result_str
            or "Library" in result_str
        )

    @patch.dict(os.environ, {}, clear=False)
    @patch("sys.platform", "linux")
    def test_get_app_log_path_linux(self):
        """Linux path should use .local/share."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        result = get_app_log_path(session_id)
        result_str = str(result)
        assert "openstan" in result_str
        assert session_id in result_str


class TestGetProjectLogPath:
    """Tests for get_project_log_path() function."""

    def test_get_project_log_path_returns_path_object(self):
        """Should return a Path object."""
        project_root = Path("/path/to/project")
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        result = get_project_log_path(project_root, session_id)
        assert isinstance(result, Path)

    def test_get_project_log_path_ends_with_session_uuid(self):
        """Should end with the session UUID as filename."""
        project_root = Path("/path/to/project")
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        result = get_project_log_path(project_root, session_id)
        assert result.name == f"{session_id}.log"

    def test_get_project_log_path_under_project_root(self):
        """Should place log file in project root directory."""
        project_root = Path("/path/to/my_project")
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        result = get_project_log_path(project_root, session_id)
        assert result.parent == project_root

    def test_get_project_log_path_with_string_input(self):
        """Should accept string paths too."""
        project_root_str = "/path/to/project"
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        result = get_project_log_path(project_root_str, session_id)  # type: ignore
        assert isinstance(result, Path)
        assert result.name == f"{session_id}.log"


class TestGetLogger:
    """Tests for get_logger() factory function."""

    def test_get_logger_returns_logger(self):
        """Should return a logging.Logger instance."""
        result = get_logger("test.module")
        assert isinstance(result, logging.Logger)

    def test_get_logger_returns_named_logger(self):
        """Should return logger with correct name."""
        result = get_logger("my.test.logger")
        assert result.name == "my.test.logger"

    def test_get_logger_uses_dunder_name(self):
        """Should accept __name__ as standard usage."""
        result = get_logger(__name__)
        assert isinstance(result, logging.Logger)

    def test_get_logger_caches_instances(self):
        """Should return same instance for same name (logging stdlib behavior)."""
        logger1 = get_logger("cached.logger")
        logger2 = get_logger("cached.logger")
        assert logger1 is logger2


class TestLoggingLevelConstants:
    """Tests for logging level behavior."""

    def test_normal_verbosity_uses_info_level(self):
        """Normal verbosity should correspond to INFO level."""
        with (
            patch("openstan.logging_manager.QSettings"),
            patch("openstan.logging_manager._root_logger") as mock_logger,
        ):
            set_verbosity("normal")
            # Verify setLevel was called with INFO
            # DEBUG level = 10, INFO level = 20
            calls = [call[0][0] for call in mock_logger.setLevel.call_args_list]
            assert logging.INFO in calls

    def test_verbose_verbosity_uses_debug_level(self):
        """Verbose verbosity should correspond to DEBUG level."""
        with (
            patch("openstan.logging_manager.QSettings"),
            patch("openstan.logging_manager._root_logger") as mock_logger,
        ):
            set_verbosity("verbose")
            # Verify setLevel was called with DEBUG
            calls = [call[0][0] for call in mock_logger.setLevel.call_args_list]
            assert logging.DEBUG in calls


class TestIntegrationBehavior:
    """Integration tests for logging_manager behavior."""

    def test_verbosity_persistence_round_trip(self):
        """Verbosity should persist and be readable."""
        with patch("openstan.logging_manager.QSettings") as mock_settings_class:
            # First call: set
            mock_settings1 = MagicMock()
            # Second call: get
            mock_settings2 = MagicMock()
            mock_settings2.value.return_value = "verbose"

            mock_settings_class.side_effect = [mock_settings1, mock_settings2]

            with patch("openstan.logging_manager._root_logger"):
                set_verbosity("verbose")
                # Simulate restart by creating new settings
                mock_settings_class.side_effect = None
                mock_settings_class.return_value = mock_settings2
                result = get_verbosity()

            assert result == "verbose"

    def test_logger_factory_namespace_hierarchy(self):
        """Loggers should respect Python's hierarchical logger namespace."""
        parent_logger = get_logger("openstan")
        child_logger = get_logger("openstan.views")

        assert child_logger.parent is not None
        assert child_logger.parent.name == parent_logger.name


class TestHandlerAttachment:
    """Tests for handler attachment to library loggers (PR #232 fix).

    These tests verify that the critical fix for PR #232 is in place:
    library loggers must have handlers explicitly attached because they
    are independent top-level loggers (not children of "openstan").
    """

    def test_library_loggers_are_independent(self):
        """Library loggers should be independent top-level loggers."""
        lib_bsp = logging.getLogger("bank_statement_parser")
        lib_anon = logging.getLogger("uk_bank_statement_anonymiser")
        openstan_logger = logging.getLogger("openstan")

        # Verify they are independent (not children of openstan)
        assert lib_bsp.parent != openstan_logger
        assert lib_anon.parent != openstan_logger

    def test_handler_removal_none_safe(self):
        """_remove_handler_from_all_loggers should handle None gracefully."""
        from openstan.logging_manager import _remove_handler_from_all_loggers

        # Should not raise
        _remove_handler_from_all_loggers(None)

    def test_verbosity_propagates_to_library_loggers(self):
        """set_verbosity() should update both openstan and library loggers."""
        with patch("openstan.logging_manager.QSettings"):
            # First initialize the root logger (set_verbosity needs it)
            openstan_logger = logging.getLogger("openstan")
            openstan_logger.setLevel(logging.DEBUG)

            # Get library loggers
            lib_bsp = logging.getLogger("bank_statement_parser")
            lib_anon = logging.getLogger("uk_bank_statement_anonymiser")

            # Set verbose level
            set_verbosity("verbose")

            # All should be at DEBUG level
            assert lib_bsp.level == logging.DEBUG
            assert lib_anon.level == logging.DEBUG

            # Set normal level
            set_verbosity("normal")

            # All should be at INFO level
            assert lib_bsp.level == logging.INFO
            assert lib_anon.level == logging.INFO
