from datetime import datetime

from PyQt6.QtSql import QSqlTableModel


class SessionModel(QSqlTableModel):
    def __init__(self, db):
        super().__init__(db=db)
        self.setTable("session")
        self.select()

    def add_record(self, session_id, user_id) -> tuple[bool, str, str | None]:
        record = self.record()
        record.setValue("session_id", session_id)
        record.setValue("user_id", user_id)
        record.setValue("created", datetime.now())
        record.setValue("terminated", None)
        record.setValue("is_active", 1)
        if self.insertRecord(-1, record):
            self.submitAll()
            return (True, session_id, None)
        return (False, session_id, self.lastError().text())

    def end_active_sessions(self) -> tuple[bool, str, str | None]:
        sessions_ended = 0
        for row in range(self.rowCount()):
            record = self.record(row)
            if record.value("is_active"):
                self.setData(self.index(row, self.fieldIndex("terminated")), datetime.now())
                self.setData(self.index(row, self.fieldIndex("is_active")), 0)
                self.submitAll()
                sessions_ended += 1
        if sessions_ended > 0:
            print(f"Ended {sessions_ended} active sessions.")
            return (True, f"{sessions_ended} sessions ended", None)
        else:
            print("No active sessions to end.")
            return (False, "No active sessions ended", self.lastError().text())
