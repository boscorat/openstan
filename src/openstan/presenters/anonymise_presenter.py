"""anonymise_presenter.py — Presenter for the AnonymiseDialog.

Owns all logic for the anonymisation workflow:
  - loading and saving config TOML files
  - browsing for a source PDF
  - running ``bsa.anonymise_pdf`` in a background worker
  - opening the original / anonymised PDFs via the OS viewer
"""

import time
import tomllib
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

import bank_statement_anonymiser as bsa
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from openstan.components import StanErrorMessage

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
    def from_toml(cls, toml_path: Path) -> "NeverAnonymiseConfig":
        """Load from a TOML file."""
        if not toml_path.exists():
            return cls()

        try:
            text = toml_path.read_text(encoding="utf-8")
            config = tomllib.loads(text)
            exclude = config.get("exclude", [])
            return cls(exclude=exclude)
        except Exception:
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
    def from_toml(cls, toml_path: Path) -> "AlwaysAnonymiseConfig":
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
        except Exception:
            traceback.print_exc()
            return cls()


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


class _AnonymiseSignals(QObject):
    """Signals emitted by the background anonymisation worker."""

    finished: Signal = Signal(Path)  # output path
    error: Signal = Signal(str)


class _AnonymiseWorker(QRunnable):
    """Runs ``bsa.anonymise_pdf`` on a thread-pool thread."""

    def __init__(
        self,
        input_path: Path,
        always_anonymise_path: Path | None = None,
        never_anonymise_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.signals = _AnonymiseSignals()
        self._input = input_path
        self._always_path = always_anonymise_path
        self._never_path = never_anonymise_path

    @Slot()
    def run(self) -> None:  # noqa: N802  (Qt override)
        try:
            out = bsa.anonymise_pdf(
                self._input,
                always_anonymise_path=self._always_path,
                never_anonymise_path=self._never_path,
            )
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
        ``config/user/always_anonymise.toml`` and ``never_anonymise.toml``.
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
        self._config_dir: Path = Path(str(project_paths.root)) / "config" / "user"
        self._always_anonymise_path: Path = self._config_dir / "always_anonymise.toml"
        self._never_anonymise_path: Path = self._config_dir / "never_anonymise.toml"
        self._input_path: Path | None = initial_pdf
        self._output_path: Path | None = None
        # Remembers the parent of the last PDF the user selected.
        self._last_dir: Path | None = (
            initial_pdf.parent if initial_pdf is not None else None
        )

        # Current config state (loaded from TOML)
        self._always_config = AlwaysAnonymiseConfig()
        self._never_config = NeverAnonymiseConfig()

        # Wire buttons
        self.dialog.button_browse.clicked.connect(self._browse_pdf)
        self.dialog.button_run.clicked.connect(self._run_anonymisation)
        self.dialog.button_open_original.clicked.connect(self._open_original)
        self.dialog.button_open_anonymised.clicked.connect(self._open_anonymised)

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
            except Exception as exc:
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

        # Pass None if file doesn't exist (bsa uses system defaults)
        always_path = (
            self._always_anonymise_path
            if self._always_anonymise_path.exists()
            else None
        )
        never_path = (
            self._never_anonymise_path if self._never_anonymise_path.exists() else None
        )

        self.dialog.button_run.setEnabled(False)
        self.dialog.button_browse.setEnabled(False)
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

    @Slot(Path)
    def _on_finished(self, output_path: Path) -> None:
        """Called on the GUI thread when the worker completes successfully."""
        self._output_path = output_path
        self.dialog.button_run.setEnabled(True)
        self.dialog.button_browse.setEnabled(True)
        self.dialog.button_open_anonymised.setEnabled(True)
        self.dialog.label_status.setText(
            f"Done. Anonymised PDF saved to:\n{output_path}"
        )

    @Slot(str)
    def _on_error(self, message: str) -> None:
        """Called on the GUI thread when the worker raises an exception."""
        self.dialog.button_run.setEnabled(True)
        self.dialog.button_browse.setEnabled(True)
        self.dialog.label_status.setText("Anonymisation failed — see error dialog.")
        StanErrorMessage(parent=self.dialog).showMessage(
            f"Anonymisation failed:\n\n{message}"
        )

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
