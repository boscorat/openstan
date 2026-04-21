"""
test_statement_queue_model.py — unit tests for StatementQueueModel and
StatementQueueTreeModel.

Uses the ``gui_db`` fixture from conftest.py (fresh temp SQLite per test).
Models are instantiated against the in-memory-equivalent DB, so no bsp
pipeline or real project directory is needed.

The ``seed_session_and_project`` helper in conftest.py inserts the minimum
FK rows (session + project) before each test that needs them.
"""

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from PyQt6.QtSql import QSqlDatabase

from openstan.models.statement_queue_model import (
    StatementQueueModel,
    StatementQueueTreeModel,
)
from tests.unit.conftest import seed_session_and_project


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _add_folder(
    model: StatementQueueModel,
    session_id: str,
    path: str = "/tmp/folder",
) -> str:
    """Insert a folder row (own-parent) and return its queue_id."""
    folder_id = uuid4().hex
    ok, _, msg = model.add_record(
        queue_id=folder_id,
        parent_id=folder_id,
        session_id=session_id,
        status_id=0,
        path=path,
        is_folder=1,
    )
    assert ok, f"Could not add folder: {msg}"
    return folder_id


def _add_file(
    model: StatementQueueModel,
    session_id: str,
    parent_id: str,
    path: str = "/tmp/folder/file.pdf",
) -> str:
    """Insert a child file row and return its queue_id."""
    file_id = uuid4().hex
    ok, _, msg = model.add_record(
        queue_id=file_id,
        parent_id=parent_id,
        session_id=session_id,
        status_id=0,
        path=path,
        is_folder=0,
    )
    assert ok, f"Could not add file: {msg}"
    return file_id


def _add_standalone_file(
    model: StatementQueueModel,
    session_id: str,
    path: str = "/tmp/standalone.pdf",
) -> str:
    """Insert a standalone file (own-parent, is_folder=0) and return its queue_id."""
    file_id = uuid4().hex
    ok, _, msg = model.add_record(
        queue_id=file_id,
        parent_id=file_id,
        session_id=session_id,
        status_id=0,
        path=path,
        is_folder=0,
    )
    assert ok, f"Could not add standalone file: {msg}"
    return file_id


# ---------------------------------------------------------------------------
# TestDeleteRecords
# ---------------------------------------------------------------------------


