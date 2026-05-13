from PyQt6.QtWidgets import QDialogButtonBox, QVBoxLayout

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
        self.combo_delete.setToolTip("Select the project to delete")
        self.check_delete_folder = StanCheckBox(
            "Also delete the project folder from disk"
        )
        self.check_delete_folder.setToolTip(
            "If checked, the project folder and all its contents will be permanently "
            "deleted from disk in addition to the database record"
        )
        self.button_delete_project = StanButton("Delete Project")
        self.button_delete_project.setToolTip(
            "Permanently delete the selected project — requires confirmation"
        )

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
        self.combo_remove.setToolTip("Select the project to remove from the UI")
        self.button_remove_project = StanButton("Remove from UI")
        self.button_remove_project.setToolTip(
            "Remove the project record from the database without touching files on disk"
        )

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
        self.button_empty_db.setToolTip(
            "Delete and recreate gui.db, then restart the application — "
            "all projects, sessions, and users will be permanently lost"
        )
        self.button_empty_db.setStyleSheet(
            "StanButton { color: palette(highlight); font-weight: bold; }"
        )

        layout_empty.addWidget(lbl_empty_title)
        layout_empty.addWidget(lbl_empty_info)
        layout_empty.addWidget(
            self.button_empty_db, alignment=Qt.AlignmentFlag.AlignLeft
        )
        section_empty.setLayout(layout_empty)

        # ------------------------------------------------------------------
        # Section 4 — Anonymise PDF
        # ------------------------------------------------------------------
        section_anon = StanFrame()
        layout_anon = QVBoxLayout()
        layout_anon.setSpacing(8)

        lbl_anon_title = StanLabel("##### Anonymise PDF")
        lbl_anon_info = StanLabel(
            "Select a PDF, edit the exclusion config, and produce an anonymised copy "
            "suitable for sharing or attaching to a bug report."
        )
        lbl_anon_info.setWordWrap(True)

        self.button_open_anonymise = StanButton("Open Anonymise Tool")
        self.button_open_anonymise.setToolTip(
            "Open the PDF anonymisation tool to produce a redacted copy "
            "suitable for sharing or attaching to a bug report"
        )

        layout_anon.addWidget(lbl_anon_title)
        layout_anon.addWidget(lbl_anon_info)
        layout_anon.addWidget(
            self.button_open_anonymise, alignment=Qt.AlignmentFlag.AlignLeft
        )
        section_anon.setLayout(layout_anon)

        # ------------------------------------------------------------------
        # Section 5 — Privacy / update check
        # ------------------------------------------------------------------
        section_privacy = StanFrame()
        layout_privacy = QVBoxLayout()
        layout_privacy.setSpacing(8)

        lbl_privacy_title = StanLabel("##### Privacy")
        lbl_privacy_info = StanLabel(
            "On startup, openstan checks for a newer release by querying the "
            "GitHub Releases API (HTTPS). No personal data is transmitted. "
            "Uncheck below to disable this check."
        )
        lbl_privacy_info.setWordWrap(True)

        self.check_update_check = StanCheckBox("Enable update check on startup")
        self.check_update_check.setToolTip(
            "When checked, openstan silently queries api.github.com on startup "
            "to see if a newer version is available. No personal data is sent."
        )

        layout_privacy.addWidget(lbl_privacy_title)
        layout_privacy.addWidget(lbl_privacy_info)
        layout_privacy.addWidget(self.check_update_check)
        section_privacy.setLayout(layout_privacy)

        # ------------------------------------------------------------------
        # Assemble outer layout
        # ------------------------------------------------------------------
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)

        outer.addWidget(section_delete)
        outer.addWidget(section_remove)
        outer.addWidget(section_empty)
        outer.addWidget(section_anon)
        outer.addWidget(section_privacy)
        outer.addWidget(button_box)
        self.setLayout(outer)
