# AGENTS.md — Developer & Agent Guide for `openstan`

## Project Overview

`openstan` is a Python/PyQt6 desktop application for bank statement analysis and
visualization. It follows a strict **MVP (Model–View–Presenter)** architecture with
SQLite backing via Qt's `QSqlDatabase` layer.

---

## Environment & Package Manager

- **Python ≥ 3.14** is required.
- **`uv`** is the sole package/build manager. Do **not** use `pip`, `poetry`, or `conda`.
- Install dependencies: `uv sync`
- Run the app: `uv run openstan`  or  `uv run python -m openstan`

---

## Build / Lint / Type-Check Commands

```bash
# Lint (Ruff — default E + F rules, 88-char line length)
uv run ruff check src/

# Auto-fix lint issues
uv run ruff check --fix src/

# Format code (Ruff formatter, 88-char lines, double quotes)
uv run ruff format src/

# Type-check (Meta's Pyrefly — NOT mypy)
uv run pyrefly check
```

---

## Pre-PR Checklist

**Always run all of the following before opening or updating a pull request.**
These mirror the steps in `.github/workflows/ci.yml` and will be enforced by GitHub Actions.

```bash
# 1. Lint
uv run ruff check .

# 2. Format check (do NOT skip — ruff format changes are required to pass CI)
uv run ruff format --check .
# Auto-fix if needed:
uv run ruff format .

# 3. Type check
uv run pyrefly check

# 4. Tests
uv run pytest tests/ -v
```

All four commands must exit cleanly (zero errors) before the PR is opened or force-pushed.

---

## Tests

```bash
# Install pytest (one-time)
uv add --dev pytest

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/path/to/test_file.py

# Run a single test function
uv run pytest tests/path/to/test_file.py::test_function_name

# Run a single test class method
uv run pytest tests/path/to/test_file.py::TestClass::test_method
```

---

## Code Style

### Formatter & Linter

- **Ruff** handles both linting and formatting. No Black, no isort, no Flake8.
- Line length: **88 characters**.
- Indent: **4 spaces**.
- Quote style: **double quotes** (Ruff formatter default).
- Always run `uv run ruff format src/` before committing.

### Type Checking

- Use **Pyrefly** (`uv run pyrefly check`), not mypy.
- Annotate all function return types (`-> None`, `-> bool`, `-> tuple[bool, str, str]`).
- Annotate local variables where it improves clarity.
- Keep `__all__: list[str]` in every `__init__.py`.

### Multi-exception syntax

Both forms below are **valid Python 3.14** and semantically identical:

```python
except ValueError, TypeError:     # valid — bare-comma form, preferred by ruff format
except (ValueError, TypeError):   # valid — parenthesised form, also acceptable
```

**`ruff format` actively removes the parentheses**, converting the parenthesised form
to the bare-comma form on save. Do not "fix" bare-comma except clauses — they are correct
and Ruff-idiomatic. Do not flag `except A, B:` as Python 2 syntax; in Python 3.14 it
parses as a tuple of exception types, equivalent to `except (A, B):`.

The instance in `project_presenter.py` (`except sqlite3.OperationalError, bsp.StatementError:`)
is correct as written. This has been investigated and confirmed — do not re-flag it.

---

## Widget Library

All Qt widgets **must** use the `Stan`-prefixed subclasses from
`src/openstan/components.py` rather than the raw PyQt6 originals.
These subclasses set `setAutoFillBackground(True)` and apply any
app-wide defaults (alternating row colours, selection behaviour, etc.)
so that every widget inherits the correct appearance on both light and
dark themes.

### Quick reference — Stan subclass → Qt base

