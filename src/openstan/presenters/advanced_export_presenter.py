"""advanced_export_presenter.py — Presenter for the Advanced Export pane.

Wires the ``AdvancedExportView`` to BSP's ``export_spec`` function
(``bank_statement_parser.modules.export_spec.export_spec``).
On project load this presenter:

1. Queries ``DimAccount`` and ``DimStatement`` from the project datamart
   (via BSP Polars API) on a background thread to populate the account and
   statement combo boxes.
2. Scans ``<project>/config/export/*.toml`` to build the spec button list.

Clicking a spec button runs ``export_spec`` off the GUI thread via
``ExportWorker``.  On success the output folder is opened in the system
file manager; on failure a modal error dialog is shown.

The project path is pushed in by ``StanPresenter`` via ``load_project()``.
"""

import tomllib
import traceback
from datetime import date
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

import bank_statement_parser as bsp
import polars as pl
from bank_statement_parser.modules.export_spec import export_spec as bsp_export_spec
from PyQt6.QtCore import QObject, QRunnable, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from openstan.components import StanErrorMessage
from openstan.presenters.workers import ExportWorker
from openstan.views.advanced_export_view import make_spec_button

if TYPE_CHECKING:
    from PyQt6.QtCore import QThreadPool

    from openstan.views.advanced_export_view import AdvancedExportView


# ---------------------------------------------------------------------------
# Background worker: load account/statement data from datamart
# ---------------------------------------------------------------------------


class _DatamartLoadSignals(QObject):
    """Signals emitted by ``_DatamartLoadWorker``."""

    finished = pyqtSignal(
        object, object
    )  # (accounts_df, statements_df) as pl.DataFrame
    error = pyqtSignal(str)


class _DatamartLoadWorker(QRunnable):
    """Queries DimAccount and DimStatement from project.db off the GUI thread.

    Emits ``finished(accounts_df, statements_df)`` on success or
    ``error(traceback_str)`` on failure (e.g. project.db not yet built).
    """

    def __init__(self, project_path: Path) -> None:
        super().__init__()
        self._project_path = project_path
        self.signals = _DatamartLoadSignals()

    def run(self) -> None:  # noqa: N802
        try:
            accounts_df: pl.DataFrame = (
                bsp.db.DimAccount(self._project_path)
                .all.select(
                    [
                        "id_account",
                        "account_int",
                        "account_number",
                        "account_holder",
                        "account_type",
                    ]
                )
                .collect()
            )
            statements_df: pl.DataFrame = (
                bsp.db.DimStatement(self._project_path)
                .all.select(
                    [
                        "id_statement",
                        "statement_int",
                        "id_account",
                        "account_int",
                        "statement_date",
                        "filename",
                    ]
                )
                .collect()
            )
            self.signals.finished.emit(accounts_df, statements_df)
        except Exception:
            self.signals.error.emit(traceback.format_exc())


# ---------------------------------------------------------------------------
# Presenter
# ---------------------------------------------------------------------------


