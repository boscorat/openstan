"""parquet_view_dialog.py — Dialog for inspecting REVIEW statement parquet files.

Opens from the "View Parquet" button in :class:`DebugInfoDialog` for REVIEW rows.
Displays three parquet files in a vertical layout:

* **checks_and_balances** — single-row horizontal table.
* **statement_heads** — single-row horizontal table.
* **statement_lines** — a totals table (one row) above a scrollable data table.

All columns are sized to their header text width and remain interactively
resizable.  Column widths are kept in sync between the totals and data tables.
All ``ID_*`` and ``index`` columns are hidden as noise.  Hovering over any cell
shows the full value as a tooltip.

All three paths are optional; when a path is ``None`` or the file no longer
exists a muted "Not available" label is shown in its place.
"""

from __future__ import annotations

import traceback
from pathlib import Path

import polars as pl
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QHeaderView,
    QVBoxLayout,
    QWidget,
)

from openstan.components import (
    StanDialog,
    StanHeaderLabel,
    StanMutedLabel,
    StanPolarsModel,
    StanScrollArea,
    StanTableView,
)

# Columns in statement_lines where a plain sum is not meaningful:
# opening_balance = first row's opening balance (running total, start of statement).
# closing_balance = last row's closing balance (running total, end of statement).
_FIRST_VALUE_COLS: frozenset[str] = frozenset({"STD_OPENING_BALANCE"})
_LAST_VALUE_COLS: frozenset[str] = frozenset({"STD_CLOSING_BALANCE"})


# ---------------------------------------------------------------------------
# Module-private model — adds full-value tooltip on every cell
# ---------------------------------------------------------------------------


class _TooltipPolarsModel(StanPolarsModel):
    """StanPolarsModel that also returns the cell value as a hover tooltip."""

    def data(self, index, role=Qt.ItemDataRole.DisplayRole) -> str | None:  # type: ignore[override]
        if role == Qt.ItemDataRole.ToolTipRole:
            if index.isValid():
                return str(self.df.item(index.row(), index.column()))
            return None
        return super().data(index, role)


# ---------------------------------------------------------------------------
# DataFrame helpers
# ---------------------------------------------------------------------------


def _read_parquet(path: Path | None) -> pl.DataFrame | None:
    """Read *path* as a Polars DataFrame, returning ``None`` on any failure."""
    if path is None or not path.exists():
        return None
    try:
        return pl.read_parquet(path)
    except Exception:
        traceback.print_exc()
        return None


def _drop_id_cols(df: pl.DataFrame) -> pl.DataFrame:
    """Remove ``index`` and all ``ID_*`` columns — noise for human review."""
    keep = [c for c in df.columns if c != "index" and not c.upper().startswith("ID_")]
    return df.select(keep)


def _totals_df(df: pl.DataFrame) -> pl.DataFrame:
    """Return a one-row DataFrame of column aggregates for the totals row.

    * ``STD_OPENING_BALANCE`` — first value (running total: start of statement).
    * ``STD_CLOSING_BALANCE`` — last value  (running total: end of statement).
    * All other numeric columns — sum.
    * Non-numeric columns — empty string.
    """
    exprs: list[pl.Expr] = []
    for col_name in df.columns:
        if col_name in _FIRST_VALUE_COLS:
            exprs.append(pl.col(col_name).first())
        elif col_name in _LAST_VALUE_COLS:
            exprs.append(pl.col(col_name).last())
        elif df[col_name].dtype.is_numeric():
            exprs.append(pl.col(col_name).sum())
        else:
            exprs.append(pl.lit("").alias(col_name))
    return df.select(exprs)


# ---------------------------------------------------------------------------
# Widget helpers
# ---------------------------------------------------------------------------


def _set_columns_to_header_width(view: StanTableView) -> None:
    """Set every column to the width of its header label text + padding.

    Uses Interactive resize mode so the user can still drag columns wider.
    Column content is intentionally not measured — the tooltip covers overflow.
    """
    hdr = view.horizontalHeader()
    assert hdr is not None
    fm = hdr.fontMetrics()
    model = view.model()
    for i in range(hdr.count()):
        label = (
            model.headerData(i, Qt.Orientation.Horizontal) if model is not None else ""
        )
        width = fm.horizontalAdvance(str(label)) + 16  # 16 px side padding
        hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        hdr.resizeSection(i, width)


