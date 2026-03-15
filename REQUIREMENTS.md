# Requirements

> **Living document.** Update this file in the same commit as any code change that adds,
> removes, or alters a feature. All development must align with an accepted entry here.
> Architectural constraints that govern *where* development belongs are captured in
> [DECISIONS.md](DECISIONS.md) — consult it before starting any new feature.

---

## 1. Project Management

Users must be able to create and manage bank-statement analysis projects. A project maps to a
folder on disk that is scaffolded and validated by `bank_statement_parser`.

### User Stories

- **PM-1** As a user, I want to create a new named project in a location I choose, so that I
  have a dedicated folder for a set of bank statements.
- **PM-2** As a user, I want to register an existing project folder that was previously created
  (e.g. on another machine or via the CLI), so that I can continue working with it in the UI.
- **PM-3** As a user, I want to switch between projects using a drop-down, so that I can manage
  multiple accounts or time periods independently.
- **PM-4** As a user, I want to remove a project from the UI without deleting it from disk, so
  that I can declutter the list without losing data.
- **PM-5** As a user, I want to permanently delete a project including its folder from disk, so
  that I can clean up projects I no longer need.
- **PM-6** As a user, I want to see a summary of the selected project's contents (transaction
  count, statement count, and account count) displayed beneath the project selector, so that I
  can assess the scope of a project at a glance without opening any views.
- **PM-7** As a user, I want to select which bank config subfolders to include in a new project
  (and optionally source them from an existing project rather than the BSP defaults), so that
  I don't have to manually copy or delete bank-specific configuration files after creation.

### Acceptance Criteria

- A new project folder is created on disk and scaffolded via `bsp.validate_or_initialise_project()`
  before the record is written to `gui.db`.
- An existing project folder is validated via `bsp.validate_or_initialise_project()` before
  registration; invalid folders are rejected with a clear error message.
- The project drop-down reflects live `gui.db` state at all times.
- Remove-from-UI deletes only the `gui.db` record; the folder on disk is untouched.
- Delete-from-disk requires explicit user confirmation via `StanInfoMessage` before any
  destructive action is taken.
- All project mutations are recorded in `event_log` via the existing SQLite triggers.
- (PM-6) The summary label is displayed immediately below the project selector combo box and
  reads in the form `N transactions in M statements across K accounts`.
- (PM-6) Summary counts are fetched in a background thread (`ProjectSummaryWorker`) so the UI
  is never blocked; the label is cleared while the fetch is in progress.
- (PM-6) Counts are sourced exclusively from the `bsp.db` mart API (`FactTransaction`,
  `DimStatement`, `DimAccount`) — no raw SQL from `openstan` (see D001).
- (PM-6) If the data mart has not yet been built for the project (mart tables absent or all
  zero), the summary label is left blank.
- (PM-6) The summary refreshes automatically whenever the selected project changes, and again
  after a batch is committed.
- (PM-7) The New Project Wizard presents a second page ("Configure Project") after the basic
  details page, allowing the user to select which bank config subfolders to include in the
  new project and from which source.
- (PM-7) Each row of the config table represents a unique config subfolder name discovered
  across the BSP default config and all registered projects whose config folder exists on disk.
- (PM-7) Each column represents a source: "Default" (BSP bundled config) plus one column per
  registered project with an accessible config folder. Projects whose folder is absent from
  disk are silently omitted.
- (PM-7) A radio button appears in a cell only where the subfolder actually exists for that
  source. A "Skip" radio button is always available at the end of each row.
- (PM-7) The default selection is: "Default" chosen for every subfolder that exists in the
  BSP default config; "Skip" chosen for subfolders that only appear in existing projects.
- (PM-7) Selecting "Skip" for a subfolder causes openstan to delete that subfolder from the
  new project's config after BSP scaffolding completes.
- (PM-7) Selecting a non-default project for a subfolder causes openstan to replace the
  BSP-scaffolded subfolder with a copy from the chosen project, and to merge the top-level
  TOML files from that project into the new project's equivalents (see merge rules below).
- (PM-7) Selecting "Default" for a subfolder requires no post-scaffolding action; BSP has
  already placed the correct files.
- (PM-7) `account_types.toml` merge rule: any top-level key present in the source project's
  file but absent from the new project's file is appended. Existing keys are never overwritten.
- (PM-7) `standard_fields.toml` merge rule: for each `[STD_*]` key, any `std_refs` entry
  whose `statement_type` is not already present in the new project's list for that key is
  appended. Entirely new `[STD_*]` keys from the source are added wholesale.
- (PM-7) `anonymise_example.toml` is never modified during project creation.
- (PM-7) The config selection page only appears in the "New Project" wizard flow, not in
  "Add Existing Project".

---

## 2. Statement Import

