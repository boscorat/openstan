# Phase 3: openstan Logging Integration — Detailed Implementation Plan

## Overview

Phase 3 integrates logging infrastructure across openstan to consume and display logs from the application and dependent libraries (`bank_statement_parser`, `uk-bank-statement-anonymiser`). Users can view logs via the admin dialog, toggle verbose mode, and logs automatically route to the correct file (app vs. project context).

**Status:** READY FOR EXECUTION  
**Total Effort:** ~12-15 hours (code) + 2-3 hours (docs) across multiple PRs  
**Branch Strategy:** `logging` (base) → `logging-phase3-<part>-DEV` (feature) → `logging` (PR + merge) → `master` (final PR)

---

## Design Decisions (Locked In)

| Decision | Outcome | Rationale |
|----------|---------|-----------|
| **Verbosity scope** | Global (one `logging/verbosity` key in QSettings) | Single source of truth for app-wide logging level |
| **Cascade to libraries** | YES — openstan's verbosity cascades to `bank_statement_parser` and `uk-bank-statement-anonymiser` | Project logs contain library diagnostics, not duplicate app logging |
| **Project log button state** | Hook into project selection signal in `stan_presenter.py` | Consistent with other project-specific UI state |
| **Button behavior** | Disabled when no project selected | No info dialog needed (state is self-explanatory) |
| **Verbosity applies** | Immediately (no restart) | Better UX; logger levels updated in real-time |
| **Log viewer capacity** | Show last 500 lines max | Balance between completeness and performance |
| **30-day cleanup** | Run on app closure (`closeEvent()`) | Avoids startup delay |
| **Application.log** | Cleared on app startup | Fresh logs for each session; rotation handles retention |

---

## Implementation Parts (15 Steps)

### Part A: Foundation — Logging Manager & Dialog

#### **Part A.1: Create `src/openstan/logging_manager.py`**

**Objective:** Central orchestrator for logging configuration, context switching, and cleanup.

**Deliverables:**
- [ ] Logger factory with verbosity levels (INFO/DEBUG)
- [ ] Initialize application.log to platform-specific directory (XDG/macOS/Windows)
- [ ] Clear application.log on app startup
- [ ] Context switching: app ↔ project logs
- [ ] 10 MB rotation + 5 backups for both app and project logs
- [ ] 30-day project log cleanup (file mod time based)
- [ ] QSettings persistence for verbosity ("normal" / "verbose")
- [ ] Cascade verbosity to library loggers (`bank_statement_parser`, `uk_bank_statement_anonymiser`)

**Key Methods:**
```python
initialize(verbosity: str = "normal") -> None
    # On app startup: clear app.log, read verbosity from QSettings, set up handlers
    # Cascade verbosity to library loggers

switch_to_app_log() -> None
    # Route all future logs to application.log (remove project handler)

switch_to_project_log(project_root: Path) -> None
    # Route all future logs to <project_root>/project.log

set_verbosity(level: str) -> None
    # "normal" (INFO) or "verbose" (DEBUG)
    # Update ALL loggers (openstan + libraries)
    # Persist to QSettings

get_verbosity() -> str
    # Retrieve from QSettings (default "normal")

get_app_log_path() -> Path
    # Platform-specific app log location

get_project_log_path(project_root: Path) -> Path
    # <project_root>/project.log

cleanup_old_project_logs() -> None
    # Delete project.log files with mtime >30 days ago
```

**Implementation Notes:**
- Use `QSettings("openstan", "openstan")` for persistence
- Root logger name: `"openstan"` (so all `openstan.*` loggers inherit from it)
- Library logger names: `"bank_statement_parser"`, `"uk_bank_statement_anonymiser"`
- **Handler Attachment Strategy (CRITICAL):**
  - Handlers must be attached to BOTH the "openstan" logger AND library loggers
  - Library loggers are top-level independent loggers (not children of "openstan")
  - Without explicit handler attachment, library logs propagate to Python's root
    logger (which has no handlers) and are silently dropped
  - Attach handlers via `_add_handler_to_all_loggers()` helper
  - Remove handlers via `_remove_handler_from_all_loggers()` helper
  - This applies to ALL context switches (app ↔ project logs)
