from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout

from openstan.gui.components import StanFrame


class ContentFrameView(StanFrame):
    def __init__(self, widgets):
        super().__init__()
        self.widgets = widgets
        layout = QGridLayout()
        for w in self.widgets:
            layout.addWidget(w[0], w[1], w[2], alignment=Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)
