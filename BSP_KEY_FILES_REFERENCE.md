# Key Files Reference for OpenStan BSP Integration

## File Structure Overview

```
src/openstan/
├── presenters/
│   ├── statement_queue_presenter.py      # Queue management + SQWorker
│   ├── statement_result_presenter.py     # Result display + DebugWorker + CommitWorker
│   ├── project_presenter.py              # Project info (queries datamart via BSP)
│   ├── export_data_presenter.py          # Standard exports (CSV, Excel, JSON)
│   ├── advanced_export_presenter.py      # Spec-based exports
│   ├── stan_presenter.py                 # Main coordinator
│   ├── workers.py                        # ExportWorker base class
│   └── [other presenters...]
│
├── models/
│   ├── statement_queue_model.py          # Statement queue DB model (gui.db)
│   ├── statement_result_model.py         # Result models + JSON serialization
│   ├── batch_model.py                    # Batch metadata model
│   └── [other models...]
│
├── views/
│   ├── statement_queue_view.py           # Queue tree view
│   ├── statement_result_view.py          # Result tabs (SUCCESS/REVIEW/FAILURE)
│   ├── debug_info_dialog.py              # Debug info modal + file/parquet buttons
│   ├── parquet_view_dialog.py            # Parquet data viewer
│   ├── export_data_view.py               # Export panel UI
│   ├── advanced_export_view.py           # Advanced export panel UI
│   └── [other views...]
│
└── data/
    └── create_gui_db.py                  # GUI DB schema initialization
```

## Critical Files by Functionality

### 1. Statement Queue Management
- **statement_queue_presenter.py** (611 lines)
  - `SQWorker` — background thread that calls `bsp.process_pdf_statement()` per PDF
  - `StatementQueuePresenter` — handles Add/Remove/Clear UI, lock state machine
  - `WorkerSignals` — cross-thread signals for progress/completion

- **statement_queue_model.py** (283 lines)
  - `StatementQueueModel` — QSqlTableModel for statement_queue table
  - `StatementQueueTreeModel` — tree model for folder/file display
  - Queue locking: `set_batch_id()`, `clear_batch_id()`, `get_batch_id()`

### 2. Statement Result Processing
- **statement_result_presenter.py** (1012 lines)
  - `StatementResultPresenter` — result accumulation, persist, debug, commit
  - `DebugWorker` — background debug JSON generation via `bsp.debug_pdf_statement()`
  - `CommitWorker` — three-step commit: `update_db()` → `copy_statements()` → `delete_temps()`
  - `DebugWorkerSignals`, `CommitWorkerSignals` — cross-thread signals

- **statement_result_model.py** (599 lines)
  - `ResultRow` — in-memory data carrier dataclass
  - `SuccessResultModel`, `ReviewResultModel`, `FailureResultModel` — QStandardItemModel
  - `StatementResultModel` — DB persistence (display columns only)
  - `StatementResultPayloadModel` — JSON payload persistence
  - `_pdf_result_to_json()`, `_json_to_pdf_result()` — custom serialization

### 3. Debugging & Analysis UI
- **debug_info_dialog.py** (309 lines)
  - `DebugInfoDialog` — modal showing non-success statements
  - Columns: filename, type, status, JSON button, PDF button, Parquet button, Anonymise button
  - Live updates as DebugWorker progresses
  - Handles missing/stale files gracefully

- **parquet_view_dialog.py** (261 lines)
  - `ParquetViewDialog` — displays three parquet files (checks_and_balances, statement_heads, statement_lines)
  - `_TooltipPolarsModel` — custom model with cell hover tooltips
  - ID/index columns hidden, numeric columns auto-totaled
  - Uses `StanPolarsModel` for Polars DataFrame display

### 4. Project Information
- **project_presenter.py** (435 lines)
  - `get_project_info()` — queries project.db datamart via BSP Polars API
  - Collects: tx/statement/account counts, date range, per-account summary, gap report
  - Uses: `bsp.db.DimStatement()`, `bsp.db.DimAccount()`, `bsp.db.FactBalance()`, `bsp.db.GapReport()`
  - Polars lazy queries collected off-thread

### 5. Export Mechanisms
- **export_data_presenter.py** (342 lines)
  - `ExportDataPresenter` — wires standard export buttons (CSV, Excel, JSON)
  - Calls BSP default export functions off-thread via `ExportWorker`
  - Custom folder selection or BSP defaults
  - Pending batch dialog (for incomplete imports)

- **advanced_export_presenter.py** (395 lines)
  - `AdvancedExportPresenter` — custom TOML spec-based exports
  - `_DatamartLoadWorker` — loads DimAccount/DimStatement async
  - Scans `<project>/config/export/*.toml` for spec buttons
  - Calls `bsp_export_spec()` with user-selected filters

