# Openstan Codebase Architecture Exploration

**Date:** 2026-09-30  
**Scope:** Phase 3 preparation for logging infrastructure  
**Focus:** Understanding project structure, existing patterns, and requirements

---

## 1. Directory Structure

### Main Source Tree
```
src/openstan/
├── __init__.py
├── __main__.py
├── main.py                          # Main window (Stan class) & app startup
├── components.py                    # Stan-prefixed Qt widget subclasses
├── palettes.py                      # Theme palette management
├── paths.py                         # Platform-aware path resolution
├── updater.py                       # GitHub update checker
│
├── data/
│   ├── __init__.py
│   ├── create_gui_db.py             # Bootstrap GUI SQLite schema
│   ├── sql_files/                   # DDL SQL files
│   └── fonts/                       # Bundled Inter font files
│
├── icons/
│   ├── __init__.py
│   ├── light/                       # Legacy theme-specific icons (unused)
│   ├── dark/                        # Legacy theme-specific icons (unused)
│   └── tabler/                      # Universal Tabler SVG icons (theme-neutral)
│
├── models/                          # QSqlTableModel subclasses + domain logic
│   ├── __init__.py
│   ├── batch_model.py               # Batch record CRUD
│   ├── project_model.py             # Project record CRUD (has db_updated signal)
│   ├── report_model.py              # Report data model (non-SQL)
│   ├── session_model.py             # User session CRUD
│   ├── statement_queue_model.py     # Statement import queue model
│   ├── statement_result_model.py    # Statement import results (success/review/failure)
│   └── user_model.py                # User record CRUD
│
├── presenters/                      # Business logic & signal wiring (MVP pattern)
│   ├── __init__.py                  # Exports all presenter classes
│   ├── admin_presenter.py           # Admin dialog: destructive operations
│   ├── advanced_export_presenter.py # Advanced export logic
│   ├── anonymise_presenter.py       # Anonymise PDF helper dialog
│   ├── export_data_presenter.py     # Statement export logic
│   ├── project_presenter.py         # Project selection & info
│   ├── run_reports_presenter.py     # Report generation logic
│   ├── session_presenter.py         # Session management
│   ├── stan_presenter.py            # Top-level coordinator (cross-presenter signals)
│   ├── statement_queue_presenter.py # Import queue UI logic
│   ├── statement_result_presenter.py# Import results & batch commit
│   ├── user_presenter.py            # User management
│   └── workers.py                   # QRunnable worker classes
│
└── views/                           # Qt layout & widgets (zero business logic)
    ├── __init__.py                  # Exports all view classes
    ├── about_dialog.py              # Pure display (no presenter)
    ├── admin_view.py                # Admin dialog widget tree
    ├── advanced_export_view.py
    ├── anonymise_dialog.py
    ├── anonymise_results_dialog.py
    ├── content_view.py
    ├── debug_info_dialog.py
    ├── export_data_view.py
    ├── footer_view.py
    ├── parquet_view_dialog.py
    ├── pending_batch_dialog.py
    ├── project_view.py              # Project selection, nav, welcome, info panels
    ├── run_reports_view.py
    ├── statement_queue_view.py
    ├── statement_result_view.py
    ├── title.py                     # App title bar with logo & buttons
    └── __init__.py
```

---

## 2. Existing Admin System

### AdminView (views/admin_view.py)
**Purpose:** Modeless admin dialog for destructive operations & config

**Structure:** `StanDialog` subclass with 5 independent sections

**Sections:**
1. **Delete Project** - Remove project record + optionally delete folder
   - Combo: project selection
   - Checkbox: "Also delete folder from disk"
   - Button: `button_delete_project`

2. **Remove Project from UI Only** - DB record removal without disk deletion
   - Combo: project selection
   - Button: `button_remove_project`

3. **Empty Database** - Reset gui.db + restart app
   - Button: `button_empty_db`

4. **Anonymise Tool** - Open PDF anonymisation dialog for active project
   - Button: `button_open_anonymise`

5. **Privacy Settings** - Update check toggle
   - Checkbox: `check_update_check` (persisted to QSettings)

**Features:**
- Non-modal (modeless) — stays on top of main window
- Scrollable on low-resolution screens (`.make_scrollable()`)
- All action buttons require confirmation before execution
- Opened via double-clicking footer label

