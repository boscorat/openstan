"""export_data_view.py — Export Data panel view.

Presents six one-click export actions (three formats × simple/full schema).
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
        # "Simple" = single flat transactions table.
        # "Full"   = full star schema (statement, account, calendar,
        #             transactions, balances, gaps).
        label_simple = StanLabel("**Simple**")
        label_full = StanLabel("**Full**")
        label_simple.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_full.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Export buttons ─────────────────────────────────────────────────
        self.button_csv_simple = StanButton("Export CSV (Simple)")
        self.button_csv_full = StanButton("Export CSV (Full)")
        self.button_excel_simple = StanButton("Export Excel (Simple)")
        self.button_excel_full = StanButton("Export Excel (Full)")
        self.button_json_simple = StanButton("Export JSON (Simple)")
        self.button_json_full = StanButton("Export JSON (Full)")

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
