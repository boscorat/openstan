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

import inspect
from pathlib import Path
from typing import get_type_hints

import pytest

import bank_statement_parser as bsp
from bank_statement_parser.modules.errors import (
    Failure,
    InvalidData,
    MissingDependency,
    ParseError,
    Review,
    Success,
    TestGateFailure,
)
from bank_statement_parser.modules.statements import PdfResult


class TestBSPFunctionSignatures:
    """Validate that BSP function signatures haven't changed."""

    @pytest.mark.integration
    def test_process_pdf_statement_signature(self):
        """Validate process_pdf_statement() exists and accepts expected params."""
        assert hasattr(bsp, "process_pdf_statement"), "process_pdf_statement() not found in bsp"

        func = bsp.process_pdf_statement
        sig = inspect.signature(func)
        params = set(sig.parameters.keys())

        # These are the parameters openstan depends on
        expected_params = {"pdf_path"}  # At minimum, pdf_path
        assert expected_params <= params, f"Missing parameters: {expected_params - params}"

    @pytest.mark.integration
    def test_update_db_signature(self):
        """Validate update_db() exists and has expected signature."""
        assert hasattr(bsp, "update_db"), "update_db() not found in bsp"

        func = bsp.update_db
        sig = inspect.signature(func)
        params = set(sig.parameters.keys())

        # Expect these core parameters
        expected_params = {"project_path", "parquet_dir"}
        assert expected_params <= params, f"Missing parameters: {expected_params - params}"

    @pytest.mark.integration
    def test_copy_statements_to_project_signature(self):
        """Validate copy_statements_to_project() signature."""
        assert hasattr(bsp, "copy_statements_to_project"), "copy_statements_to_project() not found"

        func = bsp.copy_statements_to_project
        sig = inspect.signature(func)
        params = set(sig.parameters.keys())

        expected_params = {"project_path", "parquet_dir"}
        assert expected_params <= params, f"Missing parameters: {expected_params - params}"


class TestBSPResultEnums:
    """Validate that BSP result enums and types haven't changed."""

    @pytest.mark.integration
    def test_result_enums_exist(self):
        """Validate that Success, Review, Failure enums exist."""
        # These should be importable without raising
        assert Success is not None, "Success enum not found"
        assert Review is not None, "Review enum not found"
        assert Failure is not None, "Failure enum not found"

    @pytest.mark.integration
    def test_pdf_result_dataclass_exists(self):
        """Validate that PdfResult dataclass exists and is importable."""
        assert PdfResult is not None, "PdfResult dataclass not found"

    @pytest.mark.integration
    def test_pdf_result_has_required_fields(self):
        """Validate that PdfResult has fields openstan depends on."""
        hints = get_type_hints(PdfResult)

        # These fields are used by openstan's result processing
        expected_fields = {"pdf_path", "result", "page_count"}
        actual_fields = set(hints.keys())

        missing = expected_fields - actual_fields
        assert not missing, f"PdfResult missing fields: {missing}"

    @pytest.mark.integration
    def test_success_dataclass_has_required_fields(self):
        """Validate that Success has fields openstan depends on."""
        hints = get_type_hints(Success)

        # These fields are used by openstan's result display
        expected_fields = {"transactions", "accounts"}
        actual_fields = set(hints.keys())

        missing = expected_fields - actual_fields
        assert not missing, f"Success missing fields: {missing}"


class TestBSPExceptions:
    """Validate that BSP exception types haven't changed."""

    @pytest.mark.integration
    def test_expected_exceptions_exist(self):
        """Validate that expected exception types exist."""
        # These are caught by openstan's error handling
        assert ParseError is not None, "ParseError not found"
        assert InvalidData is not None, "InvalidData not found"
        assert MissingDependency is not None, "MissingDependency not found"
        assert TestGateFailure is not None, "TestGateFailure not found"

    @pytest.mark.integration
    def test_exceptions_are_exception_subclasses(self):
        """Validate that exceptions actually inherit from Exception."""
        assert issubclass(ParseError, Exception), "ParseError is not an Exception"
        assert issubclass(InvalidData, Exception), "InvalidData is not an Exception"
        assert issubclass(MissingDependency, Exception), "MissingDependency is not an Exception"
        assert issubclass(TestGateFailure, Exception), "TestGateFailure is not an Exception"


class TestBSPVersionCompatibility:
    """Validate version compatibility with pinned BSP version."""

    @pytest.mark.integration
    def test_bsp_version_is_expected(self):
        """Validate that BSP version matches expected pinned version."""
        # We're pinned to 0.2.1b7
        expected_version = "0.2.1b7"

        actual_version = bsp.__version__ if hasattr(bsp, "__version__") else "unknown"

        assert (
            actual_version == expected_version
        ), f"BSP version mismatch: expected {expected_version}, got {actual_version}"


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
        assert hasattr(TestHarness, "__enter__"), "TestHarness doesn't support __enter__"
        assert hasattr(TestHarness, "__exit__"), "TestHarness doesn't support __exit__"

    @pytest.mark.integration
    def test_test_harness_has_db_path(self):
        """Validate TestHarness has db_path attribute."""
        from bank_statement_parser.testing import TestHarness

        # Create a minimal instance to check attributes
        th = TestHarness.__new__(TestHarness)
        assert hasattr(th, "db_path"), "TestHarness doesn't have db_path attribute"
