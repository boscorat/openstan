from typing import TYPE_CHECKING
from uuid import uuid4

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from openstan.models.session_model import SessionModel


class SessionPresenter(QObject):
    db_lock_signal = pyqtSignal()

    def __init__(self: "SessionPresenter", model: "SessionModel", view=None) -> None:
        super().__init__()
        self.model: "SessionModel" = model
        self.view = view
        if self.view is not None:
            self.view.setModel(self.model)

    def end_active_sessions(self) -> tuple[bool, str, str]:
        result: tuple[bool, str, str] = self.model.end_active_sessions()
        if not result[0]:
            print("Failed to end active sessions in the database.")
            self.db_lock_signal.emit()
        return result

    def new_session(self, userID: str) -> tuple[bool, str, str]:
        result: tuple[bool, str, str] = self.model.add_record(uuid4().hex, userID)
        msg: str = ""
        if not result[0]:
            msg = "Failed to create or retrieve session ID from the database. Do you have another active session?"
            self.db_lock_signal.emit()
        else:
            sessionID: str = result[1]
            msg: str = f"Session created successfully: {sessionID} for user ID: {userID}"
            return result
        print(msg)
        return result