- Log format: `%(asctime)s | %(levelname)-8s | %(name)s | %(message)s`
- No handlers configured in library; all file/stream setup in this module
- Platform paths:
  - Linux: `~/.local/share/openstan/application.log`
  - macOS: `~/Library/Application Support/openstan/application.log`
  - Windows: `%APPDATA%\openstan\application.log`
- Use `pathlib.Path` for all path operations
- Use `logging.handlers.RotatingFileHandler` for rotation
- Resource Leak Prevention: Remove existing handlers during re-initialization to
  prevent file handles from staying open if `initialize()` is called multiple times

**PR Title:** `feat: implement logging_manager for centralized log orchestration`

---

#### **Part A.2: Create `src/openstan/dialogs/log_viewer_dialog.py`**

**Objective:** Read-only modal dialog to display logs with privacy warnings.

**Deliverables:**
- [ ] Inherit from `StanDialog` with `make_scrollable()`
- [ ] Privacy warning banner at top (markdown enabled)
- [ ] Current log file path display
- [ ] Load up to 500 lines from log file (most recent lines)
- [ ] Show "Showing last 500 lines..." notice if file truncated
- [ ] Refresh button (reload from disk)
- [ ] Copy button (copy all displayed text to clipboard)
- [ ] Close button (dismiss dialog)
- [ ] Read-only QPlainTextEdit for log display

**Class Structure:**
```python
class LogViewerDialog(StanDialog):
    def __init__(self, parent=None) -> None:
        # Set up scrollable layout
        # Create widgets: privacy banner, file path label, log display, buttons
        
    def show_log(self, log_path: Path) -> None:
        # Load log file (last 500 lines)
        # Update file path label
        # Show truncation notice if needed
        
    def on_refresh(self) -> None:
        # Reload from disk
        
    def on_copy(self) -> None:
        # Copy QPlainTextEdit contents to clipboard
```

**Implementation Notes:**
- Privacy warning (markdown): "This log may contain sensitive bank account information. Be cautious when sharing with others."
- Use `StanLabel` for privacy banner with markdown enabled
- Use `QPlainTextEdit` (read-only: `setReadOnly(True)`)
- Use `StanButton` for Refresh/Copy/Close (min_width=200)
- Load last 500 lines efficiently: read file backwards or use seek/tail logic
- If file is larger than 500 lines, prepend notice: "⚠ Showing last 500 lines (file is larger)"

**PR Title:** `feat: implement log_viewer_dialog for viewing logs with privacy warnings`

---

### Part B: Admin UI Extensions

#### **Part B.1: Update `src/openstan/views/admin_view.py`**

**Objective:** Add "View Logs" and "Logging Settings" sections to admin dialog.

**Deliverables:**
- [ ] Add "View Logs" section:
  - `view_app_log_button: StanButton` — "View Application Log"
  - `view_project_log_button: StanButton` — "View Project Log"
- [ ] Add "Logging Settings" section:
  - `verbosity_checkbox: StanCheckBox` — "Enable verbose mode (DEBUG logging)"
  - `verbosity_help_icon: StanHelpIcon` — Tooltip about DEBUG diagnostics
- [ ] Use `StanForm` layout (right-aligned labels, 15px spacing)
- [ ] Maintain existing sections (User info, Data location, Help)

**Implementation Notes:**
- Buttons: min_width=200, use `StanButton`
- Checkbox: use `StanCheckBox`, unchecked = "normal", checked = "verbose"
- Help icon: tooltip text: "Enable DEBUG logging for detailed diagnostics (slower, verbose logs). Disabling reduces noise."
- Don't wire signals here (presenter handles all logic)
- Export button/checkbox references so presenter can access them

**PR Title:** `feat: add logging UI sections to admin_view (View Logs, Logging Settings)`

---

#### **Part B.2: Update `src/openstan/presenters/admin_presenter.py`**

**Objective:** Wire log viewer buttons and verbosity toggle.

**Deliverables:**
- [ ] Import LogViewerDialog and logging_manager
- [ ] In `__init__()`:
  - Wire button clicks to slots
  - Wire checkbox state change to slot
  - Load current verbosity from QSettings and set checkbox state
  - Initialize project log button state based on `self.stan.current_project_id`
- [ ] Implement 3 slot methods:
  - `view_app_log()` — Opens LogViewerDialog with app log
  - `view_project_log()` — Opens LogViewerDialog with project log (only if project selected)
  - `toggle_verbosity(state)` — Call `logging_manager.set_verbosity()`
