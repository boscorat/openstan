"""
statement_result_model.py — In-memory presentation models and DB persistence models
for statement import results.

Architecture
------------
Two layers:

**In-memory presentation layer** — populated live as each statement is processed
by the background worker.  These are lightweight ``QStandardItemModel`` subclasses
that require no DB access and update the view instantly on every signal:

* ``SuccessResultModel`` — SUCCESS rows
* ``ReviewResultModel``  — REVIEW rows
* ``FailureResultModel`` — FAILURE rows

Each holds ``ResultRow`` dataclass instances (including the raw ``PdfResult``
payload) in memory.  The three view tables in ``StatementResultView`` are bound
directly to these models.

**DB persistence layer** — written once when the batch completes (``import_finished``
signal).  Two ``QSqlTableModel`` subclasses back the ``statement_result`` and
``statement_result_payload`` tables in gui.db:

* ``StatementResultModel``        — display columns only (no BLOB).
* ``StatementResultPayloadModel`` — single BLOB column (pickle of ``PdfResult``).

On session restore (project switch / app restart with a locked batch) the DB layer
is read back and the in-memory models are repopulated so the results view can be
shown without re-running the import.
"""

import pickle

from PyQt6.QtCore import QByteArray
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtSql import QSqlRecord, QSqlTableModel

if TYPE_CHECKING:
    from bank_statement_parser import PdfResult


# ---------------------------------------------------------------------------
# ResultRow — in-memory data carrier
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ResultRow:
    """All data for one processed statement, held in memory during a batch.

    ``pdf_result`` carries the raw ``PdfResult`` object so pickling only
    happens once, at batch-end persist time.  It is ``None`` when the row
    is reconstructed from the DB on session restore (payload not needed for
    display).
    """

    result_id: str
    batch_id: str
    queue_id: str
    project_id: str
    result: str  # "SUCCESS" | "REVIEW" | "FAILURE"
    file_path: Path
    id_account: str | None
    statement_date: str | None
    payments_in: float | None
    payments_out: float | None
    error_type: str | None
    message: str | None
    pdf_result: "PdfResult | None" = field(default=None)


# ---------------------------------------------------------------------------
# Column layout shared by all three in-memory models
# ---------------------------------------------------------------------------

_COLUMNS: list[str] = [
    "File",
    "Result",
    "Account",
    "Date",
    "Payments In",
    "Payments Out",
    "Error Type",
    "Message",
]

_COL_FILE = 0
_COL_RESULT = 1
_COL_ACCOUNT = 2
_COL_DATE = 3
_COL_IN = 4
_COL_OUT = 5
_COL_ERROR = 6
_COL_MESSAGE = 7


def _row_items(row: "ResultRow") -> list[QStandardItem]:
    """Build a list of QStandardItems from a ResultRow (one per column)."""
    return [
        QStandardItem(row.file_path.name),
        QStandardItem(row.result),
        QStandardItem(row.id_account or ""),
        QStandardItem(row.statement_date or ""),
        QStandardItem(str(row.payments_in) if row.payments_in is not None else ""),
        QStandardItem(str(row.payments_out) if row.payments_out is not None else ""),
        QStandardItem(row.error_type or ""),
        QStandardItem(row.message or ""),
    ]


