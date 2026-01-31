from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel

from openstan.components import StanPolarsModel

if TYPE_CHECKING:
    from bank_statement_parser.modules.classes import statements


class ChecksAndBalancesModel(StanPolarsModel):
    def __init__(self, stmt):
        super().__init__(stmt.checks_and_balances)


class HeaderModel(StanPolarsModel):
    def __init__(self, stmt):
        super().__init__(stmt.header_results.collect())


class LinesModel(StanPolarsModel):
    def __init__(self, stmt):
        super().__init__(stmt.lines_results.collect())


class StatementResultModel(QStandardItemModel):
    model_updated = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setHorizontalHeaderLabels(["", "In", "Out", "Movement", "Success?"])
        self.invisibleRootItem()
        self.statements: list[statements.Statement] = []
        self.total_statements_processed = 0
        self.successful_statements = 0
        self.failed_statements = 0

    def on_statements_updated(self) -> None:
        self.clear()
        self.setHorizontalHeaderLabels(["", "In", "Out", "Movement", "Success?"])
        self.invisibleRootItem()
        self.total_statements_processed = 0
        self.successful_statements = 0
        self.failed_statements = 0
        for stmt in self.statements:
            self.add_statement(stmt)
        self.model_updated.emit()

    def add_statement(self, stmt: statements.Statement) -> None:
        self.statements.append(stmt)
        self.total_statements_processed += 1
        if stmt.success:
            self.successful_statements += 1
        else:
            self.failed_statements += 1
        self.cab = ChecksAndBalancesModel(stmt)
        self.header = HeaderModel(stmt)
        self.lines = LinesModel(stmt)

        stmt_name: QStandardItem = QStandardItem(
            str(stmt.ID_ACCOUNT) + " " + str(self.header.df["STD_STATEMENT_DATE"][0]) if self.header.df.height > 0 else "Unknown Statement"
        )
        stmt_in: QStandardItem = (
            QStandardItem(str(self.cab.df["STD_PAYMENTS_IN"][0])) if self.header.df.height > 0 else QStandardItem("Unknown Statement")
        )
        stmt_out: QStandardItem = (
            QStandardItem(str(self.cab.df["STD_PAYMENTS_OUT"][0])) if self.header.df.height > 0 else QStandardItem("Unknown Statement")
        )
        stmt_movement: QStandardItem = (
            QStandardItem(str(self.cab.df["STD_MOVEMENT"][0])) if self.header.df.height > 0 else QStandardItem("Unknown Statement")
        )
        stmt_success: QStandardItem = QStandardItem(str(stmt.success)) if self.header.df.height > 0 else QStandardItem("False")

        for row in self.lines.df.iter_rows():
            item_name = QStandardItem(str(row[9]) + " " + str(row[11]))
            item_in = QStandardItem(str(row[12]))
            item_out = QStandardItem(str(row[13]))
            try:
                item_movement = QStandardItem(str(row[17]))
            except IndexError:
                item_movement = QStandardItem("")
            item_success = QStandardItem("")
            stmt_name.appendRow(
                [
                    item_name,
                    item_in,
                    item_out,
                    item_movement,
                    item_success,
                ]
            )
        self.appendRow(
            [
                stmt_name,
                stmt_in,
                stmt_out,
                stmt_movement,
                stmt_success,
            ]
        )
        self.model_updated.emit()
