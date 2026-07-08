"""debug_info_dialog.py — Modal dialog showing per-statement debug progress.

Opened by the "View Debug Info" button in the Statement Results panel.
Populated live as the background DebugWorker emits ``entry_done`` signals,
and updated on session restore from persisted ``debug_status`` / ``debug_json_path`` /
``debug_excel_path`` fields in ``statement_result``.

Each row shows:
  - Statement filename
  - Result type (REVIEW / FAILURE)
  - Debug status
  - "Open JSON" button (enabled once debug_json_path is known)
  - "Open Excel" button (enabled once debug_excel_path is known)
  - "Open PDF" button (always enabled — uses the original file_path)
  - "View Parquet" button (REVIEW rows only — opens ParquetViewDialog)
  - "Anonymise" button (enabled when project_paths is available)
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QHeaderView,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from openstan.components import StanButton, StanDialog, StanLabel, StanTableWidget

if TYPE_CHECKING:
    from bank_statement_parser import ProjectPaths

    from openstan.models.statement_result_model import ResultRow


# Column indices
_COL_FILE = 0
_COL_TYPE = 1
_COL_STATUS = 2
_COL_JSON = 3
_COL_EXCEL = 4
_COL_PDF = 5
_COL_PARQUET = 6
_COL_ANON = 7
_COL_MESSAGE = 8
_HEADERS = [
    "Statement",
    "Type",
    "Debug Status",
    "Debug JSON",
    "Debug Excel",
    "PDF",
    "Parquet",
    "Anonymise",
    "Message",
]


class DebugInfoDialog(StanDialog):
    """Modal dialog displaying the debug progress for all non-success statements.

    Can be opened while the debug worker is still running — rows update
    live via ``update_row()``.  Once all entries are resolved
    ``set_all_done()`` finalises any still-pending status labels.

    Parameters
    ----------
    rows:
        The non-success result rows to display.
    project_paths:
        Optional ``ProjectPaths`` for the active project.  When supplied,
        an "Anonymise" button is shown per row that opens the
        :class:`AnonymiseDialog` pre-loaded with that PDF.
    parent:
        Optional parent widget.
    """

    def __init__(
        self,
        rows: "list[ResultRow]",
        project_paths: "ProjectPaths | None" = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Debug Information")
        self.setMinimumWidth(900)
        self.setMinimumHeight(400)

        self._project_paths = project_paths
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
        hdr.setSectionResizeMode(_COL_EXCEL, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_PDF, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_PARQUET, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_ANON, QHeaderView.ResizeMode.ResizeToContents)
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
        debug_excel_path: Path | None = None,
    ) -> None:
        """Update the status and debug file links for a single row."""
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

        # Update Excel button
        excel_widget = self._table.cellWidget(idx, _COL_EXCEL)
        if isinstance(excel_widget, StanButton):
            if debug_excel_path is not None and debug_excel_path.exists():
                excel_widget.setEnabled(True)
                excel_widget.setProperty("_path", str(debug_excel_path))
            else:
                excel_widget.setEnabled(False)
                excel_widget.setProperty("_path", None)

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

        # Open Excel button
        excel_btn = StanButton("Open Excel", min_width=0)
        excel_btn.setEnabled(False)
        excel_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        excel_btn.setToolTip("View extracted dataframes in multi-tab Excel file")
        if row.debug_excel_path is not None and row.debug_excel_path.exists():
            excel_btn.setEnabled(True)
            excel_btn.setProperty("_path", str(row.debug_excel_path))
        excel_btn.clicked.connect(
            lambda _checked, btn=excel_btn: self.__open_file(btn.property("_path"))
        )
        self._table.setCellWidget(table_row, _COL_EXCEL, excel_btn)

        # Open PDF button
        pdf_btn = StanButton("Open PDF", min_width=0)
        pdf_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        pdf_path = str(row.file_path)
        pdf_btn.clicked.connect(lambda _checked, p=pdf_path: self.__open_file(p))
        self._table.setCellWidget(table_row, _COL_PDF, pdf_btn)

        # View Parquet button — REVIEW rows only
        parquet_btn = StanButton("View Parquet", min_width=0)
        parquet_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if row.result == "REVIEW" and row.pdf_result is not None:
            cab_path = row.pdf_result.checks_and_balances
            pq = row.pdf_result.payload
            heads_path: "Path | None" = None
            lines_path: "Path | None" = None
            from bank_statement_parser.modules.data import Review as _Review

            if isinstance(pq, _Review):
                heads_path = pq.parquet_files.statement_heads
                lines_path = pq.parquet_files.statement_lines

            files_available = all(
                p is not None and p.exists() for p in (cab_path, heads_path, lines_path)
            )
            if files_available:
                parquet_btn.clicked.connect(
                    lambda _checked, c=cab_path, h=heads_path, ln=lines_path: (
                        self.__open_parquet(c, h, ln)
                    )
                )
            else:
                parquet_btn.setEnabled(False)
                parquet_btn.setToolTip("Parquet files no longer available.")
        else:
            parquet_btn.setEnabled(False)
        self._table.setCellWidget(table_row, _COL_PARQUET, parquet_btn)

        # Anonymise button — opens AnonymiseDialog pre-loaded with this PDF
        anon_btn = StanButton("Anonymise", min_width=0)
        anon_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if self._project_paths is not None:
            file_path = row.file_path
            anon_btn.clicked.connect(
                lambda _checked, p=file_path: self.__open_anonymise(p)
            )
        else:
            anon_btn.setEnabled(False)
            anon_btn.setToolTip("No active project — cannot open Anonymise tool.")
        self._table.setCellWidget(table_row, _COL_ANON, anon_btn)

        # Message
        self._table.setItem(
            table_row, _COL_MESSAGE, QTableWidgetItem(row.message or "")
        )

    @staticmethod
    def __open_file(path: str | None) -> None:
        """Open *path* in the OS default application."""
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def __open_parquet(
        self,
        checks_and_balances: "Path | None",
        statement_heads: "Path | None",
        statement_lines: "Path | None",
    ) -> None:
        """Open the ParquetViewDialog for the three REVIEW parquet files."""
        from openstan.views.parquet_view_dialog import ParquetViewDialog

        dlg = ParquetViewDialog(
            checks_and_balances=checks_and_balances,
            statement_heads=statement_heads,
            statement_lines=statement_lines,
            parent=self,
        )
        dlg.exec()

    def __open_anonymise(self, pdf_path: Path) -> None:
        """Open the AnonymiseDialog pre-loaded with *pdf_path*."""
        from openstan.presenters.anonymise_presenter import AnonymisePresenter
        from openstan.views.anonymise_dialog import AnonymiseDialog

        if self._project_paths is None:
            return
        dlg = AnonymiseDialog(parent=self)
        _presenter = AnonymisePresenter(
            dialog=dlg,
            project_paths=self._project_paths,
            initial_pdf=pdf_path,
        )
        dlg.exec()

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
