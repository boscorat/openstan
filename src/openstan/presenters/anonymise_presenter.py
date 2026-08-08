"""anonymise_presenter.py — Presenter for the AnonymiseDialog.

Owns all logic for the anonymisation workflow:
  - loading and saving config TOML files
  - browsing for a source PDF or folder of PDFs
  - running ``bsa.anonymise_pdf`` in a background worker
  - opening the original / anonymised PDFs via the OS viewer
"""

import subprocess
import sys
import time
import tomllib
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

import bank_statement_anonymiser as bsa
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from openstan.components import StanErrorMessage, StanFolderDialog, StanInfoMessage

if TYPE_CHECKING:
    from bank_statement_parser import ProjectPaths

    from openstan.views.anonymise_dialog import AnonymiseDialog


# ---------------------------------------------------------------------------
# Data models for config
# ---------------------------------------------------------------------------


class NeverAnonymiseConfig:
    """Represents the never_anonymise.toml config (phrases to exclude from scrambling)."""

    def __init__(self, exclude: list[str] | None = None) -> None:
        self.exclude = exclude or []

    def to_toml(self) -> str:
        """Generate TOML content for this config."""
        if not self.exclude:
            return "exclude = [\n]\n"

        lines = ["exclude = ["]
        for phrase in self.exclude:
            # Escape quotes in phrases
            escaped = phrase.replace('"', '\\"')
            lines.append(f'    "{escaped}",')
        lines.append("]")
        return "\n".join(lines)

    @classmethod
    def from_toml(cls, toml_path: Path) -> NeverAnonymiseConfig:
        """Load from a TOML file."""
        if not toml_path.exists():
            return cls()

        try:
            text = toml_path.read_text(encoding="utf-8")
            config = tomllib.loads(text)
            exclude = config.get("exclude", [])
            return cls(exclude=exclude)
        except tomllib.TOMLDecodeError, OSError:
            traceback.print_exc()
            return cls()


class AlwaysAnonymiseConfig:
    """Represents the always_anonymise.toml config (forced replacements)."""

    def __init__(self, replacements: dict[str, str] | None = None) -> None:
        self.replacements = replacements or {}

    def to_toml(self) -> str:
        """Generate TOML content for this config."""
        if not self.replacements:
            return "# Forced replacements (applied before scramble)\n"

        lines = ["# Forced replacements (applied before scramble)"]
        for original, replacement in self.replacements.items():
            # Escape quotes in both original and replacement
            orig_escaped = original.replace('"', '\\"')
            repl_escaped = replacement.replace('"', '\\"')
            lines.append(f'"{orig_escaped}" = "{repl_escaped}"')
        return "\n".join(lines)

    @classmethod
    def from_toml(cls, toml_path: Path) -> AlwaysAnonymiseConfig:
        """Load from a TOML file."""
        if not toml_path.exists():
            return cls()

        try:
            text = toml_path.read_text(encoding="utf-8")
            config = tomllib.loads(text)
            # TOML top-level keys (excluding standard metadata) are the replacements
            # Filter out comment-only lines; BSA uses key=value pairs
            replacements = {
                k: v
                for k, v in config.items()
                if isinstance(v, str) and not k.startswith("_")
            }
            return cls(replacements=replacements)
        except tomllib.TOMLDecodeError, OSError:
            traceback.print_exc()
            return cls()


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


class _AnonymiseSignals(QObject):
    """Signals emitted by the background anonymisation worker."""

    finished: Signal = Signal(Path)  # single-file output path
    error: Signal = Signal(str)
    progress: Signal = Signal(int, int)  # (current_index, total)
    batch_finished: Signal = Signal(list)  # list of (input, output|None, error|None)


