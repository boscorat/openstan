"""project_info_view.py — Project Information panel view.

Displays a per-project datamart summary: headline counts, a per-account table,
and an optional gap indicator.  All data is pushed in via :meth:`ProjectInfoView.update`;
this view contains no logic and makes no DB calls.
"""

from typing import TYPE_CHECKING

import polars as pl
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

from openstan.components import (
    Qt,
    StanDialog,
    StanHeaderLabel,
    StanLabel,
    StanMutedLabel,
    StanPolarsModel,
    StanTableView,
    StanThemedPixmapLabel,
    StanTreeView,
    StanWidget,
)

if TYPE_CHECKING:
    from openstan.presenters.project_presenter import ProjectInfo


class GapDetailDialog(StanDialog):
    """Modal dialog showing gap-report rows as a tree grouped by account.

    Top-level nodes: one per unique (account_holder, account_type, account_number).
    Child nodes: one per GAP row — "Missing statement between <prev> and <current>".
    The tree is fully expanded on load.
    """

    def __init__(self, parent: StanWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Gap Report — Missing Statements")
        self.setMinimumWidth(640)
        self.setMinimumHeight(320)

        self._tree = StanTreeView()
        self._tree.setMinimumHeight(250)
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(StanLabel("##### Detected gaps between imported statements"))
        layout.addWidget(self._tree)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def load(self, gap_rows: pl.DataFrame) -> None:
        """Populate the tree from *gap_rows*.

        Expected columns: account_holder, account_type, account_number,
        prev_statement_date, statement_date.
        """
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Gap"])

        # Group rows by (account_holder, account_type, account_number) in the
        # order they first appear — preserves natural sort from the query.
        seen: dict[tuple[str, str, str], QStandardItem] = {}
        for row in gap_rows.iter_rows(named=True):
            key = (
                row["account_holder"],
                row["account_type"],
                row["account_number"],
            )
            if key not in seen:
                holder, acc_type, acc_num = key
                node_label = f"{holder} / {acc_type} — {acc_num}"
                parent_item = QStandardItem(node_label)
                parent_item.setEditable(False)
                model.appendRow(parent_item)
                seen[key] = parent_item

            prev = row["prev_statement_date"] or "?"
            curr = row["statement_date"] or "?"
            child_label = f"Missing statement between {prev} and {curr}"
            child_item = QStandardItem(child_label)
            child_item.setEditable(False)
            seen[key].appendRow(child_item)

        self._tree.setModel(model)
        self._tree.expandAll()


class ProjectInfoView(StanWidget):
    """Project Information panel.

    Layout (top-to-bottom):
    1. Headline summary strip — tx / stmt / account counts and date range
    2. Per-account ``StanTableView``
    3. Gap indicator button (hidden when gap_count == 0)

    The header label is supplied externally by ``ContentFrameView`` in
    ``main.py`` — consistent with all other panel views.

    The single public entry point is :meth:`update`.
    """

    header: str = "##### Project Information"

    # Emitted when the user clicks the gap indicator button.
    gap_clicked: pyqtSignal = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        # ── Placeholder page (page 0) ─────────────────────────────────────────
        placeholder_page = StanWidget()
        ph_layout = QVBoxLayout()
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_icon = StanThemedPixmapLabel("project.svg", size=64)
        ph_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_text = StanMutedLabel(
            "No data yet — import and commit some statements to see your project summary."
        )
        ph_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_text.setWordWrap(True)
        ph_layout.addWidget(ph_icon)
        ph_layout.addSpacing(8)
        ph_layout.addWidget(ph_text)
        placeholder_page.setLayout(ph_layout)

        # ── Content page (page 1) ─────────────────────────────────────────────
        content_page = StanWidget()

        # ── Summary strip ─────────────────────────────────────────────────────
        self._lbl_tx = StanLabel("")
        self._lbl_stmt = StanLabel("")
        self._lbl_acc = StanLabel("")
        self._lbl_dates = StanLabel("")

        summary_row = QHBoxLayout()
        summary_row.setSpacing(24)
        summary_row.addWidget(self._lbl_tx)
        summary_row.addWidget(self._lbl_stmt)
        summary_row.addWidget(self._lbl_acc)
        summary_row.addWidget(self._lbl_dates)
        summary_row.addStretch()

        # ── Account table ─────────────────────────────────────────────────────
        self._acc_table_header = StanHeaderLabel("Accounts")
        self._acc_table_currency_note = StanMutedLabel(
            "Monetary values are in the currency recorded in each statement."
        )
        self._acc_table = StanTableView()
        self._acc_table.horizontalHeader().setSectionResizeMode(  # type: ignore[union-attr]
            self._acc_table.horizontalHeader().ResizeMode.ResizeToContents  # type: ignore[union-attr]
        )
        self._acc_table.horizontalHeader().setStretchLastSection(True)  # type: ignore[union-attr]

        # ── Gap indicator ─────────────────────────────────────────────────────
        self._gap_button = QPushButton()
        self._gap_button.setFlat(True)
        # Use the Link colour role so the warning text adapts to the active
        # theme (including high-contrast modes) rather than a hardcoded hex.
        self._gap_button.setStyleSheet(
            "QPushButton { color: palette(link); font-weight: bold; text-align: left; border: none; }"
            "QPushButton:hover { text-decoration: underline; }"
        )
        self._gap_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._gap_button.setToolTip(
            "A gap means there is a missing statement between two consecutive imported statements "
            "for the same account.  Click to see which accounts and date ranges are affected."
        )
        self._gap_button.setAccessibleDescription(
            "One or more statement gaps detected. Click to review."
        )
        self._gap_button.clicked.connect(self.gap_clicked)
        self._gap_button.hide()

        # ── Gap detail dialog ─────────────────────────────────────────────────
        self._gap_dialog = GapDetailDialog(self)
        self.gap_clicked.connect(self._gap_dialog.exec)

        # ── Content page layout ───────────────────────────────────────────────
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)
        content_layout.addLayout(summary_row)
        content_layout.addWidget(self._acc_table_header)
        content_layout.addWidget(self._acc_table_currency_note)
        content_layout.addWidget(self._acc_table)
        content_layout.addWidget(self._gap_button)
        content_layout.addStretch()
        content_page.setLayout(content_layout)

        # ── Stacked widget ────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.addWidget(placeholder_page)  # page 0
        self._stack.addWidget(content_page)  # page 1
        self._stack.setCurrentIndex(0)

        # ── Outer layout ──────────────────────────────────────────────────────
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._stack)
        self.setLayout(outer)

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def show_placeholder(self, show: bool) -> None:
        """Switch between placeholder (page 0) and real content (page 1)."""
        self._stack.setCurrentIndex(0 if show else 1)

    def update(self, info: "ProjectInfo | None") -> None:  # type: ignore[override]
        """Refresh the entire panel from *info*.

        Passing ``None`` clears all data (placeholder is controlled separately
        via :meth:`show_placeholder`).
        """
        if info is None:
            self._clear()
            return

        # Summary strip
        acc_word = "account" if info.acc_count == 1 else "accounts"
        self._lbl_tx.setText(f"**{info.tx_count:,}** transactions")
        self._lbl_stmt.setText(f"**{info.stmt_count:,}** statements")
        self._lbl_acc.setText(f"**{info.acc_count:,}** {acc_word}")
        if info.earliest_date and info.latest_date:
            self._lbl_dates.setText(f"{info.earliest_date} — {info.latest_date}")
        else:
            self._lbl_dates.setText("")

        # Account table
        model = StanPolarsModel(info.account_rows)
        self._acc_table.setModel(model)

        # Gap indicator
        if info.gap_count > 0:
            gap_word = "gap" if info.gap_count == 1 else "gaps"
            self._gap_button.setText(
                f"Warning: {info.gap_count} statement {gap_word} detected — click to review"
            )
            self._gap_dialog.load(info.gap_rows)
            self._gap_button.show()
        else:
            self._gap_button.hide()

        self._acc_table_header.show()
        self._acc_table_currency_note.show()
        self._acc_table.show()

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    def _clear(self) -> None:
        """Reset content to empty state."""
        self._lbl_tx.setText("")
        self._lbl_stmt.setText("")
        self._lbl_acc.setText("")
        self._lbl_dates.setText("")
        self._acc_table.setModel(None)
        self._gap_button.hide()
        self._acc_table_header.hide()
        self._acc_table_currency_note.hide()
        self._acc_table.hide()
