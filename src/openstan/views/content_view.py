from PyQt6.QtWidgets import QGridLayout

from openstan.components import Qt, StanFrame


class ContentFrameView(StanFrame):
    def __init__(self, widgets) -> None:
        super().__init__()
        self.widgets = widgets
        layout = QGridLayout()
        for w in self.widgets:
            layout.addWidget(w[0], w[1], w[2], alignment=Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)
