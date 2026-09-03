"""Generate bank dropdown options for GitHub issue templates.

Reads bank_statement_parser TOML configs and updates the bank dropdown
in .github/ISSUE_TEMPLATE/bug_report.yml.

Run before committing::

    uv run python scripts/generate_issue_template.py
"""

from __future__ import annotations

import re
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


def _load_bank_names(import_dir: Path) -> list[str]:
    """Return sorted list of bank company names."""
    banks: list[str] = []
    for bank_dir in sorted(import_dir.iterdir()):
        if not bank_dir.is_dir() or bank_dir.name.startswith("."):
            continue
        companies_toml = bank_dir / "companies.toml"
        if not companies_toml.exists():
            continue
        with open(companies_toml, "rb") as fh:
            companies: dict[str, dict[str, str]] = tomllib.load(fh)
        for data in companies.values():
            banks.append(data["company"])
    return banks


def _update_bug_report_yaml(bank_names: list[str]) -> None:
    """Replace the bank dropdown options in bug_report.yml."""
    yml_path = Path(".github/ISSUE_TEMPLATE/bug_report.yml")
    content = yml_path.read_text()

    pattern = r"(# AUTO-GENERATED: bank options start\n)(.*?)(# AUTO-GENERATED: bank options end)"
    options = (
        "\n".join(f"        - {name}" for name in bank_names)
        + "\n        - Other / N/A\n        "
    )
    replacement = f"\\1{options}\\3"
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    yml_path.write_text(new_content)
    print(f"Updated {yml_path} with {len(bank_names)} banks")


def main() -> None:
    """Read TOML configs and update bug_report.yml bank dropdown."""
    import_dir = _find_import_dir()
    bank_names = _load_bank_names(import_dir)
    _update_bug_report_yaml(bank_names)


if __name__ == "__main__":
    main()
