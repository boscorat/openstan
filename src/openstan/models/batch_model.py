"""
batch_model.py — DB persistence model for the ``batch`` table in gui.db.

Each row records the ``batch_id``, the owning ``project_id``, and the
cumulative ``duration_secs`` of actual PDF processing time (wall-clock seconds
from ``run_import()`` start to ``import_finished`` emission, excluding any time
the user spends reviewing results before committing).

The duration must survive across sessions: the user may process a batch, close
the application, reopen it, and only then commit.  Persisting to gui.db here
ensures the value is available at commit time regardless of whether the same
Python process is still running.

Lifecycle
---------
* ``create_batch()``   — called by ``StanPresenter.on_import_finished``.
* ``get_duration()``   — called by ``StatementResultPresenter.__on_commit_batch``.
* ``delete_batch()``   — called on abandon *and* after a successful commit.
"""

import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtSql import QSqlRecord, QSqlTableModel

if TYPE_CHECKING:
    from PyQt6.QtSql import QSqlDatabase


class BatchModel(QSqlTableModel):
    """``QSqlTableModel`` backed by the ``batch`` table in gui.db."""

    db_updated: pyqtSignal = pyqtSignal()

    def __init__(self, db: "QSqlDatabase") -> None:
        super().__init__(db=db)
        self.setTable("batch")
        self.select()

    # ---------------------------------------------------------------------------
    # Write
    # ---------------------------------------------------------------------------

    def create_batch(
        self,
        batch_id: str,
        project_id: str,
        duration_secs: float,
    ) -> tuple[bool, str]:
        """Insert a new batch row.  Returns (success, message)."""
        record: QSqlRecord = self.record()
        record.setValue("batch_id", batch_id)
        record.setValue("project_id", project_id)
        record.setValue("duration_secs", duration_secs)
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
        self.setFilter(f"batch_id = '{batch_id}'")
        self.select()
        for row in range(self.rowCount() - 1, -1, -1):
            self.removeRow(row)
        if self.submitAll():
            self.setFilter("")
            self.select()
            self.db_updated.emit()
            return (True, f"Batch {batch_id} deleted")
        err = self.lastError().text()
        self.setFilter("")
        self.select()
        return (False, err)

    # ---------------------------------------------------------------------------
    # Read
    # ---------------------------------------------------------------------------

    def get_duration(self, batch_id: str) -> float:
        """Return persisted ``duration_secs`` for *batch_id*, or ``0.0`` if absent."""
        self.setFilter(f"batch_id = '{batch_id}'")
        self.select()
        duration = 0.0
        if self.rowCount() > 0:
            val = self.record(0).value("duration_secs")
            if val is not None:
                duration = float(val)
        self.setFilter("")
        self.select()
        return duration
