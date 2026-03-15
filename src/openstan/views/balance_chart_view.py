"""Balance chart view — left account tree + right stacked chart area.

Layout:
    ┌─ back button ──────────────────────────────────────────────────┐
    ├─ account tree (left) ──┬─ chart scroll area (right) ───────────┤
    │  Company A             │  Account 1  line chart                │
    │    ↳ Account 1         │  Account 2  line chart                │
    │    ↳ Account 2         │  Company A  stacked-area summary      │
    │  Company B             │  Company B  line chart                │
    │    ↳ Account 3         │  All accounts stacked-area summary    │
    └────────────────────────┴───────────────────────────────────────┘

The chart area is a QScrollArea containing a vertical stack of QChartView
widgets.  All charts share the same QDateTimeAxis x-axis so that panning or
zooming on any one chart propagates to the others via ``rangeChanged``.
"""

from __future__ import annotations

from PyQt6.QtCharts import QChartView
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from openstan.components import StanButton, StanTreeView, StanWidget


class BalanceChartView(StanWidget):
    """Root widget for the balance chart panel.

    Attributes:
        header:         Class attribute read by ``main.py`` when building the
                        ``ContentFrameView`` header label.
        back_button:    Returns the user to the statement queue block.
        account_tree:   ``StanTreeView`` populated by ``BalanceChartPresenter``
                        with a ``BalanceAccountModel``.
        chart_scroll:   ``QScrollArea`` that contains ``chart_container``.
        chart_container: Plain ``QWidget`` with a ``QVBoxLayout``; presenters
                        add/remove ``QChartView`` widgets here.
        status_label:   Shown when no data is available or while loading.
    """

    header = "##### Balance Overview"

    def __init__(self) -> None:
        super().__init__()

        # ── Top bar ──────────────────────────────────────────────────────
        self.back_button = StanButton("← Back")
        self.back_button.setMinimumWidth(100)
        self.back_button.setMaximumWidth(140)

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignLeft)
        top_bar.addStretch(1)

        # ── Left panel: account tree ──────────────────────────────────────
        self.account_tree = StanTreeView()
        self.account_tree.setSelectionMode(
            StanTreeView.SelectionMode.SingleSelection  # type: ignore[attr-defined]
        )
        self.account_tree.setHeaderHidden(False)
        self.account_tree.setMinimumWidth(240)
        self.account_tree.setMaximumWidth(360)
        self.account_tree.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )

        # ── Right panel: scrollable chart area ────────────────────────────
        self.chart_container = QWidget()
        self.chart_container.setAutoFillBackground(True)
        self._chart_layout = QVBoxLayout()
        self._chart_layout.setContentsMargins(4, 4, 4, 4)
        self._chart_layout.setSpacing(8)
        self.chart_container.setLayout(self._chart_layout)

        # Status label shown when there is no data or while loading
        self.status_label = QLabel("No balance data available for this project.")
        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self.status_label.setTextFormat(Qt.TextFormat.MarkdownText)
        self._chart_layout.addWidget(
            self.status_label, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self._chart_layout.addStretch(1)

        self.chart_scroll = QScrollArea()
        self.chart_scroll.setWidgetResizable(True)
        self.chart_scroll.setWidget(self.chart_container)
        self.chart_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # ── Splitter: tree | charts ───────────────────────────────────────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.account_tree)
        self.splitter.addWidget(self.chart_scroll)
        self.splitter.setStretchFactor(0, 0)  # tree: fixed preferred width
        self.splitter.setStretchFactor(1, 1)  # charts: take remaining space
        self.splitter.setSizes([260, 900])

        # ── Root layout ───────────────────────────────────────────────────
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        top_widget = QWidget()
        top_widget.setLayout(top_bar)
        root.addWidget(top_widget, stretch=0)
        root.addWidget(self.splitter, stretch=1)

        self.setLayout(root)

    # ------------------------------------------------------------------
    # Chart slot management — called by BalanceChartPresenter
    # ------------------------------------------------------------------

    def clear_charts(self) -> None:
        """Remove all QChartView widgets and the stretch; restore status label."""
        # Remove all items from the chart layout
        while self._chart_layout.count():
            item = self._chart_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.setParent(None)  # type: ignore[call-overload]
        # Re-add status label and trailing stretch
        self._chart_layout.addWidget(
            self.status_label, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self._chart_layout.addStretch(1)
        self.status_label.show()

    def set_status(self, text: str) -> None:
        """Update the status label text (loading / no-data messages)."""
        self.status_label.setText(text)
        self.status_label.show()

    def add_chart_view(self, chart_view: QChartView) -> None:
        """Insert a QChartView above the trailing stretch."""
        # Hide status label once real charts are being added
        self.status_label.hide()
        # Insert before the stretch (last item)
        insert_pos = max(0, self._chart_layout.count() - 1)
        self._chart_layout.insertWidget(insert_pos, chart_view)
