# OpenStan BSP Integration - Exploration Index

## Overview

This index provides navigation to comprehensive documentation about how OpenStan integrates with the `bank_statement_parser` (BSP) library. The exploration includes statement import workflows, debugging features, file handling, and export mechanisms.

## Documentation Files

### 1. BSP_INTEGRATION_SUMMARY.md (PRIMARY REFERENCE)
**Size:** 17 KB | **Sections:** 12

Comprehensive end-to-end overview of the entire BSP integration architecture.

**Contents:**
- **Section 1:** BSP Integration Points (7 core functions)
- **Section 2:** Import & Processing Workflow (5 phases)
- **Section 3:** Statement Debugging & Analysis UI (DebugInfoDialog, ParquetViewDialog, Project Info)
- **Section 4:** Current File Handling & Export Mechanisms
- **Section 5:** Database Schema (gui.db architecture)
- **Section 6:** Worker Thread Architecture (4 worker classes)
- **Section 7:** Error Handling & Diagnostics
- **Section 8:** State Machine: Queue Lock (prevents concurrent edits)
- **Section 9:** Session Restore Path (app restart with incomplete imports)
- **Section 10:** BSP API Contracts Validated (test_bsp_contract.py)
- **Section 11:** Key Integration Patterns (4 architectural patterns)
- **Section 12:** Next Steps for Enhancement

**Use this file for:**
- Understanding the complete workflow
- Architecture decisions and rationale
- Error handling strategies
- Future enhancement ideas

### 2. BSP_KEY_FILES_REFERENCE.md (DETAILED REFERENCE)
**Size:** 14 KB | **Sections:** Organized by functionality

Detailed file-by-file breakdown with cross-dependencies and data flow diagrams.

**Contents:**
- **File Structure Overview:** Directory layout with annotations
- **Critical Files by Functionality:** 6 categories (Queue, Results, Debug, Project, Export, DB)
- **Data Flow Diagrams:** 3 text-based flowcharts
  - Import Workflow
  - Debug Info Access
  - Export Flow
- **Cross-File Dependencies:** Import/dependency analysis
- **Key Classes & Types:** All BSP and OpenStan types used
- **Worker Threads:** Details on 5 worker classes
- **Dialogs:** DebugInfoDialog, ParquetViewDialog, etc.
- **Testing Support:** Contract tests and integration tests
- **Configuration & Setup:** Environment variables and BSP config files
- **Performance Notes:** Threading, batch locking, lazy queries, soft-delete
- **Error Recovery:** Session restore, worker cancellation, JSON corruption handling

**Use this file for:**
- Finding specific files and their purposes
- Understanding dependencies between components
- Tracing data flow through the system
- Performance optimization considerations
- Error recovery procedures

## Quick Navigation

### By Topic

#### Statement Import
→ See **BSP_INTEGRATION_SUMMARY.md § 2** (5 phases)
→ See **BSP_KEY_FILES_REFERENCE.md** → Data Flow Diagrams → Import Workflow

**Key files:** statement_queue_presenter.py, statement_result_presenter.py, statement_result_model.py

#### Debug & Analysis
→ See **BSP_INTEGRATION_SUMMARY.md § 3** (UI dialogs)
→ See **BSP_KEY_FILES_REFERENCE.md** → Data Flow Diagrams → Debug Info Access

**Key files:** debug_info_dialog.py, parquet_view_dialog.py

#### Exports
→ See **BSP_INTEGRATION_SUMMARY.md § 4** (export mechanisms)
→ See **BSP_KEY_FILES_REFERENCE.md** → Data Flow Diagrams → Export Flow

**Key files:** export_data_presenter.py, advanced_export_presenter.py, workers.py

#### Database Architecture
→ See **BSP_INTEGRATION_SUMMARY.md § 5** (dual database model)
→ See **BSP_KEY_FILES_REFERENCE.md** → Performance Notes (soft-delete pattern)

**Key files:** statement_result_model.py, create_gui_db.py

#### Worker Threads
→ See **BSP_INTEGRATION_SUMMARY.md § 6** (4 worker classes)
→ See **BSP_KEY_FILES_REFERENCE.md** → Worker Threads

**Key files:** statement_queue_presenter.py, statement_result_presenter.py, workers.py

#### Session Restore
→ See **BSP_INTEGRATION_SUMMARY.md § 9** (restart with incomplete imports)
→ See **BSP_KEY_FILES_REFERENCE.md** → Error Recovery

**Key files:** statement_queue_presenter.py, statement_result_presenter.py

#### Error Handling
→ See **BSP_INTEGRATION_SUMMARY.md § 7** (exceptions and diagnostics)
→ See **BSP_KEY_FILES_REFERENCE.md** → Error Recovery

**Key files:** All presenters (error handling in workers)

#### State Machine
→ See **BSP_INTEGRATION_SUMMARY.md § 8** (queue lock state machine)

**Key files:** statement_queue_presenter.py

#### Integration Patterns
→ See **BSP_INTEGRATION_SUMMARY.md § 11** (4 architectural patterns)

**Key files:** All components

### By File

| File | Documentation | Sections |
|------|---------------|----------|
| statement_queue_presenter.py | Summary § 2.1, § 8 | Reference § 1, Data Flows |
| statement_result_presenter.py | Summary § 2.2-2.5, § 3 | Reference § 2, Data Flows |
| statement_result_model.py | Summary § 2.3 | Reference § 2, Serialization |
| debug_info_dialog.py | Summary § 3 | Reference § 3, Data Flows |
| parquet_view_dialog.py | Summary § 3 | Reference § 3 |
| project_presenter.py | Summary § 3 | Reference § 4 |
| export_data_presenter.py | Summary § 4 | Reference § 5, Data Flows |
| advanced_export_presenter.py | Summary § 4 | Reference § 5, Data Flows |
| workers.py | Summary § 6 | Reference § 5.3 |