| Stan class | Qt base | Notes |
|---|---|---|
| `StanWidget` | `QWidget` | Base for all custom panels/panes |
| `StanLabel` | `QLabel` | Markdown text format enabled |
| `StanMutedLabel` | `StanLabel` | De-emphasised colour, theme-aware |
| `StanHeaderLabel` | `StanLabel` | Bold font weight |
| `StanThemedPixmapLabel` | `StanLabel` | SVG icon that reloads on theme change |
| `StanButton` | `QPushButton` | `min_width=200`; use `set_themed_icon()` for SVG icons |
| `StanHelpIcon` | `QPushButton` | Focusable info-icon with tooltip |
| `StanToolButton` | `QToolButton` | |
| `StanCheckBox` | `QCheckBox` | |
| `StanRadioButton` | `QRadioButton` | |
| `StanComboBox` | `QComboBox` | |
| `StanLineEdit` | `QLineEdit` | |
| `StanDateEdit` | `QDateEdit` | Calendar popup enabled |
| `StanListWidget` | `QListWidget` | Alternating row colours |
| `StanTableView` | `QTableView` | No grid, no vertical header, ResizeToContents |
| `StanTableWidget` | `QTableWidget` | No edit triggers, stretch last section |
| `StanTreeView` | `QTreeView` | Alternating row colours, uniform row heights |
| `StanGroupBox` | `QGroupBox` | |
| `StanScrollArea` | `QScrollArea` | |
| `StanFrame` | `QFrame` | Panel/Sunken/StyledPanel — **not** for line separators |
| `StanTabWidget` | `QTabWidget` | |
| `StanForm` | `QFormLayout` | Right-aligned labels, 15 px spacing |
| `StanDialog` | `QDialog` | Modal, auto-fill |
| `StanWizard` | `QWizard` | Modal, auto-fill |
| `StanWizardPage` | `QWizardPage` | |
| `StanErrorMessage` | `QDialog` | Modal error dialog — call `.showMessage(str)` |
| `StanInfoMessage` | `QMessageBox` | For Yes/Cancel confirmations before destructive actions |
| `StanPolarsModel` | `QAbstractTableModel` | Polars DataFrame table model |
| `StanProgressBar` | `QProgressBar` | |

### Permitted raw Qt usage

A small number of raw Qt classes are acceptable because no `Stan` subclass
covers them or the subclass has different semantics:

- **`QFrame` as a line separator** — `StanFrame` has full panel styling;
  for a `VLine`/`HLine` divider use `QFrame` directly and set shape/shadow
  manually.
- **`QWidget.setTabOrder(a, b)`** — static utility call; not a widget
  instantiation.
- **`QMessageBox.information / .warning / .critical` (static)** — one-shot
  non-interactive notifications. Use `StanInfoMessage` for confirmations
  that require a Yes / Cancel choice.
- Layout classes (`QHBoxLayout`, `QVBoxLayout`, `QSortFilterProxyModel`,
  `QStackedWidget`, `QSplitter`, `QSizePolicy`, `QHeaderView`, etc.) — no
  `Stan` equivalents; use the Qt originals.

---

## Naming Conventions

### Files
- All module files: `snake_case.py`
- Follow the `<domain>_<layer>.py` pattern:
  `project_model.py`, `project_view.py`, `project_presenter.py`

### Classes
- Application-specific Qt widgets: `Stan` prefix + `PascalCase`
  (`StanButton`, `StanLabel`, `StanFrame`, `StanTreeView`, `StanErrorMessage`)
- Domain classes: `PascalCase` with layer suffix
  (`ProjectModel`, `StatementQueueView`, `AdminPresenter`)
- Worker threads: `PascalCase` + `Worker` suffix (`SQWorker`)
- Signal containers: `PascalCase` + `Signals` suffix (`WorkerSignals`)
- Main window: `Stan` (no suffix)

### Functions & Methods
- **`snake_case`** for all Python-defined methods.
- Qt-mandated overrides that Qt expects in `camelCase` (e.g. `rowCount`,
  `closeEvent`) are written in `camelCase` with `# noqa: N802` if needed.
- Event handler slots: `on_<event>` or descriptive verb phrases
  (`on_model_updated`, `run_import`, `update_progress`).
- Model CRUD methods: `add_record`, `delete_record_by_id`, `delete_records`,
  `clear_records`.

### Variables & Constants
- Local variables and instance attributes: **`snake_case`**.
- Module-level constants: `UPPER_SNAKE_CASE` (e.g. `NEW_RECORD_STATUS = 8`).
- Private module-level DDL strings: `_UPPER_SNAKE_CASE`
  (e.g. `_DDL_TABLES`, `_DDL_VIEW`, `_STATUS_ROWS`).
- Prefer `project_id`, `session_id`, `user_id` (snake_case) for ID variables;
  legacy `sessionID`/`userID` camelCase exists in older code — do not extend it.

### Signals
- `pyqtSignal` class attributes: **`snake_case`**
  (`db_updated`, `model_updated`, `import_finished`, `path_or_name_changed`).
- Import `pyqtSignal` directly; avoid aliasing it as `Signal` (inconsistency
  exists in `statement_queue_model.py` — do not replicate it).

---

## Import Style

### Ordering (PEP 8; isort not enforced but follow this order)
1. Standard library (`os`, `sys`, `pathlib`, `datetime`, `uuid`, `typing`)
2. Third-party (`bank_statement_parser`, `PyQt6.*`)
3. First-party (`openstan.*`)

Separate each group with a blank line.

