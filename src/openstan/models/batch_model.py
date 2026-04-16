"""
batch_model.py — DB persistence model for the ``batch`` table in gui.db.

Each row records the ``batch_id``, the owning ``project_id``, the cumulative
``duration_secs`` of actual PDF processing time, and a ``status`` flag.

The duration must survive across sessions: the user may process a batch, close
the application, reopen it, and only then commit.  Persisting to gui.db here
ensures the value is available at commit time regardless of whether the same
Python process is still running.

Lifecycle
---------
* ``create_batch()``   — called by ``StanPresenter.on_import_finished``.
                         Status starts as ``BATCH_STATUS_PENDING`` (0).
* ``get_duration()``   — called by ``StatementResultPresenter.__on_commit_batch``.
* ``commit_batch()``   — called by ``StatementResultPresenter.__on_commit_finished``.
                         Flips status to ``BATCH_STATUS_COMMITTED`` (2).
* ``delete_batch()``   — called on abandon *and* on stale-lock cleanup.
                         Committed batches are kept permanently.

Status constants
----------------
* ``BATCH_STATUS_PENDING``   = 0  (import done, not yet committed)
* ``BATCH_STATUS_COMMITTED`` = 2  (successfully committed to project.db)
"""

import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtSql import QSqlRecord, QSqlTableModel

if TYPE_CHECKING:
    from PyQt6.QtSql import QSqlDatabase


class BatchModel(QSqlTableModel):
    """``QSqlTableModel`` backed by the ``batch`` table in gui.db."""

    db_updated: pyqtSignal = pyqtSignal()

    # Status values (mirror the ``status`` lookup table in gui.db)
    BATCH_STATUS_PENDING: int = 0  # import finished, awaiting commit
    BATCH_STATUS_COMMITTED: int = 2  # successfully committed to project.db

    def __init__(self, db: "QSqlDatabase") -> None:
        super().__init__(db=db)
        self.setTable("batch")
        self.select()

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    @contextmanager
    def _filtered(self, filter_str: str):
        """Set *filter_str*, select, yield, then reset filter and re-select."""
        self.setFilter(filter_str)
        self.select()
        try:
            yield
        finally:
            self.setFilter("")
            self.select()

    def _get_batch_id_by_status(self, project_id: str, status: int) -> str | None:
        """Return the most recent ``batch_id`` for *project_id* with *status*,
        or ``None`` if no matching rows exist.
        """
        self.setFilter(f"project_id = '{project_id}' AND status = {status}")
        self.setSort(self.fieldIndex("created"), Qt.SortOrder.DescendingOrder)
        self.select()
        batch_id: str | None = None
        if self.rowCount() > 0:
            val = self.record(0).value("batch_id")
            if val is not None:
                batch_id = str(val)
        self.setFilter("")
        self.setSort(self.fieldIndex("created"), Qt.SortOrder.AscendingOrder)
        self.select()
        return batch_id

    # ---------------------------------------------------------------------------
    # Write
    # ---------------------------------------------------------------------------

    def create_batch(
        self,
        batch_id: str,
        project_id: str,
        duration_secs: float,
    ) -> tuple[bool, str]:
        """Insert a new batch row with ``status=BATCH_STATUS_PENDING``.

        Returns (success, message).
        """
        record: QSqlRecord = self.record()
        record.setValue("batch_id", batch_id)
        record.setValue("project_id", project_id)
        record.setValue("duration_secs", duration_secs)
        record.setValue("status", self.BATCH_STATUS_PENDING)
        record.setValue(
            "created",
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        )
        if self.insertRecord(-1, record) and self.submitAll():
            self.db_updated.emit()
            return (True, f"Batch {batch_id} created")
        err = self.lastError().text()
        print(f"ERROR: BatchModel.create_batch failed: {err}", file=sys.stderr)
        return (False, err)

    def delete_batch(self, batch_id: str) -> tuple[bool, str]:
        """Delete the row for *batch_id*.  Returns (success, message)."""
        with self._filtered(f"batch_id = '{batch_id}'"):
            for row in range(self.rowCount() - 1, -1, -1):
                self.removeRow(row)
            if self.submitAll():
                self.db_updated.emit()
                return (True, f"Batch {batch_id} deleted")
            return (False, self.lastError().text())

    def commit_batch(self, batch_id: str) -> tuple[bool, str]:
        """Set ``status`` to ``BATCH_STATUS_COMMITTED`` for *batch_id*.

        Called by ``StatementResultPresenter.__on_commit_finished`` after all
        three BSP calls (``update_db``, ``copy_statements``, ``delete_temps``)
        succeed.  Returns (success, message).
        """
        with self._filtered(f"batch_id = '{batch_id}'"):
            if self.rowCount() == 0:
                return (False, f"Batch {batch_id} not found")
            record: QSqlRecord = self.record(0)
            record.setValue("status", self.BATCH_STATUS_COMMITTED)
            self.setRecord(0, record)
            if self.submitAll():
                self.db_updated.emit()
                return (True, f"Batch {batch_id} committed")
            err = self.lastError().text()
            print(f"ERROR: BatchModel.commit_batch failed: {err}", file=sys.stderr)
            return (False, err)

    # ---------------------------------------------------------------------------
    # Read
    # ---------------------------------------------------------------------------

    def get_duration(self, batch_id: str) -> float:
        """Return persisted ``duration_secs`` for *batch_id*, or ``0.0`` if absent."""
        with self._filtered(f"batch_id = '{batch_id}'"):
            val = self.record(0).value("duration_secs") if self.rowCount() > 0 else None
            return float(val) if val is not None else 0.0

    def get_latest_batch_id(self, project_id: str) -> str | None:
        """Return the most recent *committed* ``batch_id`` for *project_id*,
        or ``None`` if no committed batches exist.
        """
        return self._get_batch_id_by_status(project_id, self.BATCH_STATUS_COMMITTED)

    def get_pending_batch_id(self, project_id: str) -> str | None:
        """Return the most recent *pending* ``batch_id`` for *project_id*,
        or ``None`` if no pending batches exist.

        Used by ``ExportDataPresenter`` to detect when an import has been
        completed but not yet committed, so the user can be warned before
        exporting stale data.
        """
        return self._get_batch_id_by_status(project_id, self.BATCH_STATUS_PENDING)
