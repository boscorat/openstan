# Categorisation Feature — Resume Notes

> **Branch:** `categorisation`
> **Parked from:** `dev` at commit `79a8bb4` (Project Summary Figures)
> **Reason for parking:** AI categorisation quality is insufficient with the current prompting
> strategy. Need a more structured/detailed prompting approach before the feature is useful
> in practice. All infrastructure (storage, UI, wiring) is in place and importable.

---

## What is complete

### Storage shim
- `src/openstan/shim_annotations.py` — `ensure_annotation_table`, `upsert_annotations`,
  `read_annotations`. Writes directly to `project.db` via `sqlite3` as a documented D001
  exception (see DECISIONS.md D005). The `TransactionAnnotation` table is append-safe and
  survives `build_datamart` rebuilds.

### Config
- `src/openstan/llm_config.py` — `LLMConfig` dataclass + `load_llm_config` / `save_llm_config`.
  Reads/writes `<project>/config/llm_categories.toml`. Falls back to hard-coded defaults.
- `/Users/boscorat/repos/bank_statement_parser/src/bank_statement_parser/project/config/llm_categories.toml`
  — default config scaffolded into every new project by bsp. **This file lives in the bsp
  sibling repo, not here.** If bsp is updated or re-cloned, re-add this file.

### Presenter + Worker
- `src/openstan/presenters/category_presenter.py` — `CategorySignals`, `CategoryWorker`,
  `CategoryPresenter`. Worker calls Ollama via structured JSON format; writes each annotation
  immediately (crash-safe). Presenter manages table model, manual edit persistence, config
  round-trip, health-check timer.

### View
- `src/openstan/views/category_view.py` — `CategoryTableModel` (editable Category column,
  `pending_edits()` / `clear_pending_edits()`) + `CategoryView` (table + controls + config
  pane in a splitter).

### Wiring
- `main.py` — `CategoryView`, `CategoryPresenter`, `category_block` added.
- `views/statement_queue_view.py` — `buttonViewCategories` added (row 5, hidden initially).
- `presenters/stan_presenter.py` — `show_categories()`, `hide_categories()`, `set_project()`
  wired. `buttonViewCategories` and `button_back` connected.
- `views/__init__.py`, `presenters/__init__.py` — exports added.
- `components.py` — `StanPolarsModel.data()` return type widened to `object`.

### Spec
- `REQUIREMENTS.md` — Section 8 (TC-1 – TC-6) added.
- `DECISIONS.md` — D005 added.

---

## What is NOT done / the known problem

### Core issue: prompting quality
The current prompting strategy (single system message + raw transaction description → JSON
`{"category": "..."}`) produces unreliable results. Common failure modes:
- Model ignores the category list and invents its own labels.
- Very short descriptions (e.g. reference numbers) get arbitrarily assigned.
- No context about the account, date, or merchant type is used.

### Ideas to explore before resuming
1. **Few-shot examples** — include 3–5 labelled examples per category in the system prompt
   so the model has concrete patterns to match against.
2. **Richer input** — pass `id_account` and `id_date` alongside `transaction_desc` so the
   model can use account type (current / savings / credit) and seasonality as signals.
3. **Two-pass approach** — first pass: extract merchant/payee name; second pass: classify
   the merchant. Reduces noise from reference numbers.
4. **Confidence threshold** — ask the model to return a confidence score alongside the
   category; only accept assignments above a threshold, leave the rest as "Uncategorised"
   for manual review.
5. **Prompt per account type** — different system prompts for current account vs. credit
   card vs. savings, since spending categories differ.
6. **Batch requests** — send N transactions in one prompt (JSON array in / JSON array out)
   to reduce per-call overhead and give the model cross-transaction context.
7. **Evaluate a larger model** — `qwen2.5:3b` or `qwen2.5:7b` instead of `1.5b`; the
   quality gap may be significant enough to justify the extra RAM.
8. **Fine-tuning data** — if the user has manually categorised a representative set, use
   those as few-shot examples dynamically selected by similarity (embedding lookup).

### Other loose ends
- No unit tests for `shim_annotations` or `llm_config` (the bsp test suite has no GUI
  tests by convention, but these are pure Python and could have tests if desired).
- `CategoryTableModel` has no combo-box delegate wired up — double-clicking a Category cell
  opens a plain text editor rather than a dropdown. A `QStyledItemDelegate` subclass is
  needed to render a `QComboBox` populated from `model.data(index, Qt.UserRole)`.
- `buttonViewCategories` is set visible on every project change regardless of whether any
  transactions exist yet (minor UX: could hide it until the data mart has been built).
- The Ollama health-check makes a real HTTP request on the main thread during
  `_check_ollama_health` — should be moved to a `QRunnable` to avoid any UI stutter if
  the host is slow to respond.

---

## How to resume

```bash
git checkout categorisation
uv sync --all-groups
uv run openstan          # smoke-test the UI
```

Key files to read first:
- `DECISIONS.md` — D005 (shim exception)
- `REQUIREMENTS.md` — Section 8 (TC-1 – TC-6)
- `src/openstan/presenters/category_presenter.py` — worker + presenter
- `src/openstan/views/category_view.py` — view + editable model
- `src/openstan/shim_annotations.py` — storage shim
- `src/openstan/llm_config.py` — config dataclass + TOML I/O

The bsp sibling repo default config file lives at:
`/Users/boscorat/repos/bank_statement_parser/src/bank_statement_parser/project/config/llm_categories.toml`

---

## Dependency added (already in pyproject.toml + uv.lock)

```
ollama==0.6.1
```

Default Ollama model: `qwen2.5:1.5b` — pull with `ollama pull qwen2.5:1.5b`.
