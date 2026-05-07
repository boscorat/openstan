"""anonymise_presenter.py — Presenter for the AnonymiseDialog.

Owns all logic for the anonymisation workflow:
  - loading and saving ``anonymise.toml``
  - browsing for a source PDF
  - running ``bsp.anonymise_pdf`` in a background worker
  - opening the original / anonymised PDFs via the OS viewer
"""

import shutil
import tomllib
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

import bank_statement_parser as bsp
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog

from openstan.components import StanErrorMessage

if TYPE_CHECKING:
    from bank_statement_parser import ProjectPaths

    from openstan.views.anonymise_dialog import AnonymiseDialog


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


class _AnonymiseSignals(QObject):
    """Signals emitted by the background anonymisation worker."""

    started: pyqtSignal = pyqtSignal()
    finished: pyqtSignal = pyqtSignal(Path)  # output path
    error: pyqtSignal = pyqtSignal(str)


class _AnonymiseWorker(QRunnable):
    """Runs ``bsp.anonymise_pdf`` on a thread-pool thread."""

    def __init__(self, input_path: Path, config_path: Path) -> None:
        super().__init__()
        self.signals = _AnonymiseSignals()
        self._input = input_path
        self._config = config_path

    def run(self) -> None:  # noqa: N802  (Qt override)
        try:
            out = bsp.anonymise_pdf(self._input, config_path=self._config)
            self.signals.finished.emit(out)
        except Exception as exc:
            self.signals.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Presenter
# ---------------------------------------------------------------------------


