# OpenStan: Bank Statement Parser (BSP) Integration Summary

## Overview

OpenStan is a Python/PySide6 desktop application for bank statement analysis. It tightly integrates with the `bank_statement_parser` (BSP) library to process PDF bank statements, analyze them, and persist results to a data mart (project.db).

## 1. BSP Integration Points

### Core Functions Used
The application calls these BSP functions throughout the import/processing lifecycle:

| Function | Location | Purpose |
|----------|----------|---------|
| `bsp.process_pdf_statement()` | `statement_queue_presenter.py` (worker thread) | Parse single PDF, return PdfResult |
| `bsp.update_db()` | `statement_result_presenter.py` (commit worker) | Persist parsed statements to project.db datamart |
| `bsp.copy_statements_to_project()` | `statement_result_presenter.py` (commit worker) | Copy statement files to project structure |
| `bsp.delete_temp_files()` | `statement_result_presenter.py` (commit worker) | Clean up temporary working files |
| `bsp.debug_pdf_statement()` | `statement_result_presenter.py` (debug worker) | Generate debug JSON for failed/review statements |
| `bsp.db.DimStatement()`, `bsp.db.DimAccount()`, etc. | `project_presenter.py`, `advanced_export_presenter.py` | Query datamart tables (via Polars API) |
| `bsp.ProjectPaths.resolve()` | Multiple files | Resolve project root path and settings |

### Result Types Handled
The application processes three result types returned by `bsp.process_pdf_statement()`:

```python
from bank_statement_parser.modules.statements import PdfResult, Success, Review, Failure
```

**PdfResult** structure:
- `result`: Literal["SUCCESS", "REVIEW", "FAILURE"]
- `outcome`: Status indicator
- `batch_lines`: Path to batch processing file
- `checks_and_balances`: Path to validation file (if applicable)
- `payload`: Union[Success, Review, Failure]

**Success** payload:
- `statement_info`: Account/date/amount data
- `parquet_files`: Paths to SUCCESS parquet files (statement_heads, statement_lines)

**Review** payload:
- `statement_info`: Same as Success
- `parquet_files`: Same as Success
- `message`: Issue description
- `message_detail`: Extended explanation

**Failure** payload:
- `message`: Error message
- `error_type`: Category (parsing error, validation failure, etc.)
- `message_detail`: Extended traceback/details

---

## 2. Import & Processing Workflow

### Phase 1: Queue Management
**Location:** `src/openstan/presenters/statement_queue_presenter.py`

```
User adds PDFs to queue
    ↓
Queue rows stored in gui.db (statement_queue table)
    ↓
User clicks "Run Import"
    ↓
SQWorker thread spawned (calls bsp.process_pdf_statement per PDF)
    ↓
Signals emitted: statement_imported(Path, PdfResult, progress%, queue_id)
```

**Key Model:** `StatementQueueModel` (QSqlTableModel)
- Manages `statement_queue` table in gui.db
- Rows include: `queue_id`, `path`, `is_folder`, `batch_id`, `session_id`, `project_id`
- Methods: `add_record()`, `delete_records()`, `set_batch_id()` (lock for batch), `clear_batch_id()` (unlock)

### Phase 2: In-Memory Result Accumulation
**Location:** `src/openstan/models/statement_result_model.py`

During the import worker loop, each `PdfResult` is:

1. Converted to a `ResultRow` dataclass:
   ```python
   @dataclass
   class ResultRow:
       result_id: str
       batch_id: str
       queue_id: str
       project_id: str
       result: str  # "SUCCESS" | "REVIEW" | "FAILURE"
       file_path: Path
       id_account: str | None
       statement_date: str | None
       payments_in: float | None
       payments_out: float | None
       error_type: str | None
       message: str | None
       pdf_result: PdfResult | None  # the raw result
   ```

2. Added to one of three in-memory models:
   - `SuccessResultModel` (QStandardItemModel)
   - `ReviewResultModel` (QStandardItemModel)
   - `FailureResultModel` (QStandardItemModel)

3. Displayed in the Statement Results View (three tabs)

**Key Signal:** `StanPresenter.statement_imported` → `StatementResultPresenter.add_result_to_memory()`

