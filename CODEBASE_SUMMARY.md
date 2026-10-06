# Openstan Codebase Exploration — Executive Summary

## 1. Directory Structure (Simplified)

```
src/openstan/
├── main.py                  # Stan main window + bootstrap
├── components.py            # Stan-prefixed Qt widget subclasses
├── paths.py                 # Platform-aware path resolution
├── models/                  # QSqlTableModel CRUD + signals
├── presenters/              # Business logic & signal wiring
└── views/                   # Qt layouts (zero logic)
```

**Key Finding:** No dialogs/ subdirectory exists yet. Dialogs live in views/ directory.

---

## 2. Admin System (Existing Pattern)

### AdminView (views/admin_view.py)
- Modeless dialog (stays on top, non-modal)
- 5 sections: Delete project, Remove from UI, Empty DB, Anonymise, Privacy settings
- All widgets public attributes for presenter access: `combo_delete`, `button_delete_project`, etc.
- Uses `StanDialog` base class with `.make_scrollable()` support

### AdminPresenter (presenters/admin_presenter.py)
- Owns all business logic + signal wiring
- Key method: `refresh_combos()` - Updates project selection lists
- Signal pattern: Button clicks → Slots that show confirmations → Execute actions
- Uses `StanErrorMessage` and `StanInfoMessage` for dialogs

### Configuration Storage
- Uses `QSettings("openstan", "openstan")`
- Existing key: `privacy/update_check_enabled` (boolean, default: True)
- **Will add:** `logging/verbosity` (values: "normal" or "verbose")

---

## 3. Current Logging State

### In main.py
- ~15 print() statements for startup diagnostics
- Format: `[openstan] <context>: <message>`
- Linux color scheme detection, theme application, platform detection

### Across Presenters & Models
**Files with print():**
- `presenters/user_presenter.py` (2 calls) - User creation failures
- `presenters/stan_presenter.py` (1 call) - "Session ended." on exit
- `presenters/statement_queue_presenter.py` (TBD)
- `presenters/statement_result_presenter.py` (~20 calls) - Batch commit/rollback, errors
- `models/batch_model.py` (TBD)
- `models/statement_result_model.py` (TBD)

### Current State
**NO structured logging infrastructure yet** — Python `logging` module not imported anywhere
**All output goes to stderr via print()** — not to files or rotating handlers

---

## 4. Configuration & Settings

### QSettings Pattern (Already in Use)
```python
from PySide6.QtCore import QSettings

settings = QSettings("openstan", "openstan")
raw = settings.value("privacy/update_check_enabled")  # None if not set
settings.setValue("privacy/update_check_enabled", True)
```

### Platform Storage Locations
- Windows: Registry `HKEY_CURRENT_USER\Software\openstan\openstan\`
- macOS: `~/Library/Preferences/com.openstan.plist`
- Linux: `~/.config/openstan/openstan.conf` (XDG standard)

### For Logging
**Will add new key:** `logging/verbosity`
- Default: "normal"
- Values: "normal" (INFO level) or "verbose" (DEBUG level)

---

## 5. Dialog Patterns

### Pure Display (No Presenter)
```python
AboutDialog(self).exec()  # Views/about_dialog.py
```

### Modal with Presenter
```python
dlg = AnonymiseDialog(parent=self.view)
_presenter = AnonymisePresenter(dialog=dlg, project_paths=..., threadpool=...)
dlg.exec()  # Blocks until closed
```

### Key Pattern
- View: Extends `StanDialog`, exposes widgets publicly (`self.combo_delete`, `self.button_delete_project`)
- Presenter: Receives view at `__init__`, connects all signals/slots
- No business logic in views, all logic in presenters

---

## 6. Project Selection & Context Switching

### Project Selection Flow
**Main Window (Stan):**
```python
self.current_project_id  # Currently selected
self.current_project_name  # Display name
self.current_project_paths  # ProjectPaths object for active project
```

### Critical Integration Point: StanPresenter.update_current_project_info()
```python
def update_current_project_info(self, index: int) -> None:
    current_record = self.project_presenter.model.record(index)
    self.stan.current_project_id = current_record.value("project_ID")
    # ... updates all child presenters with new project context ...
    # THIS IS WHERE LOGGING CONTEXT SHOULD SWITCH TO NEW PROJECT LOG
