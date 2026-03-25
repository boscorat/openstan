# Roadmap

> **Living document.** Milestones have no hard dates. Items move between milestones as
> priorities shift. The backlog holds accepted but unscheduled work. Anything not listed
> here has not been accepted into the plan — raise it as a discussion before implementing.
>
> Each milestone defines a **Definition of Done**: the milestone is complete only when
> every listed item satisfies its acceptance criteria in [REQUIREMENTS.md](REQUIREMENTS.md).

---

## Milestone 1 — Core Import Flow

**Theme:** A user can create or open a project, queue bank statement PDFs, run a background
import, and see the results. This is the end-to-end happy path for the primary use case.

**Status:** In progress

### Included

| ID | Story | Notes |
|----|-------|-------|
| PM-1 | Create a new project | Scaffolding via `bsp.validate_or_initialise_project()` |
| PM-2 | Register an existing project | Validation via bsp before DB write |
| PM-3 | Switch between projects via drop-down | |
| SI-1 | Add individual PDF files to the queue | |
| SI-2 | Add a folder of PDFs to the queue | |
| SI-3 | Remove / clear queue items | |
| SI-4 | Run import in the background | `SQWorker` + `QThreadPool` |
| SI-5 | Per-file progress feedback | Progress bar + real-time signal updates |
| SR-1 | Summary of import results (counts, totals) | |
| SR-2 | Expand statement rows to inspect transaction lines | |
| SR-7 | Exit results view and return to queue | |
| SU-1 | Auto-detect OS username on launch | |
| SU-2 | Create a new session on launch | |
| SU-3 | Terminate sessions on close | |
| SU-4 | Display user and session in footer | |
| AB-1 | About dialog with logo, version, and external links | |

### Definition of Done

- A fresh install can create a project, add PDFs, run an import, and view results without
  errors.
- Background import does not block the UI.
- Session is correctly created and terminated within a single application lifecycle.
- All listed acceptance criteria in REQUIREMENTS.md are met.

---

## Milestone 2 — Results Review & Actions

**Theme:** Users can act on import results — committing successful data to the mart, discarding,
or routing failures to the debug review queue for manual correction. This closes the first full
data lifecycle loop, with `project.db` integrity enforced by a checks & balances gate.

**Status:** Planned

### Included

| ID | Story | Notes |
|----|-------|-------|
| SR-3 | Add successful statements to the data mart | Delegates write to `bank_statement_parser` API |
| SR-4 | Abandon successful statements | In-memory discard only |
| SR-5 | Abandon failed statements | In-memory discard only |
| SR-6 | Send failed statements to debug review queue | Persists to `gui.db`; never to `project.db` |
| SR-7 | Exit results view and return to queue | |
| DQ-1 | View failed statements with error detail | |
| DQ-2 | Inspect raw text vs. parse attempt | |
| DQ-3 | Manually edit header fields and transaction lines | |
| DQ-4 | Re-validate corrected statement against checks & balances | Via `bank_statement_parser` API |
| DQ-5 | Commit a validated corrected statement to the data mart | Only after passing DQ-4 |
| DQ-6 | Discard a statement from the debug queue permanently | |

### Definition of Done

- All result-action buttons are fully implemented (no `pass` stubs remain).
- "Add Failed" button is absent from the results view; failed statements can only reach the
  mart via the debug queue after passing checks & balances.
- Debug review queue persists to `gui.db` across sessions.
- Data mart writes are delegated to `bank_statement_parser` with no raw SQL in `openstan`.
- All listed acceptance criteria in REQUIREMENTS.md are met.

---

## Milestone 3 — Export & Reporting

**Theme:** Users can export project data from the data mart to Excel and/or CSV, with control
over scope (full data vs. latest batch).

**Status:** Planned

### Included

| ID | Story | Notes |
|----|-------|-------|
| EX-1 | Export to Excel (.xlsx) | Query defined in `bank_statement_parser` (D001) |
| EX-2 | Export to CSV | Query defined in `bank_statement_parser` (D001) |
| EX-3 | Choose full data or latest batch | Scope parameter passed to bsp export API |

### Definition of Done

- Export runs on a background thread; UI is not blocked.
- Both format options (Excel, CSV) work independently and together.
- Exports are always written to the project's dedicated exports subfolder; no file-save dialog.
- Export query is defined in `bank_statement_parser`; `openstan` passes only the target path and scope.
- Success and failure are surfaced to the user via `StanInfoMessage` / `StanErrorMessage`.
- All listed acceptance criteria in REQUIREMENTS.md are met.

---

## Milestone 4 — Multi-user Desktop

**Theme:** A small team sharing one machine (or a shared network path) can each use the
application with their own session and project context.

**Status:** Planned (pending D002 design work)

### Included

| ID | Story | Notes |
|----|-------|-------|
| SU-* | All session/user stories hold for concurrent users | Requires DB concurrency review |
| AD-* | Admin actions are user-scoped or require elevated confirmation | |
| — | Shared `gui.db` on a network share or local shared path | SQLite WAL mode candidate |
| — | Session conflict detection and graceful messaging | |
| — | User switching within a running instance | |

### Definition of Done

- Two users on the same machine can run the application simultaneously without data
  corruption.
- Session records correctly isolate each user's activity.
- All admin destructive actions require explicit confirmation and are audit-logged.
- D002 is updated to `Accepted` with the chosen concurrency approach documented.

---

## Administration (cross-cutting, delivered incrementally)

The admin panel features (AD-1 through AD-4) are partially implemented. They are not a
standalone milestone but are expected to reach full completion by the end of Milestone 2.

| ID | Story | Target milestone |
|----|-------|-----------------|
| AD-1 | Delete project + folder from admin panel | M1 (PM-5 equivalent) |
| AD-2 | Remove project from UI only via admin panel | M1 (PM-4 equivalent) |
| AD-3 | Reset `gui.db` to clean state | M1 |
| AD-4 | View event log | M2 |

---

## Backlog / Icebox

Items accepted in principle but not yet assigned to a milestone. Requires a requirements
entry before implementation begins.

| Item | Notes |
|------|-------|
| User management UI (`UserView`) | Currently disabled; low priority for single-user target |
| Charting / visualisation | In-app charts fed by data mart; rendering in `openstan`, queries in `bank_statement_parser` (D001) |
| DuckDB analytics layer | `duck.py` experiments suggest interest; requires ADR before proceeding |
| Packaging & distribution | Installable `.app` / `.exe` / `.deb`; no timeline yet |
| CLI passthrough for power users | Out of scope for `openstan`; belongs in `bank_statement_parser` directly |
| Full network / server scale | Explicitly out of scope; would require a separate application (D002) |
