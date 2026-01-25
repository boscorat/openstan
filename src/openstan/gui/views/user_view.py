from PyQt6.QtWidgets import QTableView


class UserView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Additional initialization code can be added here
        self.setWindowTitle("User View")
        self.resizeColumnsToContents()
        self.setDisabled(True)
