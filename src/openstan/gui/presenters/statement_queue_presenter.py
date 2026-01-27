from pathlib import Path
from uuid import uuid4

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSlot as Slot


class StatementQueuePresenter(QObject):
    def __init__(self, model, view, tree_model):
        super().__init__()
        self.sessionID = None  # to be set by StanPresenter
        self.projectID = None  # to be set by StanPresenter
        self.model = model
        self.view = view
        self.tree_model = tree_model
        # self.view.table.setModel(self.model)
        self.view.tree.setModel(self.tree_model)
        self.view.tree.setHeaderHidden(True)
        # Connect signals
        self.view.buttonAddFolders.clicked.connect(self.open_folder_dialog)
        self.view.buttonAddFiles.clicked.connect(self.open_file_dialog)
        self.view.buttonRemove.clicked.connect(self.remove_selected_items)
        self.view.buttonClear.clicked.connect(self.clear_all_items)
        self.view.tree.selectionModel().selectionChanged.connect(self.tree_selection_changed)  # type: ignore

    @Slot()
    def tree_selection_changed(self):
        selected_indexes = self.view.tree.selectionModel().selectedIndexes()  # type: ignore
        selected_paths = [index.data() for index in selected_indexes if index.column() == 1]
        print("Tree selection changed. Selected paths:", selected_paths)

    @Slot()
    def open_folder_dialog(self):
        if self.view.folder_dialog.exec():
            selected_folder = self.view.folder_dialog.selectedFiles()[0]
            print("Selected folder:", selected_folder)
            # add folder as it's own parent
            folder_id = uuid4().hex
            folder_path = Path(selected_folder)
            self.add_record(queue_id=folder_id, parent_id=folder_id, path=folder_path, is_folder=1)
            # add each file in the folder as child items
            for file in folder_path.iterdir():
                if file.is_file() and file.suffix.lower() == ".pdf":
                    file_id = uuid4().hex
                    self.add_record(queue_id=file_id, parent_id=folder_id, path=file, is_folder=0)
            self.update_view()

    @Slot()
    def open_file_dialog(self):
        if self.view.file_dialog.exec():
            selected_files = self.view.file_dialog.selectedFiles()
            print("Selected files:", selected_files)
            for file in selected_files:
                file_id = uuid4().hex
                self.add_record(queue_id=file_id, parent_id=file_id, path=Path(file), is_folder=0)
            self.update_view()

    @Slot()
    def remove_selected_items(self):
        # Logic to remove selected items from the model/view
        selected_indexes = self.view.tree.selectionModel().selectedIndexes()
        selected_ids: list[str] = [str(index.data()) for index in selected_indexes if index.column() == 1]
        self.model.delete_records(queue_ids = selected_ids)
        self.update_view()

    @Slot()
    def clear_all_items(self):
        result = self.model.clear_records()
        print(result)
        self.update_view()

    def add_record(self, queue_id, parent_id, path, is_folder):
        # Logic to add a record to the model
        success, queue_id, error = self.model.add_record(
            queue_id=queue_id,
            parent_id=parent_id,
            project_id=self.projectID,
            session_id=self.sessionID,
            status_id=0,  # pending status
            path=path,
            is_folder=is_folder,
        )
        if not success:
            print(f"Error adding record: {error}")
        else:
            print(f"Record added successfully: {queue_id}")

    def get_records(self):
        # Logic to retrieve records from the model
        pass

    def update_view(self):
        if self.projectID is not None:
            self.model.setFilter(f"project_id = '{self.projectID}'")
            self.model.select()
            self.tree_model.update_model(self.projectID)
            # self.view.table.resizeColumnsToContents()
            # self.view.tree.expandAll()
            self.view.tree.expandToDepth(0)
        else:
            print("Project ID is not set. Cannot update view.")