### AdminPresenter (presenters/admin_presenter.py)
**Purpose:** Owns all admin business logic & dialog state management

**Key Methods:**
- `is_update_check_enabled()` - Static check of QSettings privacy/update_check_enabled
- `refresh_combos()` - Repopulate project selection combos from model
- `_confirm()` - Show Yes/Cancel confirmation dialog (returns bool)
- `delete_project()` - [Slot] Delete selected project ± folder
- `remove_project_from_ui()` - [Slot] Remove DB record only
- `empty_gui_db()` - [Slot] Delete gui.db & restart app
- `open_anonymise_tool()` - [Slot] Open AnonymiseDialog for active project
- `update_check_changed(state)` - [Slot] Persist checkbox state to QSettings

**Signal Wiring:**
```python
self.view.button_delete_project.clicked.connect(self.delete_project)
self.view.button_remove_project.clicked.connect(self.remove_project_from_ui)
self.view.button_empty_db.clicked.connect(self.empty_gui_db)
self.view.button_open_anonymise.clicked.connect(self.open_anonymise_tool)
self.view.check_update_check.stateChanged.connect(self.update_check_changed)
```

**Configuration Management:**
- Uses `QSettings(_SETTINGS_ORG, _SETTINGS_APP)` where:
  - `_SETTINGS_ORG = "openstan"`
  - `_SETTINGS_APP = "openstan"`
- Key pattern: `privacy/update_check_enabled` (can store other privacy settings)
- Settings persist to platform-standard locations:
  - Windows: Registry
  - macOS: `~/Library/Preferences/com.openstan.plist`
  - Linux: `~/.config/openstan/openstan.conf`

---

## 3. Current Logging Setup

### In main.py
**Print statements for diagnostic output (NOT structured logging):**
- `_detect_scheme_via_dbus()` - Linux color scheme detection
- `_apply_palette()` - Theme application
- App startup bootstrap messages
- Platform detection (Windows/macOS/Linux)
- Qt style selection

**Format:** `[openstan] <context>: <message>`

**Example:**
```python
print("[openstan] startup: sys.frozen=True  platform=linux")
print("[openstan] _detect_scheme_via_dbus: detected → Dark")
print("[openstan] style: Fusion  productType='linux'")
```

**Note:** Uses `qDebug()` once at app start but mostly `print()` for stderr output

### Across Presenters & Models
**Files with print() calls:**
1. `presenters/user_presenter.py` - User creation failures
2. `presenters/session_presenter.py` - (TBD)
3. `presenters/stan_presenter.py` - `print("Session ended.")` on exit
4. `presenters/statement_queue_presenter.py` - Import queue operations
5. `presenters/statement_result_presenter.py` - Batch commit/rollback, debug worker
6. `models/batch_model.py` - Batch operations
7. `models/statement_result_model.py` - Result data operations

**Typical patterns:**
```python
print(f"ERROR: Could not delete payloads: {msg}", file=sys.stderr)
print(f"[commit warning] {message}", file=sys.stderr)
```

**No structured logging infrastructure exists yet** — Phase 3 deliverable

---

## 4. Settings & Configuration Management

### Current System
**Technology:** `PySide6.QtCore.QSettings`

**Usage Pattern:**
```python
from PySide6.QtCore import QSettings

settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
# Read
raw = settings.value(_KEY_UPDATE_CHECK)  # Returns None if key doesn't exist
# Write
settings.setValue(_KEY_UPDATE_CHECK, enabled)
```