class _AnonymiseWorker(QRunnable):
    """Runs ``bsa.anonymise_pdf`` on a thread-pool thread.

    Supports two modes:
    - **Single-file mode**: ``input_paths`` is ``None``; ``input_path`` is used.
    - **Folder mode**: ``input_paths`` is a list of PDFs to process sequentially.
    """

    def __init__(
        self,
        input_path: Path | None = None,
        input_paths: list[Path] | None = None,
        always_anonymise_path: Path | None = None,
        never_anonymise_path: Path | None = None,
        output_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self.signals = _AnonymiseSignals()
        self._input = input_path
        self._inputs = input_paths or []
        self._always_path = always_anonymise_path
        self._never_path = never_anonymise_path
        self._output_dir = output_dir

    @Slot()
    def run(self) -> None:
        if self._inputs:
            self._run_batch()
        else:
            self._run_single()

    def _run_single(self) -> None:
        """Process a single PDF (legacy mode)."""
        try:
            assert self._input is not None
            out = bsa.anonymise_pdf(
                self._input,
                always_anonymise_path=self._always_path,
                never_anonymise_path=self._never_path,
            )
            self.signals.finished.emit(out)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(str(exc))

    def _run_batch(self) -> None:
        """Process multiple PDFs sequentially, emitting progress per file."""
        total = len(self._inputs)
        results: list[tuple[Path, Path | None, str | None]] = []

        for idx, input_path in enumerate(self._inputs):
            self.signals.progress.emit(idx + 1, total)
            try:
                out = bsa.anonymise_pdf(
                    input_path,
                    always_anonymise_path=self._always_path,
                    never_anonymise_path=self._never_path,
                )
                # Move output to the dedicated subfolder if specified
                if self._output_dir is not None:
                    dest = self._output_dir / out.name
                    if dest.exists():
                        counter = 1
                        while dest.exists():
                            dest = (
                                self._output_dir / f"{out.stem}_{counter}{out.suffix}"
                            )
                            counter += 1
                    out.rename(dest)
                    out = dest
                results.append((input_path, out, None))
            except Exception as exc:  # noqa: BLE001
                results.append((input_path, None, str(exc)))

        self.signals.batch_finished.emit(results)


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
        ``config/user/always_anonymise.toml`` and ``never_anonymise.toml``.
    initial_pdf:
        Optional pre-selected PDF path (e.g. passed in from the debug screen).
    """

    def __init__(
        self,
        dialog: AnonymiseDialog,
        project_paths: ProjectPaths,
        initial_pdf: Path | None = None,
    ) -> None:
        super().__init__()
        self.dialog = dialog
        self._project_paths = project_paths
        self._config_dir: Path = Path(str(project_paths.root)) / "config" / "user"
        self._always_anonymise_path: Path = self._config_dir / "always_anonymise.toml"
        self._never_anonymise_path: Path = self._config_dir / "never_anonymise.toml"
        self._input_path: Path | None = initial_pdf
        self._output_path: Path | None = None
        # Remembers the parent of the last PDF the user selected.
        self._last_dir: Path | None = (
            initial_pdf.parent if initial_pdf is not None else None
        )

        # Folder-mode state
        self._input_folder: Path | None = None
        self._input_files: list[Path] = []
        self._completed: list[tuple[Path, Path | None, str | None]] = []
        self._output_dir: Path | None = None

        # Current config state (loaded from TOML)
        self._always_config = AlwaysAnonymiseConfig()
        self._never_config = NeverAnonymiseConfig()

        # Wire buttons
        self.dialog.button_browse.clicked.connect(self._browse_pdf)
        self.dialog.button_browse_folder.clicked.connect(self._browse_folder)
        self.dialog.button_run.clicked.connect(self._run_anonymisation)
        self.dialog.button_open_original.clicked.connect(self._open_original)
        self.dialog.button_open_anonymised.clicked.connect(self._open_anonymised)
        self.dialog.button_open_results.clicked.connect(self._show_results_dialog)
        self.dialog.button_open_output_folder.clicked.connect(self._open_output_folder)

        # Wire table buttons
        self.dialog.button_add_always.clicked.connect(self._add_always_row)
        self.dialog.button_remove_always.clicked.connect(self._remove_always_row)
        self.dialog.button_add_never.clicked.connect(self._add_never_row)
        self.dialog.button_remove_never.clicked.connect(self._remove_never_row)

        # Ensure config directory exists
        self._config_dir.mkdir(parents=True, exist_ok=True)

        # Load and populate tables
        self._load_and_populate_tables()

        # Pre-populate PDF path if supplied
        if initial_pdf is not None:
            self._set_input_path(initial_pdf)

        # Wire dialog close event to save before exit
        self.dialog.finished.connect(self._on_dialog_finished)

    # ---------------------------------------------------------------------------
    # Config loading and table population
    # ---------------------------------------------------------------------------

    def _load_and_populate_tables(self) -> None:
        """Load TOML files and populate table widgets."""
        self._always_config = AlwaysAnonymiseConfig.from_toml(
            self._always_anonymise_path
        )
        self._never_config = NeverAnonymiseConfig.from_toml(self._never_anonymise_path)

        # Populate "Always Anonymise" table
        self.dialog.populate_always_table(self._always_config.replacements)

        # Populate "Never Anonymise" table
        self.dialog.populate_never_table(self._never_config.exclude)

    # ---------------------------------------------------------------------------
    # Config saving with retry logic
    # ---------------------------------------------------------------------------

    def _save_configs(self) -> bool:
        """Save both configs to disk with 3-retry logic.

        Returns True on success, False on failure.
        """
        # Read current state from tables
        self._always_config.replacements = self.dialog.get_always_table_data()
        self._never_config.exclude = self.dialog.get_never_table_data()

        max_retries = 3
        retry_delay = 1.0  # seconds

        for attempt in range(max_retries):
            try:
                # Try to write both files
                self._always_anonymise_path.write_text(
                    self._always_config.to_toml(), encoding="utf-8"
                )
                self._never_anonymise_path.write_text(
                    self._never_config.to_toml(), encoding="utf-8"
                )
                # Success
                return True
            except OSError as exc:
                traceback.print_exc()
                if attempt < max_retries - 1:
                    # Retry after delay
                    time.sleep(retry_delay)
                else:
                    # Final attempt failed
                    StanErrorMessage(parent=self.dialog).showMessage(
                        f"Failed to save config files after {max_retries} attempts:\n\n{exc}"
                    )
                    return False

        return False

    # ---------------------------------------------------------------------------
    # PDF selection
    # ---------------------------------------------------------------------------

    @Slot()
    def _add_always_row(self) -> None:
        """Add a new empty row to the 'Always Anonymise' table."""
        from PySide6.QtWidgets import QTableWidgetItem

        row_pos = self.dialog.table_always.rowCount()
        self.dialog.table_always.insertRow(row_pos)

        self.dialog.table_always.setItem(row_pos, 0, QTableWidgetItem(""))
        self.dialog.table_always.setItem(row_pos, 1, QTableWidgetItem(""))

        # Set focus to the new row
        self.dialog.table_always.setCurrentCell(row_pos, 0)

    @Slot()
    def _remove_always_row(self) -> None:
        """Remove the selected row from the 'Always Anonymise' table."""
        current_row = self.dialog.table_always.currentRow()
        if current_row >= 0:
            self.dialog.table_always.removeRow(current_row)

    @Slot()
    def _add_never_row(self) -> None:
        """Add a new empty row to the 'Never Anonymise' table."""
        from PySide6.QtWidgets import QTableWidgetItem

        row_pos = self.dialog.table_never.rowCount()
        self.dialog.table_never.insertRow(row_pos)

        self.dialog.table_never.setItem(row_pos, 0, QTableWidgetItem(""))

        # Set focus to the new row
        self.dialog.table_never.setCurrentCell(row_pos, 0)

    @Slot()
    def _remove_never_row(self) -> None:
        """Remove the selected row from the 'Never Anonymise' table."""
        current_row = self.dialog.table_never.currentRow()
        if current_row >= 0:
            self.dialog.table_never.removeRow(current_row)

    @Slot()
    def _browse_pdf(self) -> None:
        """Open a file dialog to choose the source PDF."""
        self._clear_folder_mode()
        start_dir = (
            str(self._last_dir) if self._last_dir is not None else str(Path.home())
        )
        path_str, _ = QFileDialog.getOpenFileName(
            self.dialog,
            "Select PDF Statement",
            start_dir,
            "PDF Files (*.pdf)",
        )
        if path_str:
            self._last_dir = Path(path_str).parent
            self._set_input_path(Path(path_str))

    @Slot()
    def _browse_folder(self) -> None:
        """Open a folder dialog to choose a directory of PDFs."""
        self._clear_folder_mode()
        dlg = StanFolderDialog("Select folder containing PDF statements")
        if not dlg.exec():
            return
        selected = dlg.selectedFiles()
        if not selected:
            return
        folder = Path(selected[0])
        self._last_dir = folder
        self._set_input_folder(folder)

    def _set_input_folder(self, folder: Path) -> None:
        """Discover PDFs in *folder* and switch to folder mode."""
        self._input_folder = folder
        self._input_path = None
        self._output_path = None
        self._completed = []
        self._input_files = sorted(folder.rglob("*.pdf"))

        # Update UI
        self.dialog.line_edit_pdf_path.setText(str(folder))
        self.dialog.label_file_count.setText(
            f"{len(self._input_files)} PDF file(s) found"
        )
        self.dialog.label_file_count.setVisible(True)

        if self._input_files:
            self.dialog.button_run.setEnabled(True)
            self.dialog.label_status.setText(
                f"Ready — click 'Run Anonymisation' to anonymise "
                f"{len(self._input_files)} file(s)."
            )
        else:
            self.dialog.button_run.setEnabled(False)
            self.dialog.label_status.setText("No PDF files found in selected folder.")

        # Hide single-file result buttons; show folder result buttons
        self.dialog.button_open_original.setEnabled(False)
        self.dialog.button_open_anonymised.setEnabled(False)
        self.dialog.button_open_results.setVisible(False)
        self.dialog.button_open_output_folder.setVisible(False)

    def _clear_folder_mode(self) -> None:
        """Reset folder state and restore single-file UI."""
        self._input_folder = None
        self._input_files = []
        self._completed = []
        self.dialog.label_file_count.setVisible(False)
        self.dialog.progress_bar.setVisible(False)
        self.dialog.button_open_results.setVisible(False)
        self.dialog.button_open_output_folder.setVisible(False)

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

    @Slot()
    def _run_anonymisation(self) -> None:
        """Save configs and kick off background anonymisation.

        Automatically saves the current table state to both TOML files
        (with 3-retry logic) before starting the anonymisation process.
        """
        if self._input_folder is not None:
            self._run_folder_anonymisation()
        else:
            self._run_single_anonymisation()

    def _run_single_anonymisation(self) -> None:
        """Process a single PDF file."""
        if self._input_path is None:
            return

        if not self._input_path.exists():
            StanErrorMessage(parent=self.dialog).showMessage(
                f"Source PDF not found:\n{self._input_path}"
            )
            return

        # Save configs before anonymising
        if not self._save_configs():
            self.dialog.label_status.setText("Fix config errors before anonymising.")
            return

        always_path, never_path = self._config_paths()

        self.dialog.button_run.setEnabled(False)
        self.dialog.button_browse.setEnabled(False)
        self.dialog.button_browse_folder.setEnabled(False)
        self.dialog.button_open_anonymised.setEnabled(False)
        self.dialog.label_status.setText("Running anonymisation…")

        worker = _AnonymiseWorker(
            input_path=self._input_path,
            always_anonymise_path=always_path,
            never_anonymise_path=never_path,
        )
        worker.signals.finished.connect(self._on_finished)
        worker.signals.error.connect(self._on_error)
        thread_pool = QThreadPool.globalInstance()
        assert thread_pool is not None, "QThreadPool.globalInstance() returned None"
        thread_pool.start(worker)

    def _run_folder_anonymisation(self) -> None:
        """Process all PDFs in the selected folder."""
        if not self._input_files:
            return

        # Show warning about reviewing each file
        msg = StanInfoMessage(parent=self.dialog)
        msg.setWindowTitle("Confirm Folder Anonymisation")
        msg.setText(
            f"Anonymise {len(self._input_files)} PDF file(s)?\n\n"
            "Each anonymised file must be reviewed individually before sharing.\n"
            "Automated anonymisation may not catch all sensitive information."
        )
        msg.setStandardButtons(
            StanInfoMessage.StandardButton.Yes | StanInfoMessage.StandardButton.Cancel
        )
        msg.setDefaultButton(StanInfoMessage.StandardButton.Cancel)
        if msg.exec() != StanInfoMessage.StandardButton.Yes:
            return

        # Save configs before anonymising
        if not self._save_configs():
            self.dialog.label_status.setText("Fix config errors before anonymising.")
            return

        always_path, never_path = self._config_paths()

        # Create output subfolder
        assert self._input_folder is not None
        output_dir = self._input_folder / "anonymised"
        output_dir.mkdir(parents=True, exist_ok=True)
        self._output_dir = output_dir

        self.dialog.button_run.setEnabled(False)
        self.dialog.button_browse.setEnabled(False)
        self.dialog.button_browse_folder.setEnabled(False)
        self.dialog.progress_bar.setMaximum(len(self._input_files))
        self.dialog.progress_bar.setValue(0)
        self.dialog.progress_bar.setVisible(True)
        self.dialog.label_status.setText("Starting anonymisation…")

        worker = _AnonymiseWorker(
            input_paths=self._input_files,
            always_anonymise_path=always_path,
            never_anonymise_path=never_path,
            output_dir=output_dir,
        )
        worker.signals.progress.connect(self._on_progress)
        worker.signals.batch_finished.connect(self._on_batch_finished)
        thread_pool = QThreadPool.globalInstance()
        assert thread_pool is not None, "QThreadPool.globalInstance() returned None"
        thread_pool.start(worker)

    def _config_paths(self) -> tuple[Path | None, Path | None]:
        """Return (always_path, never_path) — None if the file doesn't exist."""
        always_path = (
            self._always_anonymise_path
            if self._always_anonymise_path.exists()
            else None
        )
        never_path = (
            self._never_anonymise_path if self._never_anonymise_path.exists() else None
        )
        return always_path, never_path

    @Slot(Path)
    def _on_finished(self, output_path: Path) -> None:
        """Called on the GUI thread when the worker completes successfully."""
        self._output_path = output_path
        self.dialog.button_run.setEnabled(True)
        self.dialog.button_browse.setEnabled(True)
        self.dialog.button_browse_folder.setEnabled(True)
        self.dialog.button_open_anonymised.setEnabled(True)
        self.dialog.label_status.setText(
            f"Done. Anonymised PDF saved to:\n{output_path}"
        )

    @Slot(str)
    def _on_error(self, message: str) -> None:
        """Called on the GUI thread when the worker raises an exception."""
        self.dialog.button_run.setEnabled(True)
        self.dialog.button_browse.setEnabled(True)
        self.dialog.button_browse_folder.setEnabled(True)
        self.dialog.label_status.setText("Anonymisation failed — see error dialog.")
        StanErrorMessage(parent=self.dialog).showMessage(
            f"Anonymisation failed:\n\n{message}"
        )

    @Slot(int, int)
    def _on_progress(self, current: int, total: int) -> None:
        """Update progress bar during folder batch processing."""
        self.dialog.progress_bar.setValue(current)
        self.dialog.label_status.setText(f"Anonymising file {current} of {total}…")

    @Slot(list)
    def _on_batch_finished(self, results: list) -> None:
        """Called on the GUI thread when all folder files have been processed."""
        self._completed = results
        self.dialog.button_run.setEnabled(True)
        self.dialog.button_browse.setEnabled(True)
        self.dialog.button_browse_folder.setEnabled(True)
        self.dialog.progress_bar.setVisible(False)

        succeeded = sum(1 for _, out, err in results if out is not None)
        failed = sum(1 for _, _, err in results if err is not None)

        if failed == 0:
            self.dialog.label_status.setText(
                f"Done. {succeeded} file(s) anonymised successfully."
            )
        else:
            self.dialog.label_status.setText(
                f"Done. {succeeded} succeeded, {failed} failed."
            )

        # Show folder result buttons
        self.dialog.button_open_results.setVisible(True)
        self.dialog.button_open_output_folder.setVisible(True)

    def _show_results_dialog(self) -> None:
        """Open a dialog listing all anonymised files with open buttons."""
        from openstan.views.anonymise_results_dialog import AnonymiseResultsDialog

        dlg = AnonymiseResultsDialog(completed=self._completed, parent=self.dialog)
        dlg.exec()

    def _open_output_folder(self) -> None:
        """Open the output folder in the OS file manager."""
        if self._input_folder is None:
            return
        output_dir = self._input_folder / "anonymised"
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(output_dir)])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", str(output_dir)])
        else:
            subprocess.Popen(["xdg-open", str(output_dir)])

    # ---------------------------------------------------------------------------
    # Dialog lifecycle
    # ---------------------------------------------------------------------------

    @Slot(int)
    def _on_dialog_finished(self, result: int) -> None:
        """Save configs when dialog is closing.

        Called automatically when the dialog is closed via any method
        (Close button, X button, accept, or reject). Attempts to save
        the current table state to both TOML files using 3-retry logic.
        """
        # Save configs on exit
        self._save_configs()

    # ---------------------------------------------------------------------------
    # Open PDF helpers
    # ---------------------------------------------------------------------------

    @Slot()
    def _open_original(self) -> None:
        """Open the source PDF in the OS default viewer."""
        if self._input_path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._input_path)))

    @Slot()
    def _open_anonymised(self) -> None:
        """Open the anonymised PDF in the OS default viewer."""
        if self._output_path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_path)))