### Phase 3: Persist to GUI DB
**Location:** `src/openstan/presenters/statement_result_presenter.py::persist_batch_to_db()`

When import finishes, all in-memory rows are written once to gui.db:

- **statement_result** table: Display columns (file_path, result, account, date, amounts, error_type, message)
- **statement_result_payload** table: JSON serialization of the `PdfResult` object (for REVIEW/SUCCESS rows only)

**JSON Serialization** (`statement_result_model.py`):
- Custom serializer handles non-JSON types: `Path` → POSIX string, `Decimal` → string, `date` → ISO-8601
- Includes `_type` discriminator so deserializer knows the payload class (Success/Review/Failure)
- Deserialization gracefully skips corrupt rows

### Phase 4: Debug Generation (Background)
**Location:** `src/openstan/presenters/statement_result_presenter.py::DebugWorker`

After persist completes, for each non-success row:
1. Calls `bsp.debug_pdf_statement()` off-thread
2. Returns path to debug JSON file
3. Updates `statement_result.debug_json_path` and `debug_status` in gui.db
4. Updates `DebugInfoDialog` live with progress

**Cancel Support:** User can cancel debug worker during project switch or app exit

### Phase 5: Commit to Project DB
**Location:** `src/openstan/presenters/statement_result_presenter.py::CommitWorker`

Three-step batch operation:

```
1. bsp.update_db(processed_pdfs, batch_id, session_id, user_id, path, ...)
   → Persists to project.db datamart (statements, accounts, transactions, balances)
   
2. bsp.copy_statements_to_project(processed_pdfs, pdfs, project_path)
   → Copies PDF files to project structure
   
3. bsp.delete_temp_files(processed_pdfs, project_path)
   → Cleans up temporary working files
```

On success:
- Soft-delete result rows from gui.db (so results panel clears immediately)
- Hard-delete after debug worker finishes
- Clear queue batch lock (unlock for next import)

---

## 3. Statement Debugging & Analysis UI

### DebugInfoDialog
**Location:** `src/openstan/views/debug_info_dialog.py`

Modal dialog opened by "View Debug Info" button. Shows all REVIEW and FAILURE rows.

**Columns:**
- Statement (filename)
- Type (REVIEW | FAILURE)
- Debug Status (pending → done | error)
- Debug JSON button (opens JSON file in browser when done)
- PDF button (opens original PDF)
- Parquet button (REVIEW rows only — opens ParquetViewDialog)
- Anonymise button (if project_paths available)
- Message (error text)

**Live Updates:** Rows update as DebugWorker completes each entry

### ParquetViewDialog
**Location:** `src/openstan/views/parquet_view_dialog.py`

Displays parquet data from REVIEW statements:
- **checks_and_balances** — validation results (single-row table)
- **statement_heads** — statement summary (single-row table)
- **statement_lines** — transactions detail + totals row

**Features:**
- Columns auto-sized, user-resizable
- ID_* and index columns hidden
- Full value shown on cell hover (tooltip)
- Uses `StanPolarsModel` to display Polars DataFrames
- Handles missing files gracefully

### Project Info View
**Location:** `src/openstan/presenters/project_presenter.py::get_project_info()`

When project is selected, queries the datamart (project.db) via BSP's Polars API:

**Data Displayed:**
- Transaction count
- Statement count
- Account count
- Date range (earliest → latest statement)
- Per-account summary (statements, date range, totals in/out, latest balance)
- Gap report (missing statements between dates)

Uses Polars lazy queries: `bsp.db.DimStatement()`, `bsp.db.DimAccount()`, `bsp.db.FactTransaction()`, etc.

---

## 4. Current File Handling & Export Mechanisms

### Statement Queue File Management
**Add Statements:**
- Single files: User selects via file dialog
- Folders: User selects root folder, app discovers PDFs recursively, groups by parent directory
- Drag & drop: PDFs and folders can be dropped onto the queue tree view
- Tree state persisted: Expanded/collapsed folders remembered across refresh

**Remove Statements:**
- Individual: Click remove button (requires multi-parent FK support)
- All: Clear all items (with confirmation)

