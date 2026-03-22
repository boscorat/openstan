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

* ``StatementResultModel``        — display columns only (no payload).
* ``StatementResultPayloadModel`` — single TEXT column (JSON of ``PdfResult``).

On session restore (project switch / app restart with a locked batch) the DB layer
is read back and the in-memory models are repopulated so the results view can be
shown without re-running the import.
"""

import dataclasses
import json
import sys
import traceback
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtSql import QSqlQuery, QSqlRecord, QSqlTableModel

if TYPE_CHECKING:
    from bank_statement_parser import PdfResult


# ---------------------------------------------------------------------------
# JSON serialisation helpers for PdfResult
# ---------------------------------------------------------------------------


def _pdf_result_to_json(pdf_result: "PdfResult") -> str:
    """Serialise a ``PdfResult`` to a JSON string.

    All non-JSON-native leaf types are converted to strings:
    * ``pathlib.Path``    → POSIX string
    * ``decimal.Decimal`` → string (preserves exact precision)
    * ``datetime.date``   → ISO-8601 string (``YYYY-MM-DD``)

    A ``_type`` discriminator key (``"Success"``, ``"Review"``, or
    ``"Failure"``) is embedded in the ``payload`` dict so that
    ``_json_to_pdf_result`` can reconstruct the correct concrete class.
    """

    def _convert(obj: Any) -> Any:
        if isinstance(obj, Path):
            return obj.as_posix()
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, date):
            return obj.isoformat()
        raise TypeError(
            f"Object of type {type(obj).__name__!r} is not JSON serialisable"
        )

    raw: dict[str, Any] = dataclasses.asdict(pdf_result)
    # Embed a discriminator so the deserialiser knows the payload type.
    raw["payload"]["_type"] = type(pdf_result.payload).__name__
    return json.dumps(raw, default=_convert)


def _json_to_pdf_result(text: str) -> "PdfResult":
    """Deserialise a JSON string produced by ``_pdf_result_to_json`` back to
    a ``PdfResult`` instance.

    Raises ``ValueError`` if the JSON is missing required keys or contains an
    unrecognised ``_type`` discriminator.  Any such error aborts the call so
    the caller can skip the corrupt row gracefully.
    """
    from bank_statement_parser import PdfResult
    from bank_statement_parser.modules.data import (
        Failure,
        ParquetFiles,
        Review,
        StatementInfo,
        Success,
    )

    data: dict[str, Any] = json.loads(text)

    def _path_or_none(value: str | None) -> Path | None:
        return Path(value) if value is not None else None

    # Reconstruct StatementInfo (shared by Success and Review payloads).
    def _statement_info(d: dict[str, Any]) -> StatementInfo:
        return StatementInfo(
            id_statement=d["id_statement"],
            id_account=d["id_account"],
            account=d["account"],
            statement_date=date.fromisoformat(d["statement_date"]),
            payments_in=Decimal(d["payments_in"]),
            payments_out=Decimal(d["payments_out"]),
            opening_balance=Decimal(d["opening_balance"]),
            closing_balance=Decimal(d["closing_balance"]),
            filename_new=d["filename_new"],
        )

    # Reconstruct ParquetFiles (shared by Success and Review payloads).
    def _parquet_files(d: dict[str, Any]) -> ParquetFiles:
        return ParquetFiles(
            statement_heads=_path_or_none(d["statement_heads"]),
            statement_lines=_path_or_none(d["statement_lines"]),
        )

    payload_data = data["payload"]
    discriminator: str = payload_data["_type"]

    if discriminator == "Success":
        payload: Success | Review | Failure = Success(
            statement_info=_statement_info(payload_data["statement_info"]),
            parquet_files=_parquet_files(payload_data["parquet_files"]),
        )
    elif discriminator == "Review":
        payload = Review(
            statement_info=_statement_info(payload_data["statement_info"]),
            parquet_files=_parquet_files(payload_data["parquet_files"]),
            message=payload_data["message"],
            message_detail=payload_data.get("message_detail", ""),
        )
    elif discriminator == "Failure":
        payload = Failure(
            message=payload_data["message"],
            error_type=payload_data["error_type"],
            message_detail=payload_data.get("message_detail", ""),
        )
    else:
        raise ValueError(f"Unknown PdfResult payload type: {discriminator!r}")

    return PdfResult(
        result=data["result"],
        outcome=data["outcome"],
        batch_lines=Path(data["batch_lines"]),
        checks_and_balances=_path_or_none(data["checks_and_balances"]),
        payload=payload,
    )


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
    debug_json_path: Path | None = field(default=None)
    debug_status: str | None = field(default=None)
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
    COL_DEBUG_JSON_PATH = 12
    COL_DEBUG_STATUS = 13
    COL_DELETED = 14
    COL_CREATED = 15

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
        record.setValue("debug_json_path", None)
        record.setValue("debug_status", None)
        record.setValue("deleted", 0)
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

    def update_debug_info(
        self,
        result_id: str,
        status: str,
        debug_json_path: Path | None,
    ) -> tuple[bool, str]:
        """Update debug_status and debug_json_path for a single result row."""
        query = QSqlQuery(self.database())
        query.prepare(
            "UPDATE statement_result "
            "SET debug_status = :status, debug_json_path = :path "
            "WHERE result_id = :result_id"
        )
        query.bindValue(":status", status)
        query.bindValue(":path", str(debug_json_path) if debug_json_path else None)
        query.bindValue(":result_id", result_id)
        if query.exec():
            self.select()
            return (True, "")
        return (False, query.lastError().text())

    def soft_delete_batch(self, batch_id: str) -> tuple[bool, str]:
        """Mark all result rows for *batch_id* as deleted=1 (soft delete).

        Called after a successful commit so the results panel clears
        immediately while the debug worker may still be writing files.
        """
        query = QSqlQuery(self.database())
        query.prepare(
            "UPDATE statement_result SET deleted = 1 WHERE batch_id = :batch_id"
        )
        query.bindValue(":batch_id", batch_id)
        if query.exec():
            self.select()
            return (True, "")
        return (False, query.lastError().text())

    def hard_delete_soft_deleted(self, batch_id: str) -> tuple[bool, str]:
        """Permanently delete all soft-deleted rows for *batch_id*.

        Called once the debug worker finishes (or is confirmed cancelled)
        after a commit, so no orphan rows remain in gui.db.
        """
        query = QSqlQuery(self.database())
        query.prepare(
            "DELETE FROM statement_result WHERE batch_id = :batch_id AND deleted = 1"
        )
        query.bindValue(":batch_id", batch_id)
        if query.exec():
            self.select()
            return (True, "")
        return (False, query.lastError().text())

    def delete_results_for_batch(self, batch_id: str) -> tuple[bool, str]:
        """Hard-delete all non-soft-deleted result rows for *batch_id*.

        Used by the abandon path.  Soft-deleted rows (deleted=1) are left
        for ``hard_delete_soft_deleted`` to clean up after the debug worker.
        """
        self.setFilter(f"batch_id = '{batch_id}' AND deleted = 0")
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
        """Return all live (not soft-deleted) result rows for *batch_id*.

        ``pdf_result`` is left as ``None`` — payloads are not needed for
        display on session restore.
        """
        self.setFilter(f"batch_id = '{batch_id}' AND deleted = 0")
        self.select()
        rows: list[ResultRow] = []
        for i in range(self.rowCount()):
            rec = self.record(i)
            pin = rec.value("payments_in")
            pout = rec.value("payments_out")
            djp = rec.value("debug_json_path")
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
                    debug_json_path=Path(str(djp)) if djp else None,
                    debug_status=rec.value("debug_status") or None,
                )
            )
        self.setFilter("")
        self.select()
        return rows

    def get_result_ids_for_batch(self, batch_id: str) -> list[str]:
        """Return result_id values for all live rows in *batch_id*."""
        self.setFilter(f"batch_id = '{batch_id}' AND deleted = 0")
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
    """Persistence model for JSON-serialised PdfResult payloads.

    Only touched during:
    * ``add_payload`` — once per imported statement at batch-end persist.
    * ``load_payloads_for_batch`` — once on session restore (read path).

    The TEXT payload is never fetched during normal display operations.
    """

    def __init__(self, db) -> None:
        super().__init__(None, db)
        self.setTable("statement_result_payload")
        self.select()

    def add_payload(self, result_id: str, pdf_result: "PdfResult") -> tuple[bool, str]:
        """Serialise *pdf_result* to JSON and persist it linked to *result_id*."""
        try:
            text: str = _pdf_result_to_json(pdf_result)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return (False, "Failed to serialise PdfResult to JSON")
        record: QSqlRecord = self.record()
        record.setValue("result_id", result_id)
        record.setValue("payload", text)
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
        """Deserialise JSON and return a {result_id: PdfResult} mapping for *result_ids*.

        Failed deserialisation attempts are logged to stderr and skipped
        gracefully so a single corrupt row does not abort session restore.
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
            text = record.value("payload")
            try:
                obj = _json_to_pdf_result(str(text))
                results[rid] = obj
            except Exception:
                print(
                    f"WARNING: Could not deserialise payload for result_id={rid} — skipping.",
                    file=sys.stderr,
                )
                traceback.print_exc(file=sys.stderr)
        self.setFilter("")
        self.select()
        return results