- **workers.py** (56 lines)
  - `ExportWorker` — generic background export runner
  - `ExportWorkerSignals` — finished(description, folder) | error(traceback)
  - Used by both export_data and advanced_export presenters

### 6. Database Schema
- **create_gui_db.py**
  - Initializes gui.db schema (separate from project.db datamart)
  - Tables: statement_queue, statement_result, statement_result_payload, batch, session, user, project

---

## Data Flow Diagrams

### Import Workflow
```
User selects PDFs
    ↓
StatementQueuePresenter.open_folder_dialog() / open_file_dialog()
    ↓
StatementQueueModel.add_record() → gui.db statement_queue
    ↓
User clicks "Run Import"
    ↓
StatementQueuePresenter.run_import()
    → SQWorker thread spawned
    → For each PDF:
       - bsp.process_pdf_statement(pdf, batch_id, ...) → PdfResult
       - signals.progress.emit(Path, progress%, PdfResult, queue_id)
    ↓
StanPresenter.statement_imported() ← receives from SQWorker
    ↓
StatementResultPresenter.add_result_to_memory(ResultRow)
    → Routes to SuccessResultModel, ReviewResultModel, or FailureResultModel
    → Displayed in StatementResultView (three tabs, one per category)
    ↓
SQWorker finished
    ↓
StanPresenter.on_import_finished()
    ↓
StatementResultPresenter.persist_batch_to_db(batch_id)
    → Iterates in-memory models
    → StatementResultModel.add_result() → gui.db statement_result
    → StatementResultPayloadModel.add_payload() → gui.db payload (JSON serialization)
    ↓
DebugWorker starts (auto)
    → For each non-success row:
       - bsp.debug_pdf_statement(pdf, batch_id, ...) → debug JSON path
       - signals.entry_done.emit(result_id, debug_json_path)
       - StatementResultModel.update_debug_info(result_id, status, path)
    ↓
User clicks "Commit Batch"
    ↓
StatementResultPresenter.__on_commit_batch()
    → CommitWorker thread spawned
    ↓
CommitWorker.run()
    1. bsp.update_db(processed_pdfs, ...) → persists to project.db datamart
    2. bsp.copy_statements_to_project() → copies PDF files
    3. bsp.delete_temp_files() → cleans temp files
    ↓
CommitWorker finished successfully
    ↓
StatementResultPresenter.__on_commit_finished()
    → StatementResultPayloadModel.delete_payloads_for_results() (no longer needed)
    → StatementResultModel.soft_delete_batch() (deleted=1)
    → StatementResultModel.hard_delete_soft_deleted() (when debug worker finishes)
    → StatementQueueModel.clear_batch_id() → unlock queue
    → Queue state: UNLOCKED (ready for next import)
```

### Debug Info Access
```
User clicks "View Debug Info"
    ↓
StatementResultPresenter.__on_view_debug_info()
    ↓
DebugInfoDialog initialized with non-success rows
    ↓
Per row, buttons available:
    "Debug JSON" → Click → Open debug_json_path in browser (if exists)
    "PDF" → Click → QDesktopServices.openUrl(file_path)
    "Parquet" (REVIEW only) → Click → ParquetViewDialog(row.pdf_result)
    "Anonymise" → Click → AnonymiseDialog(pdf_path)
    ↓
ParquetViewDialog.display():
    1. Read parquet files: checks_and_balances, statement_heads, statement_lines
    2. Drop ID/index columns (_drop_id_cols)
    3. statement_lines: show totals row + scrollable data table
    4. Display in StanTableView (tooltips on hover)
```

### Export Flow
```
Standard Export (CSV/Excel/JSON):
    User clicks button (button_csv, button_excel, button_json)
    ↓
    ExportDataPresenter._on_csv() / ._on_excel() / ._on_json()
    ↓
    ExportWorker(fn=bsp.export_csv, description="CSV", output_folder)
    ↓
    ExportWorker.run() off-thread
    ↓
    signals.finished.emit(description, output_folder)
    ↓
    QDesktopServices.openUrl(output_folder)
    
---

Advanced Export (Spec):
    User selects account/statement filters
    ↓
    User clicks spec button
    ↓
    AdvancedExportPresenter._on_spec_button()
    ↓
    ExportWorker(fn=partial(bsp_export_spec, ...), description=spec_name, output_folder)
    ↓
    ExportWorker.run() off-thread
    ↓
    signals.finished.emit(description, output_folder)
    ↓
    QDesktopServices.openUrl(output_folder)
```

---

## Cross-File Dependencies

