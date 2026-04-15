"""
test_integration.py — integration tests for the openstan import pipeline.

Two test classes are provided:

``TestImportResults``
    Validates that the openstan pipeline processes the expected number of PDFs
    and that SUCCESS/REVIEW counts match what bsp's StatementBatch produced for
    the same good/ PDFs.

``TestDatabaseComparison``
    Compares the resulting openstan project.db against the bsp reference
    project.db built by TestHarness.  For each of the five datamart tables
    (DimDate, DimAccount, DimStatement, FactTransaction, FactBalance) it checks
    row counts and numeric column sums.

Run with::

    uv run pytest tests/ -v
"""

import sqlite3
from typing import TYPE_CHECKING, Any

from bank_statement_parser.testing import _pdf_dir

if TYPE_CHECKING:
    from bank_statement_parser.testing import TestHarness

from tests.conftest import OpenStanEnv

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FLOAT_TOL = 0.005  # reused from bsp's test_datamart.py

# Datamart tables excluded from row-count/sum comparison:
#   batch_heads, batch_lines      — batch GUIDs and timestamps differ per run
#   checks_and_balances           — processing artefacts, not datamart
#   statement_heads, statement_lines — raw staging tables; focus on DIM*/FACT*
DATAMART_TABLES = [
    "DimDate",
    "DimAccount",
    "DimStatement",
    "FactTransaction",
    "FactBalance",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scalar(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> Any:
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def _real_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """Return names of all REAL/NUMERIC columns in *table*."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    # column info: (cid, name, type, notnull, dflt_value, pk)
    return [r[1] for r in rows if r[2].upper() in ("REAL", "NUMERIC", "FLOAT")]


# ---------------------------------------------------------------------------
# TestImportResults
# ---------------------------------------------------------------------------


class TestImportResults:
    """Validates import result counts produced by the openstan pipeline."""

    def test_total_pdfs_processed(self, openstan_env: OpenStanEnv) -> None:
        """Total processed PDFs equals the number of PDFs in good/ + bad/."""
        good_count = len(list(_pdf_dir("good").glob("*.pdf")))
        bad_count = len(list(_pdf_dir("bad").glob("*.pdf")))
        expected_total = good_count + bad_count
        actual_total = (
            openstan_env.n_success + openstan_env.n_review + openstan_env.n_failure
        )
        assert actual_total == expected_total, (
            f"Expected {expected_total} PDFs processed "
            f"({good_count} good + {bad_count} bad), "
            f"got {actual_total} "
            f"(SUCCESS={openstan_env.n_success}, "
            f"REVIEW={openstan_env.n_review}, "
            f"FAILURE={openstan_env.n_failure})"
        )

    def test_success_count_matches_bsp(self, openstan_env: OpenStanEnv) -> None:
        """SUCCESS count equals bsp TestHarness SUCCESS count (good PDFs only)."""
        assert openstan_env.n_success == openstan_env.bsp_n_success, (
            f"openstan SUCCESS={openstan_env.n_success}, "
            f"bsp SUCCESS={openstan_env.bsp_n_success}"
        )

    def test_review_count_matches_bsp(self, openstan_env: OpenStanEnv) -> None:
        """REVIEW count from good/ PDFs equals bsp TestHarness REVIEW count."""
        assert openstan_env.n_review_good == openstan_env.bsp_n_review, (
            f"openstan REVIEW (good/ only)={openstan_env.n_review_good}, "
            f"bsp REVIEW={openstan_env.bsp_n_review}"
        )

    def test_at_least_one_failure(self, openstan_env: OpenStanEnv) -> None:
        """At least one FAILURE result is produced (bad/ PDFs are expected to fail)."""
        assert openstan_env.n_failure >= 1, (
            f"Expected at least 1 FAILURE from bad/ PDFs, got 0. "
            f"(SUCCESS={openstan_env.n_success}, REVIEW={openstan_env.n_review})"
        )

    def test_bad_pdfs_not_deduplicated(self, openstan_env: OpenStanEnv) -> None:
        """bad/ PDFs with same filenames as good/ PDFs are processed independently.

        The bad/ folder contains 5 PDFs with the same filenames as some good/
        PDFs but different content.  They must not be silently skipped.
        """
        bad_count = len(list(_pdf_dir("bad").glob("*.pdf")))
        good_count = len(list(_pdf_dir("good").glob("*.pdf")))
        actual_total = (
            openstan_env.n_success + openstan_env.n_review + openstan_env.n_failure
        )
        # If bad PDFs were deduplicated against good ones, total would be < good + bad
        assert actual_total == good_count + bad_count, (
            f"Bad PDFs appear to have been deduplicated: "
            f"expected {good_count + bad_count} total, got {actual_total}"
        )


# ---------------------------------------------------------------------------
# TestDatabaseComparison
# ---------------------------------------------------------------------------


class TestDatabaseComparison:
    """Compares the openstan project.db datamart against the bsp reference db.

    Both databases are queried with raw sqlite3 (read-only).  The fixture
    ``bsp_harness`` provides the reference db; ``openstan_env`` provides the
    openstan db.
    """

    # ── DimDate ──────────────────────────────────────────────────────────────

    def test_dim_time_row_count_matches(
        self, bsp_harness: TestHarness, openstan_env: OpenStanEnv
    ) -> None:
        bsp_conn = sqlite3.connect(str(bsp_harness.db_path))
        ost_conn = sqlite3.connect(
            str(openstan_env.project_path / "database" / "project.db")
        )
        try:
            bsp_rows = _scalar(bsp_conn, "SELECT COUNT(*) FROM DimDate")
            ost_rows = _scalar(ost_conn, "SELECT COUNT(*) FROM DimDate")
            assert ost_rows == bsp_rows, (
                f"DimDate row count: openstan={ost_rows}, bsp={bsp_rows}"
            )
        finally:
            bsp_conn.close()
            ost_conn.close()

    def test_dim_time_numeric_sums_match(
        self, bsp_harness: TestHarness, openstan_env: OpenStanEnv
    ) -> None:
        bsp_conn = sqlite3.connect(str(bsp_harness.db_path))
        ost_conn = sqlite3.connect(
            str(openstan_env.project_path / "database" / "project.db")
        )
        try:
            for col in _real_columns(bsp_conn, "DimDate"):
                bsp_sum = _scalar(bsp_conn, f"SELECT SUM({col}) FROM DimDate") or 0.0
                ost_sum = _scalar(ost_conn, f"SELECT SUM({col}) FROM DimDate") or 0.0
                assert abs(bsp_sum - ost_sum) < FLOAT_TOL, (
                    f"DimDate.{col} sum mismatch: openstan={ost_sum}, bsp={bsp_sum}"
                )
        finally:
            bsp_conn.close()
            ost_conn.close()

    # ── DimAccount ───────────────────────────────────────────────────────────

    def test_dim_account_row_count_matches(
        self, bsp_harness: TestHarness, openstan_env: OpenStanEnv
    ) -> None:
        bsp_conn = sqlite3.connect(str(bsp_harness.db_path))
        ost_conn = sqlite3.connect(
            str(openstan_env.project_path / "database" / "project.db")
        )
        try:
            bsp_rows = _scalar(bsp_conn, "SELECT COUNT(*) FROM DimAccount")
            ost_rows = _scalar(ost_conn, "SELECT COUNT(*) FROM DimAccount")
            assert ost_rows == bsp_rows, (
                f"DimAccount row count: openstan={ost_rows}, bsp={bsp_rows}"
            )
        finally:
            bsp_conn.close()
            ost_conn.close()

    def test_dim_account_numeric_sums_match(
        self, bsp_harness: TestHarness, openstan_env: OpenStanEnv
    ) -> None:
        bsp_conn = sqlite3.connect(str(bsp_harness.db_path))
        ost_conn = sqlite3.connect(
            str(openstan_env.project_path / "database" / "project.db")
        )
        try:
            for col in _real_columns(bsp_conn, "DimAccount"):
                bsp_sum = _scalar(bsp_conn, f"SELECT SUM({col}) FROM DimAccount") or 0.0
                ost_sum = _scalar(ost_conn, f"SELECT SUM({col}) FROM DimAccount") or 0.0
                assert abs(bsp_sum - ost_sum) < FLOAT_TOL, (
                    f"DimAccount.{col} sum mismatch: openstan={ost_sum}, bsp={bsp_sum}"
                )
        finally:
            bsp_conn.close()
            ost_conn.close()

    # ── DimStatement ─────────────────────────────────────────────────────────

    def test_dim_statement_row_count_matches(
        self, bsp_harness: TestHarness, openstan_env: OpenStanEnv
    ) -> None:
        bsp_conn = sqlite3.connect(str(bsp_harness.db_path))
        ost_conn = sqlite3.connect(
            str(openstan_env.project_path / "database" / "project.db")
        )
        try:
            bsp_rows = _scalar(bsp_conn, "SELECT COUNT(*) FROM DimStatement")
            ost_rows = _scalar(ost_conn, "SELECT COUNT(*) FROM DimStatement")
            assert ost_rows == bsp_rows, (
                f"DimStatement row count: openstan={ost_rows}, bsp={bsp_rows}"
            )
        finally:
            bsp_conn.close()
            ost_conn.close()

    def test_dim_statement_numeric_sums_match(
        self, bsp_harness: TestHarness, openstan_env: OpenStanEnv
    ) -> None:
        bsp_conn = sqlite3.connect(str(bsp_harness.db_path))
        ost_conn = sqlite3.connect(
            str(openstan_env.project_path / "database" / "project.db")
        )
        try:
            for col in _real_columns(bsp_conn, "DimStatement"):
                bsp_sum = (
                    _scalar(bsp_conn, f"SELECT SUM({col}) FROM DimStatement") or 0.0
                )
                ost_sum = (
                    _scalar(ost_conn, f"SELECT SUM({col}) FROM DimStatement") or 0.0
                )
                assert abs(bsp_sum - ost_sum) < FLOAT_TOL, (
                    f"DimStatement.{col} sum mismatch: openstan={ost_sum}, bsp={bsp_sum}"
                )
        finally:
            bsp_conn.close()
            ost_conn.close()

    # ── FactTransaction ───────────────────────────────────────────────────────

    def test_fact_transaction_row_count_matches(
        self, bsp_harness: TestHarness, openstan_env: OpenStanEnv
    ) -> None:
        bsp_conn = sqlite3.connect(str(bsp_harness.db_path))
        ost_conn = sqlite3.connect(
            str(openstan_env.project_path / "database" / "project.db")
        )
        try:
            bsp_rows = _scalar(bsp_conn, "SELECT COUNT(*) FROM FactTransaction")
            ost_rows = _scalar(ost_conn, "SELECT COUNT(*) FROM FactTransaction")
            assert ost_rows == bsp_rows, (
                f"FactTransaction row count: openstan={ost_rows}, bsp={bsp_rows}"
            )
        finally:
            bsp_conn.close()
            ost_conn.close()

    def test_fact_transaction_numeric_sums_match(
        self, bsp_harness: TestHarness, openstan_env: OpenStanEnv
    ) -> None:
        bsp_conn = sqlite3.connect(str(bsp_harness.db_path))
        ost_conn = sqlite3.connect(
            str(openstan_env.project_path / "database" / "project.db")
        )
        try:
            for col in _real_columns(bsp_conn, "FactTransaction"):
                bsp_sum = (
                    _scalar(bsp_conn, f"SELECT SUM({col}) FROM FactTransaction") or 0.0
                )
                ost_sum = (
                    _scalar(ost_conn, f"SELECT SUM({col}) FROM FactTransaction") or 0.0
                )
                assert abs(bsp_sum - ost_sum) < FLOAT_TOL, (
                    f"FactTransaction.{col} sum mismatch: openstan={ost_sum}, bsp={bsp_sum}"
                )
        finally:
            bsp_conn.close()
            ost_conn.close()

    def test_fact_transaction_value_integrity(self, openstan_env: OpenStanEnv) -> None:
        """Internal check: SUM(value) == SUM(value_in) - SUM(value_out)."""
        ost_conn = sqlite3.connect(
            str(openstan_env.project_path / "database" / "project.db")
        )
        try:
            total_in = (
                _scalar(ost_conn, "SELECT SUM(value_in)  FROM FactTransaction") or 0.0
            )
            total_out = (
                _scalar(ost_conn, "SELECT SUM(value_out) FROM FactTransaction") or 0.0
            )
            total_val = (
                _scalar(ost_conn, "SELECT SUM(value)     FROM FactTransaction") or 0.0
            )
            assert abs(total_val - (total_in - total_out)) < FLOAT_TOL, (
                f"FactTransaction value integrity: "
                f"SUM(value)={total_val}, SUM(value_in)-SUM(value_out)={total_in - total_out}"
            )
        finally:
            ost_conn.close()

    # ── FactBalance ───────────────────────────────────────────────────────────

    def test_fact_balance_row_count_matches(
        self, bsp_harness: TestHarness, openstan_env: OpenStanEnv
    ) -> None:
        bsp_conn = sqlite3.connect(str(bsp_harness.db_path))
        ost_conn = sqlite3.connect(
            str(openstan_env.project_path / "database" / "project.db")
        )
        try:
            bsp_rows = _scalar(bsp_conn, "SELECT COUNT(*) FROM FactBalance")
            ost_rows = _scalar(ost_conn, "SELECT COUNT(*) FROM FactBalance")
            assert ost_rows == bsp_rows, (
                f"FactBalance row count: openstan={ost_rows}, bsp={bsp_rows}"
            )
        finally:
            bsp_conn.close()
            ost_conn.close()

    def test_fact_balance_numeric_sums_match(
        self, bsp_harness: TestHarness, openstan_env: OpenStanEnv
    ) -> None:
        bsp_conn = sqlite3.connect(str(bsp_harness.db_path))
        ost_conn = sqlite3.connect(
            str(openstan_env.project_path / "database" / "project.db")
        )
        try:
            for col in _real_columns(bsp_conn, "FactBalance"):
                bsp_sum = (
                    _scalar(bsp_conn, f"SELECT SUM({col}) FROM FactBalance") or 0.0
                )
                ost_sum = (
                    _scalar(ost_conn, f"SELECT SUM({col}) FROM FactBalance") or 0.0
                )
                assert abs(bsp_sum - ost_sum) < FLOAT_TOL, (
                    f"FactBalance.{col} sum mismatch: openstan={ost_sum}, bsp={bsp_sum}"
                )
        finally:
            bsp_conn.close()
            ost_conn.close()

    def test_fact_balance_coverage(self, openstan_env: OpenStanEnv) -> None:
        """FactBalance has exactly one row per (account × day) in the date spine."""
        ost_conn = sqlite3.connect(
            str(openstan_env.project_path / "database" / "project.db")
        )
        try:
            n_accounts = _scalar(ost_conn, "SELECT COUNT(*) FROM DimAccount") or 0
            n_days = _scalar(ost_conn, "SELECT COUNT(*) FROM DimDate") or 0
            expected = n_accounts * n_days
            actual = _scalar(ost_conn, "SELECT COUNT(*) FROM FactBalance") or 0
            assert actual == expected, (
                f"FactBalance coverage: expected {n_accounts}×{n_days}={expected} rows, "
                f"got {actual}"
            )
        finally:
            ost_conn.close()
