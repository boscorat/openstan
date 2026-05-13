[![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/boscorat/openstan?include_prereleases)](https://github.com/boscorat/openstan/releases)
[![CI](https://github.com/boscorat/openstan/actions/workflows/release.yml/badge.svg)](https://github.com/boscorat/openstan/actions/workflows/release.yml)
[![Docs](https://img.shields.io/badge/docs-openstan.org-informational)](https://openstan.org)

# openstan

**openstan** is a free, open-source desktop application for importing, organising, and analysing
UK bank statement PDFs. All data is stored locally in a SQLite database on your own machine —
no account, no cloud, no data leaves your device.

It provides a no-code workflow: import PDFs, review parse results, build reports, and export
data to Excel, CSV, or JSON — no Python or database knowledge required.

![Import results](https://raw.githubusercontent.com/boscorat/openstan/master/docs/assets/screenshots/dark/statement_results.png)

> Full documentation: **[openstan.org](https://openstan.org)**

---

## Features

- Import bank statement PDFs one at a time or entire folders in a single pass
- Review import results with per-file debug output and the original PDF side by side
- Detect coverage gaps — missing statements between consecutive periods are flagged automatically
- Export transactions to Excel, CSV, or JSON as a flat table or full star-schema dataset
- Build no-code reports with filters, grouping, and aggregations
- Light and dark theme, full keyboard navigation
- Supports HSBC UK, TSB UK, and more via configurable TOML bank definitions

---

## Download

Pre-built installers are available on the
[Releases](https://github.com/boscorat/openstan/releases) page:

| Platform | File |
|---|---|
| Windows 10 / 11 | `.msi` |
| macOS 12+ (Intel & Apple Silicon) | `.dmg` |
| Ubuntu / Debian | `.deb` |
| Fedora / RHEL / CentOS | `.rpm` |

No Python installation required.

---

## Running from source

**Requirements:** [uv](https://docs.astral.sh/uv/) — handles Python 3.14 automatically.

```bash
git clone https://github.com/boscorat/openstan.git
cd openstan
uv sync
uv run openstan
```

Linux users also need a few Qt XCB system libraries — see
[Installation](https://openstan.org/installation/) for details.

---

## Development

```bash
uv run ruff check .           # lint
uv run ruff format --check .  # format check
uv run pyrefly check          # type check
uv run pytest tests/ -v       # tests
```

All four must pass before opening a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).
