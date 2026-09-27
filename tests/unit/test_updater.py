"""
test_updater.py — unit tests for UpdateChecker and version parsing.

Tests cover:
- Version string parsing and comparison logic
- Edge cases with version strings (prefixes, pre-release tags, etc.)
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QThreadPool

from openstan.updater import (
    UpdateChecker,
    _current_version,
    _parse_version,
)


class TestParseVersion:
    """Tests for _parse_version() version string parsing."""

    def test_parse_simple_version(self) -> None:
        """Parses simple semantic versions like '1.2.3'."""
        result = _parse_version("1.2.3")
        assert result == (1, 2, 3)

    def test_parse_version_with_v_prefix(self) -> None:
        """Parses versions with 'v' prefix like 'v1.2.3'."""
        result = _parse_version("v1.2.3")
        assert result == (1, 2, 3)

    def test_parse_version_strips_prerelease_suffix(self) -> None:
        """Strips pre-release suffixes like 'a9', 'b1', 'rc1'."""
        assert _parse_version("1.2.3a9") == (1, 2, 3)
        assert _parse_version("1.2.3b1") == (1, 2, 3)
        assert _parse_version("1.2.3rc1") == (1, 2, 3)

    def test_parse_version_with_only_major(self) -> None:
        """Parses version with only major component, pads with zeros."""
        result = _parse_version("1")
        assert result == (1, 0, 0)

    def test_parse_version_with_major_minor(self) -> None:
        """Parses version with major and minor, pads patch with zero."""
        result = _parse_version("1.2")
        assert result == (1, 2, 0)

    def test_parse_version_comparison_newer_minor(self) -> None:
        """Newer minor version compares greater."""
        v1 = _parse_version("1.1.0")
        v2 = _parse_version("1.2.0")
        assert v2 > v1

    def test_parse_version_comparison_newer_major(self) -> None:
        """Newer major version compares greater."""
        v1 = _parse_version("0.2.2")
        v2 = _parse_version("1.0.0")
        assert v2 > v1

    def test_parse_version_prerelease_strips_suffix(self) -> None:
        """Pre-release suffixes are stripped, so versions with/without suffix are equal.

        Because pre-release suffixes (a9, rc1, etc.) are discarded during parsing,
        a pre-release version and its corresponding release version parse to the
        same tuple and compare as equal.
        """
        v_rc = _parse_version("1.0.0rc1")
        v_rel = _parse_version("1.0.0")
        # Both parse to (1, 0, 0) because the suffix is stripped
        assert v_rc == v_rel

    def test_parse_version_zero_padding(self) -> None:
        """Handles zero-padding and non-numeric suffixes correctly."""
        result = _parse_version("1.02.003")
        assert result == (1, 2, 3)


class TestCurrentVersion:
    """Tests for _current_version()."""

    def test_current_version_returns_string(self) -> None:
        """_current_version() always returns a string."""
        result = _current_version()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_current_version_is_semantic(self) -> None:
        """_current_version() returns a valid semantic version format."""
        result = _current_version()
        # Should be parseable by _parse_version without error
        parsed = _parse_version(result)
        assert isinstance(parsed, tuple)
        assert len(parsed) == 3


class TestUpdateChecker:
    """Tests for UpdateChecker signal emission."""

    @pytest.fixture
    def threadpool(self) -> QThreadPool:
        """Create a thread pool for tests."""
        return QThreadPool()

    def test_update_checker_initialization(self, threadpool: QThreadPool) -> None:
        """UpdateChecker initializes without errors."""
        checker = UpdateChecker(threadpool=threadpool)
        assert checker is not None

    def test_update_checker_has_update_available_signal(
        self, threadpool: QThreadPool
    ) -> None:
        """UpdateChecker has update_available signal."""
        checker = UpdateChecker(threadpool=threadpool)
        assert hasattr(checker, "update_available")

    def test_update_checker_check_async_starts_worker(
        self, threadpool: QThreadPool
    ) -> None:
        """check_async() starts a worker on the thread pool."""
        checker = UpdateChecker(threadpool=threadpool)

        # Mock threadpool.start to verify it's called with a QRunnable
        with patch.object(threadpool, "start") as mock_start:
            checker.check_async()

            # Assert threadpool.start() was called exactly once with a QRunnable
            mock_start.assert_called_once()
            args, _ = mock_start.call_args
            # The first argument should be a QRunnable (the worker)
            assert args[0] is not None  # Verify a worker was passed

    def test_update_checker_show_update_dialog_no_crash(
        self, threadpool: QThreadPool
    ) -> None:
        """show_update_dialog() constructs and executes the update dialog."""
        checker = UpdateChecker(threadpool=threadpool)

        # Patch _UpdateDialog to avoid creating real widgets
        with patch("openstan.updater._UpdateDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog_class.return_value = mock_dialog

            # Call the method with required arguments
            checker.show_update_dialog(
                latest_version="2.0.0", release_url="https://example.com/releases/2.0.0"
            )

            # Verify the dialog was created
            mock_dialog_class.assert_called_once()
            # Verify exec() was called to show it
            mock_dialog.exec.assert_called_once()
