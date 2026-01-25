from uuid import uuid4

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal as Signal


class SessionPresenter(QObject):
    db_lock_signal = Signal()

    def __init__(self, model, view=None):
        super().__init__()
        self.model = model
        self.view = view
        if self.view is not None:
            self.view.setModel(self.model)

    def end_active_sessions(self, sessionID, userID):
        session_db = self.model.end_active_sessions()
        if not session_db[0]:
            print("Failed to end active sessions in the database.")
            self.db_lock_signal.emit()
            return False
        else:
            return True

    def new_session(self, userID):
        session_db = self.model.add_record(uuid4().hex, userID)
        if not session_db[0]:
            print("Failed to create or retrieve session ID from the database. Do you have another active session?")
            self.db_lock_signal.emit()
            return False
        else:
            sessionID = session_db[1]
            return sessionID
