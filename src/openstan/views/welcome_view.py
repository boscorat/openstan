"""welcome_view.py — Full-content-area welcome panel shown when no project is selected."""

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout

from openstan.components import (
    Qt,
    StanButton,
    StanLabel,
    StanThemedPixmapLabel,
    StanWidget,
)


class WelcomeView(StanWidget):
    """Shown in the content stack when no project is open.

    Contains two call-to-action buttons whose ``clicked`` signals are wired
    by ``StanPresenter`` to the project presenter's wizard slots.
    """

    header: str = "Welcome"

    def __init__(self) -> None:
        super().__init__()

        icon = StanThemedPixmapLabel("project.svg", size=96)
        icon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        heading = StanLabel("## Welcome to openstan")
        heading.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )

        subheading = StanLabel(
            "Get started by creating a new project or adding an existing one."
        )
        subheading.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )

        self.button_new = StanButton("Create New Project", min_width=200)
        self.button_new.set_themed_icon("project.svg")
        self.button_new.setToolTip("Open the wizard to create a new project")
        self.button_new.setAccessibleName("Create new project")

        self.button_existing = StanButton("Add Existing Project", min_width=200)
        self.button_existing.set_themed_icon("folder_add.svg")
        self.button_existing.setToolTip("Add an existing project folder to openstan")
        self.button_existing.setAccessibleName("Add existing project")

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        btn_row.addStretch()
        btn_row.addWidget(self.button_new)
        btn_row.addWidget(self.button_existing)
        btn_row.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)
        layout.addStretch()
        layout.addWidget(icon)
        layout.addWidget(heading)
        layout.addWidget(subheading)
        layout.addSpacing(24)
        layout.addLayout(btn_row)
        layout.addStretch()

        self.setLayout(layout)
