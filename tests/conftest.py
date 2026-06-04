"""
conftest.py — session-scoped fixtures for openstan integration tests.

Two fixtures are provided:

``bsp_harness``
    Builds a fully-populated bsp reference project from the bundled anonymised
    good PDFs, runs bsp's own pytest suite as a quality gate, and exposes the
    resulting ``project.db`` path for comparison.  Tears down on session end.

``openstan_env``
    Drives the complete openstan import pipeline — queue model → SQWorker →
    CommitWorker — against both the good/ and bad/ bundled PDFs, writing into a
    real bsp project directory and recording results in the live gui.db.  The
    test project row is deleted from gui.db during teardown (exercises
    ``ProjectModel.delete_record_by_id``).  Yields an ``OpenStanEnv`` dataclass
    with counts and paths needed by the test suite.

Both fixtures depend on ``bsp_harness`` having completed successfully (bsp's
own pytest gate must pass before openstan's pipeline is exercised).
"""

import os
import sys
import tempfile
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import bank_statement_parser as bsp
import pytest
from bank_statement_parser.testing import TestHarness, _pdf_dir

# ============================================================================
# PDF Mode Detection (Anonymised vs. Synthetic)
# ============================================================================

def _detect_pdf_mode() -> tuple[str, Path, Path]:
    """
    Detect which PDF set is available and return mode + paths.
    
    Returns:
        Tuple of (mode, good_pdfs_dir, bad_pdfs_dir) where:
        - mode: "anonymised" if symlinks exist, "bundled" otherwise
        - good_pdfs_dir: Path to good PDFs directory
        - bad_pdfs_dir: Path to bad PDFs directory
    """
    # Check for anonymised symlinks (manual setup by developer)
    test_dir = Path(__file__).parent
    anonymised_good = test_dir / "fixtures/pdfs/anonymised_good"
    anonymised_bad = test_dir / "fixtures/pdfs/anonymised_bad"
    
    if anonymised_good.is_symlink() and anonymised_bad.is_symlink():
        return ("anonymised", anonymised_good, anonymised_bad)
    
    # Fallback to bundled PDFs from installed package
    fallback_good = _pdf_dir("good")
    fallback_bad = _pdf_dir("bad")
    
    if list(fallback_good.glob("*.pdf")) and list(fallback_bad.glob("*.pdf")):
        return ("bundled", fallback_good, fallback_bad)
    
    return ("none", fallback_good, fallback_bad)


# Initialize PDF mode at module load time
PDF_MODE, _GOOD_PDF_DIR_OVERRIDE, _BAD_PDF_DIR_OVERRIDE = _detect_pdf_mode()

# Output PDF mode to test session
print(f"\n[PDF_FIXTURES] Mode: {PDF_MODE.upper()}")
if PDF_MODE == "anonymised":
    print(f"[PDF_FIXTURES] Using ANONYMISED PDFs (symlinks detected)")
    print(f"[PDF_FIXTURES] Location: {_GOOD_PDF_DIR_OVERRIDE}")
elif PDF_MODE == "bundled":
    print(f"[PDF_FIXTURES] Using BUNDLED PDFs from installed package")
else:
    print(f"[PDF_FIXTURES] No PDFs available (tests will skip)")

# ---------------------------------------------------------------------------
# Ensure Qt can run headless on Linux CI (no-op on macOS/Windows)
# ---------------------------------------------------------------------------

