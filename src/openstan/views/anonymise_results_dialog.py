"""anonymise_results_dialog.py — Dialog showing anonymisation batch results.

Displays a scrollable table of all processed files with their original and
anonymised paths and Open buttons for each.  Used after a folder batch
anonymisation completes.
"""

from pathlib import Path
from typing import ClassVar

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QHeaderView,
    QTableWidgetItem,
    QVBoxLayout,
)

from openstan.components import (
    StanButton,
    StanDialog,
    StanLabel,
    StanTableWidget,
)


class AnonymiseResultsDialog(StanDialog):
    """Modal dialog listing anonymised files with open-in-viewer buttons.

    Parameters
    ----------
    completed:
        List of ``(input_path, output_path | None, error | None)`` tuples
        produced by ``_AnonymiseWorker``.
    parent:
        Parent widget.
    """

    _COL_STATUS: ClassVar[int] = 0
    _COL_ORIGINAL: ClassVar[int] = 1
    _COL_ANONYMISED: ClassVar[int] = 2
    _COL_OPEN_ORIG: ClassVar[int] = 3
    _COL_OPEN_ANON: ClassVar[int] = 4
    _HEADERS: ClassVar[list[str]] = [
        "Status",
        "Original File",
        "Anonymised File",
        "",
        "",
    ]

    def __init__(
        self,
        completed: list[tuple[Path, Path | None, str | None]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Anonymisation Results")
        self.setMinimumWidth(800)
        self.setMinimumHeight(400)

        self._completed = completed

        outer = QVBoxLayout()
        outer.setSpacing(12)
        outer.setContentsMargins(20, 20, 20, 20)

        # Summary label
        succeeded = sum(1 for _, out, _ in completed if out is not None)
        failed = sum(1 for _, _, err in completed if err is not None)
        summary = StanLabel(f"**{succeeded}** succeeded, **{failed}** failed")
        outer.addWidget(summary)

        # Table
        self._table = StanTableWidget(rows=len(completed), cols=5)
        self._table.setHorizontalHeaderLabels(self._HEADERS)
        header = self._table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(
                self._COL_STATUS, QHeaderView.ResizeMode.ResizeToContents
            )
            header.setSectionResizeMode(
                self._COL_ORIGINAL, QHeaderView.ResizeMode.Stretch
            )
            header.setSectionResizeMode(
                self._COL_ANONYMISED, QHeaderView.ResizeMode.Stretch
            )
            header.setSectionResizeMode(
                self._COL_OPEN_ORIG, QHeaderView.ResizeMode.ResizeToContents
            )
            header.setSectionResizeMode(
                self._COL_OPEN_ANON, QHeaderView.ResizeMode.ResizeToContents
            )

        for row, (input_path, output_path, error) in enumerate(completed):
            # Status
            if output_path is not None:
                status_item = QTableWidgetItem("✓")
                status_item.setForeground(self.palette().color(self.foregroundRole()))
            else:
                status_item = QTableWidgetItem("✗")
            status_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self._table.setItem(row, self._COL_STATUS, status_item)

            # Original file path
            self._table.setItem(
                row, self._COL_ORIGINAL, QTableWidgetItem(str(input_path))
            )

            # Anonymised file path or error
            if output_path is not None:
                self._table.setItem(
                    row, self._COL_ANONYMISED, QTableWidgetItem(str(output_path))
                )
            elif error is not None:
                err_item = QTableWidgetItem(error)
                self._table.setItem(row, self._COL_ANONYMISED, err_item)

            # Open Original button (always available)
            btn_orig = StanButton("Open Original", min_width=80)
            btn_orig.clicked.connect(
                lambda _checked, p=input_path: QDesktopServices.openUrl(
                    QUrl.fromLocalFile(str(p))
                )
            )
            self._table.setCellWidget(row, self._COL_OPEN_ORIG, btn_orig)

            # Open Anonymised button (only for successful files)
            if output_path is not None:
                btn_anon = StanButton("Open Anonymised", min_width=80)
                btn_anon.clicked.connect(
                    lambda _checked, p=output_path: QDesktopServices.openUrl(
                        QUrl.fromLocalFile(str(p))
                    )
                )
                self._table.setCellWidget(row, self._COL_OPEN_ANON, btn_anon)

        self._table.resizeRowsToContents()
        outer.addWidget(self._table, stretch=1)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.accept)
        outer.addWidget(button_box)

        self.setLayout(outer)
