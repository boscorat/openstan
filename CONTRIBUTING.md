# Contributing to openstan

Thanks for your interest in contributing.

---

## Prerequisites

Install [uv](https://docs.astral.sh/uv/). That's it — `uv` will download
and manage the correct Python version (3.14) automatically.

---

## Getting started

```bash
git clone https://github.com/boscorat/openstan.git
cd openstan
uv sync --all-groups
uv run openstan
```

Linux users need a few Qt XCB system libraries:

```bash
sudo apt install libegl1 libxcb-cursor0 libxkbcommon-x11-0 \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
    libxcb-render-util0 libxcb-xinerama0 libxcb-xfixes0
```

---

## Code style

- **Linter / formatter:** [Ruff](https://docs.astral.sh/ruff/) — no Black, no isort.
- **Line length:** 88 characters.
- **Quotes:** double quotes.
- **Type checker:** [Pyrefly](https://pyrefly.org/) — not mypy. Annotate all function return types.
- All Qt widgets must use the `Stan`-prefixed subclasses from
  `src/openstan/components.py` rather than raw PyQt6 originals.

See [AGENTS.md](AGENTS.md) for the full architecture guide, naming conventions,
and database access rules.

---

## Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
Every commit message must follow this format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Allowed types:**

| Type | Use for |
|---|---|
| `feat` | New user-facing feature |
| `fix` | Bug fix |
| `docs` | Documentation only changes |
| `build` | Build system or dependency changes |
| `ci` | CI/CD configuration changes |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks (tooling, config, etc.) |

**Examples:**

```
feat: add Monzo bank parser support
fix: prevent crash when importing empty PDF
docs: update installation instructions for Ubuntu
build: bump PySide6 to 6.8.0
ci: add changelog generation to release workflow
```

The changelog is auto-generated from commit messages on each release. Using the correct
type ensures changes appear in the right section.

---

## Before opening a pull request

All four commands must exit cleanly:

```bash
uv run ruff check .           # lint
uv run ruff format --check .  # format (auto-fix: uv run ruff format .)
uv run pyrefly check          # type check
uv run pytest tests/ -v       # tests
```
