import shutil
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QApplication, QMessageBox

from openstan.components import StanErrorMessage, StanInfoMessage
from openstan.data.create_gui_db import create_gui_db
from openstan.paths import Paths

if TYPE_CHECKING:
    from openstan.main import Stan
    from openstan.models.project_model import ProjectModel
    from openstan.views.admin_view import AdminView


class AdminPresenter(QObject):
    """Presenter for the admin dialog.

    Owns all destructive admin actions: project deletion, UI-only project
    removal, and full database reset.  The view contains no business logic.
    """

    def __init__(
        self: "AdminPresenter",
        model: "ProjectModel",
        view: "AdminView",
        stan: "Stan",
    ) -> None:
        super().__init__()
        self.model: "ProjectModel" = model
        self.view: "AdminView" = view
        self.stan: "Stan" = stan

        self.view.button_delete_project.clicked.connect(self.delete_project)
        self.view.button_remove_project.clicked.connect(self.remove_project_from_ui)
        self.view.button_empty_db.clicked.connect(self.empty_gui_db)

    # ---------------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------------

    def refresh_combos(self) -> None:
        """Repopulate both project combo boxes from the current model data.

        Called each time the admin dialog is opened and after any successful
        action that changes the project list.
        """
        self.model.select()
        self.view.combo_delete.clear()
        self.view.combo_remove.clear()
        for row in range(self.model.rowCount()):
            record = self.model.record(row)
            name: str = str(record.value("project_name"))
            self.view.combo_delete.addItem(name, userData=row)
            self.view.combo_remove.addItem(name, userData=row)

    # ---------------------------------------------------------------------------
    # Slots
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def delete_project(self) -> None:
        """Delete the selected project record and optionally its folder on disk."""
        row: int = self.view.combo_delete.currentData()
        if row is None:
            return
        record = self.model.record(row)
        project_id: str = str(record.value("project_id"))
        project_name: str = str(record.value("project_name"))
        project_location: str = str(record.value("project_location"))
        delete_folder: bool = self.view.check_delete_folder.isChecked()

        folder_warning = (
            f"\n\nThe project folder will also be permanently deleted from disk:\n{project_location}"
            if delete_folder
            else ""
        )
        confirm = StanInfoMessage(parent=self.view)
        confirm.setWindowTitle("Confirm Delete")
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setText(
            f"Delete project '{project_name}'?{folder_warning}\n\nThis cannot be undone."
        )
        confirm.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        confirm.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return

        success, _, msg = self.model.delete_record_by_id(project_id)
        if not success:
            StanErrorMessage(parent=self.view).showMessage(
                f"Failed to delete project record: {msg}"
            )
            return

        if delete_folder:
            try:
                shutil.rmtree(Path(project_location))
                print(f"ADMIN: Deleted project folder: {project_location}")
            except Exception:
                traceback.print_exc()
                StanErrorMessage(parent=self.view).showMessage(
                    f"Project record removed, but the folder could not be deleted:\n{project_location}"
                )

        print(f"ADMIN: Project '{project_name}' deleted.")
        self.refresh_combos()

    @pyqtSlot()
    def remove_project_from_ui(self) -> None:
        """Remove the selected project record from gui.db without touching disk."""
        row: int = self.view.combo_remove.currentData()
        if row is None:
            return
        record = self.model.record(row)
        project_id: str = str(record.value("project_id"))
        project_name: str = str(record.value("project_name"))

        confirm = StanInfoMessage(parent=self.view)
        confirm.setWindowTitle("Confirm Remove")
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setText(
            f"Remove project '{project_name}' from the UI?\n\n"
            "The project folder on disk will not be affected."
        )
        confirm.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        confirm.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return

        success, _, msg = self.model.delete_record_by_id(project_id)
        if not success:
            StanErrorMessage(parent=self.view).showMessage(
                f"Failed to remove project record: {msg}"
            )
            return

        print(f"ADMIN: Project '{project_name}' removed from UI.")
        self.refresh_combos()

    @pyqtSlot()
    def empty_gui_db(self) -> None:
        """Delete and recreate gui.db, then quit the application."""
        confirm = StanInfoMessage(parent=self.view)
        confirm.setWindowTitle("Confirm Reset")
        confirm.setIcon(QMessageBox.Icon.Critical)
        confirm.setText(
            "Reset the application?\n\n"
            "This will permanently delete all projects, sessions, and users from gui.db "
            "and close the application.\n\n"
            "This action cannot be undone."
        )
        confirm.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        confirm.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return

        gui_db_path = Path(Paths.databases("gui.db"))

        # Close the Qt database connection before touching the file
        self.stan.gui_db.close()

        try:
            if gui_db_path.exists():
                gui_db_path.unlink()
            create_gui_db(gui_db_path)
            print("ADMIN: gui.db deleted and recreated.")
        except Exception:
            traceback.print_exc()
            StanErrorMessage(parent=self.view).showMessage(
                "Failed to recreate gui.db. The application will now close."
            )

        QApplication.quit()
