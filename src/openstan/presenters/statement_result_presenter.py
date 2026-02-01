from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from openstan.models.statement_result_model import StatementResultModel
    from openstan.views.statement_result_view import StatementResultView


class StatementResultPresenter(QObject):
    exit_results = pyqtSignal()

    def __init__(self, model: StatementResultModel, view: StatementResultView) -> None:
        super().__init__()
        self.view = view
        self.model = model
        self.view.tree.setModel(self.model)
        self.model.model_updated.connect(self.on_model_updated)

        # signals
        self.view.buttonAddFailed.clicked.connect(self.add_failed_statements)
        self.view.buttonAddSuccessful.clicked.connect(self.add_successful_statements)
        self.view.buttonAbandonFailed.clicked.connect(self.abandon_failed_statements)
        self.view.buttonAbandonSuccessful.clicked.connect(self.abandon_successful_statements)
        self.view.buttonDebugFailed.clicked.connect(self.debug_failed_statements)
        self.view.buttonExit.clicked.connect(self.exit_results_view)

    @pyqtSlot()
    def add_failed_statements(self) -> None:
        pass

    @pyqtSlot()
    def add_successful_statements(self) -> None:
        pass

    @pyqtSlot()
    def abandon_failed_statements(self) -> None:
        pass

    @pyqtSlot()
    def abandon_successful_statements(self) -> None:
        self.model.statements = [stmt for stmt in self.model.statements if stmt.success]
        self.model.on_statements_updated()

    @pyqtSlot()
    def debug_failed_statements(self) -> None:
        pass

    @pyqtSlot()
    def exit_results_view(self) -> None:
        self.exit_results.emit()

    @pyqtSlot()
    def on_model_updated(self) -> None:
        self.view.tree.resizeColumnToContents(0)
        self.view.labelStatementsProcessed.setText(
            f"Statements Processed: {self.model.total_statements_processed}  Successful: {self.model.successful_statements}  Failed: {self.model.failed_statements}"
        )

    def show_buttons_based_on_results(self) -> None:
        if self.model.total_statements_processed > 0:
            if self.model.failed_statements > 0:
                self.view.buttonAddFailed.setVisible(True)
                self.view.buttonAbandonFailed.setVisible(True)
                self.view.buttonDebugFailed.setVisible(True)
            else:
                self.view.buttonAddFailed.setVisible(False)
                self.view.buttonAbandonFailed.setVisible(False)
                self.view.buttonDebugFailed.setVisible(False)
            if self.model.successful_statements > 0:
                self.view.buttonAddSuccessful.setVisible(True)
                self.view.buttonAbandonSuccessful.setVisible(True)
            else:
                self.view.buttonAddSuccessful.setVisible(False)
                self.view.buttonAbandonSuccessful.setVisible(False)
        else:
            self.view.buttonAddFailed.setVisible(False)
            self.view.buttonAbandonFailed.setVisible(False)
            self.view.buttonDebugFailed.setVisible(False)
            self.view.buttonAddSuccessful.setVisible(False)
            self.view.buttonAbandonSuccessful.setVisible(False)
            self.view.buttonExit.setVisible(True)