class TestDeleteRecords:
    """Tests for StatementQueueModel.delete_records."""

    def test_delete_standalone_file(self, gui_db: QSqlDatabase) -> None:
        """Deleting a standalone file (own-parent, is_folder=0) succeeds."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        file_id = _add_standalone_file(model, session_id)
        model.select()
        assert model.rowCount() == 1

        success, deleted, msg = model.delete_records([file_id])

        assert success is True
        assert file_id in deleted
        model.select()
        assert model.rowCount() == 0

    def test_delete_folder_with_children(self, gui_db: QSqlDatabase) -> None:
        """Deleting a folder also removes its child file rows (pass 1 children first)."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        folder_id = _add_folder(model, session_id)
        child_id = _add_file(model, session_id, parent_id=folder_id)
        model.select()
        assert model.rowCount() == 2

        success, deleted, msg = model.delete_records([folder_id])

        assert success is True
        assert folder_id in deleted
        assert child_id in deleted
        model.select()
        assert model.rowCount() == 0

    def test_delete_multiple_ids(self, gui_db: QSqlDatabase) -> None:
        """Multiple queue IDs can be deleted in a single call."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        file_a = _add_standalone_file(model, session_id, path="/tmp/a.pdf")
        file_b = _add_standalone_file(model, session_id, path="/tmp/b.pdf")
        model.select()
        assert model.rowCount() == 2

        success, deleted, _ = model.delete_records([file_a, file_b])

        assert success is True
        assert file_a in deleted
        assert file_b in deleted
        model.select()
        assert model.rowCount() == 0

    def test_return_tuple_structure(self, gui_db: QSqlDatabase) -> None:
        """delete_records returns a 3-tuple (bool, list[str], str)."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        file_id = _add_standalone_file(model, session_id)
        model.select()
        result = model.delete_records([file_id])

        assert isinstance(result, tuple)
        assert len(result) == 3
        success, deleted, msg = result
        assert isinstance(success, bool)
        assert isinstance(deleted, list)
        assert isinstance(msg, str)

    def test_delete_empty_id_list_succeeds(self, gui_db: QSqlDatabase) -> None:
        """Passing an empty list calls submitAll with nothing to remove — succeeds."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        # Add a file that is NOT in the deletion list
        _add_standalone_file(model, session_id)
        model.select()

        success, deleted, _ = model.delete_records([])

        assert success is True
        assert deleted == []
        # The untargeted row must still be present
        model.select()
        assert model.rowCount() == 1


# ---------------------------------------------------------------------------
# TestGetBatchId
# ---------------------------------------------------------------------------


class TestGetBatchId:
    """Tests for StatementQueueModel.get_batch_id and is_locked."""

    def test_empty_queue_returns_none(self, gui_db: QSqlDatabase) -> None:
        """An empty queue has no batch_id — returns None."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        assert model.get_batch_id() is None

    def test_queue_with_null_batch_id_returns_none(self, gui_db: QSqlDatabase) -> None:
        """Rows with batch_id=NULL (default) return None."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        _add_standalone_file(model, session_id)
        model.select()

        # batch_id is NULL by default — should return None
        assert model.get_batch_id() is None

    def test_queue_with_valid_batch_id_returns_it(self, gui_db: QSqlDatabase) -> None:
        """After set_batch_id, get_batch_id returns that batch_id."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        _add_standalone_file(model, session_id)
        model.select()

        batch_id = uuid4().hex
        ok, _ = model.set_batch_id(batch_id)
        assert ok

        assert model.get_batch_id() == batch_id

    def test_is_locked_false_when_no_batch(self, gui_db: QSqlDatabase) -> None:
        """is_locked returns False when get_batch_id returns None."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        _add_standalone_file(model, session_id)
        model.select()

        assert model.is_locked() is False

    def test_is_locked_true_when_batch_set(self, gui_db: QSqlDatabase) -> None:
        """is_locked returns True after set_batch_id is called."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        _add_standalone_file(model, session_id)
        model.select()

        batch_id = uuid4().hex
        model.set_batch_id(batch_id)

        assert model.is_locked() is True

    def test_clear_batch_id_unlocks_queue(self, gui_db: QSqlDatabase) -> None:
        """clear_batch_id sets batch_id back to None, unlocking the queue."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        _add_standalone_file(model, session_id)
        model.select()

        batch_id = uuid4().hex
        model.set_batch_id(batch_id)
        assert model.is_locked() is True

        ok, _ = model.clear_batch_id()
        assert ok
        assert model.is_locked() is False
        assert model.get_batch_id() is None


# ---------------------------------------------------------------------------
# TestGetFolderPathsForBatch
# ---------------------------------------------------------------------------


class TestGetFolderPathsForBatch:
    """Tests for StatementQueueModel.get_folder_paths_for_batch."""

    def test_no_folder_rows_returns_empty_string(self, gui_db: QSqlDatabase) -> None:
        """With no folder rows, returns an empty string."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        batch_id = uuid4().hex
        # Add a standalone file (is_folder=0) and stamp it with the batch_id
        _add_standalone_file(model, session_id)
        model.select()
        model.set_batch_id(batch_id)

        result = model.get_folder_paths_for_batch(batch_id)
        assert result == ""

    def test_single_folder_returns_path(self, gui_db: QSqlDatabase) -> None:
        """A single folder row returns its path with no pipe character."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        batch_id = uuid4().hex
        folder_id = _add_folder(model, session_id, path="/data/statements")
        model.select()
        model.set_batch_id(batch_id)

        result = model.get_folder_paths_for_batch(batch_id)
        assert result == "/data/statements"
        assert "|" not in result

    def test_two_folders_returns_pipe_joined(self, gui_db: QSqlDatabase) -> None:
        """Two folder rows are returned as a pipe-joined string."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        batch_id = uuid4().hex
        _add_folder(model, session_id, path="/data/good")
        _add_folder(model, session_id, path="/data/bad")
        model.select()
        model.set_batch_id(batch_id)

        result = model.get_folder_paths_for_batch(batch_id)
        parts = result.split("|")
        assert len(parts) == 2
        assert "/data/good" in parts
        assert "/data/bad" in parts

    def test_wrong_batch_id_excluded(self, gui_db: QSqlDatabase) -> None:
        """Rows stamped with a different batch_id are not included."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        batch_id_a = uuid4().hex
        batch_id_b = uuid4().hex

        _add_folder(model, session_id, path="/data/folder_a")
        model.select()
        model.set_batch_id(batch_id_a)

        # Result for batch_b should be empty since rows are stamped with batch_a
        result = model.get_folder_paths_for_batch(batch_id_b)
        assert result == ""

    def test_non_folder_rows_excluded(self, gui_db: QSqlDatabase) -> None:
        """Only is_folder=1 rows are included; file rows are filtered out."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        model = StatementQueueModel(db=gui_db)
        model.set_project(project_id)

        batch_id = uuid4().hex
        folder_id = _add_folder(model, session_id, path="/data/folder")
        _add_file(model, session_id, parent_id=folder_id, path="/data/folder/x.pdf")
        model.select()
        model.set_batch_id(batch_id)

        result = model.get_folder_paths_for_batch(batch_id)
        # Only the folder path should appear, not the child file path
        assert result == "/data/folder"
        assert "x.pdf" not in result


