import sqlite3
import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import bank_statement_parser as bsp
import polars as pl
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from openstan.models.project_model import ProjectModel
    from openstan.views.project_view import ProjectView


class ProjectSummarySignals(QObject):
    """Cross-thread signals for ProjectSummaryWorker."""

    summary_ready: pyqtSignal = pyqtSignal(str)


class ProjectSummaryWorker(QRunnable):
    """Background worker that queries project.db mart tables and emits a summary string.

    Emits an empty string when the mart has not yet been built or all counts are zero.
    Any exception is printed to stderr and an empty string is emitted so the UI is
    never left in a broken state.
    """

    def __init__(self, project_path: Path) -> None:
        super().__init__()
        self._project_path: Path = project_path
        self.signals: ProjectSummarySignals = ProjectSummarySignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            tx_count: int = (
                bsp.db.FactTransaction(self._project_path)
                .all.select(pl.len())
                .collect()
                .item()
            )
            stmt_count: int = (
                bsp.db.DimStatement(self._project_path)
                .all.select(pl.len())
                .collect()
                .item()
            )
            acc_count: int = (
                bsp.db.DimAccount(self._project_path)
                .all.select(pl.len())
                .collect()
                .item()
            )
        except sqlite3.OperationalError, bsp.StatementError:
            # Mart tables not yet built, or project.db missing — show nothing.
            self.signals.summary_ready.emit("")
            return
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.signals.summary_ready.emit("")
            return

        if tx_count == 0 and stmt_count == 0 and acc_count == 0:
            self.signals.summary_ready.emit("")
            return

        text = (
            f"{tx_count:,} transactions in {stmt_count:,} statements"
            f" across {acc_count:,} {'account' if acc_count == 1 else 'accounts'}"
        )
        self.signals.summary_ready.emit(text)


