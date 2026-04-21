from datetime import datetime
from uuid import uuid4

from PyQt6.QtSql import QSqlQuery, QSqlRecord, QSqlTableModel

NEW_RECORD_STATUS = 8  # active status


class UserModel(QSqlTableModel):
    def __init__(self, db) -> None:
        super().__init__(db=db)
        self.setTable("user")
        self.select()

    def add_record(self, username: str, sessionID: str) -> tuple[bool, str, str]:
        msg: str = ""
        user_id: str = uuid4().hex
        record: QSqlRecord = self.record()
        record.setValue("user_id", user_id)
        record.setValue("username", username)
        record.setValue("createdBy_session", sessionID)
        record.setValue("updatedBy_session", sessionID)
        record.setValue("created", datetime.now())
        record.setValue("updated", datetime.now())
        record.setValue("status_id", NEW_RECORD_STATUS)  # active status
        if self.insertRecord(-1, record):
            self.submitAll()
            msg = f"User record {user_id} successfully added"
            return (True, user_id, msg)
        else:
            msg = self.lastError().text()
            return (False, user_id, msg)

    def user_id_from_username(self, username: str) -> str | None:
        query = QSqlQuery(self.database())
        query.prepare("SELECT user_id FROM user WHERE username = :username")
        query.bindValue(":username", username)
        if query.exec() and query.last():
            return str(query.value("user_id"))
        return None
