"""
conftest.py — shared fixtures for openstan unit tests.

Provides two fixtures used by all unit test modules:

``qapp``
    Ensures a single ``QCoreApplication`` exists for the entire test session.
    Qt models require this even when no GUI is displayed.

``gui_db``
    Opens a fresh temporary SQLite database, bootstraps the full gui.db schema
    via ``create_gui_db``, and opens a ``QSqlDatabase`` connection against it.
    Yields the ``QSqlDatabase`` instance; tears down after each test function
    by closing the connection, removing it from Qt's registry, and deleting
    the temp file.

Each unit test that exercises a Qt SQL model receives a clean, isolated
database — there is no shared state between tests.
"""

import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Ensure Qt can run headless on Linux CI
# ---------------------------------------------------------------------------

if sys.platform not in ("darwin", "win32"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication  # noqa: E402
from PyQt6.QtSql import QSqlDatabase  # noqa: E402

from openstan.data.create_gui_db import create_gui_db  # noqa: E402


# ---------------------------------------------------------------------------
# QCoreApplication — exactly one per process
# ---------------------------------------------------------------------------

_qapp: QCoreApplication | None = None


def _get_or_create_qapp() -> QCoreApplication:
    global _qapp
    if _qapp is None:
        _qapp = QCoreApplication.instance()
        if _qapp is None:
            _qapp = QCoreApplication(sys.argv[:1])
    return _qapp


@pytest.fixture(scope="session")
def qapp() -> QCoreApplication:
    """Session-scoped: one QCoreApplication for the whole unit test run."""
    return _get_or_create_qapp()


# ---------------------------------------------------------------------------
# gui_db — fresh isolated database per test function
# ---------------------------------------------------------------------------


@pytest.fixture()
def gui_db(qapp: QCoreApplication) -> Generator[QSqlDatabase, None, None]:
    """Function-scoped: a fresh gui.db schema in a temp file for each test.

    Yields an open ``QSqlDatabase``.  The connection is closed and the temp
    file is deleted during teardown.
    """
    # Create a named temp file (Qt QSQLITE driver does not support :memory:
    # via QSqlDatabase on all platforms, so we use a real temp file).
    fd, tmp_path_str = tempfile.mkstemp(suffix=".db", prefix="openstan_unit_")
    os.close(fd)  # create_gui_db opens its own connection
    tmp_path = Path(tmp_path_str)

    create_gui_db(tmp_path)

    conn_name = f"unit_test_{uuid4().hex}"
    db: QSqlDatabase = QSqlDatabase.addDatabase("QSQLITE", conn_name)
    db.setDatabaseName(str(tmp_path))
    assert db.open(), f"Could not open unit test DB: {db.lastError().text()}"

    yield db

    db.close()
    QSqlDatabase.removeDatabase(conn_name)
    tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Seed helpers — available to test modules via import
# ---------------------------------------------------------------------------


def seed_session_and_project(
    db: QSqlDatabase,
) -> tuple[str, str, str]:
    """Insert the minimum rows needed to satisfy FKs for queue/result tests.

    Inserts a bootstrap session and a project row directly via sqlite3 (FK
    constraints are off by default in SQLite, so the circular session→user→
    session dependency is not a problem here).

    Returns (session_id, project_id, db_path_str).
    """
    import sqlite3

    db_path = db.databaseName()
    session_id = uuid4().hex
    project_id = uuid4().hex

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO session (session_id, user_id, created, is_active) "
            "VALUES (?, 'bootstrap', datetime('now'), 1)",
            (session_id,),
        )
        conn.execute(
            "INSERT INTO project "
            "(project_id, project_name, project_location, "
            " createdBy_session, updatedBy_session, status_id) "
            "VALUES (?, ?, ?, ?, ?, 8)",
            (
                project_id,
                f"test_project_{project_id[:8]}",
                "/tmp",
                session_id,
                session_id,
            ),
        )
        conn.commit()

    return session_id, project_id, db_path