**Platform Storage:**
- **Windows:** Registry (`HKEY_CURRENT_USER\Software\openstan\openstan\`)
- **macOS:** `~/Library/Preferences/com.openstan.plist`
- **Linux:** `~/.config/openstan/openstan.conf` (XDG standard)

**Existing Keys:**
- `privacy/update_check_enabled` - Boolean (default: True)

**No verbosity toggle exists yet** — Will be added as:
- Key: `logging/verbosity` (values: "normal" or "verbose")
- Default: "normal"

---

## 5. Existing Dialog Patterns

### Pure Display Dialogs (no presenter needed)
**AboutDialog** (views/about_dialog.py)
- Extends `StanDialog`
- Shows logo, version, links, copyright
- No business logic, no model access
- Opened directly from main window when requested
- Method: `AboutDialog(parent=self).exec()`

**ParquetViewDialog** (views/parquet_view_dialog.py)
- Displays Polars DataFrame in table view
- No presenter, passed data directly to constructor
- Scrollable table with column headers

### Modal Dialogs with Presenters
**AnonymiseDialog** (views/anonymise_dialog.py) + AnonymisePresenter
- Input: file selection, output folder
- Presenter: handles actual PDF anonymisation (async worker)
- Constructor: `AnonymiseDialog(parent=self.view)`
- Presenter: `AnonymisePresenter(dialog=dlg, project_paths=..., threadpool=...)`
- Execution: `dlg.exec()`

**DebugInfoDialog** (views/debug_info_dialog.py)
- Displays per-statement debug progress
- Updates live via `update_row()` as worker emits signals
- Buttons: Open JSON, Open Excel, Open PDF, View Parquet, Anonymise
- Constructor: `DebugInfoDialog(rows=[], project_paths=None, parent=None, threadpool=None)`

### Dialog Creation Patterns

**Pattern 1 — Pure display (no presenter):**
```python
AboutDialog(self).exec()
```

**Pattern 2 — Modeless dialog with presenter (stays on top):**
```python
dialog = MyDialog(parent=self)
presenter = MyPresenter(dialog=dialog, ...)
# Dialog persists after construction; presenter wired internally
```

**Pattern 3 — Modal dialog with helper presenter:**
```python
dlg = AnonymiseDialog(parent=self.view)
_presenter = AnonymisePresenter(dialog=dlg, project_paths=..., threadpool=...)
dlg.exec()  # Blocks until closed
```

---

## 6. Project Selection & Management

### Project Selection Flow
**Entry Point:** Main window (`Stan` class)
- `self.project_view.selection` - ComboBox showing all projects
- `self.current_project_id` - Currently selected project ID
- `self.current_project_name` - Currently selected project name
- `self.current_project_paths` - `ProjectPaths` object for active project

### ProjectPresenter
**Signals:**
- `project_switched` - Emitted when user selects a project

**Key Methods:**
- `on_project_selected(index)` - Handle combo box selection change
- `update_view_visibility(has_projects, selected_project)` - Show/hide project panels

### StanPresenter (Top-level Coordinator)
**Owns the cross-presenter orchestration:**

```python
@Slot(int)
def project_selection_changed(self, index: int) -> None:
    # If results view active, close first
    if self.stan.content_stack.currentIndex() == self.stan.nav_idx_results:
        self.hide_results()
    self.update_current_project_info(index)


def update_current_project_info(self, index: int) -> None:
    current_record = self.project_presenter.model.record(index)
    self.stan.current_project_name = current_record.value("project_name")
    self.stan.current_project_id = current_record.value("project_ID")

    # Update all child presenters with new project context
    self.statement_queue_presenter.projectID = self.stan.current_project_id
    self.statement_queue_presenter.projectPath = self.stan.current_project_paths.root
    self.statement_result_presenter.project_path = self.stan.current_project_paths.root
    self.export_data_presenter.project_path = self.stan.current_project_paths.root
    # ... etc

    # Propagate to footer display
    self.footer_view.labelProject.setText(
        f"##### Project: {self.stan.current_project_name} (ID: {self.stan.current_project_id})"
    )
```

**Key Insight:** Project switching is centralized in `StanPresenter.update_current_project_info()` —
this is where logging context should be updated to switch log files.

---

## 7. Print Statements Inventory

### By File & Count

| File | Count | Severity | Examples |
|------|-------|----------|----------|
| `main.py` | ~15 | **LOW** | Startup diagnostics, theme detection |
| `presenters/user_presenter.py` | 2 | **MEDIUM** | User creation failures |
| `presenters/session_presenter.py` | ? | TBD | Session management |
| `presenters/stan_presenter.py` | 1 | **LOW** | "Session ended." on exit |
| `presenters/statement_queue_presenter.py` | ? | TBD | Import queue operations |
| `presenters/statement_result_presenter.py` | ~20 | **HIGH** | Batch commit, debug worker, errors |
| `models/batch_model.py` | ? | **MEDIUM** | Batch operations |
| `models/statement_result_model.py` | ? | **MEDIUM** | Result tracking |

**Replacement Strategy:**
1. **main.py:** Keep as-is (diagnostic startup output) or migrate to logger with DEBUG level
2. **Error paths:** Replace with `logger.error(..., exc_info=True)`
3. **Process milestones:** Replace with `logger.info(...)`
4. **Diagnostic details:** Replace with `logger.debug(...)`

---

## 8. Architecture Patterns & Key Classes

### MVP Pattern (strict separation)
| Layer | Responsibility | Example |
|-------|-----------------|---------|
| **Model** | `QSqlTableModel` subclasses, CRUD, emits signals | `ProjectModel` with `db_updated` signal |
| **View** | Widget layout only, zero business logic | `AdminView` with combo boxes & buttons |
| **Presenter** | All signal wiring, business logic, model → view | `AdminPresenter` owns all slot handlers |

### Signal Convention
- Models emit when data changes: `db_updated = Signal()`
- Presenters connect signals and wire UI responses
- Views expose widget references publicly (no internal signal connections)

### Model Return Convention
All model mutation methods return a 3-tuple:
```python
def add_record(...) -> tuple[bool, str, str]:
    return (success: bool, record_id: str, message: str)
```

### Database Access
- **Runtime:** Only via `QSqlDatabase` / `QSqlTableModel`
- **Initialization:** Raw `sqlite3` only in `create_gui_db.py`
- **No direct file access** — uses Qt SQL layer exclusively

### Widget Subclass Convention
All Qt widgets must use `Stan`-prefixed subclasses from `components.py`:
- `StanWidget`, `StanLabel`, `StanButton`, `StanDialog`, etc.
- These apply consistent styling (auto-fill background, alternating rows, etc.)
- Enables theme switching without widget recreation

---

## 9. Application Bootstrap & Lifecycle

**Startup Sequence (main.py → Stan.__init__):**
1. QApplication created + platform style set
2. Theme detection (Linux via gdbus portal, other platforms via Qt)
3. Palette applied for dark/light mode
4. Font database populated (Inter fonts registered)
5. GUI database opened (`gui.db`)
6. All models created and select() called
7. All views instantiated
8. All presenters instantiated with signal wiring
9. StanPresenter.__init__ runs bootstrap (user creation, session creation)
10. Window shown + app.exec()

**Shutdown:**
- `closeEvent()` checks if import in progress (warns user)
- `cleanup_before_exit()` cancels workers and ends sessions
- Database connection closed

**Key Storage Locations:**
- `~/.local/share/openstan/gui.db` (Linux)
- `~/Library/Application Support/openstan/gui.db` (macOS)
- `%APPDATA%\openstan\gui.db` (Windows)

---

## 10. Configuration Requirements for Logging

### Needed for Implementation
1. **Verbosity setting** storage (QSettings key: `logging/verbosity`)
2. **Log file paths** resolution (via existing `Paths` class)
3. **Project context switching** hook (in `StanPresenter.update_current_project_info()`)
4. **Admin UI sections** for viewing logs (add to `AdminView`)
5. **Log viewer dialog** (new, pure display)
6. **Presenter slots** for opening log viewers (in `AdminPresenter`)

### Already in Place
- QSettings infrastructure (privacy/update_check_enabled example)
- Platform-aware path resolution (`Paths.databases()` model)
- Dialog pattern (AboutDialog, DebugInfoDialog examples)
- Project selection coordination (StanPresenter)
- Cross-presenter signal wiring (StanPresenter model)

---

## Summary for Phase 3 Implementation

### Key Architectural Points
1. **Logging Manager** location: `src/openstan/logging_manager.py` (new)
2. **Log Viewer Dialog** location: `src/openstan/views/log_viewer_dialog.py` (new)
3. **Admin UI integration:** Extend `AdminView` with 2 sections (View App Log, View Project Log)
4. **Presenter integration:** Add 2 slots to `AdminPresenter` for opening viewers
5. **Context switching:** Hook in `StanPresenter.update_current_project_info()` to switch log files
6. **Print replacement:** Systematic replacement in presenters/models with logging calls
7. **Settings key:** Add `logging/verbosity` to QSettings management

### Critical Integration Points
- `StanPresenter` — where to update logging context on project switch
- `AdminPresenter` — where to add log viewer slots + verbosity toggle
- `AdminView` — where to add UI sections for logs
- `main.py` → `StanPresenter.__init__` — where to initialize logging system
- All presenters/models — where to replace print() with logging

### No Breaking Changes Required
- Existing QSettings system remains unchanged
- Dialog pattern is well-established (no new conventions needed)
- MVP separation stays intact (logging as cross-cutting concern)