def _make_single_row_table(df: pl.DataFrame) -> StanTableView:
    """Compact table for a single-row DataFrame — height hugs its content."""
    view = StanTableView()
    view.setModel(_TooltipPolarsModel(df))
    _set_columns_to_header_width(view)
    view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    # Override StanTableView's hardcoded setMinimumHeight(200).
    # setMaximumHeight gives the layout a tight upper bound; the table will
    # settle at its natural height (header + one row + borders ≈ 44–56 px).
    view.setMinimumHeight(0)
    view.setMaximumHeight(80)
    return view


def _make_data_table(df: pl.DataFrame) -> StanTableView:
    """Scrollable table for the statement_lines data rows."""
    view = StanTableView()
    view.setModel(_TooltipPolarsModel(df))
    _set_columns_to_header_width(view)
    return view


def _sync_column_widths(source: StanTableView, target: StanTableView) -> None:
    """Copy every column width from *source* header to *target* header."""
    src_hdr = source.horizontalHeader()
    tgt_hdr = target.horizontalHeader()
    assert src_hdr is not None and tgt_hdr is not None
    for i in range(src_hdr.count()):
        tgt_hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
        tgt_hdr.resizeSection(i, src_hdr.sectionSize(i))
    # Switch back to Interactive so future syncs can still update sections.
    for i in range(tgt_hdr.count()):
        tgt_hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


class ParquetViewDialog(StanDialog):
    """Modal dialog displaying the three REVIEW parquet files for one statement.

    Parameters
    ----------
    checks_and_balances:
        Path to the ``checks_and_balances`` temporary parquet file.
    statement_heads:
        Path to the ``statement_heads`` temporary parquet file.
    statement_lines:
        Path to the ``statement_lines`` temporary parquet file.
    parent:
        Optional parent widget.
    """

    def __init__(
        self,
        checks_and_balances: Path | None,
        statement_heads: Path | None,
        statement_lines: Path | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Parquet File Viewer — REVIEW Statement")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(640)

        layout = QVBoxLayout()
        layout.setSpacing(12)

        # ── Checks & Balances ────────────────────────────────────────────────
        layout.addWidget(StanHeaderLabel("Checks & Balances"))
        cab_df = _read_parquet(checks_and_balances)
        if cab_df is not None:
            layout.addWidget(_make_single_row_table(_drop_id_cols(cab_df)))
        else:
            layout.addWidget(StanMutedLabel("Not available"))

        # ── Statement Heads ──────────────────────────────────────────────────
        layout.addWidget(StanHeaderLabel("Statement Heads"))
        heads_df = _read_parquet(statement_heads)
        if heads_df is not None:
            layout.addWidget(_make_single_row_table(_drop_id_cols(heads_df)))
        else:
            layout.addWidget(StanMutedLabel("Not available"))

        # ── Statement Lines ──────────────────────────────────────────────────
        layout.addWidget(StanHeaderLabel("Statement Lines"))
        lines_df = _read_parquet(statement_lines)
        if lines_df is not None:
            self.__add_lines_section(layout, _drop_id_cols(lines_df))
        else:
            layout.addWidget(StanMutedLabel("Not available"))

        # ── Close button ─────────────────────────────────────────────────────
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def __add_lines_section(self, layout: QVBoxLayout, lines_df: pl.DataFrame) -> None:
        """Add the totals table and scrollable data table for *lines_df*."""

        # ── Totals row ───────────────────────────────────────────────────────
        layout.addWidget(StanMutedLabel("Totals"))
        totals_view = _make_single_row_table(_totals_df(lines_df))
        layout.addWidget(totals_view)

        # ── Data rows ────────────────────────────────────────────────────────
        layout.addWidget(StanMutedLabel("Lines"))
        data_view = _make_data_table(lines_df)

        scroll = StanScrollArea()
        scroll.setWidget(data_view)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, stretch=1)

        # Both tables are sized to header-text widths so they start aligned.
        # Keep them in sync when the user drags a column in the data table.
        data_hdr = data_view.horizontalHeader()
        assert data_hdr is not None
        data_hdr.sectionResized.connect(
            lambda _idx, _old, _new: _sync_column_widths(data_view, totals_view)
        )
