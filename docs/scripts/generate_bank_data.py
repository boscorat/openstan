"""Generate supported banks markdown from bank_statement_parser TOML configs.

Reads companies.toml and accounts.toml from each bank's config directory
and writes a markdown table to ``docs/includes/supported_banks.md``.

Run before zensical build::

    uv run python docs/scripts/generate_bank_data.py
"""

from __future__ import annotations

import tomllib
from pathlib import Path


def _find_import_dir() -> Path:
    """Locate the ``import`` config directory inside bank_statement_parser."""
    import bank_statement_parser

    pkg_dir = Path(bank_statement_parser.__file__).parent
    import_dir = pkg_dir / "project" / "config" / "import"
    if not import_dir.is_dir():
        msg = f"import directory not found: {import_dir}"
        raise RuntimeError(msg)
    return import_dir


def _load_bank_data(import_dir: Path) -> list[dict[str, object]]:
    """Parse every bank sub-folder and return a sorted list of bank dicts."""
    account_types_path = import_dir / "account_types.toml"
    with open(account_types_path, "rb") as fh:
        account_types: dict[str, dict[str, str]] = tomllib.load(fh)

    banks: list[dict[str, object]] = []
    for bank_dir in sorted(import_dir.iterdir()):
        if not bank_dir.is_dir() or bank_dir.name.startswith("."):
            continue

        companies_toml = bank_dir / "companies.toml"
        accounts_toml = bank_dir / "accounts.toml"
        if not (companies_toml.exists() and accounts_toml.exists()):
            continue

        with open(companies_toml, "rb") as fh:
            companies: dict[str, dict[str, str]] = tomllib.load(fh)
        with open(accounts_toml, "rb") as fh:
            accounts: dict[str, dict[str, str]] = tomllib.load(fh)

        bank_key = bank_dir.name
        company_name: str = companies[bank_key]["company"]

        seen: set[str] = set()
        account_list: list[dict[str, str]] = []
        for account_data in accounts.values():
            name: str = account_data["account"]
            if name in seen:
                continue
            seen.add(name)
            type_key = account_data.get("account_type_key", "")
            type_label = account_types.get(type_key, {}).get("account_type", type_key)
            account_list.append({"name": name, "type": type_label})

        banks.append({"key": bank_key, "name": company_name, "accounts": account_list})

    return banks


def _render_markdown(banks: list[dict[str, object]]) -> str:
    """Render markdown table rows from the parsed bank data (no header)."""
    lines: list[str] = []
    for bank in banks:
        accounts: list[dict[str, str]] = bank["accounts"]  # type: ignore[assignment]
        formatted = [
            f"{a['name']} ({a['type']})"
            if a["type"] and a["type"].lower() not in a["name"].lower()
            else a["name"]
            for a in accounts
        ]
        account_str = ", ".join(formatted)
        lines.append(f"| **{bank['name']}** | {account_str} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    """Read TOML configs and write ``docs/includes/supported_banks.md``."""
    import_dir = _find_import_dir()
    banks = _load_bank_data(import_dir)
    md = _render_markdown(banks)

    out_dir = Path(__file__).resolve().parent.parent / "includes"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "supported_banks.md"
    out_file.write_text(md)

    print(f"Generated {out_file} with {len(banks)} banks")


if __name__ == "__main__":
    main()