- [ ] Add method to enable/disable project log button:
  - `update_project_log_button_state(enabled: bool)` — Called from stan_presenter on project selection change

**Implementation Notes:**
- Import: `from openstan.logging_manager import get_app_log_path, get_project_log_path, get_verbosity, set_verbosity`
- Import: `from openstan.dialogs.log_viewer_dialog import LogViewerDialog`
- In `toggle_verbosity()`, use `Qt.CheckState.Checked.value` to check state
- For `view_project_log()`, verify `self.stan.current_project_paths` is not None before proceeding
- Add docstring to `update_project_log_button_state()` for external callers

**PR Title:** `feat: wire logging controls in admin_presenter (log viewer, verbosity toggle)`

---

### Part C: Context Switching & Main App

#### **Part C.1: Update `src/openstan/presenters/stan_presenter.py`**

**Objective:** Add logging context switching on project selection.

**Deliverables:**
- [ ] In signal wiring section (~line 40-50), ensure project selection connects to handler
- [ ] In project selection handler (after `update_current_project_info()` completes):
  - Call `switch_to_project_log(self.stan.current_project_paths.root)` if project selected
  - Call `switch_to_app_log()` if no project selected
- [ ] Add method to update admin dialog project log button state:
  - `update_admin_project_log_button(enabled: bool)` — Called after project selection/deselection
  - Wire this to admin_presenter via signal or direct call

**Implementation Notes:**
- Import at top: `from openstan.logging_manager import switch_to_project_log, switch_to_app_log`
- Add import: `from openstan.presenters.admin_presenter import AdminPresenter` (already imported as TYPE_CHECKING)
- In project selection handler, after line 198 (after all project setup):
  ```python
  # Switch logging context
  if self.stan.current_project_id and self.stan.current_project_paths:
      switch_to_project_log(self.stan.current_project_paths.root)
  else:
      switch_to_app_log()
  ```
- For admin button update, store reference to admin_presenter or emit signal
- Call `admin_presenter.update_project_log_button_state(bool(self.stan.current_project_id))` if reference available

**PR Title:** `feat: add logging context switching to stan_presenter (app ↔ project)`

---

#### **Part C.2: Update `src/openstan/main.py`**

**Objective:** Initialize logging on app startup and run cleanup on closure.

**Deliverables:**
- [ ] At module top, add: `import logging` + `logger = logging.getLogger(__name__)`
- [ ] In `run()` function (before QApplication creation):
  - Import and call `initialize_logging()` from logging_manager
  - Add info log: app starting, platform, Python version
- [ ] In `Stan.__init__()` or `Stan.closeEvent()`:
  - Add cleanup call in `closeEvent()` before `super().closeEvent(event)`:
    ```python
    from openstan.logging_manager import cleanup_old_project_logs

    cleanup_old_project_logs()  # Delete project.log files >30 days old
    ```
- [ ] Replace all diagnostic `print()` calls (~15 in main.py):
  - Startup messages → `logger.info()`
  - Diagnostic details → `logger.debug()`
  - Errors → `logger.error(..., exc_info=True)` if in except block

**Implementation Notes:**
- Initialize logging BEFORE creating QApplication
- After initialization, log: `logger.info(f"openstan starting | Platform: {sys.platform} | Python: {sys.version.split()[0]}")`
- In `closeEvent()`, wrap cleanup in try/except to prevent unhandled exceptions from blocking close
- Replace `print()` calls that are internal diagnostics (not user-facing output)
- Keep any user-facing CLI output as-is

**PR Title:** `feat: initialize logging in main.py and add cleanup on app closure`

---

### Part D: Replace Print Calls

#### **Part D.1: Update `src/openstan/presenters/statement_result_presenter.py`**

**Objective:** Replace ~20 print() calls with logging.

**Deliverables:**
- [ ] At top of file: `import logging` + `logger = logging.getLogger(__name__)`
- [ ] Replace print calls:
  - Batch started/completed → `logger.info("Batch <id> started|completed")`
  - Import progress/success → `logger.info("N records imported")`
  - Parse failures → `logger.error("Failed to parse statement: <details>", exc_info=True)`
  - Unusual patterns/warnings → `logger.warning("Unusual pattern detected")`

**Implementation Notes:**
- Use `exc_info=True` for all exceptions
- Use `logger.exception()` only when already in except block (it auto-adds exc_info)
- Keep log messages concise but descriptive
- Include relevant IDs (batch_id, project_id, etc.) for traceability

