"""
create_gui_db.py — GUI database creation helper for openstan.

Creates a fresh gui.db SQLite database with the full schema, seed data,
views, and triggers required by the openstan application.

Usage
-----
Called automatically at application startup if gui.db does not exist::

    from openstan.data.create_gui_db import create_gui_db
    from pathlib import Path

    create_gui_db(Path("src/openstan/data/gui.db"))

Also called by the admin "Empty Database & Restart" action, after the
existing gui.db file has been deleted.
"""

import sqlite3
from pathlib import Path


# ---------------------------------------------------------------------------
# DDL — tables
# ---------------------------------------------------------------------------

_DDL_TABLES = """
CREATE TABLE IF NOT EXISTS "status" (
    "status_id"  INTEGER,
    "status"     TEXT NOT NULL,
    PRIMARY KEY("status_id")
);

CREATE TABLE IF NOT EXISTS "user" (
    "user_id"           TEXT,
    "username"          TEXT NOT NULL UNIQUE,
    "createdBy_session" TEXT NOT NULL,
    "updatedBy_session" TEXT NOT NULL,
    "created"           TEXT NOT NULL DEFAULT 'datetime()',
    "updated"           TEXT NOT NULL DEFAULT 'datetime()',
    "status_id"         TEXT NOT NULL DEFAULT 8,
    PRIMARY KEY("user_id"),
    FOREIGN KEY("status_id") REFERENCES "status"("status_id")
);

CREATE TABLE IF NOT EXISTS "session" (
    "session_id" TEXT,
    "user_id"    TEXT NOT NULL,
    "created"    TEXT NOT NULL DEFAULT 'datetime()',
    "terminated" TEXT,
    "is_active"  INTEGER,
    PRIMARY KEY("session_id"),
    CONSTRAINT "fk_session_user" FOREIGN KEY("user_id") REFERENCES "user"("user_id")
);

CREATE TABLE IF NOT EXISTS "project" (
    "project_id"        TEXT,
    "project_name"      TEXT NOT NULL UNIQUE,
    "project_location"  TEXT NOT NULL,
    "createdBy_session" TEXT NOT NULL,
    "updatedBy_session" TEXT NOT NULL,
    "created"           TEXT NOT NULL DEFAULT 'datetime()',
    "updated"           TEXT NOT NULL DEFAULT 'datetime()',
    "status_id"         INTEGER NOT NULL DEFAULT 8,
    PRIMARY KEY("project_id"),
    FOREIGN KEY("createdBy_session") REFERENCES "session"("session_id"),
    FOREIGN KEY("updatedBy_session") REFERENCES "session"("session_id"),
    FOREIGN KEY("status_id") REFERENCES "status"("status_id")
);

CREATE TABLE IF NOT EXISTS "event_log" (
    "session_id"    TEXT NOT NULL,
    "log_time"      TEXT NOT NULL DEFAULT 'datetime()',
    "table_name"    TEXT NOT NULL,
    "update_action" TEXT NOT NULL,
    "record_id"     TEXT NOT NULL DEFAULT 'N/A',
    "success"       INTEGER NOT NULL DEFAULT 0,
    "message"       TEXT
);

CREATE TABLE IF NOT EXISTS "statement_queue" (
    "queue_id"   TEXT,
    "parent_id"  TEXT,
    "project_id" TEXT NOT NULL,
    "session_id" TEXT NOT NULL,
    "status_id"  INTEGER NOT NULL DEFAULT 0,
    "path"       TEXT NOT NULL,
    "is_folder"  INTEGER NOT NULL DEFAULT 0,
    "batch_id"   TEXT DEFAULT NULL,
    PRIMARY KEY("queue_id"),
    FOREIGN KEY("parent_id")  REFERENCES "statement_queue"("queue_id"),
    FOREIGN KEY("project_id") REFERENCES "project"("project_id"),
    FOREIGN KEY("session_id") REFERENCES "session"("session_id"),
    FOREIGN KEY("status_id")  REFERENCES "status"("status_id")
);

CREATE TABLE IF NOT EXISTS "statement_result" (
    "result_id"       TEXT,
    "batch_id"        TEXT NOT NULL,
    "queue_id"        TEXT NOT NULL,
    "project_id"      TEXT NOT NULL,
    "result"          TEXT NOT NULL,
    "file_path"       TEXT NOT NULL,
    "id_account"      TEXT,
    "statement_date"  TEXT,
    "payments_in"     REAL,
    "payments_out"    REAL,
    "error_type"      TEXT,
    "message"         TEXT,
    "debug_json_path" TEXT    DEFAULT NULL,
    "debug_status"    TEXT    DEFAULT NULL,
    "deleted"         INTEGER NOT NULL DEFAULT 0,
    "created"         TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY("result_id"),
    FOREIGN KEY("queue_id")   REFERENCES "statement_queue"("queue_id"),
    FOREIGN KEY("project_id") REFERENCES "project"("project_id")
);

CREATE TABLE IF NOT EXISTS "statement_result_payload" (
    "result_id" TEXT,
    "payload"   TEXT NOT NULL,
    PRIMARY KEY("result_id"),
    FOREIGN KEY("result_id") REFERENCES "statement_result"("result_id")
);

CREATE TABLE IF NOT EXISTS "batch" (
    "batch_id"      TEXT,
    "project_id"    TEXT NOT NULL,
    "duration_secs" REAL NOT NULL DEFAULT 0,
    "status"        INTEGER NOT NULL DEFAULT 0,
    "created"       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY("batch_id"),
    FOREIGN KEY("project_id") REFERENCES "project"("project_id"),
    FOREIGN KEY("status") REFERENCES "status"("status_id")
);
"""

