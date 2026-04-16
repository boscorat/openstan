"""debug_info_dialog.py — Modal dialog showing per-statement debug progress.

Opened by the "View Debug Info" button in the Statement Results panel.
Populated live as the background DebugWorker emits ``entry_done`` signals,
and updated on session restore from persisted ``debug_status`` / ``debug_json_path``
fields in ``statement_result``.

Each row shows:
  - Statement filename
  - Result type (REVIEW / FAILURE)
  - Debug status
  - "Open JSON" button (enabled once debug_json_path is known)
  - "Open PDF" button (always enabled — uses the original file_path)
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QHeaderView,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from openstan.components import StanButton, StanDialog, StanLabel, StanTableWidget

if TYPE_CHECKING:
    from openstan.models.statement_result_model import ResultRow


# Column indices
_COL_FILE = 0
_COL_TYPE = 1
_COL_STATUS = 2
_COL_JSON = 3
_COL_PDF = 4
_COL_MESSAGE = 5
_HEADERS = ["Statement", "Type", "Debug Status", "Debug JSON", "PDF", "Message"]


class DebugInfoDialog(StanDialog):
    """Modal dialog displaying the debug progress for all non-success statements.

    Can be opened while the debug worker is still running — rows update
    live via ``update_row()``.  Once all entries are resolved
    ``set_all_done()`` finalises any still-pending status labels.
    """

    def __init__(self, rows: "list[ResultRow]", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Debug Information")
        self.setMinimumWidth(820)
        self.setMinimumHeight(400)

        # Map result_id → table row index for fast live updates
        self._row_index: dict[str, int] = {}

        # Table
        self._table = StanTableWidget(0, len(_HEADERS))
        self._table.setHorizontalHeaderLabels(_HEADERS)
        v_header = self._table.verticalHeader()
        assert v_header is not None
        hdr = self._table.horizontalHeader()
        assert hdr is not None
        hdr.setSectionResizeMode(_COL_FILE, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_JSON, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_PDF, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_MESSAGE, QHeaderView.ResizeMode.Stretch)

        # Populate initial rows
        for row in rows:
            self.__add_row(row)

        # Status label at the bottom (shows overall progress while running)
        self._status_label = StanLabel("")
        self._status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self._table, stretch=1)
        layout.addWidget(self._status_label)
        layout.addWidget(button_box)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Public API — called by the presenter as the worker progresses
    # ------------------------------------------------------------------

    def update_row(
        self,
        result_id: str,
        status: str,
        debug_json_path: Path | None,
    ) -> None:
        """Update the status and JSON link for a single row."""
        idx = self._row_index.get(result_id)
        if idx is None:
            return

        # Update status cell
        status_item = self._table.item(idx, _COL_STATUS)
        if status_item is not None:
            status_item.setText(status)

        # Update JSON button
        json_widget = self._table.cellWidget(idx, _COL_JSON)
        if isinstance(json_widget, StanButton):
            if debug_json_path is not None and debug_json_path.exists():
                json_widget.setEnabled(True)
                json_widget.setProperty("_path", str(debug_json_path))
            else:
                json_widget.setEnabled(False)
                json_widget.setProperty("_path", None)

        self.__update_status_label()

    def set_all_done(self) -> None:
        """Mark any still-pending rows as 'unavailable' (debug did not run)."""
        for _, idx in self._row_index.items():
            item = self._table.item(idx, _COL_STATUS)
            if item is not None and item.text() in ("pending", "running", ""):
                item.setText("unavailable")
        self._status_label.setText("Debug complete.")

    def update_progress_label(self, done: int, total: int) -> None:
        """Update the bottom status label with running counts."""
        self._status_label.setText(f"Generating debug files… {done} / {total}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def __add_row(self, row: "ResultRow") -> None:
        table_row = self._table.rowCount()
        self._table.insertRow(table_row)
        self._row_index[row.result_id] = table_row

        # File name
        self._table.setItem(table_row, _COL_FILE, QTableWidgetItem(row.file_path.name))

        # Result type
        self._table.setItem(table_row, _COL_TYPE, QTableWidgetItem(row.result))

        # Debug status — show persisted value or 'pending'
        status_text = row.debug_status or "pending"
        self._table.setItem(table_row, _COL_STATUS, QTableWidgetItem(status_text))

        # Open JSON button
        json_btn = StanButton("Open JSON", min_width=0)
        json_btn.setEnabled(False)
        json_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if row.debug_json_path is not None and row.debug_json_path.exists():
            json_btn.setEnabled(True)
            json_btn.setProperty("_path", str(row.debug_json_path))
        json_btn.clicked.connect(
            lambda _checked, btn=json_btn: self.__open_file(btn.property("_path"))
        )
        self._table.setCellWidget(table_row, _COL_JSON, json_btn)

        # Open PDF button
        pdf_btn = StanButton("Open PDF", min_width=0)
        pdf_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        pdf_path = str(row.file_path)
        pdf_btn.clicked.connect(lambda _checked, p=pdf_path: self.__open_file(p))
        self._table.setCellWidget(table_row, _COL_PDF, pdf_btn)

        # Message
        self._table.setItem(
            table_row, _COL_MESSAGE, QTableWidgetItem(row.message or "")
        )

    @staticmethod
    def __open_file(path: str | None) -> None:
        """Open *path* in the OS default application."""
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def __update_status_label(self) -> None:
        total = self._table.rowCount()
        done = sum(
            1
            for i in range(total)
            if (item := self._table.item(i, _COL_STATUS)) is not None
            and item.text() in ("done", "error", "unavailable")
        )
        if done < total:
            self._status_label.setText(f"Generating debug files… {done} / {total}")
        else:
            self._status_label.setText("Debug complete.")