if sys.platform not in ("darwin", "win32"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Qt imports must come after the platform env-var is set
# QApplication is used instead of QCoreApplication so that view widgets
# (which require a QApplication) can be instantiated in the same process —
# e.g. by test_screenshots.py.  QApplication is a subclass of QCoreApplication
# and satisfies all requirements of the integration test fixtures.
from PySide6.QtSql import QSqlDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from openstan.data.create_gui_db import create_gui_db  # noqa: E402
from openstan.models import (  # noqa: E402
    BatchModel,
    FailureResultModel,
    ProjectModel,
    ReviewResultModel,
    StatementQueueModel,
    StatementQueueTreeModel,
    StatementResultModel,
    StatementResultPayloadModel,
    SuccessResultModel,
    UserModel,
)
from openstan.models.statement_result_model import ResultRow  # noqa: E402
from openstan.paths import Paths  # noqa: E402
from openstan.presenters.statement_queue_presenter import SQWorker  # noqa: E402
from openstan.presenters.statement_result_presenter import CommitWorker  # noqa: E402

# ---------------------------------------------------------------------------
# QApplication — exactly one instance per process
# ---------------------------------------------------------------------------

# Instantiate once at module level so every fixture in the session reuses it.
# pytest collects this module before any fixture runs, so this is safe.
# QApplication is used (rather than QCoreApplication) so that view widgets
# can be instantiated in the same pytest process (e.g. test_screenshots.py).
_qapp: QApplication | None = None


def _get_or_create_qapp() -> QApplication:
    global _qapp
    if _qapp is None:
        existing = QApplication.instance()
        if existing is not None:
            _qapp = existing  # type: ignore[assignment]
        else:
            _qapp = QApplication(sys.argv[:1])
    assert _qapp is not None
    return _qapp


# ---------------------------------------------------------------------------
# Data carriers
# ---------------------------------------------------------------------------


@dataclass
class OpenStanEnv:
    """All state produced by the openstan import fixture."""

    project_path: Path
    project_id: str
    n_success: int
    n_review: int
    n_failure: int
    # Counts derived from bsp TestHarness (good-only) for cross-reference
    bsp_n_success: int
    bsp_n_review: int
    # REVIEW count from the good/ folder only (for comparison against bsp_n_review)
    n_review_good: int = 0
    # Ordered list of PdfResults from the import run (success + review only;
    # failures have no payload worth committing)
    processed_pdfs: list = field(default_factory=list)
    pdf_paths: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# bsp_harness fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def bsp_harness() -> Generator[TestHarness, None, None]:
    """Build the bsp reference project using the bundled anonymised PDFs.

    Uses ``skip_bsp_tests=True`` so the harness works whether bsp is installed
    as an editable local path or as a wheel (e.g. on CI).  Tears down on
    session end.
    """
    with TestHarness(skip_bsp_tests=True) as harness:
        yield harness


# ---------------------------------------------------------------------------
# openstan_env fixture
# ---------------------------------------------------------------------------


class _PresenterStub:
    """Minimal stand-in for StatementQueuePresenter used by SQWorker.

    SQWorker only needs three attributes from the presenter:
    - ``projectPath``  — Path to the bsp project root
    - ``sessionID``    — session UUID hex string
    - ``projectID``    — project UUID hex string (unused by SQWorker itself,
                         but kept for completeness)
    """

    __slots__ = ("projectPath", "sessionID", "projectID")

    def __init__(self, project_path: Path, session_id: str, project_id: str) -> None:
        self.projectPath: Path = project_path
        self.sessionID: str = session_id
        self.projectID: str = project_id


@pytest.fixture(scope="session")
def openstan_env(bsp_harness: TestHarness) -> Generator[OpenStanEnv, None, None]:
    """Drive the full openstan import pipeline and yield test state.

    Steps
    -----
    1. Ensure a QCoreApplication exists.
    2. Open the live gui.db (creating it if absent — mirrors production startup).
    3. Create a temporary bsp project directory.
    4. Register a test user + session in gui.db via the real models.
    5. Create a project record in gui.db pointing to the temp directory.
    6. Scaffold the bsp project structure.
    7. Populate the statement_queue with two folder entries (good/ and bad/)
       and their child PDF file records.
    8. Run SQWorker.run() synchronously to process all PDFs.
    9. Collect PdfResults; record counts; create the batch record in gui.db.
    10. Run CommitWorker.run() synchronously to write to project.db.
    11. Yield OpenStanEnv.

    Teardown
    --------
    - Delete the project record from gui.db via ProjectModel.delete_record_by_id().
    - Remove the temp project directory from disk.
    """
    _get_or_create_qapp()

    # ── 1. Open gui.db (production database) ─────────────────────────────
    gui_db_path = Path(Paths.databases("gui.db"))
    if not gui_db_path.exists():
        create_gui_db(gui_db_path)

    # Ensure WAL journal mode is set before the Qt connection is opened.
    # PySide6's QSQLITE driver holds an implicit read lock in DELETE journal
    # mode once any QSqlTableModel calls select(), which blocks concurrent
    # sqlite3 writes used to seed bootstrap rows below.  WAL mode allows a
    # writer and multiple readers to coexist.  We set it via a plain sqlite3
    # connection here (before Qt opens the DB) so it takes effect even for
    # pre-existing databases created before this fix.
    import sqlite3 as _sqlite3

    with _sqlite3.connect(str(gui_db_path)) as _wal_conn:
        _wal_conn.execute("PRAGMA journal_mode=WAL")

    # Use a unique connection name so the fixture connection is isolated from
    # any connection that may already be open (e.g. from a parallel test run).
    conn_name = f"openstan_test_{uuid4().hex}"
    gui_db: QSqlDatabase = QSqlDatabase.addDatabase("QSQLITE", conn_name)
    gui_db.setDatabaseName(str(gui_db_path))
    assert gui_db.open(), f"Could not open gui.db: {gui_db.lastError().text()}"

    # ── 2. Instantiate models against this connection ─────────────────────
    user_model = UserModel(db=gui_db)
    project_model = ProjectModel(db=gui_db)
    queue_model = StatementQueueModel(db=gui_db)
    StatementQueueTreeModel(db=gui_db)  # needed by add_record path
    success_model = SuccessResultModel()
    review_model = ReviewResultModel()
    failure_model = FailureResultModel()
    result_model = StatementResultModel(db=gui_db)
    payload_model = StatementResultPayloadModel(db=gui_db)
    batch_model = BatchModel(db=gui_db)

    # ── 3. Seed: test user + session ──────────────────────────────────────
    session_id: str = uuid4().hex
    username: str = f"openstan_test_runner_{session_id[:8]}"

    # Insert the bootstrap session row via the Qt connection to avoid any
    # concurrent-writer locking between QSqlTableModel and a separate sqlite3
    # connection.  SessionModel.add_record has a circular FK dependency
    # (session → user → session via createdBy_session), so we use a raw
    # QSqlQuery here with FK enforcement off (SQLite default).
    from PySide6.QtSql import QSqlQuery

    _q = QSqlQuery(gui_db)
    _q.prepare(
        "INSERT OR IGNORE INTO session (session_id, user_id, created, is_active)"
        " VALUES (:sid, 'bootstrap', :ts, 1)"
    )
    _q.bindValue(":sid", session_id)
    _q.bindValue(":ts", datetime.now(timezone.utc).isoformat())
    assert _q.exec(), f"Could not insert bootstrap session: {_q.lastError().text()}"

    # Now add the user (createdBy_session references the bootstrap session)
    user_model.select()
    ok, user_id, msg = user_model.add_record(username, session_id)
    assert ok, f"Could not create test user: {msg}"

    # Update the bootstrap session to reference the real user_id
    _q2 = QSqlQuery(gui_db)
    _q2.prepare("UPDATE session SET user_id = :uid WHERE session_id = :sid")
    _q2.bindValue(":uid", user_id)
    _q2.bindValue(":sid", session_id)
    assert _q2.exec(), f"Could not update bootstrap session: {_q2.lastError().text()}"

    # ── 4. Create a temporary bsp project directory ───────────────────────
    tmp_root = Path(tempfile.mkdtemp(prefix="openstan_test_project_"))
    project_id: str = uuid4().hex
    project_name: str = f"openstan_integration_test_{project_id[:8]}"

    bsp.validate_or_initialise_project(tmp_root)

    # ── 5. Register the project in gui.db ─────────────────────────────────
    project_model.select()
    ok, _, msg = project_model.add_record(
        project_id, project_name, str(tmp_root), session_id
    )
    assert ok, f"Could not create test project: {msg}"

    # ── 6. Scope the queue model to the new project ───────────────────────
    queue_model.set_project(project_id)

    # ── 7. Populate the queue: two folder entries + child PDFs ────────────
    # Use detected PDF directories (anonymised if symlinked, bundled as fallback)
    good_dir: Path = _GOOD_PDF_DIR_OVERRIDE
    bad_dir: Path = _BAD_PDF_DIR_OVERRIDE
    
    if PDF_MODE == "none":
        pytest.skip(
            "No PDF fixtures available. Set up symlinks to anonymised PDFs "
            "for comprehensive testing. See: bank-statement-data/SYMLINK_SETUP.md"
        )

    for folder_path in (good_dir, bad_dir):
        folder_id: str = uuid4().hex
        ok, _, msg = queue_model.add_record(
            queue_id=folder_id,
            parent_id=folder_id,
            session_id=session_id,
            status_id=0,
            path=folder_path,
            is_folder=1,
        )
        assert ok, f"Could not add folder {folder_path}: {msg}"

        for pdf_file in sorted(folder_path.glob("*.pdf")):
            file_id: str = uuid4().hex
            ok, _, msg = queue_model.add_record(
                queue_id=file_id,
                parent_id=folder_id,
                session_id=session_id,
                status_id=0,
                path=pdf_file,
                is_folder=0,
            )
            assert ok, f"Could not add file {pdf_file}: {msg}"

    # ── 8. Lock the queue and run SQWorker synchronously ──────────────────
    # Refresh the model so set_batch_id sees all inserted rows.
    queue_model.select()
    batch_id: str = uuid4().hex
    ok, msg = queue_model.set_batch_id(batch_id)
    assert ok, f"Could not lock queue: {msg}"

    stub = _PresenterStub(
        project_path=tmp_root,
        session_id=session_id,
        project_id=project_id,
    )

    # Collect results emitted by the worker
    results: list[tuple[Path, int, bsp.PdfResult, str]] = []

    worker = SQWorker(presenter=stub, model=queue_model, batch_id=batch_id)  # type: ignore[arg-type]
    worker.signals.progress.connect(
        lambda fp, pct, result, qid: results.append((fp, pct, result, qid))
    )

    import_start = __import__("time").monotonic()
    worker.run()
    duration_secs = __import__("time").monotonic() - import_start

    # ── 9. Tally results into in-memory models ────────────────────────────
    for file_path, _pct, pdf_result, queue_id in results:
        # Extract display fields from the PdfResult
        id_account: str | None = None
        statement_date: str | None = None
        payments_in: float | None = None
        payments_out: float | None = None
        error_type: str | None = None
        message: str | None = None

        if pdf_result.result in ("SUCCESS", "REVIEW"):
            payload = pdf_result.payload
            if hasattr(payload, "statement_info"):
                info = payload.statement_info
                id_account = getattr(info, "id_account", None)
                raw_date = getattr(info, "statement_date", None)
                statement_date = str(raw_date) if raw_date is not None else None
            if hasattr(payload, "checks_and_balances"):
                cab = payload.checks_and_balances
                if cab is not None and not cab.is_empty():
                    row = cab.row(0, named=True)
                    payments_in = row.get("STD_PAYMENTS_IN")
                    payments_out = row.get("STD_PAYMENTS_OUT")
        else:
            payload = pdf_result.payload
            error_type = getattr(payload, "error_type", None)
            message = getattr(payload, "message", None)

        result_row = ResultRow(
            result_id=uuid4().hex,
            batch_id=batch_id,
            queue_id=queue_id,
            project_id=project_id,
            result=pdf_result.result,
            file_path=file_path,
            id_account=id_account,
            statement_date=statement_date,
            payments_in=payments_in,
            payments_out=payments_out,
            error_type=error_type,
            message=message,
            pdf_result=pdf_result,
        )

        if pdf_result.result == "SUCCESS":
            success_model.add_row(result_row)
        elif pdf_result.result == "REVIEW":
            review_model.add_row(result_row)
        else:
            failure_model.add_row(result_row)

    n_success = success_model.row_count
    n_review = review_model.row_count
    n_failure = failure_model.row_count

    # Track REVIEWs from the good/ folder only (for bsp comparison)
    n_review_good = sum(
        1 for row in review_model.all_rows() if Path(row.file_path).parent == good_dir
    )

    # Persist results + payloads to gui.db
    all_rows = (
        success_model.all_rows() + review_model.all_rows() + failure_model.all_rows()
    )
    for row in all_rows:
        ok, result_id, msg = result_model.add_result(
            batch_id=batch_id,
            queue_id=row.queue_id,
            project_id=row.project_id,
            result=row.result,
            file_path=row.file_path,
            id_account=row.id_account,
            statement_date=row.statement_date,
            payments_in=row.payments_in,
            payments_out=row.payments_out,
            error_type=row.error_type,
            message=row.message,
        )
        if ok and row.pdf_result is not None:
            payload_model.add_payload(result_id, row.pdf_result)

    batch_model.create_batch(batch_id, project_id, duration_secs)

    # ── 10. Run CommitWorker synchronously ────────────────────────────────
    # Only SUCCESS and REVIEW results have payloads worth committing.
    commit_rows = success_model.all_rows() + review_model.all_rows()
    result_ids = result_model.get_result_ids_for_batch(batch_id)
    id_to_payload = payload_model.load_payloads_for_batch(result_ids)

    processed_pdfs: list = []
    pdf_paths: list[Path] = []
    for i, row in enumerate(commit_rows):
        result_id = result_ids[i] if i < len(result_ids) else None
        payload = id_to_payload.get(result_id) if result_id else row.pdf_result
        if payload is None and row.pdf_result is not None:
            payload = row.pdf_result
        if payload is not None:
            processed_pdfs.append(payload)
            pdf_paths.append(row.file_path)

    commit_errors: list[str] = []
    commit_worker = CommitWorker(
        processed_pdfs=processed_pdfs,
        pdfs=pdf_paths,
        batch_id=batch_id,
        session_id=session_id,
        user_id=username,
        path=f"{good_dir}|{bad_dir}",
        pdf_count=n_success + n_review + n_failure,
        errors=n_failure,
        reviews=n_review,
        project_path=tmp_root,
        duration_secs=duration_secs,
    )
    commit_worker.signals.error.connect(lambda msg: commit_errors.append(msg))
    commit_worker.run()
    assert not commit_errors, f"CommitWorker failed: {commit_errors}"

    # Count bsp reference counts from bsp_harness (good-only, via StatementBatch)
    assert bsp_harness._batch is not None, (
        "_batch is None — did bsp_harness setup() complete?"
    )
    _bsp_batch = bsp_harness._batch
    bsp_n_success = sum(
        1
        for r in _bsp_batch.processed_pdfs
        if hasattr(r, "result") and r.result == "SUCCESS"
    )
    bsp_n_review = sum(
        1
        for r in _bsp_batch.processed_pdfs
        if hasattr(r, "result") and r.result == "REVIEW"
    )

    env = OpenStanEnv(
        project_path=tmp_root,
        project_id=project_id,
        n_success=n_success,
        n_review=n_review,
        n_failure=n_failure,
        bsp_n_success=bsp_n_success,
        bsp_n_review=bsp_n_review,
        n_review_good=n_review_good,
        processed_pdfs=processed_pdfs,
        pdf_paths=pdf_paths,
    )

    yield env

    # ── Teardown ──────────────────────────────────────────────────────────
    # 1. Delete the project record from gui.db (exercises ProjectModel.delete_record_by_id)
    project_model.select()
    ok, _, msg = project_model.delete_record_by_id(project_id)
    if not ok:
        print(
            f"WARNING: Could not delete test project from gui.db: {msg}",
            file=sys.stderr,
        )

    # 2. Close the Qt database connection
    gui_db.close()
    QSqlDatabase.removeDatabase(conn_name)

    # 3. Remove the temporary project directory from disk
    import shutil

    if tmp_root.exists():
        shutil.rmtree(tmp_root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Central PDF Management Fixtures (Phase 1.3)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qt_app() -> QApplication:
    """
    Provide the global QApplication instance for the entire test session.

    Ensures that view widgets can be instantiated in tests.

    Returns:
        QApplication: The singleton QApplication instance.
    """
    return _get_or_create_qapp()


@pytest.fixture(scope="session")
def synthetic_pdf_dir() -> Path:
    """
    Path to synthetic PDFs committed to this repo.

    These are completely synthetic (no real data) and safe for public repos.
    Generated by bank-statement-data repo's generator and committed here.

    Returns:
        Path to synthetic_pdfs directory (good/ and bad/ subdirs).

    Note:
        Falls back to bundled PDFs if synthetic PDFs not available.
    """
    synthetic_path = Path(__file__).parent / "fixtures" / "pdfs"
    if synthetic_path.exists():
        return synthetic_path
    # Fallback to bundled PDFs if synthetic not available
    return _pdf_dir("good").parent


@pytest.fixture
def sample_pdf_for_import(synthetic_pdf_dir) -> Path | None:
    """
    Single synthetic PDF for unit tests.

    Useful for testing individual PDF processing steps.

    Args:
        synthetic_pdf_dir: Path to synthetic PDFs directory.

    Returns:
        Path to a randomly selected synthetic PDF, or None if none available.
    """
    import random
    
    good_pdfs = list((synthetic_pdf_dir / "good").glob("*.pdf"))
    if good_pdfs:
        return random.choice(good_pdfs)
    
    # Fallback to bundled PDFs if no synthetic
    bundled_pdfs = list(_pdf_dir("good").glob("*.pdf"))
    if bundled_pdfs:
        return random.choice(bundled_pdfs)
    
    pytest.skip("No PDFs available for testing")
