"""
test_statement_result_presenter.py — unit tests for StatementResultPresenter.

Focuses on the session-restore debug worker retry logic (issue #212):
when ``load_results_from_db`` finds non-success rows with incomplete
debug status, it should trigger ``__start_debug_worker``.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from PySide6.QtSql import QSqlDatabase

from openstan.models.statement_result_model import (
    FailureResultModel,
    ReviewResultModel,
    StatementResultModel,
    SuccessResultModel,
)
from openstan.presenters.statement_result_presenter import StatementResultPresenter
from tests.unit.conftest import seed_session_and_project

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_result_rows(
    db: QSqlDatabase,
    batch_id: str,
    queue_id: str,
    project_id: str,
    statuses: list[str | None],
) -> list[str]:
    """Insert result rows into statement_result with given debug statuses.

    Returns the list of result_ids in insertion order.
    """
    import sqlite3

    result_ids: list[str] = []
    with sqlite3.connect(db.databaseName()) as conn:
        for status in statuses:
            rid = uuid4().hex
            conn.execute(
                "INSERT INTO statement_result "
                "(result_id, batch_id, queue_id, project_id, result, file_path, "
                " debug_json_path, debug_excel_path, debug_status, deleted, created) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, datetime('now'))",
                (
                    rid,
                    batch_id,
                    queue_id,
                    project_id,
                    "REVIEW",
                    f"/tmp/statement_{rid[:8]}.pdf",
                    None,
                    None,
                    status,
                ),
            )
            result_ids.append(rid)
        conn.commit()
    return result_ids


def _make_presenter(gui_db: QSqlDatabase) -> StatementResultPresenter:
    """Build a minimal StatementResultPresenter with mocked view."""
    success_model = SuccessResultModel()
    review_model = ReviewResultModel()
    failure_model = FailureResultModel()
    result_model = StatementResultModel(gui_db)

    # Stub out models that aren't exercised in these tests
    payload_model = MagicMock()
    queue_model = MagicMock()
    batch_model = MagicMock()

    view = MagicMock()
    # The view needs setModel and clicked signals for init wiring
    view.success_table = MagicMock()
    view.review_table = MagicMock()
    view.failure_table = MagicMock()
    view.buttonCloseResults = MagicMock()
    view.buttonAbandonBatch = MagicMock()
    view.buttonViewDebugInfo = MagicMock()
    view.buttonCommitBatch = MagicMock()
    view.labelStatementsProcessed = MagicMock()
    view.results_tabs = MagicMock()
    view.progressBar = MagicMock()

    return StatementResultPresenter(
        success_model=success_model,
        review_model=review_model,
        failure_model=failure_model,
        result_model=result_model,
        payload_model=payload_model,
        queue_model=queue_model,
        batch_model=batch_model,
        view=view,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLoadResultsFromDbDebugRetry:
    """Verify that load_results_from_db triggers the debug worker for
    rows with incomplete debug status."""

    def test_triggers_worker_when_rows_have_none_status(
        self, gui_db: QSqlDatabase
    ) -> None:
        """Rows with debug_status=None (never processed) should trigger worker."""
        _session_id, project_id, _ = seed_session_and_project(gui_db)
        batch_id = uuid4().hex
        queue_id = uuid4().hex

        _seed_result_rows(
            gui_db,
            batch_id,
            queue_id,
            project_id,
            statuses=[None, None, None],
        )

        presenter = _make_presenter(gui_db)
        presenter.project_path = Path("/tmp/test_project")

        with patch.object(
            presenter, "_StatementResultPresenter__start_debug_worker"
        ) as mock_start:
            presenter.load_results_from_db(batch_id, project_id)

            mock_start.assert_called_once_with(batch_id)

    def test_triggers_worker_when_rows_have_pending_status(
        self, gui_db: QSqlDatabase
    ) -> None:
        """Rows with debug_status='pending' (incomplete) should trigger worker."""
        _session_id, project_id, _ = seed_session_and_project(gui_db)
        batch_id = uuid4().hex
        queue_id = uuid4().hex

        _seed_result_rows(
            gui_db,
            batch_id,
            queue_id,
            project_id,
            statuses=["pending", "pending"],
        )

        presenter = _make_presenter(gui_db)
        presenter.project_path = Path("/tmp/test_project")

        with patch.object(
            presenter, "_StatementResultPresenter__start_debug_worker"
        ) as mock_start:
            presenter.load_results_from_db(batch_id, project_id)

            mock_start.assert_called_once_with(batch_id)

    def test_no_worker_when_all_done(self, gui_db: QSqlDatabase) -> None:
        """Rows with debug_status='done' should NOT trigger the worker."""
        _session_id, project_id, _ = seed_session_and_project(gui_db)
        batch_id = uuid4().hex
        queue_id = uuid4().hex

        _seed_result_rows(
            gui_db,
            batch_id,
            queue_id,
            project_id,
            statuses=["done", "done"],
        )

        presenter = _make_presenter(gui_db)
        presenter.project_path = Path("/tmp/test_project")

        with patch.object(
            presenter, "_StatementResultPresenter__start_debug_worker"
        ) as mock_start:
            presenter.load_results_from_db(batch_id, project_id)

            mock_start.assert_not_called()

    def test_no_worker_when_all_error(self, gui_db: QSqlDatabase) -> None:
        """Rows with debug_status='error' should NOT trigger the worker."""
        _session_id, project_id, _ = seed_session_and_project(gui_db)
        batch_id = uuid4().hex
        queue_id = uuid4().hex

        _seed_result_rows(
            gui_db,
            batch_id,
            queue_id,
            project_id,
            statuses=["error", "error"],
        )

        presenter = _make_presenter(gui_db)
        presenter.project_path = Path("/tmp/test_project")

        with patch.object(
            presenter, "_StatementResultPresenter__start_debug_worker"
        ) as mock_start:
            presenter.load_results_from_db(batch_id, project_id)

            mock_start.assert_not_called()

    def test_no_worker_when_project_path_is_none(self, gui_db: QSqlDatabase) -> None:
        """Worker should not start if project_path is not set."""
        _session_id, project_id, _ = seed_session_and_project(gui_db)
        batch_id = uuid4().hex
        queue_id = uuid4().hex

        _seed_result_rows(
            gui_db,
            batch_id,
            queue_id,
            project_id,
            statuses=[None, None],
        )

        presenter = _make_presenter(gui_db)
        # project_path stays None (default)

        with patch.object(
            presenter, "_StatementResultPresenter__start_debug_worker"
        ) as mock_start:
            presenter.load_results_from_db(batch_id, project_id)

            mock_start.assert_not_called()

    def test_mixed_statuses_triggers_worker(self, gui_db: QSqlDatabase) -> None:
        """A mix of done/error/pending rows should trigger worker (pending needs work)."""
        _session_id, project_id, _ = seed_session_and_project(gui_db)
        batch_id = uuid4().hex
        queue_id = uuid4().hex

        _seed_result_rows(
            gui_db,
            batch_id,
            queue_id,
            project_id,
            statuses=["done", "error", "pending", None],
        )

        presenter = _make_presenter(gui_db)
        presenter.project_path = Path("/tmp/test_project")

        with patch.object(
            presenter, "_StatementResultPresenter__start_debug_worker"
        ) as mock_start:
            presenter.load_results_from_db(batch_id, project_id)

            mock_start.assert_called_once_with(batch_id)
