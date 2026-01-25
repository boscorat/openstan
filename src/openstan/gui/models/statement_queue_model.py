from PyQt6.QtCore import pyqtSignal as Signal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtSql import QSqlTableModel


class StatementQueueModel(QSqlTableModel):
    db_updated = Signal()

    def __init__(self, db):
        super().__init__(None, db)
        self.setTable("statement_queue")
        self.select()

    def add_record(self, queue_id, parent_id, project_id, session_id, status_id, path, is_folder=0) -> tuple[bool, str, str | None]:
        record = self.record()
        record.setValue("queue_id", queue_id)
        record.setValue("parent_id", parent_id)
        record.setValue("project_id", project_id)
        record.setValue("session_id", session_id)
        record.setValue("status_id", status_id)
        record.setValue("path", path)
        record.setValue("is_folder", is_folder)
        if self.insertRecord(-1, record):
            self.submitAll()
            self.db_updated.emit()
            return (True, queue_id, None)
        else:
            return (False, queue_id, self.lastError().text())

    def delete_record_by_id(self, queue_id):
        for row in range(self.rowCount()):
            record = self.record(row)
            if record.value("queue_id") == queue_id:
                self.removeRow(row)
                if self.submitAll():
                    self.db_updated.emit()
                    return (True, queue_id, None)
                else:
                    return (False, queue_id, self.lastError().text())
        return (False, queue_id, self.lastError().text())


class StatementQueueTreeModel(QStandardItemModel):
    parent_filter = "parent_id = queue_id"
    child_filter = "parent_id != queue_id"

    def __init__(self, db):
        super().__init__()
        self.parent_model = StatementQueueModel(db=db)
        self.child_model = StatementQueueModel(db=db)

    def update_model(self, project_id):
        self.parent_filter = f"parent_id = queue_id AND project_id = '{project_id}'"
        self.parent_model.setFilter(self.parent_filter)
        self.parent_model.select()
        self.child_filter = f"parent_id != queue_id AND project_id = '{project_id}'"
        self.child_model.setFilter(self.child_filter)
        self.child_model.select()
        self.clear()
        files_root = QStandardItem("Files")
        folders_root = QStandardItem("Folders")
        folder_count = 0
        file_count = 0

        for row in range(self.parent_model.rowCount()):
            record = self.parent_model.record(row)
            child_count = 0
            is_own_parent = record.value("queue_id") == record.value("parent_id")
            if is_own_parent:
                is_folder = record.value("is_folder")
                parent_id = QStandardItem(record.value("queue_id"))
                parent_path = QStandardItem(record.value("path"))
                child_filter = f"parent_id = '{record.value('queue_id')}' AND queue_id != parent_id"
                self.child_model.setFilter(child_filter)
                if self.child_model.rowCount() > 0:
                    for child_row in range(self.child_model.rowCount()):
                        child = self.child_model.record(child_row)
                        child_id_item = QStandardItem(child.value("queue_id"))
                        child_path_item = QStandardItem(child.value("path"))
                        parent_path.appendRow([child_path_item, child_id_item])
                        child_count += 1
                if is_folder:
                    if child_count == 0:
                        parent_path.setText(parent_path.text() + " (empty)")
                    else:
                        parent_path.setText(parent_path.text() + f" ({child_count} pdf files)")
                    folders_root.appendRow([parent_path, parent_id])
                    folder_count += 1
                else:
                    files_root.appendRow([parent_path, parent_id])
                    file_count += 1

        if folder_count > 0:
            self.appendRow(folders_root)
        if file_count > 0:
            self.appendRow(files_root)