Users must be able to build a queue of PDF bank statements and run a background import that
parses them into structured data.

> **See D001.** The PDF parsing logic lives entirely in `bank_statement_parser`. `openstan`
> is responsible only for the queue UI, background-thread orchestration, and progress feedback.

### User Stories

- **SI-1** As a user, I want to add one or more PDF files to the import queue individually, so
  that I can import a specific selection of statements.
- **SI-2** As a user, I want to add a folder of PDFs to the import queue, so that I can import
  a whole batch at once without selecting files one by one.
- **SI-3** As a user, I want to remove selected items or clear the entire queue before running
  an import, so that I can correct mistakes without starting over.
- **SI-4** As a user, I want to run the import in the background so that the UI remains
  responsive during processing.
- **SI-5** As a user, I want to see per-file progress as each statement is processed, so that I
  know how far through the batch I am.

### Acceptance Criteria

- Queue entries are persisted to `statement_queue` in `gui.db`; the tree view reflects the
  persisted state.
- Folders are shown as parent nodes; individual files as child nodes within them.
- The "Run Statement Import" button is disabled until the queue contains at least one file entry.
- Import runs on a `QThreadPool` worker (`SQWorker`); the UI thread is never blocked.
- Progress bar and per-file feedback update in real time via cross-thread signals.
- On completion the queue/project panel is replaced by the results panel automatically.
- A project must be selected before an import can be initiated.

---

## 3. Statement Results & Review

After an import, users must be able to inspect the parsed output and decide what to do with
each statement — commit to the data mart, discard, or send to the debug review queue.

### User Stories

- **SR-1** As a user, I want to see a summary of all imported statements (success/fail counts,
  totals) so that I can assess the quality of the batch at a glance.
- **SR-2** As a user, I want to expand individual statement rows in a tree view to inspect
  transaction lines, so that I can verify the parsed data before committing.
- **SR-3** As a user, I want to add all successfully parsed statements to the project data mart
  with one action, so that they are available for export and analysis.
- **SR-4** As a user, I want to abandon successful statements (discard without writing to the
  mart), so that I can re-import them later with different settings.
- **SR-5** As a user, I want to abandon failed statements (discard without writing to the mart),
  so that I can investigate and re-import them later.
- **SR-6** As a user, I want to send failed statements to the debug review queue with detailed
  diagnostic information, so that I can manually correct and validate them before they reach
  the project database.
- **SR-7** As a user, I want to exit the results view and return to the import queue, so that I
  can start a new import batch.

### Acceptance Criteria

- The results tree shows one top-level row per statement with: filename, payments-in,
  payments-out, net movement, and a success/failure indicator.
- Expanding a row reveals the individual transaction lines for that statement.
- Summary label shows total statements, successful count, and failed count.
- "Add Successful" writes all successfully parsed `Statement` objects to the project data mart
  via `bank_statement_parser` API (see D001).
- Failed statements may **never** be written directly to the project data mart from the
  results view; they must pass through the Debug Review Queue (see Section 4) and satisfy
  checks & balances before being committed.
- "Abandon" actions discard in-memory results with no write to the mart or to `gui.db`.
- "Debug Failed" transfers failed statements — with full diagnostic detail — into the Debug
  Review Queue in `gui.db` (see Section 4) and switches the UI to that view.
- Action buttons are shown or hidden based on whether there are successes and/or failures in
  the current result set.
- Exiting the results view clears the in-memory result model and returns to the queue panel.

---

## 4. Debug Review Queue

A dedicated review view for failed statements. Statements here are held in `gui.db` — never
in `project.db` — until the user has manually corrected them and they pass checks & balances.
Only then may they be committed to the project data mart. This keeps `project.db` clean.

### User Stories

- **DQ-1** As a user, I want to see a list of failed statements with the specific error or
  parse issue for each, so that I can understand what went wrong.
- **DQ-2** As a user, I want to inspect the raw extracted text alongside the structured parse
  attempt for a failed statement, so that I can diagnose mismatches between the source PDF
  and the parsed output.
- **DQ-3** As a user, I want to manually edit the structured data for a failed statement
  (header fields and transaction lines), so that I can correct parse errors that automation
  could not resolve.
- **DQ-4** As a user, I want the corrected statement to be validated against the
  `bank_statement_parser` checks & balances before I can commit it, so that only
  internally-consistent data reaches the project database.
- **DQ-5** As a user, I want to commit a corrected statement that has passed checks & balances
  to the project data mart, so that recovered data is not permanently lost.
- **DQ-6** As a user, I want to discard a statement from the debug queue permanently, so that
  I can remove entries I cannot or do not wish to recover.

### Acceptance Criteria

- The debug queue is populated only via "Debug Failed" in the results view (SR-6); no other
  code path adds entries to it.
