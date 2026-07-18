"""anonymise_dialog.py — Dialog for anonymising a PDF bank statement.

Allows the user to:
   1. Select a source PDF via file browser.
   2. View and edit the project's config in two tabs:
      - Always Anonymise: forced replacements (original + replacement pairs)
      - Never Anonymise: excluded phrases
   3. Run the anonymisation (in a background worker).
   4. Open the original and anonymised PDFs side-by-side in the OS viewer.

Business logic lives entirely in ``AnonymisePresenter``.
"""

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialogButtonBox,
    QHBoxLayout,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
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
    """Modeless dialog for anonymising a PDF statement.

    All state and signal wiring is managed by ``AnonymisePresenter``.
    This class is pure layout.

    The dialog is non-modal (modeless), scrollable on low-resolution screens,
    and stays on top of the main window.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Anonymise PDF")

        self.make_scrollable()

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
        # Section 2 — Config editors (two tabs with tables)
        # ------------------------------------------------------------------
        section_config = StanFrame()
        layout_config = QVBoxLayout()
        layout_config.setSpacing(8)

        lbl_config_title = StanLabel("##### Anonymisation Config")

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Tab 1: Always Anonymise (2 columns: Original | Replacement)
        self.tab_always = StanFrame()
        layout_always = QVBoxLayout()
        layout_always.setSpacing(8)

        lbl_always_title = StanLabel("**Force Exact Replacements**")
        lbl_always_info = StanLabel(
            "Entries force exact string replacements before the scramble pass.\n"
            "Add rows with original text and replacement value."
        )
        lbl_always_info.setWordWrap(True)

        self.table_always = QTableWidget()
        self.table_always.setColumnCount(2)
        self.table_always.setHorizontalHeaderLabels(["Original Text", "Replacement"])
        self.table_always.horizontalHeader().setStretchLastSection(True)
        self.table_always.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_always.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table_always.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        row_always_buttons = QHBoxLayout()
        self.button_add_always = StanButton("Add Row", min_width=100)
        self.button_remove_always = StanButton("Remove Selected", min_width=100)
        row_always_buttons.addWidget(self.button_add_always)
        row_always_buttons.addWidget(self.button_remove_always)
        row_always_buttons.addStretch()

        layout_always.addWidget(lbl_always_title)
        layout_always.addWidget(lbl_always_info)
        layout_always.addWidget(self.table_always, stretch=1)
        layout_always.addLayout(row_always_buttons)
        self.tab_always.setLayout(layout_always)

        # Tab 2: Never Anonymise (1 column: Phrase)
        self.tab_never = StanFrame()
        layout_never = QVBoxLayout()
        layout_never.setSpacing(8)

        lbl_never_title = StanLabel("**Exclude from Scrambling**")
        lbl_never_info = StanLabel(
            "Phrases listed here are left unchanged during the scramble pass.\n"
            "Matching is case-insensitive."
        )
        lbl_never_info.setWordWrap(True)

        self.table_never = QTableWidget()
        self.table_never.setColumnCount(1)
        self.table_never.setHorizontalHeaderLabels(["Phrase"])
        self.table_never.horizontalHeader().setStretchLastSection(True)
        self.table_never.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_never.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table_never.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        row_never_buttons = QHBoxLayout()
        self.button_add_never = StanButton("Add Row", min_width=100)
        self.button_remove_never = StanButton("Remove Selected", min_width=100)
        row_never_buttons.addWidget(self.button_add_never)
        row_never_buttons.addWidget(self.button_remove_never)
        row_never_buttons.addStretch()

        layout_never.addWidget(lbl_never_title)
        layout_never.addWidget(lbl_never_info)
        layout_never.addWidget(self.table_never, stretch=1)
        layout_never.addLayout(row_never_buttons)
        self.tab_never.setLayout(layout_never)

        # Add tabs to tab widget
        self.tab_widget.addTab(self.tab_always, "Always Anonymise")
        self.tab_widget.addTab(self.tab_never, "Never Anonymise")

        layout_config.addWidget(lbl_config_title)
        layout_config.addWidget(self.tab_widget, stretch=1)
        section_config.setLayout(layout_config)

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
        outer.addWidget(section_config, stretch=1)
        outer.addWidget(section_run)
        outer.addWidget(section_open)
        outer.addWidget(button_box)
        self.setLayout(outer)

    # ---------------------------------------------------------------------------
    # Table population and data extraction
    # ---------------------------------------------------------------------------

    def populate_always_table(self, replacements: dict[str, str]) -> None:
        """Populate the 'Always Anonymise' table with replacement pairs."""
        self.table_always.setRowCount(0)

        for original, replacement in replacements.items():
            row_pos = self.table_always.rowCount()
            self.table_always.insertRow(row_pos)

            item_orig = QTableWidgetItem(original)
            item_repl = QTableWidgetItem(replacement)

            self.table_always.setItem(row_pos, 0, item_orig)
            self.table_always.setItem(row_pos, 1, item_repl)

        # Add one empty row for convenience
        self._add_empty_always_row()

    def populate_never_table(self, phrases: list[str]) -> None:
        """Populate the 'Never Anonymise' table with excluded phrases."""
        self.table_never.setRowCount(0)

        for phrase in phrases:
            row_pos = self.table_never.rowCount()
            self.table_never.insertRow(row_pos)

            item = QTableWidgetItem(phrase)
            self.table_never.setItem(row_pos, 0, item)

        # Add one empty row for convenience
        self._add_empty_never_row()

    def get_always_table_data(self) -> dict[str, str]:
        """Extract data from the 'Always Anonymise' table."""
        replacements = {}

        for row in range(self.table_always.rowCount()):
            item_orig = self.table_always.item(row, 0)
            item_repl = self.table_always.item(row, 1)

            original = item_orig.text() if item_orig else ""
            replacement = item_repl.text() if item_repl else ""

            # Skip empty rows
            if original.strip():
                replacements[original] = replacement

        return replacements

    def get_never_table_data(self) -> list[str]:
        """Extract data from the 'Never Anonymise' table."""
        phrases = []

        for row in range(self.table_never.rowCount()):
            item = self.table_never.item(row, 0)
            phrase = item.text() if item else ""

            # Skip empty rows
            if phrase.strip():
                phrases.append(phrase)

        return phrases

    def _add_empty_always_row(self) -> None:
        """Add an empty row to the 'Always Anonymise' table."""
        row_pos = self.table_always.rowCount()
        self.table_always.insertRow(row_pos)

        self.table_always.setItem(row_pos, 0, QTableWidgetItem(""))
        self.table_always.setItem(row_pos, 1, QTableWidgetItem(""))

    def _add_empty_never_row(self) -> None:
        """Add an empty row to the 'Never Anonymise' table."""
        row_pos = self.table_never.rowCount()
        self.table_never.insertRow(row_pos)

        self.table_never.setItem(row_pos, 0, QTableWidgetItem(""))
