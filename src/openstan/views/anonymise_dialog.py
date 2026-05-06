"""anonymise_dialog.py — Dialog for anonymising a PDF bank statement.

Allows the user to:
  1. Select a source PDF via file browser.
  2. View and edit the project's ``anonymise.toml`` config inline.
  3. Save the config.
  4. Run the anonymisation (in a background worker).
  5. Open the original and anonymised PDFs side-by-side in the OS viewer.

Business logic lives entirely in ``AnonymisePresenter``.
"""

from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QHBoxLayout,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from openstan.components import (
    Qt,
    StanButton,
    StanDialog,
    StanFrame,
    StanLabel,
    StanLineEdit,
)


class AnonymiseDialog(StanDialog):
    """Modal dialog for anonymising a PDF statement.

    All state and signal wiring is managed by ``AnonymisePresenter``.
    This class is pure layout.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Anonymise PDF")
        self.setMinimumWidth(620)
        self.setMinimumHeight(560)

        outer = QVBoxLayout()
        outer.setSpacing(16)
        outer.setContentsMargins(20, 20, 20, 20)

        # ------------------------------------------------------------------
        # Section 1 — Source PDF
        # ------------------------------------------------------------------
        section_pdf = StanFrame()
        layout_pdf = QVBoxLayout()
        layout_pdf.setSpacing(8)

        lbl_pdf_title = StanLabel("##### Source PDF")
        lbl_pdf_info = StanLabel("Select the PDF statement you want to anonymise.")
        lbl_pdf_info.setWordWrap(True)

        row_pdf = QHBoxLayout()
        self.line_edit_pdf_path = StanLineEdit()
        self.line_edit_pdf_path.setPlaceholderText("No PDF selected…")
        self.line_edit_pdf_path.setReadOnly(True)
        self.button_browse = StanButton("Browse…", min_width=120)

        row_pdf.addWidget(self.line_edit_pdf_path, stretch=1)
        row_pdf.addWidget(self.button_browse)

        layout_pdf.addWidget(lbl_pdf_title)
        layout_pdf.addWidget(lbl_pdf_info)
        layout_pdf.addLayout(row_pdf)
        section_pdf.setLayout(layout_pdf)

        # ------------------------------------------------------------------
        # Section 2 — anonymise.toml editor
        # ------------------------------------------------------------------
        section_toml = StanFrame()
        layout_toml = QVBoxLayout()
        layout_toml.setSpacing(8)

        lbl_toml_title = StanLabel("##### anonymise.toml")
        self.label_toml_path = StanLabel("")
        self.label_toml_path.setWordWrap(True)

        self.text_edit_toml = QPlainTextEdit()
        self.text_edit_toml.setAutoFillBackground(True)
        self.text_edit_toml.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        font = self.text_edit_toml.font()
        font.setFamily("Monospace")
        self.text_edit_toml.setFont(font)

        self.button_save_toml = StanButton("Save Config", min_width=160)

        layout_toml.addWidget(lbl_toml_title)
        layout_toml.addWidget(self.label_toml_path)
        layout_toml.addWidget(self.text_edit_toml, stretch=1)
        layout_toml.addWidget(
            self.button_save_toml, alignment=Qt.AlignmentFlag.AlignLeft
        )
        section_toml.setLayout(layout_toml)

        # ------------------------------------------------------------------
        # Section 3 — Run + status
        # ------------------------------------------------------------------
        section_run = StanFrame()
        layout_run = QVBoxLayout()
        layout_run.setSpacing(8)

        lbl_run_title = StanLabel("##### Run Anonymisation")
        self.button_run = StanButton("Run Anonymisation", min_width=200)
        self.button_run.setEnabled(False)

        self.label_status = StanLabel("Select a PDF to begin.")
        self.label_status.setWordWrap(True)

        layout_run.addWidget(lbl_run_title)
        layout_run.addWidget(self.button_run, alignment=Qt.AlignmentFlag.AlignLeft)
        layout_run.addWidget(self.label_status)
        section_run.setLayout(layout_run)

        # ------------------------------------------------------------------
        # Section 4 — Open PDFs
        # ------------------------------------------------------------------
        section_open = StanFrame()
        layout_open = QVBoxLayout()
        layout_open.setSpacing(8)

        lbl_open_title = StanLabel("##### View Results")
        lbl_open_info = StanLabel(
            "Open both PDFs in the system viewer to compare them side-by-side."
        )
        lbl_open_info.setWordWrap(True)

        row_open = QHBoxLayout()
        self.button_open_original = StanButton("Open Original PDF", min_width=180)
        self.button_open_original.setEnabled(False)
        self.button_open_anonymised = StanButton("Open Anonymised PDF", min_width=180)
        self.button_open_anonymised.setEnabled(False)

        row_open.addWidget(self.button_open_original)
        row_open.addWidget(self.button_open_anonymised)
        row_open.addStretch()

        layout_open.addWidget(lbl_open_title)
        layout_open.addWidget(lbl_open_info)
        layout_open.addLayout(row_open)
        section_open.setLayout(layout_open)

        # ------------------------------------------------------------------
        # Close button
        # ------------------------------------------------------------------
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)

        # ------------------------------------------------------------------
        # Assemble outer layout
        # ------------------------------------------------------------------
        outer.addWidget(section_pdf)
        outer.addWidget(section_toml, stretch=1)
        outer.addWidget(section_run)
        outer.addWidget(section_open)
        outer.addWidget(button_box)
        self.setLayout(outer)
