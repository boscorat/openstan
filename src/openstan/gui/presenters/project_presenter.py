from pathlib import Path
from uuid import uuid4

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal as Signal
from PyQt6.QtCore import pyqtSlot as Slot


class ProjectPresenter(QObject):
    path_or_name_changed = Signal()

    def __init__(self, model, view):
        super().__init__()
        self.sessionID = None  # to be set by StanPresenter
        self.model = model
        self.view = view
        self.wizard = self.view.wizard
        self.page_basic = self.wizard.page_basic
        self.view.selection.setModel(self.model)
        self.view.selection.setModelColumn(1)  # project_name column
        self.view.selection.setEditable(False)

        # Connect signals
        self.view.selection.currentIndexChanged.connect(self.project_selection_changed)
        self.view.button_new.clicked.connect(self.open_new_project_wizard)
        self.page_basic.location_button.clicked.connect(self.open_folder_selection_dialog)
        self.page_basic.name_row.textChanged.connect(self.name_changed)
        self.path_or_name_changed.connect(self.update_location_label)
        self.wizard.new_project_required.connect(self.create_new_project)

    @Slot()
    def create_new_project(self):
        new_pro = self.model.add_record(
            self.page_basic.newProjectID, self.page_basic.field("projectName"), self.page_basic.field("projectLocation"), self.sessionID
        )
        if new_pro[0]:
            if self.create_project_folder():
                if self.create_subfolders():
                    info = f"Project '{self.page_basic.field('projectName')}' created successfully!"
                    info += f"\nLocation: {self.page_basic.field('projectLocation')}"
                    self.wizard.success_dialog.setText("Project Created Successfully")
                    self.wizard.success_dialog.setDetailedText(info)
                    if self.wizard.success_dialog.exec():
                        self.wizard.project_created = True
                        self.model.select()
                        self.view.selection.setCurrentIndex(self.model.rowCount() - 1)
                        self.wizard.accept()
                        return True
                else:
                    error = "Failed to create project subfolders."
                    self.wizard.back()
                    self.model.delete_record_by_id(self.page_basic.newProjectID)
                    print(error)
                    self.wizard.failure_dialog.showMessage(error)
                    return False
            else:
                error = f"Failed to create project folder. \n Does the folder '{self.wizard.full_project_path}' already exist?"
                self.wizard.back()
                self.model.delete_record_by_id(self.page_basic.newProjectID)
                print(error)
                self.wizard.failure_dialog.showMessage(error)
                return False
        else:
            if new_pro[2].startswith("UNIQUE constraint failed: project.project_name"):
                error = f"Project with name '{self.page_basic.field('projectName')}' already exists."
                self.wizard.back()
                print(error)
                self.wizard.failure_dialog.showMessage(error)
                return False
            else:
                error = f"Failed to create project: {new_pro[2]}"
                self.wizard.back()
                print(error)
                self.wizard.failure_dialog.showMessage(error)
                return False

    @Slot(int)
    def project_selection_changed(self, index):
        current_record = self.model.record(index)
        current_project_name = self.view.selection.currentText()
        current_project_id = current_record.value("project_ID")
        # Here you can add logic to update other parts of the application
        print(f"SLOT: ProjectPresenter.project_selection_changed: {current_project_name} (ID: {current_project_id})")

    @Slot()
    def open_new_project_wizard(self):
        self.page_basic.location_button.setDisabled(True)
        self.page_basic.newProjectID = uuid4().hex
        self.page_basic.id_row.setText(self.page_basic.newProjectID)
        self.wizard.exec()

    @Slot()
    def name_changed(self):
        name = self.page_basic.name_row.text()
        if len(name) > 0:
            self.page_basic.location_button.setDisabled(False)
        else:
            self.page_basic.location_button.setDisabled(True)
        self.path_or_name_changed.emit()

    @Slot()
    def update_location_label(self):
        folder = self.page_basic.folder_path
        name = self.page_basic.name_row.text()
        if folder and name:
            self.wizard.full_project_path = folder.joinpath(name)
            self.page_basic.location_label.setText(str(self.wizard.full_project_path.absolute()))
            self.page_basic.location_label.show()
        else:
            self.page_basic.location_label.hide()

    @Slot()
    def open_folder_selection_dialog(self):
        dialog = self.page_basic.folder_selection_dialog
        if self.page_basic.folder_selection_dialog.exec() == 1:
            self.page_basic.folder_path = Path(dialog.selectedFiles()[0])
            self.path_or_name_changed.emit()

    # Helper methods
    def create_project_folder(self):
        try:
            self.wizard.full_project_path.mkdir(parents=True, exist_ok=False)
            return True
        except Exception as e:
            print("Error creating project folder:", e)
            return False

    def create_subfolders(self):
        try:
            self.wizard.full_project_path.joinpath("exports").mkdir()
            self.wizard.full_project_path.joinpath("configs").mkdir()
            self.wizard.full_project_path.joinpath("logs").mkdir()
            self.wizard.full_project_path.joinpath("database").mkdir()
            return True
        except Exception as e:
            print("Error creating project subfolders:", e)
            return False
