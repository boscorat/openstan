from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject

if TYPE_CHECKING:
    from openstan.gui.models.user_model import UserModel


class UserPresenter(QObject):
    def __init__(self: "UserPresenter", model: "UserModel", view=None) -> None:
        super().__init__()
        self.model: "UserModel" = model
        self.view = view
        if self.view is not None:
            self.view.setModel(self.model)

    def create_new_user(self, username, sessionID) -> tuple[bool, str, str]:
        result: tuple[bool, str, str] = self.model.add_record(username, sessionID)
        if not result[0]:
            print("Failed to create or retrieve user ID from the database.")
            return result
        else:
            msg: str = f"User created successfully: {username} (ID: {result[1]})"
            print(msg)
            return result
