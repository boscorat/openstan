# Balance Chart Feature — Resume Notes

> **Branch:** `balance_chart`
> **Parked from:** `feature/pm-7-config-selection-wizard` at commit `7156942`
> **Reason for parking:** Core feature is working and useful. Parked to allow other
> development to continue; several known enhancements remain (see below).

---

## What is complete

### Dependency
- `pyqt6-charts==6.10.0` added to `pyproject.toml` via `uv add pyqt6-charts`.
- Note: Qt's own documentation calls Qt Charts "deprecated" in favour of Qt Graphs, but
  `PyQt6-Graphs` is QML-first in Python (`QGraphsView` does not exist as a widget class)
  and is therefore unsuitable for a widget-based app. `PyQt6-Charts` works fully.

### View
- `src/openstan/views/balance_chart_view.py` — `BalanceChartView(StanWidget)`:
  - Top bar with `back_button` (StanButton)
  - Left panel: `account_tree` (StanTreeView, min 240 / max 360 px) — company → account tree
  - Right panel: `chart_scroll` (QScrollArea) containing `chart_container` (QVBoxLayout)
  - `QSplitter` layout with initial sizes [260, 900]
  - `clear_charts()`, `set_status()`, `add_chart_view()` slot methods

### Presenter + Worker
- `src/openstan/presenters/balance_chart_presenter.py`:
  - `BalanceChartSignals(QObject)` — cross-thread signals
  - `BalanceChartWorker(QRunnable)` — background worker: reads `FactBalance`
    (`outside_date == 0`) + `DimAccount`, joins, builds `display_label` (see below),
    aggregates to month-end `closing_balance` per `(company, display_label)`, emits
    `pl.DataFrame` with columns `company, display_label, year, month, closing_balance,
    period_end_date, epoch_ms`
  - `BalanceAccountModel(QAbstractItemModel)` — two-level tree model (company → account)
    keyed on `display_label`
  - `BalanceChartPresenter(QObject)` — signals: `exit_chart`, `has_data_changed(bool)`

### Chart design
- **Single `QChartView`** (800 px min height) containing all accounts on one shared axis —
  no per-account separate charts.
- **`display_label`** logic: account is shown as `account_type`; suffixed with
  `account_holder` only when the same `(company, account_type)` pair has more than one
  distinct holder (e.g. two credit cards for different people).  Re-issued cards with a
  new `account_number` but same `account_type` + `account_holder` merge onto one series.
- **Contiguous-segment gap handling**: `_split_into_segments()` creates a new `QLineSeries`
  per contiguous run of months, producing visible line breaks for months with no data.
  Only the first segment carries the legend name to avoid duplicate legend entries.
- **Net total**: bold black dashed `QLineSeries` summing all accounts per period (only when
  ≥ 2 accounts).
- **Y-axis range**: explicitly calculated from all `closing_balance` values + net-total
  values with 5 % padding each side — Qt's auto-range honours only the first series.
- **Zero reference line**: thin grey `QLineSeries` at `y = 0` spanning the full x range,
  shown only when the y range straddles zero. Its legend marker is hidden.
- **Legend cleanup**: after all series are attached, any legend marker whose `label()` is
  empty is hidden — catches unnamed continuation segments and the zero line.
- **Axis tick density**: `x_axis.setTickCount(13)`, `y_axis.setTickCount(11)`.
- **Highlight**: clicking an account in the tree sets that account's series pen to 4 px;
  all others revert to their base pen (2 px for accounts, 3 px for net total). Each pen is
  stored in `_base_pens` at build time so widths never accumulate across clicks.
- **Rubber-band zoom**: `QChartView.RubberBand.HorizontalRubberBand` on the chart view.

### Project strip button
- `src/openstan/views/project_view.py` — `button_balance` (StanButton, col 6, disabled by
  default); `summary_label` span widened to 7 cols; `setMaximumHeight` increased to 90.
