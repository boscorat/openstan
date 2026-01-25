from datetime import datetime

from PyQt6.QtCore import pyqtSignal as Signal
from PyQt6.QtSql import QSqlTableModel

NEW_RECORD_STATUS = 8  # active status


class ProjectModel(QSqlTableModel):
    db_updated = Signal()

    def __init__(self, db):
        super().__init__(db=db)
        self.setTable("project")
        self.select()

    def add_record(self, project_id, project_name, project_location, sessionID) -> tuple[bool, str, str | None]:
        record = self.record()
        record.setValue("project_ID", project_id)
        record.setValue("project_name", project_name)
        record.setValue("project_location", project_location)
        record.setValue("createdBy_session", sessionID)
        record.setValue("updatedBy_session", sessionID)
        record.setValue("created", datetime.now())
        record.setValue("updated", datetime.now())
        record.setValue("status_id", NEW_RECORD_STATUS)
        if self.insertRecord(-1, record):
            if self.submitAll():
                self.db_updated.emit()
                return (True, project_id, None)
            else:
                return (False, project_id, self.lastError().text())
        else:
            return (False, project_id, self.lastError().text())

    def delete_record_by_id(self, project_id) -> tuple[bool, str, str | None]:
        for row in range(self.rowCount()):
            record = self.record(row)
            if record.value("project_ID") == project_id:
                self.removeRow(row)
                if self.submitAll():
                    self.db_updated.emit()
                    return (True, project_id, None)
                else:
                    return (False, project_id, self.lastError().text())
        return (False, project_id, self.lastError().text())
