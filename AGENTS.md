# AGENTS.md — Developer & Agent Guide for `openstan`

## Project Overview

`openstan` is a Python/PyQt6 desktop application for bank statement analysis and
visualization. It follows a strict **MVP (Model–View–Presenter)** architecture with
SQLite backing via Qt's `QSqlDatabase` layer.

---

## Environment & Package Manager

- **Python ≥ 3.14** is required.
- **`uv`** is the sole package/build manager. Do **not** use `pip`, `poetry`, or `conda`.
- Install dependencies: `uv sync`
- Run the app: `uv run openstan`  or  `uv run python -m openstan`

---

## Build / Lint / Type-Check Commands

```bash
# Lint (Ruff — default E + F rules, 88-char line length)
uv run ruff check src/

# Auto-fix lint issues
uv run ruff check --fix src/

# Format code (Ruff formatter, 88-char lines, double quotes)
uv run ruff format src/

# Type-check (Meta's Pyrefly — NOT mypy)
uv run pyrefly check
```

---

## Tests

There is currently **no test suite**. No `pytest` or test files exist yet.
When tests are added:

```bash
# Install pytest (one-time)
uv add --dev pytest

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/path/to/test_file.py

# Run a single test function
uv run pytest tests/path/to/test_file.py::test_function_name

# Run a single test class method
uv run pytest tests/path/to/test_file.py::TestClass::test_method
```

---

## Code Style

### Formatter & Linter

- **Ruff** handles both linting and formatting. No Black, no isort, no Flake8.
- Line length: **88 characters**.
- Indent: **4 spaces**.
- Quote style: **double quotes** (Ruff formatter default).
- Always run `uv run ruff format src/` before committing.

### Type Checking

- Use **Pyrefly** (`uv run pyrefly check`), not mypy.
- Annotate all function return types (`-> None`, `-> bool`, `-> tuple[bool, str, str]`).
- Annotate local variables where it improves clarity.
- Keep `__all__: list[str]` in every `__init__.py`.

### Multi-exception syntax

Both forms below are **valid Python 3.14** and semantically identical:

```python
except ValueError, TypeError:     # valid — bare-comma form, preferred by ruff format
except (ValueError, TypeError):   # valid — parenthesised form, also acceptable
```

**`ruff format` actively removes the parentheses**, converting the parenthesised form
to the bare-comma form on save. Do not "fix" bare-comma except clauses — they are correct
and Ruff-idiomatic. Do not flag `except A, B:` as Python 2 syntax; in Python 3.14 it
parses as a tuple of exception types, equivalent to `except (A, B):`.

The instance in `project_presenter.py` (`except sqlite3.OperationalError, bsp.StatementError:`)
is correct as written. This has been investigated and confirmed — do not re-flag it.

---

## Naming Conventions

### Files
- All module files: `snake_case.py`
- Follow the `<domain>_<layer>.py` pattern:
  `project_model.py`, `project_view.py`, `project_presenter.py`

### Classes
- Application-specific Qt widgets: `Stan` prefix + `PascalCase`
  (`StanButton`, `StanLabel`, `StanFrame`, `StanTreeView`, `StanErrorMessage`)
- Domain classes: `PascalCase` with layer suffix
  (`ProjectModel`, `StatementQueueView`, `AdminPresenter`)
- Worker threads: `PascalCase` + `Worker` suffix (`SQWorker`)
- Signal containers: `PascalCase` + `Signals` suffix (`WorkerSignals`)
- Main window: `Stan` (no suffix)

### Functions & Methods
- **`snake_case`** for all Python-defined methods.
- Qt-mandated overrides that Qt expects in `camelCase` (e.g. `rowCount`,
  `closeEvent`) are written in `camelCase` with `# noqa: N802` if needed.
- Event handler slots: `on_<event>` or descriptive verb phrases
  (`on_model_updated`, `run_import`, `update_progress`).
- Model CRUD methods: `add_record`, `delete_record_by_id`, `delete_records`,
  `clear_records`.

### Variables & Constants
- Local variables and instance attributes: **`snake_case`**.
- Module-level constants: `UPPER_SNAKE_CASE` (e.g. `NEW_RECORD_STATUS = 8`).
- Private module-level DDL strings: `_UPPER_SNAKE_CASE`
  (e.g. `_DDL_TABLES`, `_DDL_VIEW`, `_STATUS_ROWS`).
- Prefer `project_id`, `session_id`, `user_id` (snake_case) for ID variables;
  legacy `sessionID`/`userID` camelCase exists in older code — do not extend it.

### Signals
- `pyqtSignal` class attributes: **`snake_case`**
  (`db_updated`, `model_updated`, `import_finished`, `path_or_name_changed`).