# ---------------------------------------------------------------------------
# TestStatementQueueTreeModel
# ---------------------------------------------------------------------------


class TestStatementQueueTreeModel:
    """Tests for StatementQueueTreeModel.update_model."""

    def test_empty_project_produces_empty_tree(self, gui_db: QSqlDatabase) -> None:
        """With no queue rows, the tree model has no rows."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        tree = StatementQueueTreeModel(db=gui_db)
        tree.update_model(project_id)

        assert tree.rowCount() == 0

    def test_folder_with_no_children_labelled_empty(
        self, gui_db: QSqlDatabase
    ) -> None:
        """A folder row with no child files is labelled '(empty)'."""
        session_id, project_id, _ = seed_session_and_project(gui_db)

        # Insert queue row directly so we can use tree model without
        # needing a StatementQueueModel scoped to the project
        queue_model = StatementQueueModel(db=gui_db)
        queue_model.set_project(project_id)
        _add_folder(queue_model, session_id, path="/data/empty_folder")

        tree = StatementQueueTreeModel(db=gui_db)
        tree.update_model(project_id)

        # Folders root should be present
        assert tree.rowCount() == 1
        folders_root = tree.item(0)
        assert folders_root is not None
        assert folders_root.text() == "Folders"

        folder_item = folders_root.child(0)
        assert folder_item is not None
        assert "(empty)" in folder_item.text()

    def test_folder_with_children_labelled_with_count(
        self, gui_db: QSqlDatabase
    ) -> None:
        """A folder with N children is labelled '(N pdf files)'."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        queue_model = StatementQueueModel(db=gui_db)
        queue_model.set_project(project_id)

        folder_id = _add_folder(queue_model, session_id, path="/data/folder")
        _add_file(queue_model, session_id, parent_id=folder_id, path="/data/folder/a.pdf")
        _add_file(queue_model, session_id, parent_id=folder_id, path="/data/folder/b.pdf")

        tree = StatementQueueTreeModel(db=gui_db)
        tree.update_model(project_id)

        folders_root = tree.item(0)
        assert folders_root is not None
        folder_item = folders_root.child(0)
        assert folder_item is not None
        assert "2 pdf files" in folder_item.text()
        assert "(empty)" not in folder_item.text()

    def test_standalone_file_placed_under_files_root(
        self, gui_db: QSqlDatabase
    ) -> None:
        """A standalone file (own-parent, is_folder=0) appears under a 'Files' root."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        queue_model = StatementQueueModel(db=gui_db)
        queue_model.set_project(project_id)

        _add_standalone_file(queue_model, session_id, path="/data/standalone.pdf")

        tree = StatementQueueTreeModel(db=gui_db)
        tree.update_model(project_id)

        # Should have a 'Files' root, no 'Folders' root
        assert tree.rowCount() == 1
        files_root = tree.item(0)
        assert files_root is not None
        assert files_root.text() == "Files"

    def test_folder_placed_under_folders_root(self, gui_db: QSqlDatabase) -> None:
        """A folder row appears under a 'Folders' root."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        queue_model = StatementQueueModel(db=gui_db)
        queue_model.set_project(project_id)

        _add_folder(queue_model, session_id, path="/data/folder")

        tree = StatementQueueTreeModel(db=gui_db)
        tree.update_model(project_id)

        # Should have a 'Folders' root, no 'Files' root
        assert tree.rowCount() == 1
        root = tree.item(0)
        assert root is not None
        assert root.text() == "Folders"

    def test_no_folders_root_when_only_files(self, gui_db: QSqlDatabase) -> None:
        """'Folders' root is not appended when no folder rows exist."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        queue_model = StatementQueueModel(db=gui_db)
        queue_model.set_project(project_id)

        _add_standalone_file(queue_model, session_id)

        tree = StatementQueueTreeModel(db=gui_db)
        tree.update_model(project_id)

        root_texts = [tree.item(i).text() for i in range(tree.rowCount())]
        assert "Folders" not in root_texts

    def test_no_files_root_when_only_folders(self, gui_db: QSqlDatabase) -> None:
        """'Files' root is not appended when no standalone file rows exist."""
        session_id, project_id, _ = seed_session_and_project(gui_db)
        queue_model = StatementQueueModel(db=gui_db)
        queue_model.set_project(project_id)

        _add_folder(queue_model, session_id)

        tree = StatementQueueTreeModel(db=gui_db)
        tree.update_model(project_id)

        root_texts = [tree.item(i).text() for i in range(tree.rowCount())]
        assert "Files" not in root_texts
