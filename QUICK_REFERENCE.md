# Quick Reference: File Paths & Key Locations

## Print Statements to Replace

### 1. main.py (15+ locations)
**File:** `src/openstan/main.py`
- Lines 97-135: `_detect_scheme_via_dbus()` — 5 print statements (diagnostics)
- Lines 146-154: `_apply_palette()` — 3 print statements (theme application)
- Lines 255-276: App startup messages — 8 print statements (platform detection)
- Lines 280-316: Style selection logging — 7 print statements

**Strategy:** Migrate to `logger.debug()` for diagnostics

### 2. presenters/statement_result_presenter.py (20+ locations)
**File:** `src/openstan/presenters/statement_result_presenter.py`
- Multiple print() with `file=sys.stderr`
- Batch commit/rollback operations
- Debug worker output
- Error conditions

**Strategy:** Use `logger.error()` + `logger.info()` for milestones

### 3. presenters/user_presenter.py (2 locations)
**File:** `src/openstan/presenters/user_presenter.py`
- User creation failures

**Strategy:** Use `logger.error()`

### 4. presenters/stan_presenter.py (1 location)
**File:** `src/openstan/presenters/stan_presenter.py`
- Line 160: `print("Session ended.")`

**Strategy:** Use `logger.info()`

### 5. models/statement_result_model.py
**File:** `src/openstan/models/statement_result_model.py`
- TBD (check for print statements)

### 6. models/batch_model.py
**File:** `src/openstan/models/batch_model.py`
- TBD (check for print statements)

---

## Files to Create

### 1. logging_manager.py
**Location:** `src/openstan/logging_manager.py`

**Responsibilities:**
- Logger factory function `get_logger(name: str) -> logging.Logger`
- Context management: switch between app.log and project.log
- Verbosity level management (reading from QSettings)
- Rotating file handler setup (10 MB, 5 backups)

**Exports (for openstan/__init__.py):**
```python
__all__ = ["LoggingManager", "get_logger", "set_verbosity", "get_verbosity"]
```

### 2. views/log_viewer_dialog.py
**Location:** `src/openstan/views/log_viewer_dialog.py`

**Class:** `LogViewerDialog(StanDialog)`
- Read-only text display
- Shows privacy warning at top
- File path indicator
- Refresh button (re-read file)
- Copy to clipboard button
- Constructor: `LogViewerDialog(log_path: Path, parent=None)`

---

## Files to Modify

### 1. views/admin_view.py
**Location:** `src/openstan/views/admin_view.py`
**Current:** Lines 25-193

**Changes:**
- Add Section 6: View Application Log
  - Label: "View Application Log"
  - Info: "Display the application's diagnostic log file"
  - Button: `button_view_app_log`
  - Optional: Add "Clear Application Log" checkbox + button

- Add Section 7: View Project Log
  - Label: "View Project Log"
  - Info: "Display logs for the currently active project"
  - Button: `button_view_project_log`
  - Note: "(Only available when a project is selected)"

- Add Section 8: Logging Settings
  - Checkbox: `check_verbose_logging` - "Enable verbose (DEBUG) logging"
  - Info: "Increases log verbosity for debugging purposes"
  - Persisted to QSettings `logging/verbosity`

### 2. presenters/admin_presenter.py
**Location:** `src/openstan/presenters/admin_presenter.py`
**Current:** Lines 1-254

**Changes:**
- Add new signals connection in `__init__`:
  ```python
  self.view.button_view_app_log.clicked.connect(self.view_app_log)
  self.view.button_view_project_log.clicked.connect(self.view_project_log)
  self.view.check_verbose_logging.stateChanged.connect(self.toggle_verbosity)
  ```

- Add new slots:
  ```python
  @Slot()
  def view_app_log(self) -> None:
      # Open LogViewerDialog with application.log path
  
  @Slot()
  def view_project_log(self) -> None:
      # Check if project selected; open LogViewerDialog with project.log
  
  @Slot(int)
  def toggle_verbosity(self, state: Qt.CheckState) -> None:
      # Persist to QSettings logging/verbosity
  ```

- Add method: `refresh_verbosity_checkbox()` (call from `refresh_combos()`)
  - Read QSettings `logging/verbosity` and update checkbox

### 3. presenters/stan_presenter.py
**Location:** `src/openstan/presenters/stan_presenter.py`
**Current:** Lines 162-199

**Changes:**
- In `update_current_project_info()` method:
  ```python
  def update_current_project_info(self, index: int) -> None:
      # ... existing code ...
      
      if not selected_project:
          # Switch to app.log only
          LoggingManager.switch_to_app_log()
          return
      
      # Switch to project.log for this project
      project_log_path = self.stan.current_project_paths.root / "project.log"
      LoggingManager.switch_to_project_log(project_log_path, self.stan.current_project_id)
      
      # ... rest of existing code ...
  ```

### 4. main.py
**Location:** `src/openstan/main.py`
**Current:** Lines 1-60 (imports & startup)

**Changes:**
- Add import:
  ```python
  from openstan.logging_manager import LoggingManager, get_logger
  
  logger = get_logger(__name__)
  ```

- In `main()` function after QApplication created (around line 280):
  ```python
  # Initialize logging system
  log_path = Path(Paths.databases("application.log"))
  LoggingManager.initialize(
      app_log_path=log_path,
      verbosity=current_verbosity,  # Read from QSettings or default to "normal"
  )
  ```

- Replace print() calls in `_detect_scheme_via_dbus()`, `_apply_palette()`, etc. with:
  ```python
  logger.debug("...")  # for diagnostics
  logger.info("...")  # for milestones
  ```

### 5. __init__.py (openstan package)
**Location:** `src/openstan/__init__.py`

**Changes:**
- Export from logging_manager (if public API intended):
  ```python
  from openstan.logging_manager import LoggingManager, get_logger
  
  __all__ = ["LoggingManager", "get_logger", ...]
  ```

---

## QSettings Keys to Add

**Organization:** `openstan`
**Application:** `openstan`

### New Keys:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `logging/verbosity` | str | "normal" | "normal" or "verbose" |
| `logging/app_log_cleared` | bool | False | Track if app log was cleared this session |

---

## Log File Locations

### Application Log
- **Linux:** `~/.local/share/openstan/application.log`
- **macOS:** `~/Library/Application Support/openstan/application.log`
- **Windows:** `%APPDATA%\openstan\application.log`

### Project Log
- **Any platform:** `<project_root>/project.log`

### Resolved via Paths class:
```python
app_log_path = Path(Paths.databases("application.log"))
project_log_path = Path(current_project_root) / "project.log"
```

---

## Integration Checklist

- [ ] Create `logging_manager.py` with `LoggingManager` class
- [ ] Create `views/log_viewer_dialog.py` with `LogViewerDialog` class
- [ ] Update `views/admin_view.py` with 3 new sections (8 new widgets)
- [ ] Update `presenters/admin_presenter.py` with 3 new slots
- [ ] Update `presenters/stan_presenter.py` to switch log context
- [ ] Update `main.py` to initialize logging + replace print() calls
- [ ] Update `__init__.py` to export logging API (if public)
- [ ] Replace print() in `presenters/user_presenter.py`
- [ ] Replace print() in `presenters/statement_result_presenter.py`
- [ ] Replace print() in `models/batch_model.py`
- [ ] Replace print() in `models/statement_result_model.py`
- [ ] Unit tests for `logging_manager.py`
- [ ] Integration tests for log viewer + context switching

