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
        self.view.button_open_anonymise.clicked.connect(self.open_anonymise_tool)

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

    def _confirm(
        self,
        title: str,
        text: str,
        icon: QMessageBox.Icon = QMessageBox.Icon.Warning,
    ) -> bool:
        """Show a Yes/Cancel confirmation dialog.  Returns True if Yes was clicked."""
        dlg = StanInfoMessage(parent=self.view)
        dlg.setWindowTitle(title)
        dlg.setIcon(icon)
        dlg.setText(text)
        dlg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        dlg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        return dlg.exec() == QMessageBox.StandardButton.Yes

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
        if not self._confirm(
            "Confirm Delete",
            f"Delete project '{project_name}'?{folder_warning}\n\nThis cannot be undone.",
        ):
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
            except Exception:
                traceback.print_exc()
                StanErrorMessage(parent=self.view).showMessage(
                    f"Project record removed, but the folder could not be deleted:\n{project_location}"
                )

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

        if not self._confirm(
            "Confirm Remove",
            f"Remove project '{project_name}' from the UI?\n\n"
            "The project folder on disk will not be affected.",
        ):
            return

        success, _, msg = self.model.delete_record_by_id(project_id)
        if not success:
            StanErrorMessage(parent=self.view).showMessage(
                f"Failed to remove project record: {msg}"
            )
            return

        self.refresh_combos()

    @pyqtSlot()
    def empty_gui_db(self) -> None:
        """Delete and recreate gui.db, then quit the application."""
        if not self._confirm(
            "Confirm Reset",
            "Reset the application?\n\n"
            "This will permanently delete all projects, sessions, and users from gui.db "
            "and close the application.\n\n"
            "This action cannot be undone.",
            icon=QMessageBox.Icon.Critical,
        ):
            return

        gui_db_path = Path(Paths.databases("gui.db"))

        # Close the Qt database connection before touching the file
        self.stan.gui_db.close()

        try:
            if gui_db_path.exists():
                gui_db_path.unlink()
            create_gui_db(gui_db_path)
        except Exception:
            traceback.print_exc()
            StanErrorMessage(parent=self.view).showMessage(
                "Failed to recreate gui.db. The application will now close."
            )

        QApplication.quit()

    @pyqtSlot()
    def open_anonymise_tool(self) -> None:
        """Open the Anonymise PDF dialog for the currently active project."""
        from bank_statement_parser import ProjectPaths

        from openstan.presenters.anonymise_presenter import AnonymisePresenter
        from openstan.views.anonymise_dialog import AnonymiseDialog

        project_paths: ProjectPaths | None = self.stan.current_project_paths
        if project_paths is None:
            StanErrorMessage(parent=self.view).showMessage(
                "No project is currently active. "
                "Open a project before using the Anonymise tool."
            )
            return

        dlg = AnonymiseDialog(parent=self.view)
        _presenter = AnonymisePresenter(dialog=dlg, project_paths=project_paths)
        dlg.exec()