### By Concept

| Concept | Documentation | Key Files |
|---------|---------------|-----------|
| PdfResult handling | Summary § 1, § 2.2 | statement_result_model.py, statement_result_presenter.py |
| Batch locking | Summary § 8 | statement_queue_presenter.py, statement_queue_model.py |
| Soft-delete pattern | Summary § 5, § 2.5 | statement_result_model.py, statement_result_presenter.py |
| JSON serialization | Summary § 2.3 | statement_result_model.py |
| Off-thread workers | Summary § 6 | Multiple presenters |
| Polars lazy queries | Summary § 3, § 4 | project_presenter.py, advanced_export_presenter.py |
| Session restore | Summary § 9 | statement_queue_presenter.py, statement_result_presenter.py |
| Error recovery | Summary § 7 | Multiple files, Summary § 12 |

## Key Figures & Numbers

| Item | Count | Reference |
|------|-------|-----------|
| Core BSP functions used | 7 | Summary § 1 |
| Import workflow phases | 5 | Summary § 2 |
| Worker thread classes | 4 | Summary § 6 |
| Result categories | 3 | Summary § 1, § 2.2 |
| GUI DB tables | 7 | Summary § 5 |
| Export types | 2 | Summary § 4 (standard + advanced) |
| Datamart query types | 4 | Summary § 3 |
| Integration patterns | 4 | Summary § 11 |

## Critical Concepts

### Three-Step Commit
1. `bsp.update_db()` → persist to project.db datamart
2. `bsp.copy_statements_to_project()` → copy PDF files
3. `bsp.delete_temp_files()` → cleanup

**See:** Summary § 2.5

### Soft-Delete + Hard-Delete
- **Soft delete:** UPDATE deleted=1 (immediate UI update)
- **Hard delete:** DELETE FROM ... (deferred until debug worker finishes)

**See:** Summary § 5, Reference § Performance Notes

### Queue Lock State Machine
- **UNLOCKED** → buttons enabled
- **LOCKED** → buttons disabled, import running
- **LOCKED + DONE** → View Results visible, awaiting user action
- **COMMITTED/ABANDONED** → back to UNLOCKED

**See:** Summary § 8

### Batch Metadata Flow
```
session_id, user_id, batch_id, project_path
  → bsp.process_pdf_statement()
  → PdfResult
  → gui.db statement_result + statement_result_payload
  → bsp.update_db()
  → project.db datamart
```

**See:** Summary § 11

## Testing & Validation

### Contract Tests
File: `tests/test_bsp_contract.py`

Validates:
- Function signatures (process_pdf_statement, update_db, etc.)
- Result types (Success, Review, Failure)
- Exception types (StatementError, ProjectError, TestGateFailure)
- TestHarness API

**Run:** `uv run pytest tests/test_bsp_contract.py -v`

**See:** Summary § 10, Reference § Testing Support

### Integration Tests
File: `tests/test_integration.py`

Validates:
- End-to-end import workflows
- Batch processing
- Debug generation
- Export operations

Uses BSP TestHarness with anonymised PDFs

**See:** Reference § Testing Support

## Future Enhancement Ideas

Based on current architecture, potential enhancements include:

1. **Statement Export Dialog** — Per-statement CSV/JSON export from debug view
2. **Batch History** — View/retry/export previous batches from gui.db
3. **Anonymisation** — In-app anonymisation (currently opens external dialog)
4. **Advanced Filtering** — Search/filter statements by account, date range, error type
5. **Parquet Data Export** — Export statement_lines/heads to CSV from ParquetViewDialog
6. **Diagnostic Report** — Generate HTML report of batch results
7. **API Mode** — RESTful interface for headless batch processing

**See:** Summary § 12

## Performance Notes

| Operation | Threading | Details |
|-----------|-----------|---------|
| PDF parsing | Off-thread (SQWorker) | Per-file bsp.process_pdf_statement() |
| Debug generation | Off-thread (DebugWorker) | Per-row bsp.debug_pdf_statement(), cancellable |
| Batch commit | Off-thread (CommitWorker) | 3-step BSP operation with progress bar |
| Data export | Off-thread (ExportWorker) | Generic wrapper for any export function |
| Datamart queries | Off-thread (_DatamartLoadWorker) | Polars lazy API collection |

**See:** Reference § Performance Notes

## Error Recovery Procedures

| Scenario | Recovery | Reference |
|----------|----------|-----------|
| App restart with locked batch | Load results from gui.db | Summary § 9 |
| Worker cancellation | Per-row error handling, skip | Reference § Error Recovery |
| JSON payload corruption | Skip corrupt row, continue | Reference § Error Recovery |
| Missing debug files | Graceful UI handling | Summary § 3 |

**See:** Summary § 7, § 9; Reference § Error Recovery

---

**Last Updated:** July 7, 2026

**Associated Files:**
- BSP_INTEGRATION_SUMMARY.md (17 KB)
- BSP_KEY_FILES_REFERENCE.md (14 KB)
- AGENTS.md (project architecture guide)

---

For questions or clarifications, refer to the comprehensive documentation files listed above.
