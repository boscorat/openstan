"""
test_admin_presenter.py — unit tests for AdminPresenter.

Tests cover the is_update_check_enabled() method which retrieves the
update-check preference from QSettings. Special care is taken to test the
default value (True) when the setting has never been explicitly set.

Tests verify:
- Default value when setting doesn't exist (should be True)
- Setting persists when explicitly set to True
- Setting persists when explicitly set to False
- Type coercion handles both string and bool stored values
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

if sys.platform not in ("darwin", "win32"):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings

from openstan.presenters.admin_presenter import AdminPresenter


class TestIsUpdateCheckEnabled:
    """Tests for AdminPresenter.is_update_check_enabled()."""

    @pytest.fixture(autouse=True)
    def _cleanup_qsettings(self) -> None:
        """Clean up QSettings before and after each test.

        This ensures each test starts with a clean slate and doesn't leak
        settings to other tests.
        """
        settings = QSettings("openstan", "openstan")
        settings.remove("privacy")
        yield
        settings.remove("privacy")

    def test_default_returns_true_when_setting_not_set(self) -> None:
        """When key doesn't exist in QSettings, should return True (default)."""
        # Ensure the key is not set
        settings = QSettings("openstan", "openstan")
        settings.remove("privacy")

        result = AdminPresenter.is_update_check_enabled()
        assert result is True

    def test_returns_true_when_explicitly_set_to_true(self) -> None:
        """When setting is explicitly set to True, should return True."""
        settings = QSettings("openstan", "openstan")
        settings.setValue("privacy/update_check_enabled", True)

        result = AdminPresenter.is_update_check_enabled()
        assert result is True

    def test_returns_false_when_explicitly_set_to_false(self) -> None:
        """When setting is explicitly set to False, should return False."""
        settings = QSettings("openstan", "openstan")
        settings.setValue("privacy/update_check_enabled", False)

        result = AdminPresenter.is_update_check_enabled()
        assert result is False

    def test_handles_string_true_value(self) -> None:
        """Coerces string 'true' to boolean True."""
        settings = QSettings("openstan", "openstan")
        settings.setValue("privacy/update_check_enabled", "true")

        result = AdminPresenter.is_update_check_enabled()
        assert result is True

    def test_handles_string_false_value(self) -> None:
        """Coerces string 'false' to boolean False."""
        settings = QSettings("openstan", "openstan")
        settings.setValue("privacy/update_check_enabled", "false")

        result = AdminPresenter.is_update_check_enabled()
        assert result is False

    def test_handles_string_1_value(self) -> None:
        """Coerces string '1' to boolean True."""
        settings = QSettings("openstan", "openstan")
        settings.setValue("privacy/update_check_enabled", "1")

        result = AdminPresenter.is_update_check_enabled()
        assert result is True

    def test_handles_string_0_value(self) -> None:
        """Coerces string '0' to boolean False."""
        settings = QSettings("openstan", "openstan")
        settings.setValue("privacy/update_check_enabled", "0")

        result = AdminPresenter.is_update_check_enabled()
        assert result is False

    def test_setting_persistence_across_calls(self) -> None:
        """Setting persists across multiple calls to is_update_check_enabled()."""
        settings = QSettings("openstan", "openstan")

        # First set to False
        settings.setValue("privacy/update_check_enabled", False)
        assert AdminPresenter.is_update_check_enabled() is False

        # Should still be False on next call
        assert AdminPresenter.is_update_check_enabled() is False

        # Change to True
        settings.setValue("privacy/update_check_enabled", True)
        assert AdminPresenter.is_update_check_enabled() is True

        # Should still be True on next call
        assert AdminPresenter.is_update_check_enabled() is True
