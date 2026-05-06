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

## Before opening a pull request

All four commands must exit cleanly:

```bash
uv run ruff check .           # lint
uv run ruff format --check .  # format (auto-fix: uv run ruff format .)
uv run pyrefly check          # type check
uv run pytest tests/ -v       # tests
```
