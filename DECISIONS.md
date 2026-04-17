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

## D005 — Main window navigation: horizontal action bar (Option A)

**Status:** Accepted
**Applies to:** Main window navigation, panel layout

### Context

The application has four distinct panels: Project Info, Import Statements, Export Data, and
Run Reports. A navigation mechanism is needed to switch between them. Three layout options
were evaluated:

- **Option A — Horizontal action bar:** A full-width row of four checkable buttons spanning
  the width of the window, placed between the project selector and the content area. Simple,
  fits within a 1080p display with ~800 px remaining for content.
- **Option B — Vertical sidebar:** A fixed-width left sidebar (~120 px) with vertically
  stacked icon+label buttons, and the content area occupying the remaining horizontal space.
  More familiar on wider displays; requires a `QSplitter`-based horizontal layout split in
  `main.py`.
- **Option C — Switchable A↔B:** Both layouts implemented simultaneously with a user
  preference toggle persisted to `gui.db` or a config file. Nav buttons are re-parented
  between a horizontal and vertical container at runtime via `setParent()`.

### Decision

**Option A** is implemented. The nav bar is built as a self-contained `ProjectNavView`
widget so the layout contract between navigation and content is clean and explicit.

Buttons that are only meaningful for projects with existing data (Project Info, Export Data,
Run Reports) are **hidden** when no summary data is available, keeping the UI uncluttered
for new or empty projects. The active panel's button is rendered in a checked/pressed state.

### Future options if revisiting

If Option B or C is desired later, the key design questions to resolve first are:

1. **Toggle trigger:** Right-click context menu on the button bar, or a small dedicated
   layout-toggle button (e.g. in the title or footer row). The context menu approach is
   more discoverable; the dedicated button is simpler to implement.
2. **State persistence:** A new `layout_mode` column on the `session` or `user` table in
   `gui.db`, or a `settings.toml` alongside `gui.db`. The `gui.db` column approach keeps
   all GUI state in one place and is consistent with D004; `settings.toml` is simpler but
   introduces a second persistence mechanism.
3. **Implementation note:** Qt does not allow the same widget instance to live in two
   layouts simultaneously. The practical approach for C is to build both layout containers
   and toggle their visibility, avoiding `setParent()` re-parenting complexity at the cost
   of slightly more memory.

### Consequences

- `ProjectNavView` must not contain logic — button state (visible/hidden, checked) is
  managed by `StanPresenter`.
- Adding Option B later is additive, not a rewrite, given the self-contained nav widget
  design.

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

---

## D006 — Single-page New Project Wizard; no config-subfolder selection step

**Status:** Accepted
**Applies to:** PM-7, `ProjectWizard`, `ProjectPresenter`

### Context

An earlier design (PM-7) added a second "Configure Project" page to the New Project Wizard
that let users select which BSP config subfolders to include and optionally source them from
an existing project. The full backend implementation was built
(`_collect_config_sources`, `_apply_config_selections`, `_merge_toplevel_tomls`) but the UI
page was never created.

### Decision

The config-selection step is removed. The New Project Wizard has a single page (name +
location). BSP scaffolding always runs with default config. Users who need custom config
can modify the project's `config/` folder directly after creation.

The backend implementation has been deleted to prevent maintenance confusion.

### Consequences

- PM-7 is removed from REQUIREMENTS.md and ROADMAP.md.
- `_collect_config_sources`, `_apply_config_selections`, `_merge_toplevel_tomls`, and
  `_MERGE_TOML_FILES` are removed from `project_presenter.py`.
- The `shutil`, `tomllib`, and `tomli_w` imports are also removed from that module.
- If config-selection is revisited it must be re-proposed as a new requirement.

---

## D007 — Synchronous project summary fetch on main thread

**Status:** Accepted
**Applies to:** PM-6, `StanPresenter.__refresh_project_info()`

### Context

An earlier acceptance criterion for PM-6 specified a `ProjectSummaryWorker` background
thread for fetching transaction/statement/account counts. A background worker was
implemented but then reverted because it caused Qt signal/slot re-entrancy issues —
specifically, the worker completing mid-presenter-init triggered cascading state updates
that were difficult to sequence correctly.

### Decision

`get_project_info()` runs synchronously on the main thread. The call is fast enough
(a handful of lightweight Polars queries against a local SQLite file) that it does not
produce a perceptible UI pause in practice.

### Consequences

- No `ProjectSummaryWorker` class exists or should be added.
- If project databases grow large enough to make the call slow, the right fix is to
  cache the result in `project.db` via a `bank_statement_parser` API rather than
  move the call to a background thread.

---

## D008 — Bare-comma multi-exception syntax is Ruff-canonical for Python 3.14

**Status:** Accepted
**Applies to:** All exception handling in the codebase

### Context

The form `except A, B:` was flagged repeatedly as Python 2 syntax requiring correction to
`except (A, B):`. Investigation confirmed that in Python 3.14 both forms are valid and
semantically identical — the AST represents both as an `ExceptHandler` with a `Tuple` type
node. Furthermore, `ruff format` actively removes the parentheses, converting the
parenthesised form back to the bare-comma form on every save.

### Decision

`except A, B:` is the accepted style for this codebase. It is valid Python 3.14, preferred
by `ruff format`, and should not be "corrected" to the parenthesised form. This is also
documented in `AGENTS.md` under "Multi-exception syntax".

### Consequences

- Do not add parentheses to bare-comma except clauses; `ruff format` will remove them.
- Do not flag `except A, B:` as a bug or Python 2 holdover.
- The instance in `project_presenter.py` is correct as written.
