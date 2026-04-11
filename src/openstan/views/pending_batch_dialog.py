"""pending_batch_dialog.py — Modal warning dialog shown when the latest batch
is still pending (not yet committed to project.db).

Offers the user two choices:

* **Export Last Committed Batch** — proceed with the most recent *committed*
  batch (may be ``None`` if no committed batches exist, in which case an error
  is shown by the caller instead of opening this dialog).
* **Review Pending Batch** — navigate to the results panel so the user can
  commit (or abandon) the pending import first.

The dialog result is stored in ``PendingBatchDialog.choice`` after ``exec()``
returns:

* ``PendingBatchDialog.CHOICE_EXPORT_COMMITTED`` — use the last committed batch.
* ``PendingBatchDialog.CHOICE_REVIEW_PENDING``   — navigate to results view.
* ``PendingBatchDialog.CHOICE_CANCELLED``        — dialog was dismissed.

All business logic lives in ``ExportDataPresenter`` — this module contains
only layout and widget declarations.
"""

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout

from openstan.components import (
    Qt,
    StanButton,
    StanDialog,
    StanFrame,
    StanLabel,
    StanMutedLabel,
)


class PendingBatchDialog(StanDialog):
    """Modal dialog shown when the user selects 'Latest' batch but the most
    recent batch has not yet been committed to project.db.

    After calling ``exec()``, read ``dialog.choice`` to determine which action
    the user selected.
    """

    CHOICE_EXPORT_COMMITTED: int = 0
    CHOICE_REVIEW_PENDING: int = 1
    CHOICE_CANCELLED: int = 2

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pending Batch Detected")
        self.setMinimumWidth(440)

        self.choice: int = self.CHOICE_CANCELLED

        outer = QVBoxLayout()
        outer.setSpacing(16)
        outer.setContentsMargins(20, 20, 20, 20)

        # ------------------------------------------------------------------
        # Warning section
        # ------------------------------------------------------------------
        section = StanFrame()
        layout_section = QVBoxLayout()
        layout_section.setSpacing(10)

        title = StanLabel("##### Pending Batch Detected")
        body = StanMutedLabel(
            "The most recent import batch has not been committed to the project "
            "database yet. Exporting 'Latest' now would produce an empty or "
            "incomplete file because the data has not been saved.\n\n"
            "How would you like to proceed?"
        )
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout_section.addWidget(title)
        layout_section.addWidget(body)

        # ------------------------------------------------------------------
        # Action buttons
        # ------------------------------------------------------------------
        self.button_export_committed = StanButton("Export Last Committed Batch")
        self.button_review_pending = StanButton("Review Pending Batch")

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addWidget(self.button_export_committed)
        btn_row.addWidget(self.button_review_pending)
        btn_row.addStretch()

        layout_section.addLayout(btn_row)
        section.setLayout(layout_section)

        outer.addWidget(section)
        self.setLayout(outer)

        # Wire buttons
        self.button_export_committed.clicked.connect(self._on_export_committed)
        self.button_review_pending.clicked.connect(self._on_review_pending)

    def _on_export_committed(self) -> None:
        self.choice = self.CHOICE_EXPORT_COMMITTED
        self.accept()

    def _on_review_pending(self) -> None:
        self.choice = self.CHOICE_REVIEW_PENDING
        self.accept()