**PR Title:** `refactor: replace print() calls with logging in statement_result_presenter`

---

#### **Part D.2: Update other files with print() calls**

**Objective:** Replace remaining print() calls across codebase.

**Files to update:**
- [ ] `src/openstan/presenters/user_presenter.py` (~2 print calls)
- [ ] `src/openstan/presenters/stan_presenter.py` (~1 print call)
- [ ] Model classes (TBD during execution based on grep results)

**Implementation Notes:**
- Same pattern: `import logging`, `logger = logging.getLogger(__name__)`
- Match logging level to message type (info/debug/warning/error)
- Add exc_info=True for exceptions

**PR Title:** `refactor: replace print() calls with logging across presenters and models`

---

### Part E: Verbosity Cascade

#### **Part E.1: Verify & document verbosity cascade to libraries**

**Objective:** Ensure `set_verbosity()` in logging_manager cascades to library loggers.

**Deliverables:**
- [ ] In `logging_manager.set_verbosity()`:
  - Set root logger level (openstan)
  - Set `bank_statement_parser` logger level
  - Set `uk_bank_statement_anonymiser` logger level
  - Persist to QSettings
- [ ] In `logging_manager.initialize()`:
  - Read verbosity from QSettings
  - Apply to all three loggers (openstan + libraries)
- [ ] Test in integration tests:
  - Toggle verbosity, verify all three logger levels change
  - Check that library logs respect verbosity setting

**Implementation Notes:**
- Library logger names must match their package names:
  - `logging.getLogger("bank_statement_parser")`
  - `logging.getLogger("uk_bank_statement_anonymiser")`
- Verify library code uses `logging.getLogger(__name__)` (should be from Phase 1 & 2)
- Use `logging.INFO` for "normal", `logging.DEBUG` for "verbose"

**PR Title:** `feat: cascade verbosity setting to library loggers`

---

### Part F: Documentation (Parallel to implementation)

#### **Part F.1: Create `docs/admin/logging.md`**

**Objective:** User guide for viewing and managing logs.

**Sections:**
- What logs are collected and why
- Privacy notice: "Logs may contain sensitive bank account information"
- Viewing logs:
  - App log (application-wide diagnostics)
  - Project log (project-specific operations)
- Enabling verbose mode:
  - When to use (for debugging/support)
  - Performance impact
  - How it affects library logs
- Finding log files manually:
  - File paths by platform (Linux/macOS/Windows)
  - How to navigate to log directory in file explorer
- Log retention and rotation:
  - 10 MB max file size
  - 5 backup files kept
  - 30-day project log cleanup
  - Application.log cleared on restart
- Sharing logs with support

**PR Title:** `docs: create admin/logging.md user guide`

---

#### **Part F.2: Create `docs/troubleshooting.md`**

**Objective:** Common logging-related issues and solutions.

**Sections:**
- "I don't see logs in the viewer"
  - Check file path exists
  - Enable verbose mode if needed
  - Check file permissions
- "Logs are growing too large"
  - Enable rotation (automatic)
  - Clean up old project logs
  - Disable verbose mode if not needed
- "How do I share logs with support?"
  - Open log viewer, click Copy
  - Paste into issue or email
  - Remove sensitive data if needed
- "What's the difference between app log and project log?"
  - App log: application-wide events
  - Project log: project-specific operations and library logs
- "Verbose mode is showing too much output"
  - Disable via admin Settings
  - Log output updates immediately

**PR Title:** `docs: create troubleshooting.md for logging issues`

---

#### **Part F.3: Update `AGENTS.md`**

**Objective:** Document logging patterns for contributors.

**Sections to add:**
- Logging section:
  - When to log (milestones, errors, diagnostics)
  - How to use `logging.getLogger(__name__)`
  - Level conventions:
    - DEBUG: Per-field extraction, database operations, detailed diagnostics
    - INFO: Milestones (batch started/completed, project selected, important events)
    - WARNING: Checks-and-balances failures, unusual patterns, data anomalies
    - ERROR: Parse failures, I/O errors, with `exc_info=True`
  - How verbosity affects library logs (cascading)
  - Example: "Replace a print() call with logging"

**PR Title:** `docs: update AGENTS.md with logging patterns and conventions`

---

#### **Part F.4: Update `docs/screens/admin.md`**

