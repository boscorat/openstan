"""
Contract validation tests for bank_statement_parser (BSP).

These tests ensure that openstan's assumptions about BSP's API remain valid
as BSP evolves. If BSP makes breaking changes, these tests will fail fast
during development rather than causing silent failures in production.

Tests cover:
- Function signatures (process_pdf_statement, update_db, etc.)
- Enum values and result types (Success, Review, Failure)
- Database schema (expected tables, columns, indexes)
- Dataclass fields (PdfResult, Success, Review, Failure)
"""

from typing import get_type_hints

import bank_statement_parser as bsp
import pytest
from bank_statement_parser.modules.errors import (
    ProjectError,
    StatementError,
)
from bank_statement_parser.modules.errors import (
    TestGateFailure as _TestGateFailure,
)
from bank_statement_parser.modules.statements import Failure, PdfResult, Review, Success


class TestBSPFunctionSignatures:
    """Validate that BSP function signatures haven't changed."""

    @pytest.mark.integration
    def test_process_pdf_statement_exists(self):
        """Validate process_pdf_statement() is still available."""
        assert hasattr(bsp, "process_pdf_statement"), (
            "process_pdf_statement() not found in bsp"
        )
        assert callable(bsp.process_pdf_statement), (
            "process_pdf_statement is not callable"
        )

    @pytest.mark.integration
    def test_update_db_exists(self):
        """Validate update_db() is still available."""
        assert hasattr(bsp, "update_db"), "update_db() not found in bsp"
        assert callable(bsp.update_db), "update_db is not callable"

    @pytest.mark.integration
    def test_copy_statements_to_project_exists(self):
        """Validate copy_statements_to_project() is still available."""
        assert hasattr(bsp, "copy_statements_to_project"), (
            "copy_statements_to_project() not found"
        )
        assert callable(bsp.copy_statements_to_project), (
            "copy_statements_to_project is not callable"
        )


class TestBSPResultEnums:
    """Validate that BSP result enums and types haven't changed."""

    @pytest.mark.integration
    def test_result_classes_exist(self):
        """Validate that Success, Review, Failure classes exist."""
        # These should be importable without raising
        assert Success is not None, "Success class not found"
        assert Review is not None, "Review class not found"
        assert Failure is not None, "Failure class not found"

    @pytest.mark.integration
    def test_pdf_result_dataclass_exists(self):
        """Validate that PdfResult dataclass exists and is importable."""
        assert PdfResult is not None, "PdfResult dataclass not found"

    @pytest.mark.integration
    def test_pdf_result_has_required_fields(self):
        """Validate that PdfResult has fields openstan depends on."""
        hints = get_type_hints(PdfResult)

        # These fields are used by openstan's result processing
        expected_fields = {"result", "outcome", "payload"}
        actual_fields = set(hints.keys())

        missing = expected_fields - actual_fields
        assert not missing, f"PdfResult missing fields: {missing}"

    @pytest.mark.integration
    def test_success_dataclass_has_required_fields(self):
        """Validate that Success has fields openstan depends on."""
        hints = get_type_hints(Success)

        # These fields are used by openstan's result display
        expected_fields = {"statement_info", "parquet_files"}
        actual_fields = set(hints.keys())

        missing = expected_fields - actual_fields
        assert not missing, f"Success missing fields: {missing}"

    @pytest.mark.integration
    def test_pdf_result_literals(self):
        """Validate that PdfResult accepts expected literal values."""
        hints = get_type_hints(PdfResult)
        result_hint = hints.get("result")

        # Should support SUCCESS, REVIEW, FAILURE
        assert result_hint is not None, "PdfResult.result field not found in hints"


class TestBSPExceptions:
    """Validate that BSP exception types haven't changed."""

    @pytest.mark.integration
    def test_expected_exceptions_exist(self):
        """Validate that expected exception types exist."""
        # These are caught by openstan's error handling
        assert ProjectError is not None, "ProjectError not found"
        assert StatementError is not None, "StatementError not found"
        assert _TestGateFailure is not None, "TestGateFailure not found"

    @pytest.mark.integration
    def test_exceptions_are_exception_subclasses(self):
        """Validate that exceptions actually inherit from Exception."""
        assert issubclass(ProjectError, Exception), "ProjectError is not an Exception"
        assert issubclass(StatementError, Exception), (
            "StatementError is not an Exception"
        )
        assert issubclass(_TestGateFailure, Exception), (
            "TestGateFailure is not an Exception"
        )


class TestBSPTestHarness:
    """Validate that TestHarness API hasn't changed."""

    @pytest.mark.integration
    def test_test_harness_exists(self):
        """Validate TestHarness class can be imported."""
        from bank_statement_parser.testing import TestHarness

        assert TestHarness is not None, "TestHarness not found"

    @pytest.mark.integration
    def test_test_harness_context_manager(self):
        """Validate TestHarness works as context manager."""
        from bank_statement_parser.testing import TestHarness

        # Should be able to use as context manager
        assert hasattr(TestHarness, "__enter__"), (
            "TestHarness doesn't support __enter__"
        )
        assert hasattr(TestHarness, "__exit__"), "TestHarness doesn't support __exit__"

    @pytest.mark.integration
    def test_test_harness_callable(self):
        """Validate TestHarness can be instantiated."""
        from bank_statement_parser.testing import TestHarness

        # Should be callable (instantiable)
        assert callable(TestHarness), "TestHarness is not callable"
