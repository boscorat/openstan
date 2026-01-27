from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from PyQt6.QtCore import QObject, pyqtSlot

if TYPE_CHECKING:
    from openstan.gui.models.statement_queue_model import StatementQueueModel, StatementQueueTreeModel
    from openstan.gui.views.statement_queue_view import StatementQueueView


class StatementQueuePresenter(QObject):
    def __init__(
        self: "StatementQueuePresenter", model: "StatementQueueModel", view: "StatementQueueView", tree_model: "StatementQueueTreeModel"
    ) -> None:
        super().__init__()
        self.sessionID: str | None = None  # to be set by StanPresenter
        self.projectID: str | None = None  # to be set by StanPresenter
        self.model: "StatementQueueModel" = model
        self.view: "StatementQueueView" = view
        self.tree_model: "StatementQueueTreeModel" = tree_model
        # self.view.table.setModel(self.model)
        self.view.tree.setModel(self.tree_model)
        self.view.tree.setHeaderHidden(True)
        # Connect signals
        self.view.buttonAddFolders.clicked.connect(self.open_folder_dialog)
        self.view.buttonAddFiles.clicked.connect(self.open_file_dialog)
        self.view.buttonRemove.clicked.connect(self.remove_selected_items)
        self.view.buttonClear.clicked.connect(self.clear_all_items)

    @pyqtSlot()
    def open_folder_dialog(self) -> None:
        if self.view.folder_dialog.exec():
            selected_folder: str = self.view.folder_dialog.selectedFiles()[0]
            print("Selected folder:", selected_folder)
            # add folder as it's own parent
            folder_id: str = uuid4().hex
            folder_path = Path(selected_folder)
            self.add_record(queue_id=folder_id, parent_id=folder_id, path=folder_path, is_folder=1)
            # add each file in the folder as child items
            for file in folder_path.iterdir():
                if file.is_file() and file.suffix.lower() == ".pdf":
                    file_id: str = uuid4().hex
                    self.add_record(queue_id=file_id, parent_id=folder_id, path=file, is_folder=0)
            self.update_view()

    @pyqtSlot()
    def open_file_dialog(self) -> None:
        if self.view.file_dialog.exec():
            selected_files: list[str] = self.view.file_dialog.selectedFiles()
            print("Selected files:", selected_files)
            for file in selected_files:
                file_id = uuid4().hex
                self.add_record(queue_id=file_id, parent_id=file_id, path=Path(file), is_folder=0)
            self.update_view()

    @pyqtSlot()
    def remove_selected_items(self) -> None:
        # Logic to remove selected items from the model/view
        selected_indexes: list | None = self.view.tree.selectedIndexes()
        if not selected_indexes:
            return
        selected_ids: list[str] = [str(index.data()) for index in selected_indexes if index.column() == 1]
        self.model.delete_records(queue_ids=selected_ids)
        self.update_view()

    @pyqtSlot()
    def clear_all_items(self) -> None:
        result: tuple[bool, list[str], str] = self.model.clear_records()
        print(result)
        self.update_view()

    def add_record(self, queue_id, parent_id, path, is_folder) -> None:
        # Logic to add a record to the model
        result: tuple[bool, str, str] = self.model.add_record(
            queue_id=queue_id,
            parent_id=parent_id,
            project_id=self.projectID,
            session_id=self.sessionID,
            status_id=0,  # pending status
            path=path,
            is_folder=is_folder,
        )
        if not result[0]:
            print(f"Error adding record: {result[2]}")
        else:
            print(f"Record added successfully: {queue_id}")

    def get_records(self) -> None:
        # Logic to retrieve records from the model
        pass

    def update_view(self) -> None:
        if self.projectID is not None:
            self.model.setFilter(f"project_id = '{self.projectID}'")
            self.model.select()
            self.tree_model.update_model(self.projectID)
            # self.view.table.resizeColumnsToContents()
            # self.view.tree.expandAll()
            self.view.tree.expandToDepth(0)
        else:
            print("Project ID is not set. Cannot update view.")