# ---------------------------------------------------------------------------
# DDL — view
# ---------------------------------------------------------------------------

_DDL_VIEW = """
CREATE VIEW IF NOT EXISTS active_session AS
    SELECT session_id, user_id
    FROM session
    WHERE is_active = 1
    ORDER BY created DESC
    LIMIT 1;
"""

# ---------------------------------------------------------------------------
# DDL — triggers
# ---------------------------------------------------------------------------

_DDL_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS new_user
AFTER INSERT ON user
BEGIN
    INSERT INTO event_log (session_id, log_time, table_name, update_action, record_id, success, message)
    VALUES (
        NEW.createdBy_session,
        CURRENT_TIMESTAMP,
        'user',
        'INSERT',
        NEW.user_id,
        1,
        'User created: ' || NEW.username
    );
END;

CREATE TRIGGER IF NOT EXISTS new_session
AFTER INSERT ON session
BEGIN
    INSERT INTO event_log (session_id, log_time, table_name, update_action, record_id, success, message)
    VALUES (
        NEW.session_id,
        CURRENT_TIMESTAMP,
        'session',
        'INSERT',
        NEW.session_id,
        1,
        'Session created'
    );
END;

CREATE TRIGGER IF NOT EXISTS new_project
AFTER INSERT ON project
BEGIN
    INSERT INTO event_log (session_id, log_time, table_name, update_action, record_id, success, message)
    VALUES (
        NEW.createdBy_session,
        CURRENT_TIMESTAMP,
        'project',
        'INSERT',
        NEW.project_id,
        1,
        'Project created: ' || NEW.project_name
    );
END;

CREATE TRIGGER IF NOT EXISTS deleted_project
AFTER DELETE ON project
BEGIN
    INSERT INTO event_log (session_id, log_time, table_name, update_action, record_id, success, message)
    VALUES (
        OLD.updatedBy_session,
        CURRENT_TIMESTAMP,
        'project',
        'DELETE',
        OLD.project_id,
        1,
        'Project deleted: ' || OLD.project_name
    );
END;
"""

# ---------------------------------------------------------------------------
# Seed data — status lookup table
# ---------------------------------------------------------------------------

_STATUS_ROWS: list[tuple[int, str]] = [
    (0, "pending"),
    (1, "processing"),
    (2, "success"),
    (3, "failure"),
    (4, "cancelled"),
    (5, "under review"),
    (6, "awaiting re-try"),
    (7, "unknown"),
    (8, "active"),
    (9, "deleted"),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_gui_db(db_path: Path) -> None:
    """
    Create a fresh gui.db at *db_path*.

    Creates all tables, the ``active_session`` view, all triggers, and seeds
    the ``status`` lookup table.  The parent directory must already exist.
    If a file already exists at *db_path* it will be overwritten — delete it
    before calling this function if a clean slate is required.

    Args:
        db_path: Absolute path where gui.db should be created.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_DDL_TABLES)
        conn.executescript(_DDL_VIEW)
        conn.executescript(_DDL_TRIGGERS)
        conn.executemany(
            "INSERT OR IGNORE INTO status (status_id, status) VALUES (?, ?)",
            _STATUS_ROWS,
        )
        conn.commit()
        print(f"gui.db created at {db_path}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Allow running directly: python -m openstan.data.create_gui_db
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os

    _default = Path(os.path.dirname(__file__)) / "gui.db"
    create_gui_db(_default)
