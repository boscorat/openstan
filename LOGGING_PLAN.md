# Logging Implementation Plan — Issue #230

## Overview

Implement a unified, centralized logging infrastructure across all three projects:

1. **bank_statement_parser** — Python `logging` module + RotatingFileHandler
2. **uk-bank-statement-anonymiser** — Python `logging` module + RotatingFileHandler
3. **openstan** — Consume logs, route intelligently, provide UI viewers with privacy warnings

## Phases

### Phase 1: bank_statement_parser Logging

**Status:** ✅ COMPLETED

**Worktree:** `/Users/boscorat/repos/bank_statement_parser-logging`

**Objective:** Implement logging infrastructure in bank_statement_parser

**Deliverables:**
- ✅ `src/bank_statement_parser/modules/logging_config.py` — Logger factory and configuration
- ✅ Replace `print()` calls in `statements.py`, `debug.py`, `database.py` with logging
- ✅ Export `get_logger` from `__init__.py`
- ⏳ Update `AGENTS.md` with logging documentation
- ⏳ Create `docs/guides/debugging.md` — Debug mode usage guide
- ⏳ Create `docs/guides/troubleshooting.md` — Common issues

**What Was Done:**
1. Created `logging_config.py` with `get_logger()` factory function
   - Supports "normal" (INFO) and "verbose" (DEBUG) verbosity levels
   - Module-level caching of logger instances
   - Designed for consuming applications to configure handlers

2. Replaced all `print()` calls with logging:
   - `statements.py`: 8 print() calls → logger calls (DEBUG/INFO/WARNING/ERROR levels)
   - `debug.py`: 2 print() calls → logger calls
   - `database.py`: 4 print() calls → logger calls (DEBUG level for migrations, ERROR for failures)

3. Exported `get_logger` from `__init__.py` for public API access

4. All syntax tests pass (30/30)

**Key Decisions & Learnings:**
- Logging is DEBUG-level for diagnostic details (migrations, field extraction)
- INFO level for process milestones (batch started/completed, opening balance corrected)
- WARNING level for non-fatal anomalies (checks-and-balances failures)
- ERROR level with `exc_info=True` for failures
- No handlers configured in library; consumers (openstan) add handlers
- Removed `traceback.print_exc()` calls; using `exc_info=True` instead for full tracebacks

---

### Phase 2: uk-bank-statement-anonymiser Logging

**Status:** PENDING

**Worktree:** `/Users/boscorat/repos/uk-bank-statement-anonymiser-logging`

**Objective:** Implement logging infrastructure in uk-bank-statement-anonymiser

**Deliverables:**
- `src/uk_bank_statement_anonymiser/logging_config.py` — Logger factory
- Replace ~6 `print()` calls with logging
- Export `get_logger` from `__init__.py`
- Update `README.md` with debugging section
- Update `AGENTS.md` with logging documentation
- Create `docs/debugging.md` and `docs/troubleshooting.md`
- Optional: Create `mkdocs.yml` for future docs growth
- Unit tests

**Learnings/Changes from Phase 1:** *(To be updated)*

---

### Phase 3: openstan Logging Integration

**Status:** PENDING

**Worktree:** `/Users/boscorat/repos/openstan-logging`

**Objective:** Integrate logging across openstan and consume external library logs

**Deliverables:**
- `src/openstan/logging_manager.py` — Core orchestrator for context-aware routing
- `src/openstan/dialogs/log_viewer_dialog.py` — Read-only log viewer with privacy warning
- Update `src/openstan/main.py` to initialize logging and subscribe to project changes
- Update `src/openstan/views/admin_view.py` with 2 new sections (View App Log, View Project Log)
- Update `src/openstan/presenters/admin_presenter.py` with log viewer slots
- Replace `print()` calls in presenters/models with logging
- Update `AGENTS.md` with logging patterns
- Create comprehensive user documentation:
  - `docs/admin/logging.md` — User guide to logs
  - `docs/troubleshooting.md` — Common issues
  - Update `docs/screens/admin.md` to reference logs
  - Update `docs/installation.md` with troubleshooting subsection
  - Update `docs/CONTRIBUTING.md` with logging standards
- Integration tests and link verification