### Debug Output Files
**Generated by BSP:**
- **debug_json_path** → `<project>/log/debug/<batch_id>/<result_id>.json`
  - Contains parsed PDF structure, validation failures, error details
  - Human-readable JSON format
  - Persisted in `statement_result.debug_json_path` in gui.db

**User Access:**
- Click "Debug JSON" button in DebugInfoDialog → opens in browser
- Click "PDF" button → opens original PDF in system viewer
- Click "View Parquet" (REVIEW only) → opens ParquetViewDialog with parquet tables

### Export Functions
**Location:** `src/openstan/presenters/export_data_presenter.py` + `advanced_export_presenter.py`

**Standard Exports** (via BSP default export functions):
- CSV (single file)
- Excel workbook
- JSON file

**Advanced Exports** (via BSP `export_spec`):
- Custom TOML specifications in `<project>/config/export/`
- Scanned and built into spec button list
- User selects account/statement filters
- Runs `bsp_export_spec()` off-thread

**Features:**
- Browse custom folder or use BSP defaults
- Exports run on background thread (GUI stays responsive)
- System file manager opens output folder on success
- Error modal on failure (shows traceback)

---

## 5. Database Schema (gui.db)

OpenStan maintains its own SQLite database (gui.db) separate from the BSP project.db datamart.

**Key Tables:**

| Table | Purpose |
|-------|---------|
| `statement_queue` | PDFs queued for import; locked by batch_id during processing |
| `statement_result` | Display columns from parsed statements (file, result type, account, date, amounts) |
| `statement_result_payload` | JSON serialization of PdfResult (for REVIEW/SUCCESS only) |
| `batch` | Metadata: batch_id, session_id, PDF count, error/review counts, processing duration, timestamp |
| `session` | User session info |
| `user` | User credentials |
| `project` | Project names and paths |

**Soft Delete Pattern:**
- After commit, result rows are marked `deleted=1` (soft delete)
- Results panel clears immediately
- Hard delete (`DELETE FROM statement_result WHERE deleted=1`) happens after debug worker finishes
- Prevents orphaned rows if debug worker is cancelled

---

## 6. Worker Thread Architecture

### SQWorker (Statement Queue Worker)
**Purpose:** Import PDFs in background

```python
class SQWorker(QRunnable):
    def run(self):
        for file in queue:
            pdf_result = bsp.process_pdf_statement(pdf, batch_id, ...)
            signals.progress.emit(file_path, progress_pc, pdf_result, queue_id)
```

**Signals:**
- `progress(Path, int, PdfResult, str)` — emitted per file
- `finished()` — all files processed

### DebugWorker
**Purpose:** Generate debug JSON files for non-success rows

```python
class DebugWorker(QRunnable):
    def run(self):
        for row in non_success_rows:
            debug_json = bsp.debug_pdf_statement(pdf, batch_id, ...)
            signals.entry_done.emit(result_id, debug_json_path)
```

