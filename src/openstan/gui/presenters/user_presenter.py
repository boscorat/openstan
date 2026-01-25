from PyQt6.QtCore import QObject


class UserPresenter(QObject):
    def __init__(self, model, view=None):
        super().__init__()
        self.model = model
        self.view = view
        if self.view is not None:
            self.view.setModel(self.model)

    def create_new_user(self, username, sessionID) -> bool:
        user_db = self.model.add_record(username, sessionID)
        if not user_db[0]:
            print("Failed to create or retrieve user ID from the database.")
            return False
        else:
            userID = user_db[1]
            msg = f"User created successfully: {username} (ID: {userID})"
            print(msg)
            return userID