### Named Imports Only
- Always import Qt classes by name:
  `from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot`
- No wildcard imports (`from PyQt6.QtWidgets import *` is forbidden).
- No default imports from internal modules.

### Absolute Internal Imports
- Always use **absolute** package paths for internal imports:
  `from openstan.models.project_model import ProjectModel`
- **No relative imports** (`from .project_model import ...`).

### `TYPE_CHECKING` Guard (required in all presenters)
Use this pattern to break circular imports at runtime while preserving static analysis:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from openstan.models.project_model import ProjectModel
    from openstan.views.project_view import ProjectView
```

Annotate constructor parameters with string literals:
```python
def __init__(self, model: "ProjectModel", view: "ProjectView") -> None:
```

---

## Architecture

### MVP Layers (strict separation)
| Layer | Location | Responsibility |
|---|---|---|
| **Model** | `src/openstan/models/` | Qt SQL models (`QSqlTableModel`), CRUD, signals |
| **View** | `src/openstan/views/` | Widget layout only — **zero business logic** |
| **Presenter** | `src/openstan/presenters/` | All signal/slot wiring, business logic |

- Views expose widget references publicly; they never connect their own signals.
- Presenters receive model and view at `__init__` and own all connections.
- `StanPresenter` is the top-level coordinator for cross-presenter signals and
  application-level startup (user setup, session init, project sync).

### Database Access Rules
- `gui.db` (SQLite): accessed **only** via `QSqlDatabase` / `QSqlTableModel`
  subclasses at runtime. Raw `sqlite3` is used only in `create_gui_db.py`
  for initial schema bootstrap.
- `project.db` (data mart): **never** accessed directly from `openstan`.
  All mart interactions must go through the `bank_statement_parser` API (D001).
- The `event_log` table is populated exclusively by SQLite-level triggers —
  presenters and models must **never** write to it directly (NFR-4).

### Worker Thread Pattern
```python
class WorkerSignals(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

class SQWorker(QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = WorkerSignals()

    def run(self) -> None:
        # background work here
        self.signals.progress.emit(50)
        self.signals.finished.emit()

QThreadPool.globalInstance().start(worker)
```

### Model Return Convention
All model mutation methods return a **3-tuple**:
```python
(success: bool, record_id: str, message: str)
```
Callers must check `result[0]` and handle the `False` case.

---

## Error Handling

- Use `StanErrorMessage` (subclass of `QErrorMessage`) for database errors and
  unrecoverable failures — always modal, shown via `.showMessage(str)`.
- Use `StanInfoMessage` (subclass of `QMessageBox`) for confirmations before
  destructive actions, using `Yes | Cancel` with `Cancel` as default.
- Catch-all in presenters: `except Exception as e:` — use for Qt slot callbacks.
- For disk-operation failures, use `traceback.print_exc()` and surface the error
  to the user via a dialog. Do not silently swallow exceptions.
- Partial side-effects (e.g. folder creation) must be rolled back in `except`
  blocks before re-surfacing the error.
- No structured logging framework — use `print()` for debug output.

---

## Key Libraries & What to Avoid

| Use | Avoid |
|---|---|
| `polars` (via `bsp`) for tabular data | `pandas` (D003) |
| `pathlib.Path` for all paths | `os.path` string concatenation |
| `uuid.uuid4().hex` for primary keys | auto-increment integers |
| `QSqlTableModel` for GUI DB access | raw `sqlite3` at runtime |
| `uv` for package management | `pip`, `poetry`, `conda` |
| `bank_statement_parser` API for mart | direct mart DB access |

DuckDB experiments live in `data/duck.py` (entirely commented out); do not
uncomment or extend — it is scheduled for deletion (D004).

---

## Docs Site — Logo & Image Theme Switching

The docs site (`docs/`) uses [Zensical](https://github.com/zensical/zensical) (a
MkDocs Material fork). Two independent mechanisms handle theme-aware assets:

### Nav-bar logo

**How it works:**

- `docs/overrides/partials/logo.html` overrides the theme's built-in `logo.html`
  partial. It unconditionally renders **two `<img>` elements**:
  - `.stan-logo-light` — `docs/assets/logo-light.svg` (book icon + dark text, for light mode)
  - `.stan-logo-dark`  — `docs/assets/logo-dark.svg`  (book icon + light text, for dark mode)
- The partial is included at **two** sites: `header.html` (top bar) and `nav.html`
  (mobile drawer title). This produces **4 `<img>` elements** on the page — 2 per
  location. This is intentional; do not try to "fix" it.
- `docs/assets/stylesheets/extra.css` shows exactly one per location via
  `[data-md-color-scheme]` selectors. `!important` is required because the
  theme's own `.md-logo img { display: block }` rule has higher specificity
  and would otherwise force both images visible simultaneously:
  - Light scheme: `.stan-logo-dark { display: none !important }`
  - Dark scheme: `.stan-logo-light { display: none !important }`

**Critical rule — do NOT set `theme.logo` in `mkdocs.yml`:**

If `theme.logo` is set, Zensical's built-in `logo.html` would normally render
`<img src="{{ config.theme.logo }}">`. Our partial override replaces that built-in
entirely, so `theme.logo` has no effect on rendering — but some Zensical versions
also use `config.theme.logo` in *other* template locations (e.g. the nav title
label), which can inject a plain `<img>` alongside our partial's output, producing a
visible duplicate. Keep `theme.logo` absent from `mkdocs.yml` at all times.

The partial is **unconditional** (no `{% if config.theme.logo %}` guard) precisely
because we never want it to fall through to the built-in icon-SVG fallback.

**Logo source files:**

`docs/assets/logo-light.svg` and `docs/assets/logo-dark.svg` are copies of the
canonical sources at `src/openstan/icons/logo-light.svg` and `logo-dark.svg`. If
the icon or wordmark changes, update both locations.

---

### Page screenshots (`#only-light` / `#only-dark`)

All screenshots in `docs/` follow this pattern:

```markdown
![Alt text — light](assets/screenshots/foo.png#only-light)
![Alt text — dark](assets/screenshots/dark/foo.png#only-dark)
```

- Light variants live at `assets/screenshots/<name>.png`
- Dark variants live at `assets/screenshots/dark/<name>.png`
- Zensical's palette CSS hides `#only-light` images in dark mode automatically.
- `extra.css` adds the complementary rule to hide `#only-dark` images in light mode
  (Zensical omits this direction).

Do not use inline `style` attributes or JavaScript for theme-conditional images —
the fragment + CSS approach is sufficient and consistent across all pages.

---

## Dead Code — Do Not Extend

- `src/openstan/data/ops.py` — legacy raw `QSqlQuery` helpers; references an
  old DB filename. Scheduled for removal.
- `src/openstan/data/duck.py` — commented-out DuckDB experiments (D004).
- `src/openstan/models/event_log_model.py` — `EventLogModel` is imported nowhere;
  audit log is trigger-driven.

---

## Pending: Code Signing Setup

Both signing pipelines are partially complete but blocked on account approval.
Do not attempt to implement these steps until the relevant account is confirmed.

---

### Windows — SignPath Foundation

**Status:** Application submitted at `https://signpath.org/apply`; approval pending.

**URLs referenced in the application:**
- Download URL: `https://openstan.org/installation/`
- Privacy Policy: `https://openstan.org/privacy/`
- Code Signing Policy: `https://openstan.org/codesigning/`

**What needs implementing once approved:**

1. SignPath will provide an **Organisation slug** and **Project slug** — note these down.
2. Generate a **CI User token** in the SignPath dashboard and add it as a GitHub Actions
   secret: `SIGNPATH_API_TOKEN`.
3. Note the **Signing Policy name** (e.g. `release-signing`) from the SignPath project.
4. Restructure the Windows job in `.github/workflows/release.yml`:
   - Upload the unsigned MSI as a GitHub Actions artifact
   - Add a SignPath signing step using the official action:
     ```yaml
     - name: Sign MSI (SignPath)
       uses: signpath/github-action-submit-signing-request@v1
       with:
         api-token: ${{ secrets.SIGNPATH_API_TOKEN }}
         organization-id: '<org-slug>'
         project-slug: 'openstan'
         signing-policy-slug: 'release-signing'
         artifact-configuration-slug: 'msi'
         github-artifact-id: '<artifact-id>'
         wait-for-completion: true
         output-artifact-directory: dist/
     ```
   - Attach the downloaded signed MSI to the release instead of the unsigned one.
5. Every release requires **manual approval** in the SignPath dashboard before signing
   proceeds — this is by design for the free Foundation tier.

**Critical notes:**
- Unsigned bundled DLLs (PyQt6, Polars, etc.) are explicitly permitted under the
  Code Signing Policy at `docs/codesigning.md` — do not change this policy.
- MFA must be enabled on the GitHub account linked to SignPath (verify before first use).
- SignPath Foundation is free for OSS projects; do not upgrade to a paid tier.

---

### macOS — Apple Developer ID + Notarisation

**Status:** Apple Developer Program purchased (£79/year); certificate issuance
pending (up to 48 hours from purchase).

**What to collect from Apple once the account is active:**

1. **Developer ID Application certificate** — issue at
   developer.apple.com → Certificates → "+" → "Developer ID Application".
   Download, double-click to install into Keychain on a Mac.
   Export from Keychain Access as a `.p12` file with a strong password.
   Base64-encode it for the GitHub secret:
   ```bash
   base64 -i DeveloperIDApplication.p12 | pbcopy
   ```
2. **Team ID** — 10-character alphanumeric string shown at
   developer.apple.com top-right under your name (e.g. `AB12CD34EF`).
3. **App-specific password** — generate at appleid.apple.com →
   Sign-In & Security → App-Specific Passwords. Label it "openstan CI".

**GitHub Actions secrets to add** (Settings → Secrets and variables → Actions):

| Secret name | Value |
|---|---|
| `APPLE_CERTIFICATE_P12` | Base64-encoded `.p12` file (see above) |
| `APPLE_CERTIFICATE_PASSWORD` | Password set when exporting the `.p12` |
| `APPLE_ID` | Apple ID email address |
| `APPLE_APP_PASSWORD` | App-specific password generated above |
| `APPLE_TEAM_ID` | 10-character Team ID |

**New file to create:** `packaging/macos/entitlements.plist`

PyQt6 requires the `allow-unsigned-executable-memory` entitlement to run
under Apple's hardened runtime (required for notarisation):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
  <true/>
</dict>
</plist>
```

**Steps to add to the macOS job in `.github/workflows/release.yml`**
(insert after `bdist_dmg` produces `dist/*.dmg`, before the upload step):

```yaml
- name: Import Apple Developer ID certificate
  env:
    APPLE_CERTIFICATE_P12: ${{ secrets.APPLE_CERTIFICATE_P12 }}
    APPLE_CERTIFICATE_PASSWORD: ${{ secrets.APPLE_CERTIFICATE_PASSWORD }}
  run: |
    echo "$APPLE_CERTIFICATE_P12" | base64 --decode > certificate.p12
    security create-keychain -p "" build.keychain
    security default-keychain -s build.keychain
    security unlock-keychain -p "" build.keychain
    security import certificate.p12 -k build.keychain \
      -P "$APPLE_CERTIFICATE_PASSWORD" -T /usr/bin/codesign
    security set-key-partition-list -S apple-tool:,apple: \
      -s -k "" build.keychain
    rm certificate.p12

- name: Sign .app bundle
  env:
    APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
  run: |
    APP=$(find dist -name "*.app" | head -1)
    codesign --deep --force --options runtime \
      --entitlements packaging/macos/entitlements.plist \
      --sign "Developer ID Application: Jason Farrar ($APPLE_TEAM_ID)" \
      "$APP"

- name: Sign .dmg
  env:
    APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
  run: |
    DMG=$(find dist -name "*.dmg" | head -1)
    codesign --force --sign \
      "Developer ID Application: Jason Farrar ($APPLE_TEAM_ID)" \
      "$DMG"

- name: Notarise .dmg
  env:
    APPLE_ID: ${{ secrets.APPLE_ID }}
    APPLE_APP_PASSWORD: ${{ secrets.APPLE_APP_PASSWORD }}
    APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
  run: |
    DMG=$(find dist -name "*.dmg" | head -1)
    xcrun notarytool submit "$DMG" \
      --apple-id "$APPLE_ID" \
      --password "$APPLE_APP_PASSWORD" \
      --team-id "$APPLE_TEAM_ID" \
      --wait

- name: Staple notarisation ticket to .dmg
  run: |
    DMG=$(find dist -name "*.dmg" | head -1)
    xcrun stapler staple "$DMG"
```

**Critical notes:**
- The `.app` bundle must be signed before it is repacked into the `.dmg`. Check
  whether cx_Freeze's `bdist_dmg` creates the DMG from a pre-existing `.app` or
  builds `.app` and `.dmg` together — if the latter, the `.app` signing step must
  come before `bdist_dmg` runs, or the DMG must be manually repacked after signing.
- `codesign --deep` signs all nested binaries (`.dylib`, `.so`, Python extensions).
  If any nested binary fails to sign, notarisation will be rejected.
- If notarisation is rejected, retrieve the full log with:
  `xcrun notarytool log <submission-id> --apple-id ... --password ... --team-id ...`
- The Developer ID certificate expires after 5 years — set a calendar reminder.
- Annual Apple Developer Program renewal (£79/year) is required to keep the
  certificate trusted; lapsed membership revokes notarisation.
