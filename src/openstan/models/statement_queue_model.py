from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtSql import QSqlRecord, QSqlTableModel


class StatementQueueModel(QSqlTableModel):
    """SQL table model for the ``statement_queue`` table.

    Always scoped to a single project.  Call ``set_project(project_id)`` once
    when the active project changes; every other method then operates on the
    already-filtered view without touching the filter again.
    """

    db_updated: pyqtSignal = pyqtSignal()

    def __init__(self, db) -> None:
        super().__init__(None, db)
        self.setTable("statement_queue")
        self._project_id: str | None = None
        self.select()

    # ---------------------------------------------------------------------------
    # Project scoping
    # ---------------------------------------------------------------------------

    def set_project(self, project_id: str) -> None:
        """Switch the model to *project_id* and reload rows.

        Sets the canonical ``project_id`` filter that all other methods rely on.
        Call this whenever the active project changes.
        """
        self._project_id = project_id
        self.setFilter(f"project_id = '{project_id}'")
        self.select()

    # ---------------------------------------------------------------------------
    # Queue modification
    # ---------------------------------------------------------------------------

    def add_record(
        self, queue_id, parent_id, session_id, status_id, path, is_folder=0
    ) -> tuple[bool, str, str]:
        msg: str = ""
        record: QSqlRecord = self.record()
        record.setValue("queue_id", queue_id)
        record.setValue("parent_id", parent_id)
        record.setValue("project_id", self._project_id)
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
        # Pass 1 — delete children first to satisfy the self-referencing FK
        for row in range(self.rowCount()):
            record: QSqlRecord = self.record(last_record - row)
            print(record.value("parent_id"))
            if record.value("parent_id") in queue_ids:
                if record.value("queue_id") != record.value("parent_id"):  # child row
                    children_deleted.append(record.value("queue_id"))
                    self.removeRow(last_record - row)
                else:  # stand-alone own-parent record (folder or loose file)
                    if record.value("is_folder") == 1:
                        folders_deleted.append(record.value("queue_id"))
                    else:
                        files_deleted.append(record.value("queue_id"))
                    self.removeRow(last_record - row)
        # Pass 2 — remove any remaining parent rows
        last_record = self.rowCount()  # recount after child deletions
        for row in range(self.rowCount()):
            record = self.record(last_record - row)
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
            msg = (
                f"success - {len(folders_deleted)} folder(s) containing "
                f"{len(children_deleted)} file(s) deleted and "
                f"{len(files_deleted)} individual file(s) deleted"
            )
            print(msg)
            return (success, all_deleted, msg)
        else:
            msg = "failure to delete any records"
            return (success, queue_ids, msg)

    def clear_records(self) -> tuple[bool, list[str], str]:
        queue_ids: list[str] = list()
        print(f"Clearing queue with {self.rowCount()} records")
        for row in range(self.rowCount()):
            record: QSqlRecord = self.record(row)
            print(record.value("queue_id"), record.value("parent_id"))
            # Collect only parent records; children are removed automatically
            if record.value("queue_id") == record.value("parent_id"):
                queue_ids.append(record.value("queue_id"))
        return self.delete_records(queue_ids)

    # ---------------------------------------------------------------------------
    # Batch lock / unlock
    # ---------------------------------------------------------------------------

    def set_batch_id(self, batch_id: str) -> tuple[bool, str]:
        """Lock the queue by stamping every row with *batch_id*.

        Called at the start of a statement import run.  Returns (success, message).
        """
        for row in range(self.rowCount()):
            record: QSqlRecord = self.record(row)
            record.setValue("batch_id", batch_id)
            self.setRecord(row, record)
        if self.submitAll():
            self.select()
            return (True, f"Queue locked with batch_id {batch_id}")
        return (False, self.lastError().text())

    def clear_batch_id(self) -> tuple[bool, str]:
        """Unlock the queue by clearing batch_id on every row.

        Called when a batch is abandoned or committed.  Returns (success, message).
        """
        for row in range(self.rowCount()):
            record: QSqlRecord = self.record(row)
            record.setValue("batch_id", None)
            self.setRecord(row, record)
        if self.submitAll():
            self.select()
            return (True, "Queue unlocked")
        return (False, self.lastError().text())

    def get_batch_id(self) -> str | None:
        """Return the active batch_id for the current project, or None if unlocked.

        All rows for a given project share the same batch_id so checking row 0
        is sufficient.  Returns None if the queue is empty or unlocked.
        """
        if self.rowCount() == 0:
            return None
        value = self.record(0).value("batch_id")
        # QSqlTableModel returns None or empty string for NULL
        if value is None or value == "":
            return None
        return str(value)

    def is_locked(self) -> bool:
        """Return True if the queue has an active batch in flight."""
        return self.get_batch_id() is not None

    def get_folder_paths_for_batch(self, batch_id: str) -> str:
        """Return '|'-joined path values of is_folder=1 rows for *batch_id*.

        Used by the commit worker to build the ``path`` argument for
        ``bsp.update_db``.  Returns an empty string if no folder rows exist
        (e.g. the batch contained only individually-queued files).

        Iterates the already-filtered rows without changing the model filter.
        """
        paths: list[str] = []
        for row in range(self.rowCount()):
            record: QSqlRecord = self.record(row)
            if record.value("is_folder") != 1:
                continue
            if record.value("batch_id") != batch_id:
                continue
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
                parent_path.setData(record.value("path"), Qt.ItemDataRole.UserRole)
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
