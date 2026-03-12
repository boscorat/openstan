from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from openstan.models.statement_result_model import (
        FailureResultModel,
        ReviewResultModel,
        SuccessResultModel,
    )
    from openstan.views.statement_result_view import StatementResultView


class StatementResultPresenter(QObject):
    exit_results = pyqtSignal()

    def __init__(
        self,
        success_model: "SuccessResultModel",
        review_model: "ReviewResultModel",
        failure_model: "FailureResultModel",
        view: "StatementResultView",
    ) -> None:
        super().__init__()
        self.view = view
        self.success_model = success_model
        self.review_model = review_model
        self.failure_model = failure_model

        # Wire each table to its model
        self.view.success_table.setModel(self.success_model)
        self.view.review_table.setModel(self.review_model)
        self.view.failure_table.setModel(self.failure_model)

        # Refresh view whenever any model changes
        self.success_model.model_updated.connect(self.on_model_updated)
        self.review_model.model_updated.connect(self.on_model_updated)
        self.failure_model.model_updated.connect(self.on_model_updated)

        # Action buttons
        self.view.buttonAddSuccessful.clicked.connect(self.add_successful_statements)
        self.view.buttonAbandonSuccessful.clicked.connect(
            self.abandon_successful_statements
        )
        self.view.buttonDebugFailed.clicked.connect(self.debug_failed_statements)
        self.view.buttonAbandonFailed.clicked.connect(self.abandon_failed_statements)
        self.view.buttonExit.clicked.connect(self.exit_results_view)

    @pyqtSlot()
    def add_successful_statements(self) -> None:
        pass

    @pyqtSlot()
    def abandon_successful_statements(self) -> None:
        pass

    @pyqtSlot()
    def debug_failed_statements(self) -> None:
        pass

    @pyqtSlot()
    def abandon_failed_statements(self) -> None:
        pass

    @pyqtSlot()
    def exit_results_view(self) -> None:
        self.exit_results.emit()

    @pyqtSlot()
    def on_model_updated(self) -> None:
        n_success = self.success_model.row_count
        n_review = self.review_model.row_count
        n_failure = self.failure_model.row_count
        n_total = n_success + n_review + n_failure

        # Update summary and section count labels
        self.view.labelStatementsProcessed.setText(
            f"Processed: {n_total}  |  "
            f"Success: {n_success}  |  "
            f"Review: {n_review}  |  "
            f"Failed: {n_failure}"
        )
        self.view.labelSuccess.setText(f"##### SUCCESS ({n_success})")
        self.view.labelReview.setText(f"##### REVIEW ({n_review})")
        self.view.labelFailure.setText(f"##### FAILURE ({n_failure})")

        # Resize columns to content after each update
        self.view.success_table.resizeColumnsToContents()
        self.view.review_table.resizeColumnsToContents()
        self.view.failure_table.resizeColumnsToContents()

        # Reveal buttons conditionally based on available results
        self._refresh_button_visibility(n_success, n_review, n_failure)

    def _refresh_button_visibility(
        self, n_success: int, n_review: int, n_failure: int
    ) -> None:
        n_total = n_success + n_review + n_failure
        self.view.buttonAddSuccessful.setVisible(n_success > 0)
        self.view.buttonAbandonSuccessful.setVisible(n_success > 0)
        self.view.buttonDebugFailed.setVisible(n_failure > 0)
        self.view.buttonAbandonFailed.setVisible(n_failure > 0)
        self.view.buttonExit.setVisible(n_total > 0)
