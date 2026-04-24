"""
tests/test_screenshots.py — auto-generate documentation screenshots.

Renders each view widget headlessly using the offscreen QPA and saves a PNG
to docs/assets/screenshots/.  Run with:

    uv run pytest tests/test_screenshots.py -v

Screenshots are committed to the repository and referenced by the docs.
Regenerate them whenever the UI changes.

A QApplication must exist before any view widget is instantiated.  When run
as part of the full test suite, conftest.py creates one first.  When run
standalone this module creates one itself.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure offscreen rendering on Linux (no-op on macOS/Windows)
# ---------------------------------------------------------------------------

if sys.platform not in ("darwin", "win32"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Qt imports must come after the platform env-var is set
from PyQt6.QtWidgets import QApplication  # noqa: E402

# ---------------------------------------------------------------------------
# QApplication — reuse existing instance (created by conftest.py when running
# the full suite) or create one when running this file standalone.
# ---------------------------------------------------------------------------

_qapp: QApplication | None = None


def _get_qapp() -> QApplication:
    global _qapp
    if _qapp is None:
        existing = QApplication.instance()
        if existing is not None:
            _qapp = existing  # type: ignore[assignment]
        else:
            _qapp = QApplication(sys.argv[:1])
    assert _qapp is not None
    return _qapp


# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCREENSHOTS_DIR = _REPO_ROOT / "docs" / "assets" / "screenshots"

# Width × Height for all screenshots
_WIDTH = 1280
_HEIGHT = 800


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _save(widget_factory, name: str) -> None:
    """Instantiate widget_factory(), resize, and save a PNG."""
    app = _get_qapp()
    widget = widget_factory()
    widget.resize(_WIDTH, _HEIGHT)
    widget.show()
    app.processEvents()
    _SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _SCREENSHOTS_DIR / f"{name}.png"
    ok = widget.grab().save(str(out_path))
    widget.close()
    assert ok, f"Failed to save screenshot: {out_path}"


# ---------------------------------------------------------------------------
# Tests — one per screenshot
# ---------------------------------------------------------------------------


def test_screenshot_title() -> None:
    from openstan.views.title import TitleView

    _save(TitleView, "title")


def test_screenshot_project_view() -> None:
    from openstan.views.project_view import ProjectView

    _save(ProjectView, "project_view")


def test_screenshot_project_nav() -> None:
    from openstan.views.project_view import ProjectNavView

    _save(ProjectNavView, "project_nav")


def test_screenshot_project_wizard() -> None:
    from openstan.views.project_view import ProjectWizard

    _save(lambda: ProjectWizard(mode="new"), "project_wizard")


def test_screenshot_statement_queue() -> None:
    from openstan.views.statement_queue_view import StatementQueueView

    _save(StatementQueueView, "statement_queue")


def test_screenshot_statement_results() -> None:
    from openstan.views.statement_result_view import StatementResultView

    _save(StatementResultView, "statement_results")


def test_screenshot_debug_info() -> None:
    from openstan.views.debug_info_dialog import DebugInfoDialog

    _save(lambda: DebugInfoDialog(rows=[]), "debug_info")


def test_screenshot_project_info() -> None:
    from openstan.views.project_info_view import ProjectInfoView

    _save(ProjectInfoView, "project_info")


def test_screenshot_export_data() -> None:
    from openstan.views.export_data_view import ExportDataView

    _save(ExportDataView, "export_data")


def test_screenshot_advanced_export() -> None:
    from openstan.views.advanced_export_view import AdvancedExportView

    _save(AdvancedExportView, "advanced_export")


def test_screenshot_run_reports() -> None:
    from openstan.views.run_reports_view import RunReportsView

    _save(RunReportsView, "run_reports")


def test_screenshot_admin() -> None:
    from openstan.views.admin_view import AdminView

    _save(AdminView, "admin")


def test_screenshot_about() -> None:
    from openstan.views.about_dialog import AboutDialog

    _save(AboutDialog, "about")


def test_screenshot_gap_detail() -> None:
    from openstan.views.project_info_view import GapDetailDialog

    _save(GapDetailDialog, "gap_detail")
