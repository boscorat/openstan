"""anonymise_presenter.py — Presenter for the AnonymiseDialog.

Owns all logic for the anonymisation workflow:
  - loading and saving ``anonymise.toml``
  - browsing for a source PDF
  - running ``bsp.anonymise_pdf`` in a background worker
  - opening the original / anonymised PDFs via the OS viewer
"""

import tomllib
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

import bank_statement_anonymiser as bsa
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from openstan.components import StanErrorMessage, StanInfoMessage

if TYPE_CHECKING:
    from bank_statement_parser import ProjectPaths

    from openstan.views.anonymise_dialog import AnonymiseDialog


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


class _AnonymiseSignals(QObject):
    """Signals emitted by the background anonymisation worker."""

    started: Signal = Signal()
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
        self._config_dir: Path = Path(str(project_paths.root)) / "config" / "user"
        self._always_anonymise_path: Path = self._config_dir / "always_anonymise.toml"
        self._never_anonymise_path: Path = self._config_dir / "never_anonymise.toml"
        self._legacy_path: Path = self._config_dir / "anonymise_legacy.toml"
        self._input_path: Path | None = initial_pdf
        self._output_path: Path | None = None
        # Remembers the parent of the last PDF the user selected.
        self._last_dir: Path | None = (
            initial_pdf.parent if initial_pdf is not None else None
        )

        # Dirty-state tracking
        self._always_dirty: bool = False
        self._never_dirty: bool = False

        # Wire buttons
        self.dialog.button_browse.clicked.connect(self._browse_pdf)
        self.dialog.button_save_toml.clicked.connect(self._save_toml)
        self.dialog.button_run.clicked.connect(self._run_anonymisation)
        self.dialog.button_open_original.clicked.connect(self._open_original)
        self.dialog.button_open_anonymised.clicked.connect(self._open_anonymised)

        # Wire text editor signals for dirty tracking
        self.dialog.text_edit_always.textChanged.connect(self._mark_always_dirty)
        self.dialog.text_edit_never.textChanged.connect(self._mark_never_dirty)

        # Ensure config files exist and handle legacy migration
        self._ensure_config_files()

        # Populate both editors
        self._load_always_toml()
        self._load_never_toml()

        # Pre-populate PDF path if supplied
        if initial_pdf is not None:
            self._set_input_path(initial_pdf)

    # ---------------------------------------------------------------------------
    # Config file management
    # ---------------------------------------------------------------------------

    def _ensure_config_files(self) -> None:
        """Check for legacy file and migrate if needed; ensure directories exist."""
        self._config_dir.mkdir(parents=True, exist_ok=True)

        # If legacy file exists and new files don't, migrate
        if (
            self._legacy_path.exists()
            and not self._always_anonymise_path.exists()
            and not self._never_anonymise_path.exists()
        ):
            try:
                self._migrate_legacy_config()
            except Exception:
                traceback.print_exc()
                # Fall through to create empty templates

    def _migrate_legacy_config(self) -> None:
        """Parse anonymise.toml and split into two new files."""
        try:
            text = self._legacy_path.read_text(encoding="utf-8")
            config = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"Legacy config is invalid TOML: {exc}") from exc

        # Extract sections
        numbers_section = config.get("numbers_to_scramble", {})
        words_section = config.get("words_to_not_scramble", {})
        filename_section = config.get("filename_replacements", {})

        # Build always_anonymise.toml
        always_content = self._build_always_toml(numbers_section)
        self._always_anonymise_path.write_text(always_content, encoding="utf-8")

        # Build never_anonymise.toml
        never_content = self._build_never_toml(words_section, filename_section)
        self._never_anonymise_path.write_text(never_content, encoding="utf-8")

    def _build_always_toml(self, numbers_section: dict) -> str:
        """Reconstruct always_anonymise.toml content from legacy config section."""
        if not numbers_section:
            return "# Add any forced replacements here\n"

        lines = ["# Forced replacements (applied before scramble)"]
        for key, val in numbers_section.items():
            if isinstance(val, str):
                lines.append(f'"{key}" = "{val}"')
        return "\n".join(lines)

    def _build_never_toml(self, words_section: dict, filename_section: dict) -> str:
        """Reconstruct never_anonymise.toml content from legacy config sections."""
        lines = []

        if words_section or filename_section:
            exclude = words_section.get("exclude", [])
            if exclude:
                lines.append("exclude = [")
                for word in exclude:
                    lines.append(f'    "{word}",')
                lines.append("]")

        if not lines:
            lines = [
                "# Add phrases to exclude from scrambling here",
                "exclude = [",
                "]",
            ]

        return "\n".join(lines)

    # ---------------------------------------------------------------------------
    # TOML loading
    # ---------------------------------------------------------------------------

    def _load_always_toml(self) -> None:
        """Load always_anonymise.toml into editor."""
        if self._always_anonymise_path.exists():
            try:
                text = self._always_anonymise_path.read_text(encoding="utf-8")
            except Exception:
                traceback.print_exc()
                text = ""
        else:
            text = ""

        if not text:
            text = "# Add any forced replacements here\n"

        self.dialog.text_edit_always.setPlainText(text)
        self._always_dirty = False

    def _load_never_toml(self) -> None:
        """Load never_anonymise.toml into editor."""
        if self._never_anonymise_path.exists():
            try:
                text = self._never_anonymise_path.read_text(encoding="utf-8")
            except Exception:
                traceback.print_exc()
                text = ""
        else:
            text = ""

        if not text:
            text = "# Add phrases to exclude from scrambling here\nexclude = [\n]\n"

        self.dialog.text_edit_never.setPlainText(text)
        self._never_dirty = False

    # ---------------------------------------------------------------------------
    # Dirty-state tracking
    # ---------------------------------------------------------------------------

    @Slot()
    def _mark_always_dirty(self) -> None:
        """Mark always_anonymise editor as modified."""
        self._always_dirty = True
        self._update_status()

    @Slot()
    def _mark_never_dirty(self) -> None:
        """Mark never_anonymise editor as modified."""
        self._never_dirty = True
        self._update_status()

    def _update_status(self) -> None:
        """Update status label to show if unsaved changes exist."""
        if self._always_dirty or self._never_dirty:
            self.dialog.label_status.setText(
                "⚠ Unsaved changes (click 'Save Config' before anonymising)"
            )
        else:
            self.dialog.label_status.setText(
                "Ready — select a PDF and click 'Run Anonymisation'"
            )

    # ---------------------------------------------------------------------------
    # TOML validation and saving
    # ---------------------------------------------------------------------------

    def _save_always_toml(self) -> bool:
        """Validate and save always_anonymise.toml. Returns True on success."""
        text = self.dialog.text_edit_always.toPlainText()
        try:
            tomllib.loads(text)  # Validate TOML syntax
        except tomllib.TOMLDecodeError as exc:
            StanErrorMessage(parent=self.dialog).showMessage(
                f"always_anonymise.toml contains invalid TOML:\n\n{exc}"
            )
            return False

        try:
            self._always_anonymise_path.write_text(text, encoding="utf-8")
            self._always_dirty = False
            return True
        except Exception as exc:
            traceback.print_exc()
            StanErrorMessage(parent=self.dialog).showMessage(
                f"Failed to save always_anonymise.toml:\n\n{exc}"
            )
            return False

    def _save_never_toml(self) -> bool:
        """Validate and save never_anonymise.toml. Returns True on success."""
        text = self.dialog.text_edit_never.toPlainText()
        try:
            tomllib.loads(text)  # Validate TOML syntax
        except tomllib.TOMLDecodeError as exc:
            StanErrorMessage(parent=self.dialog).showMessage(
                f"never_anonymise.toml contains invalid TOML:\n\n{exc}"
            )
            return False

        try:
            self._never_anonymise_path.write_text(text, encoding="utf-8")
            self._never_dirty = False
            return True
        except Exception as exc:
            traceback.print_exc()
            StanErrorMessage(parent=self.dialog).showMessage(
                f"Failed to save never_anonymise.toml:\n\n{exc}"
            )
            return False

    @Slot()
    def _save_toml(self) -> None:
        """Validate and save both config files."""
        save_always_ok = self._save_always_toml()
        save_never_ok = self._save_never_toml()

        if save_always_ok and save_never_ok:
            self.dialog.label_status.setText("Config saved.")
        else:
            self.dialog.label_status.setText("Config has errors — see messages above.")

    # ---------------------------------------------------------------------------
    # PDF selection
    # ---------------------------------------------------------------------------

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
        """Kick off background anonymisation, prompting to save if dirty."""
        if self._input_path is None:
            return

        if not self._input_path.exists():
            StanErrorMessage(parent=self.dialog).showMessage(
                f"Source PDF not found:\n{self._input_path}"
            )
            return

        # Prompt to save if editors are dirty
        if self._always_dirty or self._never_dirty:
            reply = StanInfoMessage.question(
                self.dialog,
                "Unsaved Changes",
                "You have unsaved changes in the config editor.\n\n"
                "Save them before anonymising?",
                StanInfoMessage.StandardButton.Yes
                | StanInfoMessage.StandardButton.Cancel,
                StanInfoMessage.StandardButton.Yes,
            )
            if reply == StanInfoMessage.StandardButton.Cancel:
                return

            # Save both (if save fails, abort anonymisation)
            save_always_ok = self._save_always_toml()
            save_never_ok = self._save_never_toml()
            if not (save_always_ok and save_never_ok):
                self.dialog.label_status.setText(
                    "Fix config errors before anonymising."
                )
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
        self.dialog.button_save_toml.setEnabled(False)
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
        self.dialog.button_save_toml.setEnabled(True)
        self.dialog.button_browse.setEnabled(True)
        self.dialog.button_open_anonymised.setEnabled(True)
        self.dialog.label_status.setText(
            f"Done. Anonymised PDF saved to:\n{output_path}"
        )

    @Slot(str)
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
