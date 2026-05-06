# openstan

**openstan** is a free, open-source desktop application for importing,
organising, and analysing UK bank statement PDFs.

It provides a no-code workflow: import PDFs, review parse results,
build reports, and export data to Excel, CSV, or JSON — no Python or
database knowledge required.

![Import results](docs/assets/screenshots/dark/statement_results.png)

> Full documentation: **[openstan.org](https://openstan.org)**

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
