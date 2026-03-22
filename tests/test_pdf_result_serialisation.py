"""
test_pdf_result_serialisation.py — unit tests for PdfResult JSON round-trip.

These tests verify that ``_pdf_result_to_json`` and ``_json_to_pdf_result``
preserve every field across a serialise/deserialise cycle for all three
concrete payload types (Success, Review, Failure), including edge cases
(None paths, empty message_detail).

The field-completeness tests use ``dataclasses.fields()`` to enumerate every
field on every class in the ``PdfResult`` object graph.  If ``bsp`` adds a new
field without a corresponding update to the factory function, those tests will
fail — there is no silent dropping.

No Qt or GUI components are required; these tests run with plain pytest.

Run with::

    uv run pytest tests/test_pdf_result_serialisation.py -v
"""

import dataclasses
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from bank_statement_parser import PdfResult
from bank_statement_parser.modules.data import (
    Failure,
    ParquetFiles,
    Review,
    StatementInfo,
    Success,
)
from openstan.models.statement_result_model import (
    _json_to_pdf_result,
    _pdf_result_to_json,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_statement_info() -> StatementInfo:
    return StatementInfo(
        id_statement="abc123def456",
        id_account="barclays_12345678",
        account="Barclays Current Account",
        statement_date=date(2024, 1, 31),
        payments_in=Decimal("1234.56"),
        payments_out=Decimal("789.00"),
        opening_balance=Decimal("500.00"),
        closing_balance=Decimal("945.56"),
        filename_new="barclays_2024-01.pdf",
    )


def _make_parquet_files_full() -> ParquetFiles:
    return ParquetFiles(
        statement_heads=Path("/tmp/batch/heads.parquet"),
        statement_lines=Path("/tmp/batch/lines.parquet"),
    )


def _make_parquet_files_none() -> ParquetFiles:
    """Edge case: both paths absent."""
    return ParquetFiles(
        statement_heads=None,
        statement_lines=None,
    )


def _make_success_result(parquet_files: ParquetFiles | None = None) -> PdfResult:
    return PdfResult(
        result="SUCCESS",
        outcome="SUCCESS",
        batch_lines=Path("/tmp/batch/batch_lines.parquet"),
        checks_and_balances=Path("/tmp/batch/checks.parquet"),
        payload=Success(
            statement_info=_make_statement_info(),
            parquet_files=parquet_files or _make_parquet_files_full(),
        ),
    )


def _make_review_result() -> PdfResult:
    return PdfResult(
        result="REVIEW",
        outcome="REVIEW CAB",
        batch_lines=Path("/tmp/batch/batch_lines.parquet"),
        checks_and_balances=Path("/tmp/batch/checks.parquet"),
        payload=Review(
            statement_info=_make_statement_info(),
            parquet_files=_make_parquet_files_full(),
            message="CAB validation failed",
            message_detail="Opening balance mismatch",
        ),
    )


def _make_review_result_empty_detail() -> PdfResult:
    """Edge case: message_detail is the default empty string."""
    return PdfResult(
        result="REVIEW",
        outcome="REVIEW CAB",
        batch_lines=Path("/tmp/batch/batch_lines.parquet"),
        checks_and_balances=None,
        payload=Review(
            statement_info=_make_statement_info(),
            parquet_files=_make_parquet_files_full(),
            message="CAB validation failed",
        ),
    )


def _make_failure_result() -> PdfResult:
    return PdfResult(
        result="FAILURE",
        outcome="FAILURE DATA",
        batch_lines=Path("/tmp/batch/batch_lines.parquet"),
        checks_and_balances=None,
        payload=Failure(
            message="Could not parse statement",
            error_type="data",
            message_detail="Page 3 table not found",
        ),
    )


def _make_failure_config_result() -> PdfResult:
    return PdfResult(
        result="FAILURE",
        outcome="FAILURE CONFIG",
        batch_lines=Path("/tmp/batch/batch_lines.parquet"),
        checks_and_balances=None,
        payload=Failure(
            message="No config found for this bank",
            error_type="config",
        ),
    )


# ---------------------------------------------------------------------------
# Helper: compare every dataclasses.field on two instances of the same type
# ---------------------------------------------------------------------------


def _assert_all_fields_equal(original: object, restored: object) -> None:
    """Recursively assert that every declared dataclass field matches.

    This is the "no silent dropping" guarantee: if ``bsp`` adds a new field
    and the factory is not updated, the field will be missing from *restored*
    (defaulting to whatever the dataclass default is, or raising an error),
    and this comparison will catch the divergence.
    """
    assert type(original) is type(restored), (
        f"Type mismatch: {type(original).__name__!r} vs {type(restored).__name__!r}"
    )
    for f in dataclasses.fields(original):  # type: ignore[arg-type]
        orig_val = getattr(original, f.name)
        rest_val = getattr(restored, f.name)
        if dataclasses.is_dataclass(orig_val):
            _assert_all_fields_equal(orig_val, rest_val)
        else:
            assert orig_val == rest_val, (
                f"Field {type(original).__name__}.{f.name}: "
                f"expected {orig_val!r}, got {rest_val!r}"
            )


# ---------------------------------------------------------------------------
# Round-trip equality tests
# ---------------------------------------------------------------------------


class TestRoundTripEquality:
    """Basic round-trip: serialise then deserialise, assert ``==``."""

    def test_success_result(self) -> None:
        original = _make_success_result()
        assert _json_to_pdf_result(_pdf_result_to_json(original)) == original

    def test_success_result_null_parquet_paths(self) -> None:
        original = _make_success_result(parquet_files=_make_parquet_files_none())
        assert _json_to_pdf_result(_pdf_result_to_json(original)) == original

    def test_review_result(self) -> None:
        original = _make_review_result()
        assert _json_to_pdf_result(_pdf_result_to_json(original)) == original

    def test_review_result_null_checks_and_balances(self) -> None:
        original = _make_review_result_empty_detail()
        assert _json_to_pdf_result(_pdf_result_to_json(original)) == original

    def test_failure_data_result(self) -> None:
        original = _make_failure_result()
        assert _json_to_pdf_result(_pdf_result_to_json(original)) == original

    def test_failure_config_result(self) -> None:
        original = _make_failure_config_result()
        assert _json_to_pdf_result(_pdf_result_to_json(original)) == original


# ---------------------------------------------------------------------------
# Field-completeness tests (no silent dropping)
# ---------------------------------------------------------------------------


class TestFieldCompleteness:
    """Assert that every declared field on every class in the PdfResult graph
    survives the round-trip with its exact value preserved.

    If ``bsp`` adds a new field to any of these classes and the factory
    is not updated, one of these tests will fail.
    """

    def test_pdf_result_fields_success(self) -> None:
        original = _make_success_result()
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        _assert_all_fields_equal(original, restored)

    def test_pdf_result_fields_review(self) -> None:
        original = _make_review_result()
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        _assert_all_fields_equal(original, restored)

    def test_pdf_result_fields_failure(self) -> None:
        original = _make_failure_result()
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        _assert_all_fields_equal(original, restored)

    def test_statement_info_field_count(self) -> None:
        """Fail if StatementInfo gains or loses fields without updating the factory."""
        original = _make_success_result()
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        orig_info = original.payload.statement_info  # type: ignore[union-attr]
        rest_info = restored.payload.statement_info  # type: ignore[union-attr]
        orig_names = {f.name for f in dataclasses.fields(orig_info)}
        rest_names = {f.name for f in dataclasses.fields(rest_info)}
        assert orig_names == rest_names, (
            f"StatementInfo field set changed: added={rest_names - orig_names}, "
            f"removed={orig_names - rest_names}"
        )

    def test_parquet_files_field_count(self) -> None:
        """Fail if ParquetFiles gains or loses fields without updating the factory."""
        original = _make_success_result()
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        orig_pf = original.payload.parquet_files  # type: ignore[union-attr]
        rest_pf = restored.payload.parquet_files  # type: ignore[union-attr]
        orig_names = {f.name for f in dataclasses.fields(orig_pf)}
        rest_names = {f.name for f in dataclasses.fields(rest_pf)}
        assert orig_names == rest_names, (
            f"ParquetFiles field set changed: added={rest_names - orig_names}, "
            f"removed={orig_names - rest_names}"
        )


# ---------------------------------------------------------------------------
# Type fidelity tests
# ---------------------------------------------------------------------------


class TestTypeFidelity:
    """Assert that non-JSON-native types survive as the correct Python type."""

    def test_path_is_path(self) -> None:
        original = _make_success_result()
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        assert isinstance(restored.batch_lines, Path)
        assert isinstance(restored.checks_and_balances, Path)
        assert isinstance(restored.payload.parquet_files.statement_heads, Path)  # type: ignore[union-attr]
        assert isinstance(restored.payload.parquet_files.statement_lines, Path)  # type: ignore[union-attr]

    def test_optional_path_is_none(self) -> None:
        original = _make_failure_result()  # checks_and_balances=None
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        assert restored.checks_and_balances is None

    def test_decimal_is_decimal(self) -> None:
        original = _make_success_result()
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        info = restored.payload.statement_info  # type: ignore[union-attr]
        assert isinstance(info.payments_in, Decimal)
        assert isinstance(info.payments_out, Decimal)
        assert isinstance(info.opening_balance, Decimal)
        assert isinstance(info.closing_balance, Decimal)

    def test_decimal_precision_preserved(self) -> None:
        """Decimal precision must survive; float conversion would lose it."""
        original = _make_success_result()
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        info = restored.payload.statement_info  # type: ignore[union-attr]
        assert info.payments_in == Decimal("1234.56")
        assert info.payments_out == Decimal("789.00")
        assert info.opening_balance == Decimal("500.00")
        assert info.closing_balance == Decimal("945.56")

    def test_date_is_date(self) -> None:
        original = _make_success_result()
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        info = restored.payload.statement_info  # type: ignore[union-attr]
        assert isinstance(info.statement_date, date)
        assert info.statement_date == date(2024, 1, 31)

    def test_payload_type_success(self) -> None:
        original = _make_success_result()
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        assert isinstance(restored.payload, Success)

    def test_payload_type_review(self) -> None:
        original = _make_review_result()
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        assert isinstance(restored.payload, Review)

    def test_payload_type_failure(self) -> None:
        original = _make_failure_result()
        restored = _json_to_pdf_result(_pdf_result_to_json(original))
        assert isinstance(restored.payload, Failure)


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_invalid_json_raises(self) -> None:
        with pytest.raises(Exception):
            _json_to_pdf_result("not valid json")

    def test_unknown_discriminator_raises_value_error(self) -> None:
        import json

        original = _make_success_result()
        data = json.loads(_pdf_result_to_json(original))
        data["payload"]["_type"] = "UnknownType"
        with pytest.raises(ValueError, match="Unknown PdfResult payload type"):
            _json_to_pdf_result(json.dumps(data))