class ProjectPresenter(QObject):
    path_or_name_changed: pyqtSignal = pyqtSignal()

    def __init__(
        self: "ProjectPresenter", model: "ProjectModel", view: "ProjectView"
    ) -> None:
        super().__init__()
        self.sessionID: str | None = None  # to be set by StanPresenter
        self.model: "ProjectModel" = model
        self.view: "ProjectView" = view
        self.view.selection.setModel(self.model)
        self.view.selection.setModelColumn(1)  # project_name column
        self.view.selection.setEditable(False)

        # Connect signals — new project wizard
        self.view.button_new.clicked.connect(self.open_new_project_wizard)
        self.view.wizard.page_basic.location_button.clicked.connect(
            self.open_folder_selection_dialog
        )
        self.view.wizard.page_basic.name_row.textChanged.connect(self.name_changed)
        self.path_or_name_changed.connect(self.update_location_label)
        self.view.wizard.new_project_required.connect(self.handle_project_required)

        # Connect signals — existing project wizard
        self.view.button_existing.clicked.connect(self.open_existing_project_wizard)
        self.view.wizard_existing.page_basic.location_button.clicked.connect(
            self.open_folder_selection_dialog
        )
        self.view.wizard_existing.page_basic.name_row.textChanged.connect(
            self.path_or_name_changed.emit
        )
        self.view.wizard_existing.new_project_required.connect(
            self.handle_project_required
        )

    # ---------------------------------------------------------------------------
    # Wizard dispatch — single slot handles both modes
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def handle_project_required(self) -> None:
        """Dispatch to the correct handler based on which wizard emitted the signal."""
        wizard = self.sender()
        if wizard is self.view.wizard_existing:
            self.connect_existing_project()
        else:
            self.create_new_project()

    # ---------------------------------------------------------------------------
    # New project
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def open_new_project_wizard(self) -> None:
        self.view.wizard.page_basic.location_button.setDisabled(True)
        self.view.wizard.page_basic.newProjectID = uuid4().hex
        self.view.wizard.page_basic.id_row.setText(
            self.view.wizard.page_basic.newProjectID
        )
        self.view.wizard.exec()

    @pyqtSlot()
    def create_new_project(self) -> bool:
        wizard = self.view.wizard
        project_name: str = wizard.page_basic.field("projectName")
        full_path: Path | None = wizard.full_project_path

        if full_path is None:
            wizard.failure_dialog.showMessage("No project folder path set.")
            return False

        # Create the root project folder first (bsp requires it to exist before scaffolding)
        try:
            full_path.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            error = f"Folder '{full_path}' already exists. Choose a different name or location."
            wizard.back()
            print(error)
            wizard.failure_dialog.showMessage(error)
            return False
        except Exception as e:
            error = f"Failed to create project folder: {e}"
            wizard.back()
            print(error)
            wizard.failure_dialog.showMessage(error)
            return False

        # bsp scaffolds subfolders, database and default config automatically
        try:
            bsp.validate_or_initialise_project(full_path)
        except Exception as e:
            # Clean up the folder we just created so we don't leave a partial project
            try:
                full_path.rmdir()
            except Exception:
                pass
            error = f"Failed to initialise project: {e}"
            wizard.back()
            print(error)
            wizard.failure_dialog.showMessage(error)
            return False

        new_pro: tuple[bool, str, str] = self.model.add_record(
            wizard.page_basic.newProjectID,
            project_name,
            str(full_path),
            self.sessionID,
        )
        if new_pro[0]:
            info = (
                f"Project '{project_name}' created successfully!\nLocation: {full_path}"
            )
            wizard.success_dialog.setText("Project Created Successfully")
            wizard.success_dialog.setDetailedText(info)
            if wizard.success_dialog.exec():
                wizard.project_created = True
                self.model.select()
                self.view.selection.setCurrentIndex(self.model.rowCount() - 1)
                wizard.accept()
                return True
        else:
            if new_pro[2].startswith("UNIQUE constraint failed: project.project_name"):
                error = f"Project with name '{project_name}' already exists."
            else:
                error = f"Failed to create project: {new_pro[2]}"
            wizard.back()
            print(error)
            wizard.failure_dialog.showMessage(error)
            return False
        return False

    # ---------------------------------------------------------------------------
    # Existing project
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def open_existing_project_wizard(self) -> None:
        self.view.wizard_existing.page_basic.newProjectID = uuid4().hex
        self.view.wizard_existing.page_basic.id_row.setText(
            self.view.wizard_existing.page_basic.newProjectID
        )
        self.view.wizard_existing.exec()

    @pyqtSlot()
    def connect_existing_project(self) -> bool:
        wizard = self.view.wizard_existing
        project_name: str = wizard.page_basic.name_row.text()
        full_path: Path | None = wizard.full_project_path

        if full_path is None:
            wizard.failure_dialog.showMessage("No project folder selected.")
            return False

        # Validate the selected folder is a usable bsp project (may scaffold missing pieces)
        try:
            bsp.validate_or_initialise_project(full_path)
        except Exception as e:
            error = f"The selected folder does not appear to be a valid project: {e}"
            wizard.back()
            print(error)
            wizard.failure_dialog.showMessage(error)
            return False

        new_pro: tuple[bool, str, str] = self.model.add_record(
            wizard.page_basic.newProjectID,
            project_name,
            str(full_path),
            self.sessionID,
        )
        if new_pro[0]:
            info = (
                f"Project '{project_name}' added successfully!\nLocation: {full_path}"
            )
            wizard.success_dialog.setText("Project Added Successfully")
            wizard.success_dialog.setDetailedText(info)
            if wizard.success_dialog.exec():
                wizard.project_created = True
                self.model.select()
                self.view.selection.setCurrentIndex(self.model.rowCount() - 1)
                wizard.accept()
                return True
        else:
            if new_pro[2].startswith("UNIQUE constraint failed: project.project_name"):
                error = f"Project with name '{project_name}' already exists."
            else:
                error = f"Failed to add project: {new_pro[2]}"
            wizard.back()
            print(error)
            wizard.failure_dialog.showMessage(error)
            return False
        return False

    # ---------------------------------------------------------------------------
    # Shared folder selection and label update
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def open_folder_selection_dialog(self) -> None:
        """Handles folder selection for both wizards — detects caller via sender()."""
        # Determine which wizard's page triggered this
        sender_button = self.sender()
        if sender_button is self.view.wizard_existing.page_basic.location_button:
            page = self.view.wizard_existing.page_basic
            wizard = self.view.wizard_existing
        else:
            page = self.view.wizard.page_basic
            wizard = self.view.wizard

        if page.folder_selection_dialog.exec() == 1:
            selected: Path = Path(page.folder_selection_dialog.selectedFiles()[0])
            page.folder_path = selected

            if wizard.mode == "existing":
                # Path is the project folder itself; pre-populate name from folder name
                wizard.full_project_path = selected
                page.name_row.setDisabled(False)
                page.name_row.setPlaceholderText("")
                page.name_row.setText(selected.name)
                page.location_label.setText(str(selected.absolute()))
                page.location_label.show()
            else:
                self.path_or_name_changed.emit()

    @pyqtSlot()
    def name_changed(self) -> None:
        """Only used by the new-project wizard to gate the location button."""
        name: str = self.view.wizard.page_basic.name_row.text()
        self.view.wizard.page_basic.location_button.setDisabled(len(name) == 0)
        self.path_or_name_changed.emit()

    @pyqtSlot()
    def update_location_label(self) -> None:
        """Updates the full-path label for the new-project wizard."""
        folder: Path | None = self.view.wizard.page_basic.folder_path
        name: str = self.view.wizard.page_basic.name_row.text()
        if folder and len(name) > 0:
            self.view.wizard.full_project_path = folder.joinpath(name)
            self.view.wizard.page_basic.location_label.setText(
                str(self.view.wizard.full_project_path.absolute())
            )
            self.view.wizard.page_basic.location_label.show()
        else:
            self.view.wizard.page_basic.location_label.hide()
