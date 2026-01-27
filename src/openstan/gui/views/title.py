from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QGridLayout

from openstan.gui.components import Qt, StanLabel, StanWidget
from openstan.gui.paths import Paths


class TitleView(StanWidget):
    def __init__(self) -> None:
        super().__init__()
        title = "### Statement Analysis - configurable, accurate, flexible & extendable"
        label = StanLabel(title)
        label.setTextFormat(Qt.TextFormat.MarkdownText)
        image = StanLabel()
        image.setPixmap(QPixmap(Paths.icon("stan.svg")))
        image.setMaximumWidth(32)
        layout = QGridLayout()
        layout.addWidget(image, 0, 0)
        layout.addWidget(label, 0, 1)
        layout.unsetContentsMargins()
        self.setLayout(layout)
        self.setMaximumHeight(80)
