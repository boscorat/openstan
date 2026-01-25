from PyQt6.QtSql import QSqlTableModel


class EventLogModel(QSqlTableModel):
    def __init__(self, db):
        super().__init__(None, db)
        self.setTable("event_log")
        self.select()
