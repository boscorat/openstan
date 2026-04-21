from PyQt6.QtCore import QEvent, pyqtSignal
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QHBoxLayout

from openstan.components import StanButton, StanWidget
from openstan.paths import Paths


class TitleView(StanWidget):
    about_requested: pyqtSignal = pyqtSignal()
    admin_requested: pyqtSignal = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        self._wordmark = QSvgWidget(Paths.wordmark(with_tagline=True))
        # Fix the display size to match the SVG viewBox aspect ratio (200×56).
        self._wordmark.setFixedSize(200, 56)
        # Accessible name for screen readers in place of SVG alt text.
        self._wordmark.setAccessibleName("openstan — secure statement analysis")

        about_btn = StanButton("About", min_width=70)
        about_btn.setFixedWidth(70)
        about_btn.setToolTip("About openstan")
        about_btn.setAccessibleName("About openstan")
        about_btn.clicked.connect(self.about_requested)

        admin_btn = StanButton("Admin", min_width=70)
        admin_btn.setFixedWidth(70)
        admin_btn.setToolTip(
            "Open admin options (delete / remove projects, reset application)"
        )
        admin_btn.setAccessibleName("Admin options")
        admin_btn.clicked.connect(self.admin_requested)

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(self._wordmark)
        layout.addStretch()
        layout.addWidget(admin_btn)
        layout.addWidget(about_btn)
        self.setLayout(layout)
        self.setMaximumHeight(72)

    def changeEvent(self, a0: QEvent | None) -> None:  # noqa: N802
        """Reload the wordmark SVG whenever the application palette changes."""
        if a0 is not None and a0.type() in (
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
        ):
            self._wordmark.load(Paths.wordmark(with_tagline=True))
        super().changeEvent(a0)
