from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from openstan.models.project_model import ProjectModel
    from openstan.views.project_view import ProjectView


class ProjectPresenter(QObject):
    path_or_name_changed: pyqtSignal = pyqtSignal()

    def __init__(self: "ProjectPresenter", model: "ProjectModel", view: "ProjectView") -> None:
        super().__init__()
        self.sessionID: str | None = None  # to be set by StanPresenter
        self.model: "ProjectModel" = model
        self.view: "ProjectView" = view
        self.view.selection.setModel(self.model)
        self.view.selection.setModelColumn(1)  # project_name column
        self.view.selection.setEditable(False)

        # Connect signals
        self.view.button_new.clicked.connect(self.open_new_project_wizard)
        self.view.wizard.page_basic.location_button.clicked.connect(self.open_folder_selection_dialog)
        self.view.wizard.page_basic.name_row.textChanged.connect(self.name_changed)
        self.path_or_name_changed.connect(self.update_location_label)
        self.view.wizard.new_project_required.connect(self.create_new_project)

    @pyqtSlot()
    def create_new_project(self) -> bool:
        error: str = ""
        info: str = ""
        new_pro: tuple[bool, str, str] = self.model.add_record(
            self.view.wizard.page_basic.newProjectID,
            self.view.wizard.page_basic.field("projectName"),
            self.view.wizard.page_basic.field("projectLocation"),
            self.sessionID,
        )
        if new_pro[0]:
            if self.create_project_folder():
                if self.create_subfolders():
                    info = f"Project '{self.view.wizard.page_basic.field('projectName')}' created successfully!"
                    info += f"\nLocation: {self.view.wizard.page_basic.field('projectLocation')}"
                    self.view.wizard.success_dialog.setText("Project Created Successfully")
                    self.view.wizard.success_dialog.setDetailedText(info)
                    if self.view.wizard.success_dialog.exec():
                        self.view.wizard.project_created = True
                        self.model.select()
                        self.view.selection.setCurrentIndex(self.model.rowCount() - 1)
                        self.view.wizard.accept()
                        return True
                else:
                    error = "Failed to create project subfolders."
                    self.view.wizard.back()
                    self.model.delete_record_by_id(self.view.wizard.page_basic.newProjectID)
                    print(error)
                    self.view.wizard.failure_dialog.showMessage(error)
                    return False
            else:
                error = f"Failed to create project folder. \n Does the folder '{self.view.wizard.full_project_path}' already exist?"
                self.view.wizard.back()
                self.model.delete_record_by_id(self.view.wizard.page_basic.newProjectID)
                print(error)
                self.view.wizard.failure_dialog.showMessage(error)
                return False
        else:
            if new_pro[2].startswith("UNIQUE constraint failed: project.project_name"):
                error = f"Project with name '{self.view.wizard.page_basic.field('projectName')}' already exists."
                self.view.wizard.back()
                print(error)
                self.view.wizard.failure_dialog.showMessage(error)
                return False
            else:
                error = f"Failed to create project: {new_pro[2]}"
                self.view.wizard.back()
                print(error)
                self.view.wizard.failure_dialog.showMessage(error)
                return False
        return False

    @pyqtSlot()
    def open_new_project_wizard(self) -> None:
        self.view.wizard.page_basic.location_button.setDisabled(True)
        self.view.wizard.page_basic.newProjectID = uuid4().hex
        self.view.wizard.page_basic.id_row.setText(self.view.wizard.page_basic.newProjectID)
        self.view.wizard.exec()

    @pyqtSlot()
    def name_changed(self) -> None:
        name: str = self.view.wizard.page_basic.name_row.text()
        if len(name) > 0:
            self.view.wizard.page_basic.location_button.setDisabled(False)
        else:
            self.view.wizard.page_basic.location_button.setDisabled(True)
        self.path_or_name_changed.emit()

    @pyqtSlot()
    def update_location_label(self) -> None:
        folder: Path | None = self.view.wizard.page_basic.folder_path
        name: str = self.view.wizard.page_basic.name_row.text()
        if folder and len(name) > 0:
            self.view.wizard.full_project_path = folder.joinpath(name)
            self.view.wizard.page_basic.location_label.setText(str(self.view.wizard.full_project_path.absolute()))
            self.view.wizard.page_basic.location_label.show()
        else:
            self.view.wizard.page_basic.location_label.hide()

    @pyqtSlot()
    def open_folder_selection_dialog(self) -> None:
        if self.view.wizard.page_basic.folder_selection_dialog.exec() == 1:
            self.view.wizard.page_basic.folder_path = Path(self.view.wizard.page_basic.folder_selection_dialog.selectedFiles()[0])
            self.path_or_name_changed.emit()

    # Helper methods
    def create_project_folder(self) -> bool:
        try:
            if self.view.wizard.full_project_path:
                self.view.wizard.full_project_path.mkdir(parents=True, exist_ok=False)
                return True
        except Exception as e:
            print("Error creating project folder:", e)
            return False
        return False

    def create_subfolders(self) -> bool:
        try:
            if self.view.wizard.full_project_path is None:
                return False
            self.view.wizard.full_project_path.joinpath("exports").mkdir()
            self.view.wizard.full_project_path.joinpath("configs").mkdir()
            self.view.wizard.full_project_path.joinpath("logs").mkdir()
            self.view.wizard.full_project_path.joinpath("database").mkdir()
            return True
        except Exception as e:
            print("Error creating project subfolders:", e)
            return False
