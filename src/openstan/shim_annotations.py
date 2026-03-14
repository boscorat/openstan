"""shim_annotations.py — Temporary direct SQLite shim for TransactionAnnotation.

# TODO: move to bsp
# This module exists because bsp does not yet expose a TransactionAnnotation table
# or write API.  Once bsp adds:
#   - bsp.write_transaction_annotations(annotations, project_path)
#   - bsp.db.TransactionAnnotation(project_path)
# replace all calls to this module with those bsp equivalents and delete this file.
#
# D001 exception: this module writes directly to project.db via sqlite3.  This is
# a deliberate, documented temporary exception recorded in DECISIONS.md (D005).
# All writes are to the TransactionAnnotation table only — a table not owned by
# build_datamart and not dropped on rebuild.
"""

import sqlite3
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS TransactionAnnotation (
    annotation_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_transaction  TEXT    NOT NULL UNIQUE,
    category        TEXT,
    confidence      REAL,
    source          TEXT    NOT NULL DEFAULT 'llm',
    model           TEXT,
    updated         TEXT    NOT NULL
)
"""

_UPSERT_SQL = """
INSERT INTO TransactionAnnotation
    (id_transaction, category, confidence, source, model, updated)
VALUES
    (:id_transaction, :category, :confidence, :source, :model, :updated)
ON CONFLICT(id_transaction) DO UPDATE SET
    category   = excluded.category,
    confidence = excluded.confidence,
    source     = excluded.source,
    model      = excluded.model,
    updated    = excluded.updated
"""


def ensure_annotation_table(project_db_path: Path) -> None:
    """Create TransactionAnnotation in project.db if it does not yet exist (idempotent)."""
    try:
        with sqlite3.connect(project_db_path) as conn:
            conn.execute(_CREATE_SQL)
            conn.commit()
    except Exception:
        traceback.print_exc(file=sys.stderr)


def upsert_annotations(annotations: list[dict], project_db_path: Path) -> None:
    """Insert or replace annotation rows keyed on id_transaction.

    Each dict in *annotations* must have keys:
        id_transaction, category, confidence, source, model
    The *updated* timestamp is added automatically (UTC ISO-8601).
    """
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "id_transaction": a["id_transaction"],
            "category": a.get("category"),
            "confidence": a.get("confidence"),
            "source": a.get("source", "llm"),
            "model": a.get("model"),
            "updated": now,
        }
        for a in annotations
    ]
    try:
        with sqlite3.connect(project_db_path) as conn:
            conn.executemany(_UPSERT_SQL, rows)
            conn.commit()
    except Exception:
        traceback.print_exc(file=sys.stderr)


def read_annotations(project_db_path: Path) -> pl.DataFrame:
    """Return all TransactionAnnotation rows as a Polars DataFrame.

    Returns an empty DataFrame with the correct schema if the table does not
    exist or the database is inaccessible.
    """
    _empty = pl.DataFrame(
        {
            "annotation_id": pl.Series([], dtype=pl.Int64),
            "id_transaction": pl.Series([], dtype=pl.Utf8),
            "category": pl.Series([], dtype=pl.Utf8),
            "confidence": pl.Series([], dtype=pl.Float64),
            "source": pl.Series([], dtype=pl.Utf8),
            "model": pl.Series([], dtype=pl.Utf8),
            "updated": pl.Series([], dtype=pl.Utf8),
        }
    )
    try:
        with sqlite3.connect(project_db_path) as conn:
            cur = conn.execute(
                "SELECT annotation_id, id_transaction, category, "
                "confidence, source, model, updated "
                "FROM TransactionAnnotation"
            )
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        if not rows:
            return _empty
        return pl.DataFrame(rows, schema=cols, orient="row")
    except sqlite3.OperationalError:
        # Table does not yet exist — return empty schema
        return _empty
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return _empty
