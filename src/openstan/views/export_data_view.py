"""export_data_view.py — Export Data panel view.

Presents six one-click export actions (three formats × single/multi schema).
All button click handling and BSP calls live in ExportDataPresenter — this
module contains only layout and widget declarations.
"""

from PyQt6.QtWidgets import QGridLayout, QVBoxLayout

from openstan.components import (
    Qt,
    StanButton,
    StanLabel,
    StanMutedLabel,
    StanProgressBar,
    StanWidget,
)


class ExportDataView(StanWidget):
    """Export Data panel.

    Exposes six ``StanButton`` instances (one per format/type combination),
    a ``StanProgressBar`` for in-progress feedback, and a ``StanLabel`` for
    post-export status messages.  All wiring lives in ``ExportDataPresenter``.
    """

    header: str = "##### Export Data"

    def __init__(self) -> None:
        super().__init__()

        # ── Description ───────────────────────────────────────────────────
        description = StanMutedLabel(
            "Export project transactions to your preferred format and schema."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Column headers ─────────────────────────────────────────────────
        # "Single" = single flat transactions table.
        # "Multi"  = full star schema (statement, account, calendar,
        #             transactions, balances, gaps).
        label_simple = StanLabel("**Single**")
        label_full = StanLabel("**Multi**")
        label_simple.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_full.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Export buttons ─────────────────────────────────────────────────
        self.button_csv_simple = StanButton("Export CSV (Single)")
        self.button_csv_full = StanButton("Export CSV (Multi)")
        self.button_excel_simple = StanButton("Export Excel (Single)")
        self.button_excel_full = StanButton("Export Excel (Multi)")
        self.button_json_simple = StanButton("Export JSON (Single)")
        self.button_json_full = StanButton("Export JSON (Multi)")

        # ── Progress / status ──────────────────────────────────────────────
        self.progress_bar = StanProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate (marquee)
        self.progress_bar.setVisible(False)

        self.label_status = StanLabel("")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Button grid: row = format, col 0 = Simple, col 1 = Full ───────
        button_grid = QGridLayout()
        button_grid.setSpacing(8)

        button_grid.addWidget(label_simple, 0, 0)
        button_grid.addWidget(label_full, 0, 1)

        button_grid.addWidget(self.button_csv_simple, 1, 0)
        button_grid.addWidget(self.button_csv_full, 1, 1)

        button_grid.addWidget(self.button_excel_simple, 2, 0)
        button_grid.addWidget(self.button_excel_full, 2, 1)

        button_grid.addWidget(self.button_json_simple, 3, 0)
        button_grid.addWidget(self.button_json_full, 3, 1)

        # ── Outer layout ───────────────────────────────────────────────────
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        layout.addWidget(description)
        layout.addSpacing(8)
        layout.addLayout(button_grid)
        layout.addSpacing(4)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.label_status)

        self.setLayout(layout)