```

---

## 7. Print Statements Inventory

| File | Count | Context |
|------|-------|---------|
| main.py | ~15 | Startup diagnostics |
| user_presenter.py | 2 | Creation failures |
| statement_result_presenter.py | ~20 | Batch operations, errors |
| stan_presenter.py | 1 | Session cleanup |
| (Others) | TBD | Queue, batch model operations |

**Replacement Strategy:**
- **Errors:** `logger.error(..., exc_info=True)`
- **Milestones:** `logger.info(...)`
- **Diagnostics:** `logger.debug(...)`
- **Startup:** Keep as-is or use `logger.debug(...)`

---

## 8. Architecture Patterns

### MVP Strict Separation
| Layer | Example | Role |
|-------|---------|------|
| **Model** | ProjectModel (QSqlTableModel) | CRUD + db_updated signal |
| **View** | AdminView | Widgets only, no logic |
| **Presenter** | AdminPresenter | All signal wiring, business logic |

### Signal Convention
```python
# In Model:
db_updated = Signal()  # Emitted when data changes
self.db_updated.emit()

# In Presenter:
self.model.db_updated.connect(self.on_db_updated)
```

### Model Return Convention
```python
def add_record(...) -> tuple[bool, str, str]:
    return (success: bool, record_id: str, message: str)
```

---

## 9. Widget Subclass Convention

**All Qt widgets must use Stan-prefixed subclasses from components.py:**
- `StanWidget`, `StanLabel`, `StanButton`, `StanDialog`
- `StanComboBox`, `StanCheckBox`, `StanTableView`, etc.
- These apply consistent styling + theme switching support
- No raw Qt widgets in views (except layout classes)

---

## 10. Application Bootstrap

**Startup Order:**
1. QApplication created
2. Platform style set (Windows/macOS/Fusion)
3. Theme detection & palette application
4. GUI database opened
5. All models created + select()
6. All views instantiated
7. All presenters instantiated + signal wiring
8. StanPresenter.__init__ bootstrap (user, session creation)
9. Window shown

**Database Locations:**
- `~/.local/share/openstan/gui.db` (Linux)
- `~/Library/Application Support/openstan/gui.db` (macOS)
- `%APPDATA%\openstan\gui.db` (Windows)

---

## Key Implementation Decisions

### For Phase 3 (Openstan Logging Integration)

**New Files Needed:**
1. `src/openstan/logging_manager.py` — Logger factory + context management
2. `src/openstan/views/log_viewer_dialog.py` — Read-only log viewer

**Modifications Needed:**
1. `src/openstan/views/admin_view.py` — Add 2 sections for log viewing
2. `src/openstan/presenters/admin_presenter.py` — Add slots for log viewers
3. `src/openstan/presenters/stan_presenter.py` — Hook context switching in `update_current_project_info()`
4. `src/openstan/main.py` — Initialize logging at startup
5. All presenters/models — Replace print() with logging calls

**No Breaking Changes Required:**
- QSettings system unchanged (add new key)
- Dialog patterns already established
- MVP separation maintained
- Logging as cross-cutting concern only

---

## Critical Integration Points

1. **Context Switching:** `StanPresenter.update_current_project_info()` line ~162
2. **Admin UI:** `AdminView.__init__()` to add new sections
3. **Admin Logic:** `AdminPresenter` to add log viewer slots + verbosity toggle
4. **Initialization:** `main.py` function after QApplication setup
5. **Print Replacement:** Systematic across 6-8 files