- Button is enabled/disabled via `BalanceChartPresenter.has_data_changed(bool)`.
- On every project switch a silent `refresh(probe=True)` runs in the background so the
  button reflects data availability without disturbing the chart area.

### Wiring
- `main.py` — `BalanceChartView`, `balance_chart_block` (ContentFrameView, hidden),
  `BalanceChartPresenter` instantiated and added to the VBox layout.
- `presenters/stan_presenter.py` — `show_balance_chart()`, `hide_balance_chart()`,
  `_on_balance_data_changed()`; `balance_chart_presenter.refresh()` called after
  `on_batch_committed()`; `balance_chart_presenter.project_path` and
  `clear_for_project_change()` + `refresh(probe=True)` called in
  `update_current_project_info()`.
- `views/__init__.py`, `presenters/__init__.py` — exports added.

### Spec
- `REQUIREMENTS.md` — Section 8 "Balance Chart" added (stories BC-1 – BC-8).
- `ROADMAP.md` — Milestone 5 "Balance Chart" added; "Charting / visualisation" removed
  from backlog.

---

## Known issues / things to improve

### Display
- The legend can become crowded when there are many accounts — consider making it
  scrollable or moving it to the left panel (replace or augment the tree).
- X-axis tick labels may overlap at `tickCount(13)` when the chart is narrow — could
  make tick count dynamic based on the pixel width of the chart view.
- The chart title "Account Balances" is static — could reflect the project name.

### Interaction
- Clicking a **company node** in the tree currently does nothing (only leaf account nodes
  have an `account_key`). Could highlight all accounts belonging to that company.
- No way to deselect / reset highlight without clicking another account. A "clear
  selection" button or clicking the same account again could reset all pens to base width.
- Rubber-band zoom resets on next `refresh()` call (e.g. after a new batch is committed);
  could preserve the viewport if the project has not changed.

### Data
- The month-end aggregation uses `.last()` within each `(display_label, year, month)`
  group after sorting by `sort_date`. If two different `account_id` rows fall on the same
  last day, the closing balance is not summed — it takes whichever row sorts last.  For
  the re-issued-card case this is usually correct (same physical account), but a more
  explicit sum may be safer.  # TODO: move to bsp
- No handling for accounts where `company` or `account_type` is `NULL` in `DimAccount` —
  these would show as `"None"` in the label. Add a coalesce in the worker.
- `BalanceChartWorker` catches `sqlite3.OperationalError` and `bsp.StatementError` only;
  a `polars.exceptions.ColumnNotFoundError` (e.g. if `DimAccount` schema changes) would
  fall through to the bare `Exception` handler and print to stderr. Consider adding it
  explicitly once bsp stabilises.

### Architecture
- All three `# TODO: move to bsp` blocks in `BalanceChartWorker.run()` should eventually
  become a named query in `bank_statement_parser` so the CLI and API share the same logic
  (D001 compliance). The shim is intentional and documented.
- `BalanceAccountModel` is not unit-tested (no GUI tests by convention in this repo).

---

## How to resume

```bash
git checkout balance_chart
uv sync --all-groups
uv run openstan          # smoke-test — select a project with committed statements
```

Key files to read first:
- `REQUIREMENTS.md` — Section 8 (BC-1 – BC-8)
- `ROADMAP.md` — Milestone 5
- `src/openstan/presenters/balance_chart_presenter.py` — worker + model + presenter
- `src/openstan/views/balance_chart_view.py` — view widget
- `src/openstan/views/project_view.py` — `button_balance` addition

Useful bsp API (read-only, do not modify):
```python
import bank_statement_parser as bsp
bsp.db.FactBalance(project_path).all   # pl.LazyFrame — cols include account_id,
                                        # id_date, closing_balance, outside_date
bsp.db.DimAccount(project_path).all    # pl.LazyFrame — cols include account_id,
                                        # id_account, company, account_type,
                                        # account_holder, account_number, sortcode
```

---

## Dependency added (already in pyproject.toml + uv.lock)

```
pyqt6-charts==6.10.0
```