- Debug queue entries are persisted in `gui.db` across sessions so that unresolved failures
  are never lost on application close.
- Each entry displays: filename, error type/message, and all partial parse data available
  (header fields and any transaction lines that were extracted).
- The raw extracted text from the PDF is shown alongside the structured parse attempt to
  assist diagnosis.
- All header fields and transaction lines are editable by the user within the debug view.
- Before a corrected statement can be committed, it must be re-validated by the
  `bank_statement_parser` checks & balances logic (see D001); validation is triggered
  explicitly by the user.
- A statement that fails re-validation remains in the debug queue with the validation errors
  surfaced; the user may continue editing.
- A statement that passes re-validation may be committed to the project data mart via the
  `bank_statement_parser` API (see D001); on commit the entry is removed from the debug queue.
- Discard permanently removes the entry from `gui.db`; the user is asked to confirm before
  deletion.
- `project.db` is never written to directly from `openstan`; all mart commits go via the
  `bank_statement_parser` API.

---

## 5. Data Export

Users must be able to export project data from the data mart to Excel and/or CSV.

> **See D001.** Any database or Parquet query that feeds an export must be defined and
> executed within `bank_statement_parser`. `openstan` is responsible only for triggering
> the export, presenting format/scope options, and surfacing the result to the user.

### User Stories

- **EX-1** As a user, I want to export my project data to an Excel file (.xlsx), so that I can
  analyse it in a spreadsheet tool.
- **EX-2** As a user, I want to export my project data to CSV, so that I can use it with other
  tools or scripts.
- **EX-3** As a user, I want to choose between exporting the full project data or only the
  latest import batch, so that I can control the scope of the output.

### Acceptance Criteria

- At least one export format (Excel or CSV) must be selected; the "Run Data Export" button is
  disabled if neither is checked.
- Scope options are mutually exclusive: "Full Data" or "Latest Batch Only".
- Exports are always written to the dedicated exports subfolder within the current project
  directory; no file-save dialog is presented to the user.
- The export query is delegated entirely to `bank_statement_parser` (see D001); `openstan`
  provides the target path and scope parameter.
- On success, a `StanInfoMessage` confirms the export location (showing the resolved path).
- On failure, a `StanErrorMessage` surfaces the error detail.
- Export runs on a background thread so the UI remains responsive.

---

## 6. Administration

Power users must be able to perform maintenance operations on the application database and
project records.

### User Stories

- **AD-1** As a user, I want to delete a project record and optionally its folder from within
  the admin panel, so that I can clean up without using the main project drop-down.
- **AD-2** As a user, I want to remove a project from the UI only (keeping the folder) from
  within the admin panel.
- **AD-3** As a user, I want to reset the entire application database (`gui.db`) back to a
  clean state, so that I can recover from a corrupt or cluttered database.
- **AD-4** As a user, I want to view the event log, so that I can audit what actions have
  been taken within the application.

### Acceptance Criteria

- All destructive admin actions require explicit confirmation via `StanInfoMessage` before
  executing.
- Deleting a project from admin is equivalent in effect to PM-5; removing from UI is
  equivalent to PM-4.
- Resetting `gui.db` closes the Qt database connection, deletes the file, recreates it via
  `create_gui_db()`, and then restarts the application.
- The event log view is read-only; no editing of log entries is permitted.
- The admin panel is accessible only via the double-click gesture on the footer (not exposed
  in the main navigation).

---

## 7. Session & User Management

The application tracks who is using it and when, supporting future multi-user desktop use
without requiring authentication today.

> **See D002** for the decision on single-user vs. multi-user scope.

### User Stories

- **SU-1** As a user, I want the application to detect my OS username automatically on launch,
  so that I do not need to log in.
- **SU-2** As a user, I want a new session record to be created each time I open the
  application, so that my usage history is tracked.
- **SU-3** As a user, I want active sessions to be cleanly terminated when I close the
  application, so that stale sessions do not accumulate.
- **SU-4** As a user, I want to see my username and session ID in the footer, so that I can
  confirm which context I am working in.

### Acceptance Criteria

- OS username is read at startup; a `user` record is created in `gui.db` if one does not
  already exist for that username.
- A new `session` row is created on every application launch with a fresh UUID.
- On `closeEvent`, `SessionModel.end_active_sessions()` is called before the window closes.
- If a session cannot be created (e.g. DB lock), `db_lock_signal` is emitted and a
  `StanErrorMessage` is shown.
- Footer labels reflect the current user and session at all times.

---

## 8. Balance Chart

Users must be able to view a panel showing account closing balances over time, drawn from the
project data mart's `FactBalance` table, organised by company and account.

> **See D001.** The balance data query (join of `FactBalance` and `DimAccount`, filter on
> `outside_date = 0`, month-end aggregation) is performed in `openstan` as a temporary shim
> marked `# TODO: move to bsp`. When bsp exposes a dedicated query for this, the shim must
> be removed and the bsp API consumed instead.