class AnonymisePresenter(QObject):
    """Presenter for ``AnonymiseDialog``.

    Parameters
    ----------
    dialog:
        The view this presenter manages.
    project_paths:
        ``ProjectPaths`` for the active project — used to locate
        ``config/user/anonymise.toml``.
    initial_pdf:
        Optional pre-selected PDF path (e.g. passed in from the debug screen).
    """

    def __init__(
        self,
        dialog: "AnonymiseDialog",
        project_paths: "ProjectPaths",
        initial_pdf: Path | None = None,
    ) -> None:
        super().__init__()
        self.dialog = dialog
        self._project_paths = project_paths
        self._toml_path: Path = (
            Path(str(project_paths.root)) / "config" / "user" / "anonymise.toml"
        )
        self._input_path: Path | None = initial_pdf
        self._output_path: Path | None = None

        # Wire buttons
        self.dialog.button_browse.clicked.connect(self._browse_pdf)
        self.dialog.button_save_toml.clicked.connect(self._save_toml)
        self.dialog.button_run.clicked.connect(self._run_anonymisation)
        self.dialog.button_open_original.clicked.connect(self._open_original)
        self.dialog.button_open_anonymised.clicked.connect(self._open_anonymised)

        # Populate TOML path label and editor
        self.dialog.label_toml_path.setText(f"`{self._toml_path}`")
        self._load_toml()

        # Pre-populate PDF path if supplied
        if initial_pdf is not None:
            self._set_input_path(initial_pdf)

    # ---------------------------------------------------------------------------
    # TOML helpers
    # ---------------------------------------------------------------------------

    def _load_toml(self) -> None:
        """Read ``anonymise.toml`` and populate the text editor.

        On first use, if ``anonymise.toml`` does not yet exist but
        ``anonymise_example.toml`` is present in the same directory, the
        example is copied to ``anonymise.toml`` so the user has a working
        starting point to modify.
        """
        if not self._toml_path.exists():
            example_path = self._toml_path.parent / "anonymise_example.toml"
            if example_path.exists():
                try:
                    self._toml_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(example_path, self._toml_path)
                except Exception:
                    traceback.print_exc()

        if self._toml_path.exists():
            try:
                self.dialog.text_edit_toml.setPlainText(
                    self._toml_path.read_text(encoding="utf-8")
                )
                return
            except Exception:
                traceback.print_exc()
        self.dialog.text_edit_toml.setPlainText(
            "# anonymise.toml not found — save this editor to create it.\n"
        )

    @pyqtSlot()
    def _save_toml(self) -> None:
        """Validate and write the editor contents back to ``anonymise.toml``."""
        text = self.dialog.text_edit_toml.toPlainText()

        # Validate it parses as valid TOML before writing
        try:
            tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            StanErrorMessage(parent=self.dialog).showMessage(
                f"The config contains invalid TOML and was not saved:\n\n{exc}"
            )
            return

        try:
            self._toml_path.parent.mkdir(parents=True, exist_ok=True)
            self._toml_path.write_text(text, encoding="utf-8")
            self.dialog.label_status.setText("Config saved.")
        except Exception as exc:
            traceback.print_exc()
            StanErrorMessage(parent=self.dialog).showMessage(
                f"Failed to save config:\n\n{exc}"
            )

    # ---------------------------------------------------------------------------
    # PDF selection
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def _browse_pdf(self) -> None:
        """Open a file dialog to choose the source PDF."""
        start_dir = (
            str(self._input_path.parent)
            if self._input_path is not None
            else str(Path.home())
        )
        path_str, _ = QFileDialog.getOpenFileName(
            self.dialog,
            "Select PDF Statement",
            start_dir,
            "PDF Files (*.pdf)",
        )
        if path_str:
            self._set_input_path(Path(path_str))

    def _set_input_path(self, path: Path) -> None:
        """Update state and UI to reflect a newly selected PDF."""
        self._input_path = path
        self._output_path = None
        self.dialog.line_edit_pdf_path.setText(str(path))
        self.dialog.button_run.setEnabled(True)
        self.dialog.button_open_original.setEnabled(True)
        self.dialog.button_open_anonymised.setEnabled(False)
        self.dialog.label_status.setText(
            "Ready — click 'Run Anonymisation' to proceed."
        )

    # ---------------------------------------------------------------------------
    # Anonymisation worker
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def _run_anonymisation(self) -> None:
        """Kick off the background anonymisation worker."""
        if self._input_path is None:
            return

        if not self._input_path.exists():
            StanErrorMessage(parent=self.dialog).showMessage(
                f"Source PDF not found:\n{self._input_path}"
            )
            return

        if not self._toml_path.exists():
            StanErrorMessage(parent=self.dialog).showMessage(
                "anonymise.toml not found. Save the config first."
            )
            return

        self.dialog.button_run.setEnabled(False)
        self.dialog.button_save_toml.setEnabled(False)
        self.dialog.button_browse.setEnabled(False)
        self.dialog.button_open_anonymised.setEnabled(False)
        self.dialog.label_status.setText("Running anonymisation…")

        worker = _AnonymiseWorker(
            input_path=self._input_path,
            config_path=self._toml_path,
        )
        worker.signals.finished.connect(self._on_finished)
        worker.signals.error.connect(self._on_error)
        thread_pool = QThreadPool.globalInstance()
        assert thread_pool is not None, "QThreadPool.globalInstance() returned None"
        thread_pool.start(worker)

    @pyqtSlot(Path)
    def _on_finished(self, output_path: Path) -> None:
        """Called on the GUI thread when the worker completes successfully."""
        self._output_path = output_path
        self.dialog.button_run.setEnabled(True)
        self.dialog.button_save_toml.setEnabled(True)
        self.dialog.button_browse.setEnabled(True)
        self.dialog.button_open_anonymised.setEnabled(True)
        self.dialog.label_status.setText(
            f"Done. Anonymised PDF saved to:\n{output_path}"
        )

    @pyqtSlot(str)
    def _on_error(self, message: str) -> None:
        """Called on the GUI thread when the worker raises an exception."""
        self.dialog.button_run.setEnabled(True)
        self.dialog.button_save_toml.setEnabled(True)
        self.dialog.button_browse.setEnabled(True)
        self.dialog.label_status.setText("Anonymisation failed — see error dialog.")
        StanErrorMessage(parent=self.dialog).showMessage(
            f"Anonymisation failed:\n\n{message}"
        )

    # ---------------------------------------------------------------------------
    # Open PDF helpers
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def _open_original(self) -> None:
        """Open the source PDF in the OS default viewer."""
        if self._input_path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._input_path)))

    @pyqtSlot()
    def _open_anonymised(self) -> None:
        """Open the anonymised PDF in the OS default viewer."""
        if self._output_path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_path)))
