from PyQt6.QtWidgets import QGridLayout

from openstan.components import Qt, StanLabel, StanWidget


class FooterView(StanWidget):
    def __init__(self) -> None:
        super().__init__()
        self.labelCopy = StanLabel("##### © 2025 Jason Farrar")
        self.labelUser = StanLabel("##### User: None")
        self.labelProject = StanLabel("##### Project: None (ID: None)")

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
            self.labelCopy,
            0,
            3,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )
        self.setLayout(layout)
        self.setMaximumHeight(40)
