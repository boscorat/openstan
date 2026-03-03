# Decisions

Lightweight architectural decision records for `openstan`. Each entry captures the context,
the decision made, and its consequences. Decisions are numbered sequentially and their status
reflects whether they are in force.

> **Statuses:** `Draft` — under discussion | `Accepted` — in force | `Superseded` — replaced
> by a later decision (noted inline).

When implementing a feature, check this file first. If no decision covers your situation and
the choice has non-trivial architectural impact, add a `Draft` entry and discuss before
coding.

---

## D001 — Feature placement: openstan vs. bank_statement_parser

**Status:** Accepted
**Applies to:** All development in this repository

### Context

`openstan` is a desktop GUI built on top of `bank_statement_parser` (bsp), which is an
independent package with its own CLI and Python API. Both packages will evolve in parallel.
Without a clear boundary, logic risks being duplicated or placed in the wrong layer —
making the CLI less capable and the UI harder to maintain.

### Decision

Feature placement is determined by whether the feature has value outside a graphical UI
context:

1. **Belongs in `bank_statement_parser`:** Any functional enhancement that would be useful
   via the bsp CLI or API — parsing logic, data transformation, validation, data mart
   writes, database/Parquet queries. If `openstan` needs a new capability of this kind,
   implement it in bsp first and consume it here.

2. **Belongs in `openstan`:** Anything that specifically enhances the desktop UI experience
   and has no value in a CLI/API context — layout, navigation, progress feedback, dialogs,
   charting, and report *rendering*.

3. **Shared responsibility — queries that feed reports:** Even when a chart or report is
   rendered in `openstan`, the underlying database or Parquet query must be defined and
   executed within `bank_statement_parser`. `openstan` passes parameters (scope, filters,
   target path) and receives a result set or file; it never writes raw SQL against the
   project data mart.

### Consequences

- Agents and developers must not write SQL against `project.db` directly in `openstan`
  source files.
- Any new bsp capability required by `openstan` must be proposed to the `bank_statement_parser`
  project first. If the change is urgent and bsp cannot be updated immediately, a temporary
  shim may be used in `openstan` but must be flagged with a `# TODO: move to bsp` comment
  and tracked in the backlog.
- The `packages/bank_statement_parser/` directory must not be modified within this
  repository. Changes to bsp must go through that project's own workflow.

---

## D002 — Single-user desktop now; multi-user desktop feasibility preserved

**Status:** Accepted
**Applies to:** Session management, database design, UI access control

### Context

The initial target user is an individual working alone on a single machine. However, a
small-team use case (2–5 users sharing one machine or a shared local path) is plausible in
the near future. Full network-scale multi-tenancy is a different product category entirely.

### Decision

1. **Today:** The application is designed for a single user with no authentication. OS
   username detection is sufficient for user identification. No login screen, no roles.

2. **Near future (Milestone 4):** The architecture must not foreclose a shared-`gui.db`
   multi-user desktop mode where multiple users on the same machine (or a shared local
   network path) each have their own sessions and project context. Design decisions made
   today should be compatible with this mode — in particular:
   - User identity is keyed on OS username (already a UUID-keyed `user` table).
   - Session records isolate per-user activity (already modelled).
   - No global mutable state that would break under concurrent access.

3. **Out of scope:** Full network/server scale, web interfaces, cloud storage, and
   centralised authentication. These would require a separate application and are
   explicitly not planned here.

### Consequences

- SQLite WAL mode should be evaluated when Milestone 4 begins, to support concurrent
  readers and a single writer without locking conflicts.
- UI state that is currently implicit (e.g. "the current project") must eventually become
  per-session rather than per-application-instance.
- No authentication infrastructure (OAuth, tokens, password hashing) is needed or should
  be added speculatively.

---

## D003 — No pandas; Polars only for tabular data

**Status:** Accepted
**Applies to:** All data manipulation in both `openstan` and (by extension) `bank_statement_parser`

### Context

Early prototyping used pandas-compatible patterns. The project has since adopted Polars for
its performance, memory efficiency, and stricter type model. Mixing both libraries creates
confusion about which API to use and inflates the dependency footprint.

### Decision

All tabular data manipulation uses **Polars** `LazyFrame` / `DataFrame`. pandas is not a
dependency of this project and must not be added. The `StanPolarsModel` Qt model adapter
(`components.py`) provides the bridge between Polars DataFrames and Qt table/tree views.

### Consequences

- Any new data processing code must use Polars idioms.
- Contributors familiar only with pandas should consult the Polars documentation before
  implementing data transformations.
- `StanPolarsModel` should be extended if new display patterns are needed rather than
  reaching for a pandas-backed alternative.

---

## D004 — SQLite for persistence; no DuckDB in production paths

**Status:** Accepted
**Applies to:** Database selection for `gui.db` and `project.db`

### Context

`duck.py` contains commented-out experiments attaching `gui.db` to DuckDB for analytical
queries. DuckDB is a capable OLAP engine but introduces an additional runtime dependency and
a different connection model from the `QSqlDatabase`-managed SQLite connection used
throughout the GUI.

### Decision

- **`gui.db`** (application state) — SQLite via `QSqlDatabase`. No DuckDB access to this
  file.
- **`project.db`** (data mart) — SQLite via `sqlite3` + Polars, owned and managed entirely
  by `bank_statement_parser`. `openstan` never connects to this file directly (see D001).
- DuckDB may be reconsidered as an analytics backend for `project.db` within
  `bank_statement_parser`, but this requires its own ADR in that project and must not
  affect `openstan`'s dependency footprint.

### Consequences

- `duck.py` can be deleted when convenient; it contains no active code.
- If analytical query performance becomes a bottleneck, the fix belongs in
  `bank_statement_parser`, not in `openstan`.
