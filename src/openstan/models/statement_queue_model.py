from PyQt6.QtCore import pyqtSignal as Signal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtSql import QSqlTableModel, QSqlRecord


class StatementQueueModel(QSqlTableModel):
    db_updated: Signal = Signal()

    def __init__(self, db) -> None:
        super().__init__(None, db)
        self.setTable("statement_queue")
        self.select()

    def add_record(
        self, queue_id, parent_id, project_id, session_id, status_id, path, is_folder=0
    ) -> tuple[bool, str, str]:
        msg: str = ""
        record: QSqlRecord = self.record()
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
            msg = f"Queue record {queue_id} successfully added"
            return (True, queue_id, msg)
        else:
            msg = self.lastError().text()
            return (False, queue_id, msg)

    def delete_records(self, queue_ids: list[str]) -> tuple[bool, list[str], str]:
        success: bool = bool(False)
        msg: str = ""
        children_deleted: list[str] = list()
        folders_deleted: list[str] = list()
        files_deleted: list[str] = list()
        all_deleted: list[str] = list()
        last_record: int = self.rowCount() - 1
        # any children first
        for row in range(self.rowCount()):
            record: QSqlRecord = self.record(last_record - row)
            print(record.value("parent_id"))
            if record.value("parent_id") in queue_ids:  # is it a parent record?
                if record.value("queue_id") != record.value(
                    "parent_id"
                ):  # if it's not it's own parent then it's a child record
                    children_deleted.append(record.value("queue_id"))
                    self.removeRow(last_record - row)
                else:  # it must be a stand-alone record that's it's own parent
                    if record.value("is_folder") == 1:
                        folders_deleted.append(record.value("queue_id"))
                    else:
                        files_deleted.append(record.value("queue_id"))
                    self.removeRow(last_record - row)
            else:  # we pass on parent only records until all children have been removed due to self-referencing foreign key
                pass
        # now we re-count and remove any parents
        last_record = self.rowCount()  # update record caount after child deletions
        for row in range(self.rowCount()):
            record: QSqlRecord = self.record(last_record - row)
            if record.value("queue_id") in queue_ids:
                if record.value("is_folder") == 1:
                    folders_deleted.append(record.value("queue_id"))
                else:
                    files_deleted.append(record.value("queue_id"))
                self.removeRow(last_record - row)

        if self.submitAll():
            all_deleted.extend(children_deleted)
            all_deleted.extend(folders_deleted)
            all_deleted.extend(files_deleted)
            success = bool(True)
            self.db_updated.emit()
            msg = f"success - {str(len(folders_deleted))} folder(s) containing {str(len(children_deleted))} file(s) deleted and {str(len(files_deleted))} individual file(s) deleted"
            print(msg)
            return (success, all_deleted, msg)
        else:
            msg = "failure to delete any records"
            return (success, queue_ids, msg)

    def clear_records(self) -> tuple[bool, list[str], str]:
        queue_ids: list[str] = list()
        for row in range(self.rowCount()):
            record: QSqlRecord = self.record(row)
            if (
                record.value("queue_id") == record.value("parent_id")
            ):  # we only need to collect parent records as the children will be removed automatically
                queue_ids.append(record.value("queue_id"))
            else:
                pass
        return self.delete_records(queue_ids)

    # ---------------------------------------------------------------------------
    # Batch lock / unlock
    # ---------------------------------------------------------------------------

    def set_batch_id(self, project_id: str, batch_id: str) -> tuple[bool, str]:
        """Lock the queue for *project_id* by stamping every row with *batch_id*.

        Called at the start of a statement import run.  Returns (success, message).
        """
        self.setFilter(f"project_id = '{project_id}'")
        self.select()
        for row in range(self.rowCount()):
            record: QSqlRecord = self.record(row)
            record.setValue("batch_id", batch_id)
            self.setRecord(row, record)
        if self.submitAll():
            self.select()
            return (True, f"Queue locked with batch_id {batch_id}")
        return (False, self.lastError().text())

    def clear_batch_id(self, project_id: str) -> tuple[bool, str]:
        """Unlock the queue for *project_id* by clearing batch_id on every row.

        Called when a batch is abandoned.  Returns (success, message).
        """
        self.setFilter(f"project_id = '{project_id}'")
        self.select()
        for row in range(self.rowCount()):
            record: QSqlRecord = self.record(row)
            record.setValue("batch_id", None)
            self.setRecord(row, record)
        if self.submitAll():
            self.select()
            return (True, "Queue unlocked")
        return (False, self.lastError().text())

    def get_batch_id(self, project_id: str) -> str | None:
        """Return the active batch_id for *project_id*, or None if unlocked.

        Reads the first non-folder row's batch_id value.  All rows for a given
        project share the same batch_id so checking one is sufficient.
        """
        self.setFilter(f"project_id = '{project_id}' AND is_folder = 0")
        self.select()
        if self.rowCount() == 0:
            return None
        value = self.record(0).value("batch_id")
        # QSqlTableModel returns None or empty string for NULL
        if value is None or value == "":
            return None
        return str(value)

    def is_locked(self, project_id: str) -> bool:
        """Return True if the queue for *project_id* has an active batch in flight."""
        return self.get_batch_id(project_id) is not None

    def get_folder_paths_for_batch(self, batch_id: str) -> str:
        """Return '|'-joined path values of is_folder=1 rows for *batch_id*.

        Used by the commit worker to build the ``path`` argument for
        ``bsp.update_db``.  Returns an empty string if no folder rows exist
        (e.g. the batch contained only individually-queued files).
        """
        self.setFilter(f"batch_id = '{batch_id}' AND is_folder = 1")
        self.select()
        paths: list[str] = []
        for row in range(self.rowCount()):
            record: QSqlRecord = self.record(row)
            value = record.value("path")
            if value:
                paths.append(str(value))
        return "|".join(paths)


class StatementQueueTreeModel(QStandardItemModel):
    parent_filter = "parent_id = queue_id"
    child_filter = "parent_id != queue_id"

    def __init__(self, db) -> None:
        super().__init__()
        self.parent_model = StatementQueueModel(db=db)
        self.child_model = StatementQueueModel(db=db)

    def update_model(self, project_id) -> None:
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
            record: QSqlRecord = self.parent_model.record(row)
            child_count = 0
            is_own_parent = record.value("queue_id") == record.value("parent_id")
            if is_own_parent:
                is_folder = record.value("is_folder")
                parent_id = QStandardItem(record.value("queue_id"))
                parent_path = QStandardItem(record.value("path"))
                child_filter: str = f"parent_id = '{record.value('queue_id')}' AND queue_id != parent_id"
                self.child_model.setFilter(child_filter)
                if self.child_model.rowCount() > 0:
                    for child_row in range(self.child_model.rowCount()):
                        child: QSqlRecord = self.child_model.record(child_row)
                        child_id_item = QStandardItem(child.value("queue_id"))
                        child_path_item = QStandardItem(child.value("path"))
                        parent_path.appendRow([child_path_item, child_id_item])
                        child_count += 1
                if is_folder:
                    if child_count == 0:
                        parent_path.setText(parent_path.text() + " (empty)")
                    else:
                        parent_path.setText(
                            parent_path.text() + f" ({child_count} pdf files)"
                        )
                    folders_root.appendRow([parent_path, parent_id])
                    folder_count += 1
                else:
                    files_root.appendRow([parent_path, parent_id])
                    file_count += 1

        if folder_count > 0:
            self.appendRow(folders_root)
        if file_count > 0:
            self.appendRow(files_root)
