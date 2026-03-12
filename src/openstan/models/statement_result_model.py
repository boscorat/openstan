from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel

if TYPE_CHECKING:
    from bank_statement_parser import PdfResult


class SuccessResultModel(QStandardItemModel):
    """Flat table model for successfully imported statements.

    Columns: Filename | Account | Date | Payments In | Payments Out
    """

    model_updated = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setHorizontalHeaderLabels(
            ["Filename", "Account", "Date", "Payments In", "Payments Out"]
        )

    @property
    def row_count(self) -> int:
        return self.rowCount()

    def add_statement(self, file_path: Path, stmt: "PdfResult") -> None:
        from bank_statement_parser import Success

        info = stmt.payload
        if not isinstance(info, Success):
            return
        si = info.statement_info
        self.appendRow(
            [
                QStandardItem(file_path.stem),
                QStandardItem(si.id_account),
                QStandardItem(str(si.statement_date)),
                QStandardItem(str(si.payments_in)),
                QStandardItem(str(si.payments_out)),
            ]
        )
        self.model_updated.emit()

    def clear_records(self) -> None:
        self.removeRows(0, self.rowCount())
        self.model_updated.emit()


class ReviewResultModel(QStandardItemModel):
    """Flat table model for statements that require review (CAB failure).

    Columns: Filename | Account | Date | CAB Message
    """

    model_updated = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setHorizontalHeaderLabels(["Filename", "Account", "Date", "CAB Message"])

    @property
    def row_count(self) -> int:
        return self.rowCount()

    def add_statement(self, file_path: Path, stmt: "PdfResult") -> None:
        from bank_statement_parser import Review

        info = stmt.payload
        if not isinstance(info, Review):
            return
        si = info.statement_info
        self.appendRow(
            [
                QStandardItem(file_path.stem),
                QStandardItem(si.id_account),
                QStandardItem(str(si.statement_date)),
                QStandardItem(info.message),
            ]
        )
        self.model_updated.emit()

    def clear_records(self) -> None:
        self.removeRows(0, self.rowCount())
        self.model_updated.emit()


class FailureResultModel(QStandardItemModel):
    """Flat table model for statements that failed to import.

    Columns: Filename | Error Type | Message
    """

    model_updated = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setHorizontalHeaderLabels(["Filename", "Error Type", "Message"])

    @property
    def row_count(self) -> int:
        return self.rowCount()

    def add_statement(self, file_path: Path, stmt: "PdfResult") -> None:
        from bank_statement_parser import Failure

        info = stmt.payload
        if not isinstance(info, Failure):
            return
        self.appendRow(
            [
                QStandardItem(file_path.stem),
                QStandardItem(info.error_type),
                QStandardItem(info.message),
            ]
        )
        self.model_updated.emit()

    def clear_records(self) -> None:
        self.removeRows(0, self.rowCount())
        self.model_updated.emit()
