from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel

from openstan.components import StanPolarsModel


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

    def add_statement(self, stmt):
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
            item_movement = QStandardItem(str(row[17]))
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
