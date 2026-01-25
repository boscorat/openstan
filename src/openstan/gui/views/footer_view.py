from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout

from openstan.gui.components import StanLabel, StanWidget


class FooterView(StanWidget):
    def __init__(self, stan):
        super().__init__()
        self.sessionID = stan.sessionID
        self.username = stan.username
        self.labelCopy = StanLabel("##### StanCafe © 2026")
        self.labelUser = StanLabel(f"##### User: {self.username} | Session: {self.sessionID}")
        self.labelProject = StanLabel("##### Project: None (ID: None)")
        layout = QGridLayout()
        layout.addWidget(self.labelCopy, 0, 3, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.labelUser, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.labelProject, 0, 2, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self.setLayout(layout)
        self.setMaximumHeight(40)
