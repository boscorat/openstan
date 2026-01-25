from datetime import datetime
from uuid import uuid4

from PyQt6.QtSql import QSqlTableModel

NEW_RECORD_STATUS = 8  # active status


class UserModel(QSqlTableModel):
    def __init__(self, db):
        super().__init__(db=db)
        self.setTable("user")
        self.select()

    def add_record(self, username: str, sessionID: str) -> tuple[bool, str, str | None]:
        user_id = uuid4().hex
        record = self.record()
        record.setValue("user_id", user_id)
        record.setValue("username", username)
        record.setValue("createdBy_session", sessionID)
        record.setValue("updatedBy_session", sessionID)
        record.setValue("created", datetime.now())
        record.setValue("updated", datetime.now())
        record.setValue("status_id", NEW_RECORD_STATUS)  # active status
        if self.insertRecord(-1, record):
            self.submitAll()
            return (True, user_id, None)
        else:
            return (False, user_id, self.lastError().text())

    def user_id_from_username(self, username: str) -> str | None:
        filter_str = f"username = '{username}'"
        self.setFilter(filter_str)
        self.select()
        if self.rowCount() > 0:
            return self.record(self.rowCount() - 1).value("user_id")
        else:
            return None