class _BaseResultModel(QStandardItemModel):
    """Shared base for the three in-memory result models."""

    model_updated: pyqtSignal = pyqtSignal()

    def __init__(self) -> None:
        super().__init__(0, len(_COLUMNS))
        self.setHorizontalHeaderLabels(_COLUMNS)
        self._rows: list[ResultRow] = []

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Return flags with ItemIsEditable removed — results are read-only."""
        return super().flags(index) & ~Qt.ItemFlag.ItemIsEditable

    @property
    def row_count(self) -> int:
        return len(self._rows)

    def add_row(self, row: ResultRow) -> None:
        """Append one ResultRow and refresh the view."""
        self._rows.append(row)
        self.appendRow(_row_items(row))
        self.model_updated.emit()

    def all_rows(self) -> list[ResultRow]:
        return list(self._rows)

    def clear_rows(self) -> None:
        """Remove all rows from the model and internal list."""
        self._rows.clear()
        self.removeRows(0, self.rowCount())
        self.model_updated.emit()


class SuccessResultModel(_BaseResultModel):
    """In-memory model for SUCCESS results."""


class ReviewResultModel(_BaseResultModel):
    """In-memory model for REVIEW results."""


class FailureResultModel(_BaseResultModel):
    """In-memory model for FAILURE results."""


# ---------------------------------------------------------------------------
# DB persistence layer — StatementResultModel
# ---------------------------------------------------------------------------


class StatementResultModel(QSqlTableModel):
    """Persistent display model backed by the ``statement_result`` table.

    Contains all human-readable columns but *not* the BLOB payload — that
    lives in ``StatementResultPayloadModel``.
    """

    db_updated: pyqtSignal = pyqtSignal()

    # Column indices — must match CREATE TABLE column order
    COL_RESULT_ID = 0
    COL_BATCH_ID = 1
    COL_QUEUE_ID = 2
    COL_PROJECT_ID = 3
    COL_RESULT = 4
    COL_FILE_PATH = 5
    COL_ID_ACCOUNT = 6
    COL_STATEMENT_DATE = 7
    COL_PAYMENTS_IN = 8
    COL_PAYMENTS_OUT = 9
    COL_ERROR_TYPE = 10
    COL_MESSAGE = 11
    COL_CREATED = 12

    def __init__(self, db) -> None:
        super().__init__(None, db)
        self.setTable("statement_result")
        self.select()

    # ---------------------------------------------------------------------------
    # Write
    # ---------------------------------------------------------------------------

    def add_result(
        self,
        batch_id: str,
        queue_id: str,
        project_id: str,
        result: str,
        file_path: Path,
        id_account: str | None,
        statement_date: str | None,
        payments_in: float | None,
        payments_out: float | None,
        error_type: str | None,
        message: str | None,
    ) -> tuple[bool, str, str]:
        """Insert one result row.  Returns (success, result_id, message)."""
        result_id: str = uuid4().hex
        record: QSqlRecord = self.record()
        record.setValue("result_id", result_id)
        record.setValue("batch_id", batch_id)
        record.setValue("queue_id", queue_id)
        record.setValue("project_id", project_id)
        record.setValue("result", result)
        record.setValue("file_path", str(file_path))
        record.setValue("id_account", id_account)
        record.setValue("statement_date", statement_date)
        record.setValue("payments_in", payments_in)
        record.setValue("payments_out", payments_out)
        record.setValue("error_type", error_type)
        record.setValue("message", message)
        # QSqlTableModel sets all unset columns to NULL — including 'created'
        # which is NOT NULL.  The SQLite DEFAULT only fires when the column is
        # omitted from the INSERT entirely, so we must supply the value here.
        record.setValue(
            "created",
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        )
        if self.insertRecord(-1, record) and self.submitAll():
            self.db_updated.emit()
            return (True, result_id, f"Result {result_id} inserted")
        err = self.lastError().text()
        print(f"ERROR: StatementResultModel.add_result failed: {err}", file=sys.stderr)
        return (False, "", err)

    def delete_results_for_batch(self, batch_id: str) -> tuple[bool, str]:
        """Delete all result rows for *batch_id*.  Returns (success, message)."""
        self.setFilter(f"batch_id = '{batch_id}'")
        self.select()
        for row in range(self.rowCount() - 1, -1, -1):
            self.removeRow(row)
        if self.submitAll():
            self.setFilter("")
            self.select()
            self.db_updated.emit()
            return (True, f"Results for batch {batch_id} deleted")
        return (False, self.lastError().text())

    # ---------------------------------------------------------------------------
    # Read
    # ---------------------------------------------------------------------------

    def get_rows_for_batch(self, batch_id: str) -> list[ResultRow]:
        """Return all result rows for *batch_id* as ``ResultRow`` objects.

        ``pdf_result`` is left as ``None`` — payloads are not needed for
        display on session restore.
        """
        self.setFilter(f"batch_id = '{batch_id}'")
        self.select()
        rows: list[ResultRow] = []
        for i in range(self.rowCount()):
            rec = self.record(i)
            pin = rec.value("payments_in")
            pout = rec.value("payments_out")
            rows.append(
                ResultRow(
                    result_id=str(rec.value("result_id")),
                    batch_id=str(rec.value("batch_id")),
                    queue_id=str(rec.value("queue_id")),
                    project_id=str(rec.value("project_id")),
                    result=str(rec.value("result")),
                    file_path=Path(str(rec.value("file_path"))),
                    id_account=rec.value("id_account") or None,
                    statement_date=rec.value("statement_date") or None,
                    payments_in=float(pin) if pin not in (None, "") else None,
                    payments_out=float(pout) if pout not in (None, "") else None,
                    error_type=rec.value("error_type") or None,
                    message=rec.value("message") or None,
                    pdf_result=None,
                )
            )
        self.setFilter("")
        self.select()
        return rows

    def get_result_ids_for_batch(self, batch_id: str) -> list[str]:
        """Return all result_id values for a given batch (for payload lookup)."""
        self.setFilter(f"batch_id = '{batch_id}'")
        self.select()
        ids: list[str] = [
            str(self.record(row).value("result_id")) for row in range(self.rowCount())
        ]
        self.setFilter("")
        self.select()
        return ids


# ---------------------------------------------------------------------------
# DB persistence layer — StatementResultPayloadModel
# ---------------------------------------------------------------------------


class StatementResultPayloadModel(QSqlTableModel):
    """Persistence model for pickled PdfResult payloads.

    Only touched during:
    * ``add_payload`` — once per imported statement at batch-end persist.
    * ``load_payloads_for_batch`` — once on session restore (read path).

    The BLOB is never fetched during normal display operations.
    """

    def __init__(self, db) -> None:
        super().__init__(None, db)
        self.setTable("statement_result_payload")
        self.select()

    def add_payload(self, result_id: str, pdf_result: "PdfResult") -> tuple[bool, str]:
        """Pickle *pdf_result* and persist it linked to *result_id*."""
        try:
            blob: bytes = pickle.dumps(pdf_result)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return (False, "Failed to pickle PdfResult")
        record: QSqlRecord = self.record()
        record.setValue("result_id", result_id)
        # Wrap in QByteArray so Qt stores a true BLOB rather than a string
        # representation of bytes — required for pickle.loads to work on read.
        record.setValue("payload", QByteArray(blob))
        if self.insertRecord(-1, record) and self.submitAll():
            return (True, f"Payload for {result_id} stored")
        err = self.lastError().text()
        print(
            f"ERROR: StatementResultPayloadModel.add_payload failed: {err}",
            file=sys.stderr,
        )
        return (False, err)

    def delete_payloads_for_results(self, result_ids: list[str]) -> tuple[bool, str]:
        """Delete payload rows for all *result_ids*."""
        if not result_ids:
            return (True, "Nothing to delete")
        placeholders = ", ".join(f"'{rid}'" for rid in result_ids)
        self.setFilter(f"result_id IN ({placeholders})")
        self.select()
        for row in range(self.rowCount() - 1, -1, -1):
            self.removeRow(row)
        if self.submitAll():
            self.setFilter("")
            self.select()
            return (True, f"Payloads for {len(result_ids)} result(s) deleted")
        return (False, self.lastError().text())

    def load_payloads_for_batch(self, result_ids: list[str]) -> "dict[str, PdfResult]":
        """Unpickle and return a {result_id: PdfResult} mapping for *result_ids*.

        Failed unpickle attempts are logged to stderr and skipped gracefully so
        a single corrupt/stale pickle does not abort session restore.
        """
        if not result_ids:
            return {}
        placeholders = ", ".join(f"'{rid}'" for rid in result_ids)
        self.setFilter(f"result_id IN ({placeholders})")
        self.select()
        results: dict[str, PdfResult] = {}
        for row in range(self.rowCount()):
            record: QSqlRecord = self.record(row)
            rid = str(record.value("result_id"))
            blob = record.value("payload")
            try:
                # QSqlTableModel returns BLOB columns as QByteArray; convert to
                # bytes before unpickling.  bytes() works on both QByteArray and
                # bytearray; fall back to the raw value for any unexpected type.
                # QByteArray is not recognised by pyrefly's stubs as Buffer/iterable,
                # but at runtime it is iterable over ints, so bytearray(blob) works.
                raw: bytes = (
                    bytes(bytearray(blob))  # type: ignore[call-overload]
                    if isinstance(blob, (QByteArray, bytearray))
                    else blob
                )
                obj = pickle.loads(raw)  # noqa: S301 — intentional, bsp-internal only
                results[rid] = obj
            except Exception:
                print(
                    f"WARNING: Could not unpickle payload for result_id={rid} — skipping.",
                    file=sys.stderr,
                )
                traceback.print_exc(file=sys.stderr)
        self.setFilter("")
        self.select()
        return results