**Objective:** Reference new admin logging features.

**Changes:**
- Add section for "View Logs" buttons
- Add section for "Logging Settings" checkbox
- Link to `docs/admin/logging.md` for details
- Screenshot of admin dialog with new sections

**PR Title:** `docs: update admin.md to document logging UI features`

---

#### **Part F.5: Update `docs/installation.md`**

**Objective:** Add troubleshooting subsection.

**Changes:**
- Add troubleshooting subsection (after main installation steps)
- Link to `docs/troubleshooting.md`
- Include "Enable verbose mode" as diagnostic step

**PR Title:** `docs: add troubleshooting subsection to installation.md`

---

#### **Part F.6: Update `docs/CONTRIBUTING.md`**

**Objective:** Document logging standards for contributors.

**Sections to add:**
- Logging standards section:
  - Replace `print()` with `logging`
  - Use level conventions from AGENTS.md
  - Always use `logging.getLogger(__name__)`
  - Use `exc_info=True` for exception logging
  - Example code snippets

**PR Title:** `docs: add logging standards to CONTRIBUTING.md`

---

### Part G: Testing & Verification

#### **Part G.1: Create integration tests**

**Objective:** Test logging functionality end-to-end.

**File:** `tests/integration/test_logging_integration.py`

**Test Cases:**
- [ ] `test_app_log_created_on_startup()` — Verify app log exists after init
- [ ] `test_app_log_cleared_on_startup()` — Verify app log truncated on each startup
- [ ] `test_project_log_switching()` — Select project → verify logs switch to project.log
- [ ] `test_app_log_on_deselection()` — Deselect project → verify logs switch back to app.log
- [ ] `test_verbosity_toggle_updates_loggers()` — Toggle verbosity → verify all logger levels change
- [ ] `test_verbosity_cascade_to_libraries()` — Verify `bank_statement_parser` and `uk_bank_statement_anonymiser` logger levels update
- [ ] `test_log_rotation_at_boundary()` — Create 10 MB+ log → verify rotation occurs
- [ ] `test_privacy_dialog_on_viewer_open()` — Open log viewer → verify privacy banner visible
- [ ] `test_500_line_truncation()` — Load large log file → verify only last 500 lines shown with notice
- [ ] `test_30_day_cleanup_on_closure()` — Create old project.log files → close app → verify cleanup
- [ ] `test_verbosity_persists_to_qsettings()` — Toggle verbosity → restart app → verify setting persists
- [ ] `test_project_log_button_enabled_state()` — Select/deselect project → verify button state follows

**PR Title:** `test: add integration tests for logging functionality`

---

## PR Strategy

### Branch Structure
```
master
  └── logging (base branch for all Phase 3 work)
      ├── logging-phase3-partA-DEV → logging-phase3-partA-PR → logging
      ├── logging-phase3-partB-DEV → logging-phase3-partB-PR → logging
      ├── logging-phase3-partC-DEV → logging-phase3-partC-PR → logging
      ├── logging-phase3-partD-DEV → logging-phase3-partD-PR → logging
      ├── logging-phase3-partE-DEV → logging-phase3-partE-PR → logging
      ├── logging-phase3-partF-DEV → logging-phase3-partF-PR → logging
      ├── logging-phase3-partG-DEV → logging-phase3-partG-PR → logging
      └── [After all merged] logging → master (final PR)
```

### PR Workflow for Each Part
1. Create DEV branch: `git checkout -b logging-phase3-<part>-DEV logging`
2. Implement all steps in that part
3. Run all checks (lint, format, type-check, tests)
4. Create PR: `logging-phase3-<part>-DEV` → `logging`
5. Review and address feedback
6. Merge to `logging` when approved
7. Delete DEV branch

### Final Integration
After all 7 parts are merged into `logging`:
- Create single PR: `logging` → `master`
- Review all changes holistically
- Merge to master for release

---

## Execution Order (Recommended)

**Week 1:**
- Part A (Foundation): 3-4 hours
  - A.1: logging_manager.py
  - A.2: log_viewer_dialog.py
  - Create PR, review, merge

**Week 2:**
- Part B (Admin UI): 2-3 hours
  - B.1: admin_view.py
  - B.2: admin_presenter.py
  - Create PR, review, merge

- Part C (Context Switching): 2-3 hours
  - C.1: stan_presenter.py
  - C.2: main.py
  - Create PR, review, merge