- Import `pyqtSignal` directly; avoid aliasing it as `Signal` (inconsistency
  exists in `statement_queue_model.py` — do not replicate it).

---

## Import Style

### Ordering (PEP 8; isort not enforced but follow this order)
1. Standard library (`os`, `sys`, `pathlib`, `datetime`, `uuid`, `typing`)
2. Third-party (`bank_statement_parser`, `PyQt6.*`)
3. First-party (`openstan.*`)

Separate each group with a blank line.

### Named Imports Only
- Always import Qt classes by name:
  `from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot`
- No wildcard imports (`from PyQt6.QtWidgets import *` is forbidden).
- No default imports from internal modules.

### Absolute Internal Imports
- Always use **absolute** package paths for internal imports:
  `from openstan.models.project_model import ProjectModel`
- **No relative imports** (`from .project_model import ...`).

### `TYPE_CHECKING` Guard (required in all presenters)
Use this pattern to break circular imports at runtime while preserving static analysis:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from openstan.models.project_model import ProjectModel
    from openstan.views.project_view import ProjectView
```

Annotate constructor parameters with string literals:
```python
def __init__(self, model: "ProjectModel", view: "ProjectView") -> None:
```

---

## Architecture

### MVP Layers (strict separation)
| Layer | Location | Responsibility |
|---|---|---|
| **Model** | `src/openstan/models/` | Qt SQL models (`QSqlTableModel`), CRUD, signals |
| **View** | `src/openstan/views/` | Widget layout only — **zero business logic** |
| **Presenter** | `src/openstan/presenters/` | All signal/slot wiring, business logic |

- Views expose widget references publicly; they never connect their own signals.
- Presenters receive model and view at `__init__` and own all connections.
- `StanPresenter` is the top-level coordinator for cross-presenter signals and
  application-level startup (user setup, session init, project sync).

### Database Access Rules
- `gui.db` (SQLite): accessed **only** via `QSqlDatabase` / `QSqlTableModel`
  subclasses at runtime. Raw `sqlite3` is used only in `create_gui_db.py`
  for initial schema bootstrap.
- `project.db` (data mart): **never** accessed directly from `openstan`.
  All mart interactions must go through the `bank_statement_parser` API (D001).
- The `event_log` table is populated exclusively by SQLite-level triggers —
  presenters and models must **never** write to it directly (NFR-4).

### Worker Thread Pattern
```python
class WorkerSignals(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

class SQWorker(QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = WorkerSignals()

    def run(self) -> None:
        # background work here
        self.signals.progress.emit(50)
        self.signals.finished.emit()

QThreadPool.globalInstance().start(worker)
```

### Model Return Convention
All model mutation methods return a **3-tuple**:
```python
(success: bool, record_id: str, message: str)
```
Callers must check `result[0]` and handle the `False` case.

---

## Error Handling

- Use `StanErrorMessage` (subclass of `QErrorMessage`) for database errors and
  unrecoverable failures — always modal, shown via `.showMessage(str)`.
- Use `StanInfoMessage` (subclass of `QMessageBox`) for confirmations before
  destructive actions, using `Yes | Cancel` with `Cancel` as default.
- Catch-all in presenters: `except Exception as e:` — use for Qt slot callbacks.
- For disk-operation failures, use `traceback.print_exc()` and surface the error
  to the user via a dialog. Do not silently swallow exceptions.
- Partial side-effects (e.g. folder creation) must be rolled back in `except`
  blocks before re-surfacing the error.
- No structured logging framework — use `print()` for debug output.

---

## Key Libraries & What to Avoid

| Use | Avoid |
|---|---|
| `polars` (via `bsp`) for tabular data | `pandas` (D003) |
| `pathlib.Path` for all paths | `os.path` string concatenation |
| `uuid.uuid4().hex` for primary keys | auto-increment integers |
| `QSqlTableModel` for GUI DB access | raw `sqlite3` at runtime |
| `uv` for package management | `pip`, `poetry`, `conda` |
| `bank_statement_parser` API for mart | direct mart DB access |

DuckDB experiments live in `data/duck.py` (entirely commented out); do not
uncomment or extend — it is scheduled for deletion (D004).

---

## Dead Code — Do Not Extend

- `src/openstan/data/ops.py` — legacy raw `QSqlQuery` helpers; references an
  old DB filename. Scheduled for removal.
- `src/openstan/data/duck.py` — commented-out DuckDB experiments (D004).
- `src/openstan/models/event_log_model.py` — `EventLogModel` is imported nowhere;
  audit log is trigger-driven.
