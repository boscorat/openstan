from PyQt6.QtWidgets import QVBoxLayout

from openstan.components import (
    Qt,
    StanButton,
    StanCheckBox,
    StanComboBox,
    StanDialog,
    StanFrame,
    StanLabel,
)


class AdminView(StanDialog):
    """Modal admin dialog — opened by double-clicking the footer.

    Contains three independent sections for destructive operations.
    All action buttons require a confirmation step before executing.
    Business logic lives entirely in AdminPresenter.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Admin")
        self.setMinimumWidth(480)

        outer = QVBoxLayout()
        outer.setSpacing(16)
        outer.setContentsMargins(20, 20, 20, 20)

        # ------------------------------------------------------------------
        # Section 1 — Delete project
        # ------------------------------------------------------------------
        section_delete = StanFrame()
        layout_delete = QVBoxLayout()
        layout_delete.setSpacing(8)

        lbl_delete_title = StanLabel("##### Delete Project")
        lbl_delete_info = StanLabel(
            "Removes the project record from the database. "
            "Optionally also deletes the project folder from disk."
        )
        lbl_delete_info.setWordWrap(True)

        self.combo_delete = StanComboBox()
        self.check_delete_folder = StanCheckBox(
            "Also delete the project folder from disk"
        )
        self.button_delete_project = StanButton("Delete Project")

        layout_delete.addWidget(lbl_delete_title)
        layout_delete.addWidget(lbl_delete_info)
        layout_delete.addWidget(self.combo_delete)
        layout_delete.addWidget(self.check_delete_folder)
        layout_delete.addWidget(
            self.button_delete_project, alignment=Qt.AlignmentFlag.AlignLeft
        )
        section_delete.setLayout(layout_delete)

        # ------------------------------------------------------------------
        # Section 2 — Remove project from UI only
        # ------------------------------------------------------------------
        section_remove = StanFrame()
        layout_remove = QVBoxLayout()
        layout_remove.setSpacing(8)

        lbl_remove_title = StanLabel("##### Remove Project from UI Only")
        lbl_remove_info = StanLabel(
            "Removes the project record from the database "
            "without touching any files on disk."
        )
        lbl_remove_info.setWordWrap(True)

        self.combo_remove = StanComboBox()
        self.button_remove_project = StanButton("Remove from UI")

        layout_remove.addWidget(lbl_remove_title)
        layout_remove.addWidget(lbl_remove_info)
        layout_remove.addWidget(self.combo_remove)
        layout_remove.addWidget(
            self.button_remove_project, alignment=Qt.AlignmentFlag.AlignLeft
        )
        section_remove.setLayout(layout_remove)

        # ------------------------------------------------------------------
        # Section 3 — Empty database
        # ------------------------------------------------------------------
        section_empty = StanFrame()
        layout_empty = QVBoxLayout()
        layout_empty.setSpacing(8)

        lbl_empty_title = StanLabel("##### Reset Application")
        lbl_empty_info = StanLabel(
            "Deletes and recreates gui.db, then closes the application. "
            "All projects, sessions, and users will be permanently lost. "
            "This action cannot be undone."
        )
        lbl_empty_info.setWordWrap(True)

        self.button_empty_db = StanButton("Empty Database && Restart")

        layout_empty.addWidget(lbl_empty_title)
        layout_empty.addWidget(lbl_empty_info)
        layout_empty.addWidget(
            self.button_empty_db, alignment=Qt.AlignmentFlag.AlignLeft
        )
        section_empty.setLayout(layout_empty)

        # ------------------------------------------------------------------
        # Assemble outer layout
        # ------------------------------------------------------------------
        outer.addWidget(section_delete)
        outer.addWidget(section_remove)
        outer.addWidget(section_empty)
        self.setLayout(outer)