### statement_result_presenter.py depends on:
- `statement_result_model.py` — ResultRow, SuccessResultModel, ReviewResultModel, FailureResultModel, StatementResultModel, StatementResultPayloadModel
- `statement_queue_model.py` — StatementQueueModel (for queue unlock after commit)
- `batch_model.py` — BatchModel (for duration)
- `debug_info_dialog.py` — DebugInfoDialog (view debug JSON/PDF/Parquet)
- `bsp` — process_pdf_statement (via worker), update_db, copy_statements_to_project, delete_temp_files, debug_pdf_statement

### statement_queue_presenter.py depends on:
- `statement_queue_model.py` — StatementQueueModel, StatementQueueTreeModel
- `bsp` — process_pdf_statement (in SQWorker)

### project_presenter.py depends on:
- `bsp` — db.DimStatement, db.DimAccount, db.FactBalance, db.GapReport

### debug_info_dialog.py depends on:
- `statement_result_model.py` — ResultRow
- `parquet_view_dialog.py` — ParquetViewDialog (when "View Parquet" clicked)
- `anonymise_dialog.py` — AnonymiseDialog (when "Anonymise" clicked)

### parquet_view_dialog.py depends on:
- Polars — pl.read_parquet, DataFrame operations
- Components — StanTableView, StanPolarsModel, StanDialog, StanLabel

---

## Key Classes & Types

### From BSP (imported as `import bank_statement_parser as bsp`)
```python
bsp.PdfResult
bsp.process_pdf_statement()
bsp.update_db()
bsp.copy_statements_to_project()
bsp.delete_temp_files()
bsp.debug_pdf_statement()
bsp.ProjectPaths.resolve()
bsp.db.DimStatement()
bsp.db.DimAccount()
bsp.db.FactTransaction()
bsp.db.FactBalance()
bsp.db.GapReport()
```

### From openstan.models.statement_result_model
```python
ResultRow
SuccessResultModel
ReviewResultModel
FailureResultModel
StatementResultModel
StatementResultPayloadModel
_pdf_result_to_json()
_json_to_pdf_result()
```

### From openstan.models.statement_queue_model
```python
StatementQueueModel
StatementQueueTreeModel
_safe_hex_id()
```

### Worker Threads
```python
SQWorker(statement_queue_presenter.py)
DebugWorker(statement_result_presenter.py)
CommitWorker(statement_result_presenter.py)
ExportWorker(workers.py)
_DatamartLoadWorker(advanced_export_presenter.py)
```

### Dialogs
```python
DebugInfoDialog (debug_info_dialog.py)
ParquetViewDialog (parquet_view_dialog.py)
AnonymiseDialog (anonymise_dialog.py, external to this summary)
PendingBatchDialog (pending_batch_dialog.py, for incomplete batch recovery)
```

---

## Testing Support

### Contract Tests (test_bsp_contract.py)
- Validates BSP function signatures and result types
- Catches breaking changes early
- Run with: `uv run pytest tests/test_bsp_contract.py -v`

### Integration Tests (test_integration.py)
- Full end-to-end import workflows
- Uses BSP TestHarness with anonymised PDFs
- Validates batch processing, debug generation, export

---

## Configuration & Setup

### Environment Variables (set in __main__.py before BSP import)
```python
os.environ["BSP_PROJECT_ROOT"] = <resolved_project_path>
```

### BSP Configuration Files
- Located in: `<bsp_package>/project/` (bundled in frozen build)
- Copied to: `<user_project_root>/project/` on first run
- Contains: TOML configs, templates, data definitions

---

## Performance Notes

1. **Off-Thread Workers**: All heavy operations run off-thread to keep GUI responsive
   - SQWorker: PDF parsing
   - DebugWorker: Debug JSON generation
   - CommitWorker: DB updates + file copy
   - ExportWorker: Export operations
   - _DatamartLoadWorker: Polars lazy evaluation

2. **Batch Locking**: Queue is locked during import to prevent concurrent edits
   - Batch_id stamped on all queue rows
   - State machine prevents user actions while locked

3. **Lazy Polars Queries**: Project info queries use Polars lazy API
   - Off-thread execution
   - Single .collect() call per query

4. **Soft-Delete Pattern**: Results cleared immediately after commit
   - Soft delete: UI updates instantly
   - Hard delete: deferred until debug worker finishes

---

## Error Recovery

1. **Session Restore**: On app restart with locked batch
   - `_restore_lock_state()` checks gui.db for active batch_id
   - Results loaded from `statement_result` table
   - Debug status restored from `debug_json_path` / `debug_status` columns

2. **Worker Cancellation**: Debug worker can be cancelled
   - Threading.Event set on project change or app exit
   - Per-row error handling (skip failed entries)

3. **Payload Deserialization Errors**: JSON corruption handled gracefully
   - Per-row try/catch in `load_payloads_for_batch()`
   - Corrupt rows logged and skipped
   - Session restore continues

