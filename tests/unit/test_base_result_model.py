"""
test_base_result_model.py — unit tests for the in-memory result models and
the _row_items helper in statement_result_model.py.

``_BaseResultModel`` and its three concrete subclasses (``SuccessResultModel``,
``ReviewResultModel``, ``FailureResultModel``) are pure in-memory
``QStandardItemModel`` subclasses — no database connection required.

``_row_items`` is a pure function that converts a ``ResultRow`` into a list
of ``QStandardItem`` objects.
"""

from pathlib import Path
from uuid import uuid4


from PyQt6.QtCore import Qt

from openstan.models.statement_result_model import (
    FailureResultModel,
    ResultRow,
    ReviewResultModel,
    SuccessResultModel,
    _row_items,
)

_COLUMN_COUNT = 8  # must match len(_COLUMNS) in statement_result_model.py


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def _make_result_row(
    result: str = "SUCCESS",
    id_account: str | None = "barclays_12345678",
    statement_date: str | None = "2024-01-31",
    payments_in: float | None = 1234.56,
    payments_out: float | None = 789.00,
    error_type: str | None = None,
    message: str | None = None,
) -> ResultRow:
    return ResultRow(
        result_id=uuid4().hex,
        batch_id=uuid4().hex,
        queue_id=uuid4().hex,
        project_id=uuid4().hex,
        result=result,
        file_path=Path("/tmp/statement.pdf"),
        id_account=id_account,
        statement_date=statement_date,
        payments_in=payments_in,
        payments_out=payments_out,
        error_type=error_type,
        message=message,
    )


def _make_failure_row() -> ResultRow:
    return _make_result_row(
        result="FAILURE",
        id_account=None,
        statement_date=None,
        payments_in=None,
        payments_out=None,
        error_type="data",
        message="Could not parse page 3",
    )


# ---------------------------------------------------------------------------
# TestRowItems
# ---------------------------------------------------------------------------


class TestRowItems:
    """Tests for the _row_items pure function."""

    def test_returns_eight_items(self) -> None:
        """_row_items returns exactly one item per column."""
        row = _make_result_row()
        items = _row_items(row)
        assert len(items) == _COLUMN_COUNT

    def test_file_column_is_filename_only(self) -> None:
        """File column uses Path.name, not the full path."""
        row = _make_result_row()
        items = _row_items(row)
        assert items[0].text() == "statement.pdf"

    def test_none_optional_fields_produce_empty_strings(self) -> None:
        """None optional fields map to empty string items, not 'None'."""
        row = _make_failure_row()
        items = _row_items(row)
        # id_account (col 2), statement_date (col 3)
        assert items[2].text() == ""
        assert items[3].text() == ""
        # payments_in (col 4), payments_out (col 5)
        assert items[4].text() == ""
        assert items[5].text() == ""

    def test_error_fields_populated_for_failure(self) -> None:
        """error_type and message are populated from failure rows."""
        row = _make_failure_row()
        items = _row_items(row)
        assert items[6].text() == "data"
        assert items[7].text() == "Could not parse page 3"

    def test_payment_values_are_stringified(self) -> None:
        """Numeric payment values are converted to strings."""
        row = _make_result_row(payments_in=1234.56, payments_out=789.0)
        items = _row_items(row)
        assert "1234.56" in items[4].text()
        assert "789" in items[5].text()

    def test_result_value_in_correct_column(self) -> None:
        """The result string ('SUCCESS', 'REVIEW', 'FAILURE') is at column 1."""
        for result_str in ("SUCCESS", "REVIEW", "FAILURE"):
            row = _make_result_row(result=result_str)
            items = _row_items(row)
            assert items[1].text() == result_str


# ---------------------------------------------------------------------------
# TestBaseResultModel
# ---------------------------------------------------------------------------


class TestBaseResultModel:
    """Tests for _BaseResultModel via its concrete subclasses."""

    def test_add_row_increments_row_count(self, qapp) -> None:
        """add_row increments the row_count property."""
        model = SuccessResultModel()
        assert model.row_count == 0
        model.add_row(_make_result_row())
        assert model.row_count == 1
        model.add_row(_make_result_row())
        assert model.row_count == 2

    def test_add_row_appends_to_all_rows(self, qapp) -> None:
        """add_row appends the ResultRow to all_rows()."""
        model = SuccessResultModel()
        row = _make_result_row()
        model.add_row(row)
        all_rows = model.all_rows()
        assert len(all_rows) == 1
        assert all_rows[0] is row

    def test_clear_rows_resets_row_count(self, qapp) -> None:
        """clear_rows resets row_count to 0."""
        model = SuccessResultModel()
        model.add_row(_make_result_row())
        model.add_row(_make_result_row())
        model.clear_rows()
        assert model.row_count == 0

    def test_clear_rows_empties_all_rows(self, qapp) -> None:
        """clear_rows empties the all_rows() list."""
        model = SuccessResultModel()
        model.add_row(_make_result_row())
        model.clear_rows()
        assert model.all_rows() == []

    def test_flags_do_not_include_editable(self, qapp) -> None:
        """No cell in the model is editable (results are read-only)."""
        model = SuccessResultModel()
        model.add_row(_make_result_row())
        idx = model.index(0, 0)
        flags = model.flags(idx)
        assert not (flags & Qt.ItemFlag.ItemIsEditable)

    def test_all_rows_returns_copy(self, qapp) -> None:
        """all_rows() returns a copy — mutating it does not affect the model."""
        model = SuccessResultModel()
        row = _make_result_row()
        model.add_row(row)
        copy = model.all_rows()
        copy.clear()
        assert model.row_count == 1

    def test_qt_row_count_matches_internal_count(self, qapp) -> None:
        """The Qt model rowCount() matches the internal row_count property."""
        model = ReviewResultModel()
        model.add_row(_make_result_row(result="REVIEW"))
        model.add_row(_make_result_row(result="REVIEW"))
        assert model.rowCount() == model.row_count == 2

    def test_qt_row_count_reset_on_clear(self, qapp) -> None:
        """After clear_rows(), Qt's rowCount() is also 0."""
        model = FailureResultModel()
        model.add_row(_make_failure_row())
        model.clear_rows()
        assert model.rowCount() == 0


# ---------------------------------------------------------------------------
# TestModelIndependence
# ---------------------------------------------------------------------------


class TestModelIndependence:
    """The three concrete models are independent — no shared state."""

    def test_success_and_review_models_are_independent(self, qapp) -> None:
        """Adding to SuccessResultModel does not affect ReviewResultModel."""
        success_model = SuccessResultModel()
        review_model = ReviewResultModel()

        success_model.add_row(_make_result_row(result="SUCCESS"))
        assert success_model.row_count == 1
        assert review_model.row_count == 0

    def test_clear_one_does_not_clear_other(self, qapp) -> None:
        """Clearing one model does not affect another."""
        success_model = SuccessResultModel()
        failure_model = FailureResultModel()

        success_model.add_row(_make_result_row())
        failure_model.add_row(_make_failure_row())

        success_model.clear_rows()
        assert success_model.row_count == 0
        assert failure_model.row_count == 1
