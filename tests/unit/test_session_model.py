"""
test_session_model.py — unit tests for SessionModel.end_active_sessions.

Uses the ``gui_db`` fixture from conftest.py (fresh temp SQLite per test).
Session rows are seeded directly via sqlite3 to avoid the circular FK
dependency (session → user → session) that exists at the application level.
"""

import sqlite3
from uuid import uuid4

import pytest

from PyQt6.QtSql import QSqlDatabase

from openstan.models.session_model import SessionModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_session(db_path: str, session_id: str, is_active: int) -> None:
    """Insert a session row directly via sqlite3."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO session (session_id, user_id, created, is_active) "
            "VALUES (?, 'bootstrap', datetime('now'), ?)",
            (session_id, is_active),
        )
        conn.commit()


def _count_active_sessions(db_path: str) -> int:
    """Return the number of active sessions in the database."""
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM session WHERE is_active = 1"
        ).fetchone()
    return row[0] if row else 0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEndActiveSessions:
    """Tests for SessionModel.end_active_sessions."""

    def test_no_active_sessions_returns_false(self, gui_db: QSqlDatabase) -> None:
        """With no active sessions, end_active_sessions returns (False, ...)."""
        model = SessionModel(db=gui_db)
        model.select()

        success, msg, _ = model.end_active_sessions()

        assert success is False
        assert isinstance(msg, str)

    def test_no_active_sessions_message_informative(
        self, gui_db: QSqlDatabase
    ) -> None:
        """The message indicates there were no active sessions to end."""
        model = SessionModel(db=gui_db)
        model.select()

        _, msg, _ = model.end_active_sessions()

        assert "no active" in msg.lower() or "0" in msg.lower() or "none" in msg.lower()

    def test_one_active_session_returns_true(self, gui_db: QSqlDatabase) -> None:
        """With one active session, end_active_sessions returns (True, ...)."""
        db_path = gui_db.databaseName()
        session_id = uuid4().hex
        _insert_session(db_path, session_id, is_active=1)

        model = SessionModel(db=gui_db)
        model.select()

        success, msg, _ = model.end_active_sessions()

        assert success is True
        assert isinstance(msg, str)

    def test_one_active_session_is_deactivated(self, gui_db: QSqlDatabase) -> None:
        """After end_active_sessions, is_active is set to 0 for the active session."""
        db_path = gui_db.databaseName()
        session_id = uuid4().hex
        _insert_session(db_path, session_id, is_active=1)

        model = SessionModel(db=gui_db)
        model.select()
        model.end_active_sessions()

        assert _count_active_sessions(db_path) == 0

    def test_multiple_active_sessions_all_ended(self, gui_db: QSqlDatabase) -> None:
        """Multiple active sessions are all deactivated in a single call."""
        db_path = gui_db.databaseName()
        for _ in range(3):
            _insert_session(db_path, uuid4().hex, is_active=1)

        model = SessionModel(db=gui_db)
        model.select()
        success, _, _ = model.end_active_sessions()

        assert success is True
        assert _count_active_sessions(db_path) == 0

    def test_inactive_sessions_not_affected(self, gui_db: QSqlDatabase) -> None:
        """Inactive sessions (is_active=0) are left untouched."""
        db_path = gui_db.databaseName()
        inactive_id = uuid4().hex
        active_id = uuid4().hex
        _insert_session(db_path, inactive_id, is_active=0)
        _insert_session(db_path, active_id, is_active=1)

        model = SessionModel(db=gui_db)
        model.select()
        model.end_active_sessions()

        # The inactive session should remain present (is_active still 0)
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT is_active FROM session WHERE session_id = ?",
                (inactive_id,),
            ).fetchone()
        assert row is not None
        assert row[0] == 0

    def test_returns_3_tuple(self, gui_db: QSqlDatabase) -> None:
        """end_active_sessions returns a 3-tuple (bool, str, str) per convention."""
        model = SessionModel(db=gui_db)
        model.select()
        result = model.end_active_sessions()

        assert isinstance(result, tuple)
        assert len(result) == 3
        success, msg1, msg2 = result
        assert isinstance(success, bool)
        assert isinstance(msg1, str)
        assert isinstance(msg2, str)