### User Stories

- **BC-1** As a user, I want to open a balance chart panel from the project selection strip,
  so that I can see account balance trends without leaving the application.
- **BC-2** As a user, I want to see each account displayed as a time-series line chart with a
  shared time axis across all charts, so that I can compare balance movements across accounts
  at a glance.
- **BC-3** As a user, I want accounts grouped by company in a tree on the left, with a
  corresponding chart for each account on the right, so that I can identify which institution
  holds each account.
- **BC-4** As a user, I want a company-level summary chart (stacked area) for each company
  that has more than one account, so that I can see the combined balance position per
  institution. Credit-card (negative) balances stack below zero; positive balances stack above.
- **BC-5** As a user, I want an all-accounts summary chart when there is more than one company,
  so that I can see the total balance across all institutions.
- **BC-6** As a user, I want to click an account row in the left-hand tree to highlight the
  corresponding chart series, so that I can visually trace a specific account through the chart
  area.
- **BC-7** As a user, I want the chart to use month-end closing balances so the display is
  readable across multi-year histories without being overwhelmed by daily data points.
- **BC-8** As a user, I want the balance chart panel to be loaded in the background so the
  UI is never blocked while data is fetched from the project database.

### Acceptance Criteria

- The balance chart panel is a third swappable content block alongside the existing statement
  queue and statement results blocks. Only one block is visible at a time.
- The `"View Balances"` button in the project selection strip opens the balance chart block.
  The button is enabled only when the selected project has at least one account with balance
  data in `FactBalance`.
- A `"← Back"` button in the balance chart panel returns the user to the statement queue
  block.
- Balance data is fetched in a background `QRunnable` worker (`BalanceChartWorker`).
  The chart area shows a loading indicator while the fetch is in progress.
- The data source is `FactBalance` (filtered `outside_date = 0`) joined to `DimAccount`,
  aggregated to the last calendar day of each month per `(company, id_account)` combination.
  `closing_balance` is used directly — it is not summed.
- The left panel is a read-only `StanTreeView` with a custom `BalanceAccountModel` that
  groups accounts under their company. Clicking a leaf row highlights the corresponding
  line series in the chart area.
- The right panel contains one `QLineSeries` chart per account plus one stacked-area summary
  chart per company (only if that company has more than one account) plus one stacked-area
  all-companies chart (only if there is more than one company).
- All charts in the panel share a single time axis so balance changes can be visually aligned.
  The shared axis supports interactive pan and zoom.
- Stacked-area summary charts render positive balances above zero and negative balances
  (credit cards and similar) below zero.
- The chart panel refreshes automatically when the selected project changes and after a batch
  is committed to the data mart.
- If the data mart has not yet been built for the project (or `FactBalance` is empty after
  filtering), the chart area shows a "No balance data available" placeholder and the
  `"View Balances"` button is disabled.

---

## Non-Functional Requirements

### NFR-1 — Separation of concerns (see D001)

`openstan` is strictly a UI layer. Features that have value in a CLI or API context must be
implemented in `bank_statement_parser` and consumed here. This is a hard constraint, not a
preference.

### NFR-2 — Single-user desktop; multi-user desktop feasibility (see D002)

The application must work correctly for a single user on one machine with no authentication.
The architecture must not preclude a future shared-`gui.db` multi-user desktop mode. Full
network/server scale is explicitly out of scope and would require a separate application.

### NFR-3 — UI responsiveness

All operations that may take more than ~200 ms (PDF parsing, DB writes, file I/O, exports)
must run on a background thread. The main Qt thread must never be blocked.

### NFR-4 — Data integrity

Writes to the project data mart are delegated to `bank_statement_parser`. The `gui.db` schema
uses SQLite triggers to maintain the event log automatically; no presenter or model may write
to `event_log` directly.

Failed statements are held in `gui.db` during the debug review process and must pass the
`bank_statement_parser` checks & balances validation before they can be committed to
`project.db`. Direct writes to `project.db` from `openstan` are prohibited (see D001).

### NFR-5 — Local-only data

No network calls, no cloud storage, no telemetry. All data remains on the user's local
filesystem.

### NFR-6 — Python version & tooling

Python >= 3.14 required. `uv` is the sole package manager. No pip, poetry, conda, or
JavaScript tooling.

### NFR-7 — Portability

The application must run on macOS, Windows, and Linux without platform-specific code paths
beyond any OS-level path handling already provided by Python's `pathlib`.

### NFR-8 — Application identity

The application must display a title/branding bar containing the application name and logo.
A copyright notice must appear in the footer. These elements are cosmetic and must not
contain interactive controls or business logic.
