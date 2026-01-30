from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSlot

if TYPE_CHECKING:
    from openstan.models.statement_result_model import StatementResultModel
    from openstan.views.statement_result_view import StatementResultView


class StatementResultPresenter(QObject):
    def __init__(self, model: StatementResultModel, view: StatementResultView) -> None:
        super().__init__()
        self.view = view
        self.model = model
        self.view.tree.setModel(self.model)
        self.model.model_updated.connect(self.on_model_updated)

    @pyqtSlot()
    def on_model_updated(self) -> None:
        self.view.tree.reset()
        self.view.tree.resizeColumnToContents(0)
        # increase height of rows
        rows = self.model.rowCount()
        if rows < 25:
            self.view.tree.setMinimumHeight(rows * 20 + 20)  # 20 pixels per row + header
        self.view.tree.update()
        self.view.tree.repaint()
        self.view.labelStatementsProcessed.setText(
            f"Statements Processed: {self.model.total_statements_processed}  Successful: {self.model.successful_statements}  Failed: {self.model.failed_statements}"
        )
