from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QHBoxLayout

from openstan.components import StanWidget
from openstan.paths import Paths


class TitleView(StanWidget):
    def __init__(self) -> None:
        super().__init__()

        wordmark = QSvgWidget(Paths.wordmark(with_tagline=True))
        # Fix the display size to match the SVG viewBox aspect ratio (200×56).
        wordmark.setFixedSize(200, 56)
        # Accessible name for screen readers in place of SVG alt text.
        wordmark.setAccessibleName("openstan — secure statement analysis")

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(wordmark)
        layout.addStretch()
        self.setLayout(layout)
        self.setMaximumHeight(72)