**Learnings/Changes from Phase 1 & 2:** *(To be updated)*

---

### Phase 4: Integration Tests & Documentation Verification

**Status:** PENDING

**Objective:** Full integration testing across all three projects

**Deliverables:**
- End-to-end tests: app log → project log switching
- Log rotation tests (10 MB boundary)
- Privacy warning dialog tests
- Documentation link integrity verification
- SEO compliance checks (openstan only)
- Release preparation

**Learnings/Changes from Phase 1-3:** *(To be updated)*

---

## Log File Specifications

### Locations

| Log Type | Path | Notes |
|----------|------|-------|
| Application log | `~/.local/share/openstan/application.log` (Linux)<br>`~/Library/Application Support/openstan/application.log` (macOS)<br>`%APPDATA%\openstan\application.log` (Windows) | Created on first app startup |
| Project log | `<project_root>/project.log` | Created when project is selected |

### Rotation

- **Max file size:** 10 MB
- **Backup count:** 5 (keeps `project.log.1` through `project.log.5`)
- **Strategy:** `RotatingFileHandler(maxBytes=10485760, backupCount=5)`

### Log Format

```
%(asctime)s | %(levelname)-8s | %(name)s | %(message)s
```

Example:
```
2026-09-26 14:23:45,123 | INFO     | openstan.presenters.stan_presenter | Project 'My Budget' selected
```

### Verbosity Levels

- **Normal** (default): INFO, WARNING, ERROR, CRITICAL
- **Verbose**: DEBUG, INFO, WARNING, ERROR, CRITICAL

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Python `logging` module** | Standard, extensible, well-documented |
| **No forced handlers in libraries** | Gives flexibility to CLI vs. GUI consumers |
| **10 MB rotation + 5 backups** | Balances file growth vs. historical data retention |
| **Context-aware routing** | Real-time, no database overhead |
| **Privacy warning every time** | No "Don't show again" checkbox; always remind users |
| **Logs in project folder** | Survives project removal; users can archive with project |
| **Separate app/project logs** | Keeps app-level noise separate from project-specific issues |
| **Verbose mode optional** | Keeps normal logs clean; verbose for support/debugging |

---

## Logging Levels Reference

| Level | When to Use |
|-------|------------|
| DEBUG | Per-field extraction details, database operations, diagnostic info |
| INFO | Statement/batch started/completed, project selection, important milestones |
| WARNING | Checks-and-balances anomalies, unusual but non-fatal patterns, data anomalies |
| ERROR | Parse failures, I/O errors, import failures (always use `exc_info=True`) |

---

## Key Questions for Each Phase

### Phase 1 (bank_statement_parser)

- [ ] Should `debug.py` module's functions also log their progress, or remain silent?
- [ ] Are there other `print()` calls outside the identified modules to convert?
- [ ] Should CLI mode default to console-only logging, or file + console?
- [ ] How should the logger handle the case where `bank_statement_parser` is used as a library without consumer setup?

### Phase 2 (uk-bank-statement-anonymiser)

- [ ] Should we create `mkdocs.yml` and docs/ structure, or keep README-only for now?
- [ ] How detailed should PDF encoding/font troubleshooting guide be?
- [ ] Should anonymiser expose a `get_logger()` factory identical to bank_statement_parser?

### Phase 3 (openstan)

- [ ] Should verbosity be user-configurable via settings UI, or hardcoded to "normal"?
- [ ] Should project.log files be automatically archived/cleaned up, or manual user responsibility?
- [ ] Should the log viewer paginate large files, or load all 500 lines at once?
- [ ] Should application.log be cleared on app restart, or persist indefinitely?

---

## Notes & Learnings

*(Updated as we progress through phases)*

---

## Timeline

- **Phase 1:** 2 days
- **Phase 2:** 1 day
- **Phase 3:** 2-3 days
- **Phase 4:** 1 day

**Total:** ~1.5 weeks (code + documentation)

---

## Related Issues

- Issue #230: logging: std_out logged to file
- Issue #[tbd]: Release bank_statement_parser v0.5.0 with logging
- Issue #[tbd]: Release uk-bank-statement-anonymiser v1.1.0 with logging
