from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QGridLayout

from openstan.components import Qt, StanLabel, StanWidget


class FooterView(StanWidget):
    admin_requested: pyqtSignal = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.labelCopy = StanLabel("##### openstan © 2026")
        self.labelUser = StanLabel("##### User: None | Session: None")
        self.labelProject = StanLabel("##### Project: None (ID: None)")
        self.labelAdmin = StanLabel("##### Double-click for admin options")
        layout = QGridLayout()
        layout.addWidget(
            self.labelUser,
            0,
            0,
            1,
            2,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )
        layout.addWidget(
            self.labelProject,
            0,
            2,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )
        layout.addWidget(
            self.labelAdmin,
            0,
            3,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )
        layout.addWidget(
            self.labelCopy,
            0,
            4,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )
        self.setLayout(layout)
        self.setMaximumHeight(40)

    def mouseDoubleClickEvent(self, a0: QMouseEvent | None) -> None:  # noqa: N802
        self.admin_requested.emit()
