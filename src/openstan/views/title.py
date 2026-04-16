from PyQt6.QtCore import pyqtSignal
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QHBoxLayout

from openstan.components import StanButton, StanWidget
from openstan.paths import Paths


class TitleView(StanWidget):
    about_requested: pyqtSignal = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        wordmark = QSvgWidget(Paths.wordmark(with_tagline=True))
        # Fix the display size to match the SVG viewBox aspect ratio (200×56).
        wordmark.setFixedSize(200, 56)
        # Accessible name for screen readers in place of SVG alt text.
        wordmark.setAccessibleName("openstan — secure statement analysis")

        about_btn = StanButton("About", min_width=56)
        about_btn.setFlat(True)
        about_btn.setFixedWidth(56)
        about_btn.clicked.connect(self.about_requested)

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(wordmark)
        layout.addStretch()
        layout.addWidget(about_btn)
        self.setLayout(layout)
        self.setMaximumHeight(72)