class AdvancedExportPresenter(QObject):
    """Presenter for the Advanced Export pane.

    Receives the view and a ``QThreadPool`` at construction time.  The
    active project is loaded by calling ``load_project(project_path)``
    from ``StanPresenter`` whenever the project selection changes.
    """

    def __init__(
        self,
        view: "AdvancedExportView",
        threadpool: "QThreadPool",
    ) -> None:
        super().__init__()
        self.view: "AdvancedExportView" = view
        self.threadpool: "QThreadPool" = threadpool

        self.project_path: Path | None = None

        # Full statements DataFrame cached after load so the account combo
        # can filter it without another DB query.
        self._all_statements: pl.DataFrame | None = None

        # Error dialog — parented to the view so it is modal to the window.
        self._error_dialog = StanErrorMessage(view)

        # ── Signal wiring ──────────────────────────────────────────────────
        self.view.combo_account.currentIndexChanged.connect(self._on_account_changed)

    # ---------------------------------------------------------------------------
    # Public API — called by StanPresenter
    # ---------------------------------------------------------------------------

    def load_project(self, project_path: Path) -> None:
        """Load account/statement data and spec buttons for ``project_path``.

        Clears the current UI state, then dispatches a background worker to
        query the datamart.  Spec buttons are rebuilt immediately (they only
        require a filesystem scan, not a DB query).
        """
        self.project_path = project_path
        self._all_statements = None

        # Clear combo boxes while loading
        self.view.combo_account.blockSignals(True)
        self.view.combo_account.clear()
        self.view.combo_statement.clear()
        self.view.combo_account.addItem("Loading…")
        self.view.combo_account.blockSignals(False)

        # Rebuild spec buttons immediately (filesystem scan only)
        self._rebuild_spec_buttons()

        # Load account/statement data in background
        worker = _DatamartLoadWorker(project_path)
        worker.signals.finished.connect(self._on_datamart_loaded)
        worker.signals.error.connect(self._on_datamart_error)
        self.threadpool.start(worker)

    # ---------------------------------------------------------------------------
    # Datamart load callbacks
    # ---------------------------------------------------------------------------

    @pyqtSlot(object, object)
    def _on_datamart_loaded(
        self, accounts_df: pl.DataFrame, statements_df: pl.DataFrame
    ) -> None:
        """Populate combos once the background datamart query completes."""
        self._all_statements = statements_df

        # ── Account combo ──────────────────────────────────────────────────
        self.view.combo_account.blockSignals(True)
        self.view.combo_account.clear()
        self.view.combo_account.addItem("<all accounts>", userData=None)

        for row in accounts_df.iter_rows(named=True):
            label = f"{row['account_holder']} \u2014 {row['account_type']} ({row['account_number']})"
            self.view.combo_account.addItem(label, userData=row["id_account"])

        self.view.combo_account.blockSignals(False)

        # Trigger statement filtering for the initial selection
        self._on_account_changed(self.view.combo_account.currentIndex())

    @pyqtSlot(str)
    def _on_datamart_error(self, message: str) -> None:
        """Handle a failed datamart query (e.g. project.db not yet built)."""
        self.view.combo_account.blockSignals(True)
        self.view.combo_account.clear()
        self.view.combo_account.addItem("(no data)")
        self.view.combo_account.blockSignals(False)
        self.view.combo_statement.clear()
        self.view.combo_statement.addItem("(no data)")
        print(f"AdvancedExportPresenter: datamart load error:\n{message}", flush=True)

    # ---------------------------------------------------------------------------
    # Account combo change → filter statement combo
    # ---------------------------------------------------------------------------

    @pyqtSlot(int)
    def _on_account_changed(self, index: int) -> None:
        """Re-populate the statement combo filtered to the selected account."""
        self.view.combo_statement.clear()
        self.view.combo_statement.addItem("(all statements)", userData=None)

        if self._all_statements is None or index < 0:
            return

        account_key: str | None = self.view.combo_account.itemData(index)
        if account_key is None:
            # "<all accounts>" selected — show all statements
            filtered = self._all_statements
        else:
            filtered = self._all_statements.filter(pl.col("id_account") == account_key)

        for row in filtered.sort("statement_date", descending=True).iter_rows(
            named=True
        ):
            label = f"{row['statement_date']}  —  {row['filename']}"
            self.view.combo_statement.addItem(label, userData=row["id_statement"])

    # ---------------------------------------------------------------------------
    # Spec button list
    # ---------------------------------------------------------------------------

    def _rebuild_spec_buttons(self) -> None:
        """Scan the project's export spec directory and rebuild the button list."""
        layout: QVBoxLayout = self.view.spec_list_widget.layout()  # type: ignore[assignment]

        # Remove all existing buttons
        for i in range(layout.count() - 1, -1, -1):
            item = layout.takeAt(i)
            if item is not None:
                widget: QWidget | None = item.widget()
                if widget is not None:
                    widget.deleteLater()

        if self.project_path is None:
            self._show_no_specs("No project loaded.")
            return

        spec_dir = self.project_path / "config" / "export"
        if not spec_dir.is_dir():
            self._show_no_specs(
                f"Spec directory not found: {spec_dir}\nAdd .toml spec files to <project>/config/export/ to see them here."
            )
            return

        toml_files = sorted(spec_dir.glob("*.toml"))
        if not toml_files:
            self._show_no_specs(
                "No .toml spec files found in <project>/config/export/."
            )
            return

        for spec_path in toml_files:
            description = self._read_spec_description(spec_path)
            btn = make_spec_button(spec_path.name, description)
            btn.clicked.connect(partial(self._on_spec_clicked, spec_path))
            layout.addWidget(btn)

        self.view.label_no_specs.setVisible(False)
        self.view.scroll_area.setVisible(True)

    def _show_no_specs(self, message: str) -> None:
        """Show the empty-state label with a given message."""
        self.view.scroll_area.setVisible(False)
        self.view.label_no_specs.setText(message)
        self.view.label_no_specs.setVisible(True)

    @staticmethod
    def _read_spec_description(spec_path: Path) -> str:
        """Return the ``[meta]description`` from a TOML spec file.

        Falls back to an empty string if the file cannot be read or parsed.
        """
        try:
            with spec_path.open("rb") as fh:
                data = tomllib.load(fh)
            return str(data.get("meta", {}).get("description", ""))
        except Exception:
            return ""

    # ---------------------------------------------------------------------------
    # Spec button click → export
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def _on_spec_clicked(self, spec_path: Path) -> None:
        """Run ``export_spec`` for the selected spec file."""
        if self.project_path is None:
            self._error_dialog.showMessage(
                "No project is currently selected. Please select a project before exporting."
            )
            return

        params = self._read_params()

        project_path = self.project_path
        output_folder = project_path / "export" / spec_path.stem

        worker = ExportWorker(
            fn=lambda: bsp_export_spec(
                spec_path,
                account_key=params["account_key"],
                project_path=project_path,
                date_from=params["date_from"],
                date_to=params["date_to"],
                statement_key=params["statement_key"],
            ),
            description=f"spec '{spec_path.stem}'",
            output_folder=output_folder,
        )
        self._start_export(worker)

    # ---------------------------------------------------------------------------
    # Parameter reading
    # ---------------------------------------------------------------------------

    def _read_params(self) -> dict:
        """Read the current parameter widget values.

        Returns a dict with keys ``account_key``, ``statement_key``,
        ``date_from``, and ``date_to``.  Optional values are ``None`` when
        not set.
        """
        v = self.view

        # Account key — None means "<all accounts>"
        account_key: str | None = v.combo_account.currentData()

        # Statement key — None means "(all statements)"
        statement_key: str | None = v.combo_statement.currentData()

        # Date from
        date_from: date | None = None
        if not v.check_date_from_none.isChecked():
            qdate = v.date_from.date()
            date_from = date(qdate.year(), qdate.month(), qdate.day())

        # Date to
        date_to: date | None = None
        if not v.check_date_to_none.isChecked():
            qdate = v.date_to.date()
            date_to = date(qdate.year(), qdate.month(), qdate.day())

        return {
            "account_key": account_key,
            "statement_key": statement_key,
            "date_from": date_from,
            "date_to": date_to,
        }

    # ---------------------------------------------------------------------------
    # Export lifecycle helpers
    # ---------------------------------------------------------------------------

    def _start_export(self, worker: ExportWorker) -> None:
        """Show progress bar, disable spec buttons, and dispatch the worker."""
        self._set_spec_buttons_enabled(False)
        self.view.label_status.setText("")
        self.view.progress_bar.setVisible(True)
        worker.signals.finished.connect(self._on_export_finished)
        worker.signals.error.connect(self._on_export_error)
        self.threadpool.start(worker)

    def _set_spec_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable all spec buttons in the scroll list."""
        layout: QVBoxLayout = self.view.spec_list_widget.layout()  # type: ignore[assignment]
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is not None:
                widget: QWidget | None = item.widget()
                if widget is not None:
                    widget.setEnabled(enabled)

    @pyqtSlot(str, str)
    def _on_export_finished(self, description: str, output_folder: str) -> None:
        self.view.progress_bar.setVisible(False)
        self._set_spec_buttons_enabled(True)
        self.view.label_status.setText(
            f"###### Exported {description} to `{output_folder}`"
        )
        QDesktopServices.openUrl(QUrl.fromLocalFile(output_folder))

    @pyqtSlot(str)
    def _on_export_error(self, message: str) -> None:
        self.view.progress_bar.setVisible(False)
        self._set_spec_buttons_enabled(True)
        self.view.label_status.setText("")
        print(f"AdvancedExportPresenter: export error:\n{message}", flush=True)
        self._error_dialog.showMessage(f"Export failed:\n\n{message}")