**Features:**
- Cancellable via `threading.Event`
- Graceful error handling per row
- Skips failed entries (doesn't abort entire batch)

### CommitWorker
**Purpose:** Persist batch to project.db (three-step BSP operation)

```python
class CommitWorker(QRunnable):
    def run(self):
        bsp.update_db(processed_pdfs, ...)      # Persist to datamart
        bsp.copy_statements_to_project(...)     # Copy PDFs
        bsp.delete_temp_files(...)              # Clean up
```

**Signals:**
- `step(str)` — step description (for progress bar)
- `finished()` — all three calls succeeded
- `error(str)` — operation failed

### ExportWorker
**Purpose:** Run BSP export functions off-thread

```python
class ExportWorker(QRunnable):
    def __init__(self, fn: Callable, description: str, output_folder: Path):
        self._fn = fn
    
    def run(self):
        try:
            self._fn()
            signals.finished.emit(description, str(output_folder))
        except Exception:
            signals.error.emit(traceback.format_exc())
```

---

## 7. Error Handling & Diagnostics

### Exception Types
Caught from BSP:
- `bsp.StatementError` — Statement-level parsing failures
- `bsp.ProjectError` — Project initialization failures
- `bsp.modules.errors.TestGateFailure` — Validation failures (checks & balances)

**Handling Pattern:**
```python
try:
    result = bsp.process_pdf_statement(pdf, ...)
except sqlite3.OperationalError, bsp.StatementError:
    # Datamart not ready or statement parse failed
    # Gracefully skip and continue
except Exception as e:
    traceback.print_exc(file=sys.stderr)
    # Show error dialog to user
```

### Debug Output
- **stderr**: Worker exceptions printed for development
- **GUI dialogs**: User-facing errors via `StanErrorMessage` modal
- **Debug JSON**: Machine-readable parse tree + validation details
- **Project log**: `<project>/log/debug/<batch_id>/<result_id>.json`

---

## 8. State Machine: Queue Lock

The statement queue uses a batch_id-based lock system to prevent user modification during import:

```
UNLOCKED (batch_id = NULL):
    - Add/Remove/Clear buttons enabled
    - Run Import enabled (if queue has rows)
    - View Results hidden
    
LOCKED (batch_id = '<uuid>'):
    - Modification buttons disabled
    - Run Import disabled
    - Locked label visible
    - View Results hidden (import still running)
    
LOCKED + IMPORT DONE:
    - Modification buttons disabled
    - Run Import disabled
    - Locked label visible
    - View Results visible (user can view/commit/abandon)
    
COMMITTED or ABANDONED:
    - Queue unlocked (batch_id cleared)
    - Returns to UNLOCKED state
```

---

## 9. Session Restore Path

When user switches projects with a locked batch (incomplete import):

```
1. StanPresenter.update_current_project_info() called
   ↓
2. StatementQueuePresenter._restore_lock_state()
   → Queries gui.db for batch_id
   → If found, applies LOCKED state (shows View Results button)
   ↓
3. StatementResultPresenter.load_results_from_db(batch_id)
   → Reads statement_result rows for this batch
   → Populates in-memory models (without PdfResult payloads)
   → Results panel shown with previous import state
   ↓
4. DebugWorker may already be running
   → Dialog shows current progress
   → Worker can be cancelled
```

---

## 10. BSP API Contracts Validated

**Location:** `tests/test_bsp_contract.py`

Automated tests ensure:
- Function signatures haven't changed (`process_pdf_statement`, `update_db`, etc.)
- Result types exist and have required fields (Success, Review, Failure)
- Exception types are importable and correct
- TestHarness API works as expected

**Run tests:**
```bash
uv run pytest tests/test_bsp_contract.py -v
```

---

## 11. Key Integration Patterns

### Pattern 1: Batch Metadata Flow
```
session_id, user_id, batch_id, project_path
    ↓
bsp.process_pdf_statement(pdf, batch_id=batch_id, session_id=session_id, ...)
    ↓
Returned in PdfResult, passed to bsp.update_db()
    ↓
Persisted to gui.db + project.db for audit trail
```

### Pattern 2: Path Handling
- Input PDFs: User provides absolute paths
- Project paths: Resolved via `bsp.ProjectPaths.resolve()`
- Output files: `<project>/log/debug/<batch_id>/`, `<project>/statements/`
- Temp files: Managed by BSP, deleted after commit

### Pattern 3: Polars Integration
- Datamart tables accessed via lazy Polars API
- Queries run off-thread to prevent UI blocking
- DataFrames converted to `StanPolarsModel` for display
- Column hiding, sorting, filtering handled by view

### Pattern 4: Soft-Delete + Hard-Delete
- Soft delete: `UPDATE ... SET deleted=1` (UI clears immediately)
- Background work continues (debug worker)
- Hard delete: `DELETE FROM ...` (when background work done)
- Prevents orphaned rows from hung workers

---

## 12. Next Steps for Enhancement

Based on current architecture, potential enhancements could include:

1. **Statement Export Dialog** — Per-statement CSV/JSON export from debug view
2. **Batch History** — View/retry/export previous batches from gui.db
3. **Anonymisation** — In-app anonymisation (currently opens external dialog)
4. **Advanced Filtering** — Search/filter statements by account, date range, error type
5. **Parquet Data Export** — Export statement_lines/heads to CSV from ParquetViewDialog
6. **Diagnostic Report** — Generate HTML report of batch results
7. **API Mode** — RESTful interface for headless batch processing