**Week 3:**
- Part D (Replace Print): 1-2 hours
  - D.1: statement_result_presenter.py
  - D.2: Other files
  - Create PR, review, merge

- Part E (Cascade): 1 hour
  - E.1: Verify cascade, add tests
  - Create PR, review, merge

- Part F (Documentation): 2-3 hours (PARALLEL to Parts D-E)
  - F.1-F.6: All docs
  - Create PR, review, merge

- Part G (Integration Tests): 2-3 hours
  - G.1: Add tests
  - Create PR, review, merge

**Week 4:**
- Final PR: `logging` → `master`
  - Review all 7 PRs
  - Merge to master

---

## Success Criteria

### Code Quality
- ✅ All ruff checks pass (lint + format)
- ✅ All pyrefly type checks pass
- ✅ All pytest tests pass (100% pass rate)
- ✅ No regressions in existing functionality

### Logging Functionality
- ✅ App log created at startup, cleared on restart
- ✅ Project log created when project selected, cleared when deselected
- ✅ Logs automatically route to correct file (app ↔ project)
- ✅ Verbosity toggle applies immediately to all loggers (openstan + libraries)
- ✅ Log viewer displays up to 500 lines with truncation notice
- ✅ Privacy warning appears on every log viewer open
- ✅ Project logs >30 days old deleted on app closure (not at startup)
- ✅ Verbosity setting persists across app restarts

### UI & UX
- ✅ Admin dialog shows "View App Log" and "View Project Log" buttons
- ✅ Admin dialog shows "Enable verbose mode" checkbox with help icon
- ✅ Project log button disabled when no project selected
- ✅ Verbosity checkbox state reflects current setting
- ✅ All UI uses `Stan`-prefixed components

### Documentation
- ✅ User guide created (`docs/admin/logging.md`)
- ✅ Troubleshooting guide created (`docs/troubleshooting.md`)
- ✅ All docs have proper frontmatter with descriptions (150-160 chars)
- ✅ All docs link to related pages (3-5 internal links per doc)
- ✅ AGENTS.md updated with logging patterns
- ✅ CONTRIBUTING.md updated with logging standards
- ✅ All existing docs updated to reference logging

### Testing
- ✅ All 12+ integration tests pass
- ✅ Log rotation tested at 10 MB boundary
- ✅ Context switching tested (app → project → app)
- ✅ Verbosity cascade tested (all loggers update)
- ✅ Cleanup tested (old logs deleted)

---

## Checkpoints & Decision Points

### After Part A
- [ ] logging_manager.py working correctly?
- [ ] log_viewer_dialog.py displaying logs?
- Proceed to Part B? Yes / No / Iterate

### After Part B
- [ ] Admin UI sections visible and wired?
- [ ] Buttons and checkbox functional?
- Proceed to Part C? Yes / No / Iterate

### After Part C
- [ ] Context switching working (app ↔ project)?
- [ ] Main.py initialization working?
- Proceed to Part D? Yes / No / Iterate

### After Part D
- [ ] All print() calls replaced?
- [ ] Logs appearing in files?
- Proceed to Part E? Yes / No / Iterate

### After Part E
- [ ] Verbosity cascading to libraries?
- [ ] All loggers updating together?
- Proceed to Part F? Yes / No / Iterate

### After Part F & G
- [ ] All tests passing?
- [ ] Documentation complete and reviewed?
- Ready for final PR to master? Yes / No / Iterate

---

## Key Reminders

1. **Always work on DEV branch**, never directly on `logging`
2. **Run all checks before each PR:**
   ```bash
   uv run ruff check .
   uv run ruff format --check .
   uv run pyrefly check
   uv run pytest tests/ -v
   ```
3. **Create one PR per part** (7 PRs total before final)
4. **Review each PR before merging** (even if just self-review)
5. **Update LOGGING_PLAN_PHASE_3.md** checkboxes as you complete deliverables
6. **Document any learnings or changes** in LOGGING_PLAN.md "Learnings/Changes" section for Phase 3

---

## Questions? Issues?

If you encounter blockers or have questions while implementing a part:
1. Check the corresponding section in this document
2. Review the design decisions (locked in at top)
3. Reach out with specific part + step number for targeted help

---

**Ready to start Part A? Let me know when you want to begin, and I'll help you set up the DEV branch and start implementing!**
