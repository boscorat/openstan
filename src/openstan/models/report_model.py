"""report_model.py — Filesystem-based model for user-defined report definitions.

Reports are stored as TOML files under ``<project>/config/reports/*.toml``.
This model is intentionally not a ``QSqlTableModel`` — there is no GUI-DB
record for reports; they live on disk alongside the project, consistent with
how export specs are stored at ``<project>/config/export/*.toml``.

Each report file has the following structure::

    [meta]
    title = "Monthly Spend"
    subtitle = "Grouped by account and month"

    [query]
    columns = ["transaction_date", "account_holder", "value_in", "value_out"]
    derived_date_columns = ["year", "month"]

    [[query.filters]]
    column = "CD"
    operator = "eq"     # eq | ne | gt | lt | ge | le | contains | is_in
    value = "D"

    [[query.group_by]]
    columns = ["account_holder", "year", "month"]

    [[query.aggregations]]
    column = "value_out"
    function = "sum"    # sum | mean | min | max | count
    alias = "total_spend"

The ``ReportModel`` class is a lightweight ``QObject`` that wraps the
filesystem operations and emits ``reports_changed`` whenever the on-disk set
of reports is modified.
"""

from __future__ import annotations

import tomllib
import traceback
from pathlib import Path
from typing import Any

import tomli_w
from PyQt6.QtCore import QObject, pyqtSignal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Subdirectory within the project config folder where reports are stored.
REPORTS_SUBDIR = Path("config") / "report"

#: Columns available from ``FlatTransaction`` with user-friendly labels.
FLAT_TRANSACTION_COLUMNS: list[tuple[str, str]] = [
    ("transaction_date", "Date"),
    ("statement_date", "Statement Date"),
    ("filename", "Filename"),
    ("company", "Company"),
    ("account_type", "Account Type"),
    ("account_number", "Account Number"),
    ("sortcode", "Sort Code"),
    ("account_holder", "Account Holder"),
    ("transaction_number", "Tx #"),
    ("CD", "Credit / Debit"),
    ("type", "Type"),
    ("transaction_desc", "Description"),
    ("short_desc", "Short Description"),
    ("value_in", "Value In"),
    ("value_out", "Value Out"),
    ("value", "Net Value"),
]

#: Derived date columns that can be extracted from ``transaction_date``.
DERIVED_DATE_COLUMNS: list[tuple[str, str]] = [
    ("year", "Year"),
    ("quarter", "Quarter"),
    ("month_number", "Month Number"),
    ("month_name", "Month Name"),
    ("week", "Week"),
    ("day_of_week", "Day of Week"),
]

#: Supported filter operators with display labels.
FILTER_OPERATORS: list[tuple[str, str]] = [
    ("eq", "="),
    ("ne", "≠"),
    ("gt", ">"),
    ("lt", "<"),
    ("ge", "≥"),
    ("le", "≤"),
    ("contains", "contains"),
    ("is_in", "is in"),
    ("not_in", "not in"),
]

#: Subset of ``FLAT_TRANSACTION_COLUMNS`` that hold numeric (float) values.
#: Used to restrict the aggregation column picker to fields where sum / mean /
#: min / max are meaningful.
NUMERIC_COLUMNS: list[tuple[str, str]] = [
    ("value_in", "Value In"),
    ("value_out", "Value Out"),
    ("value", "Net Value"),
]

#: Supported aggregation functions with display labels.
AGGREGATION_FUNCTIONS: list[tuple[str, str]] = [
    ("sum", "Sum"),
    ("mean", "Mean"),
    ("min", "Min"),
    ("max", "Max"),
    ("count", "Count"),
]

# ---------------------------------------------------------------------------
# Dataclass-style type alias
# ---------------------------------------------------------------------------

ReportDefinition = dict[str, Any]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class ReportModel(QObject):
    """Filesystem-backed model for user report definitions.

    Signals
    -------
    reports_changed:
        Emitted after any successful save or delete operation so the view
        can refresh its saved-reports list.
    """

    reports_changed: pyqtSignal = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

    # ------------------------------------------------------------------
    # Directory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def reports_dir(project_path: Path) -> Path:
        """Return (and create if needed) the reports directory."""
        d = project_path / REPORTS_SUBDIR
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list_reports(self, project_path: Path) -> list[tuple[str, Path]]:
        """Return a sorted list of ``(display_name, path)`` tuples.

        ``display_name`` is the ``[meta] title`` from the TOML file, falling
        back to the stem of the filename if the file cannot be parsed.
        """
        reports_dir = self.reports_dir(project_path)
        results: list[tuple[str, Path]] = []
        for p in sorted(reports_dir.glob("*.toml")):
            try:
                with open(p, "rb") as fh:
                    data = tomllib.load(fh)
                name = data.get("meta", {}).get("title", p.stem)
            except Exception:
                name = p.stem
            results.append((name, p))
        return results

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load_report(self, path: Path) -> tuple[bool, ReportDefinition, str]:
        """Load and return a report definition from a TOML file.

        Returns
        -------
        (success, definition, message)
        """
        try:
            with open(path, "rb") as fh:
                data: ReportDefinition = tomllib.load(fh)
            return True, data, ""
        except Exception as e:
            traceback.print_exc()
            return False, {}, f"Could not load report '{path.name}': {e}"

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save_report(
        self,
        project_path: Path,
        filename: str,
        definition: ReportDefinition,
    ) -> tuple[bool, Path, str]:
        """Serialise ``definition`` to ``<reports_dir>/<filename>.toml``.

        ``filename`` should not include the ``.toml`` extension.
        Existing files with the same name are overwritten.

        Returns
        -------
        (success, path, message)
        """
        reports_dir = self.reports_dir(project_path)
        safe_name = _slugify(filename) or "report"
        path = reports_dir / f"{safe_name}.toml"
        try:
            with open(path, "wb") as fh:
                tomli_w.dump(definition, fh)
            self.reports_changed.emit()
            return True, path, ""
        except Exception as e:
            traceback.print_exc()
            return False, path, f"Could not save report: {e}"

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_report(self, path: Path) -> tuple[bool, Path, str]:
        """Delete a report TOML file.

        Returns
        -------
        (success, path, message)
        """
        try:
            path.unlink(missing_ok=True)
            self.reports_changed.emit()
            return True, path, ""
        except Exception as e:
            traceback.print_exc()
            return False, path, f"Could not delete report '{path.name}': {e}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert a report title to a safe filename stem.

    Replaces spaces and special characters with underscores and lowercases
    the result.  Strips leading/trailing underscores and collapses runs of
    underscores.
    """
    import re

    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "report"
