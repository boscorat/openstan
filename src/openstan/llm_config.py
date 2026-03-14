"""llm_config.py — LLMConfig dataclass and per-project TOML loader/saver.

Configuration for the Ollama-backed transaction categoriser is stored in
``<project>/config/llm_categories.toml``.  If that file is absent, hard-coded
defaults are returned so the UI is always usable even on older projects that
pre-date this feature.
"""

from __future__ import annotations

import sys
import tomllib
import traceback
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Hard-coded defaults — mirrors the content of the bundled llm_categories.toml
# ---------------------------------------------------------------------------

_DEFAULT_HOST = "http://localhost:11434"
_DEFAULT_MODEL = "qwen2.5:1.5b"
_DEFAULT_TEMPERATURE = 0
_DEFAULT_MAX_TOKENS = 20
_DEFAULT_KEEP_ALIVE = "30m"

_DEFAULT_SYSTEM_PROMPT = (
    "You are a UK bank transaction categoriser. "
    "Given a transaction description, reply with exactly one category from the list below. "
    "Reply with the category name only. No explanation, no punctuation."
)

_DEFAULT_CATEGORIES: list[str] = [
    "Groceries",
    "Utilities",
    "Bills",
    "Transport",
    "Fuel",
    "Eating Out",
    "Entertainment",
    "Shopping",
    "Health & Pharmacy",
    "Insurance",
    "Savings & Investments",
    "Income",
    "Transfer",
    "Refund",
    "Bank Fees",
    "Other",
]

_CONFIG_FILENAME = "llm_categories.toml"


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LLMConfig:
    """Runtime configuration for the Ollama transaction categoriser."""

    host: str = _DEFAULT_HOST
    model: str = _DEFAULT_MODEL
    temperature: int = _DEFAULT_TEMPERATURE
    max_tokens: int = _DEFAULT_MAX_TOKENS
    keep_alive: str = _DEFAULT_KEEP_ALIVE
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT
    categories: list[str] = field(default_factory=lambda: list(_DEFAULT_CATEGORIES))

    @property
    def config_path(self) -> None:
        """Not stored on the dataclass — callers pass project_path explicitly."""
        return None


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_llm_config(project_path: Path) -> LLMConfig:
    """Load ``llm_categories.toml`` from *project_path*/config/.

    Returns a fully-populated :class:`LLMConfig` using hard-coded defaults for
    any missing keys, so the function never raises on partial or absent config.
    """
    cfg_file = project_path / "config" / _CONFIG_FILENAME
    if not cfg_file.exists():
        return LLMConfig()

    try:
        with open(cfg_file, "rb") as fh:
            raw = tomllib.load(fh)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return LLMConfig()

    llm = raw.get("llm", {})
    prompt_section = llm.get("system_prompt", {})
    categories = raw.get("categories", {}).get("list", _DEFAULT_CATEGORIES)

    return LLMConfig(
        host=llm.get("host", _DEFAULT_HOST),
        model=llm.get("model", _DEFAULT_MODEL),
        temperature=int(llm.get("temperature", _DEFAULT_TEMPERATURE)),
        max_tokens=int(llm.get("max_tokens", _DEFAULT_MAX_TOKENS)),
        keep_alive=str(llm.get("keep_alive", _DEFAULT_KEEP_ALIVE)),
        system_prompt=prompt_section.get("text", _DEFAULT_SYSTEM_PROMPT).strip(),
        categories=list(categories) if categories else list(_DEFAULT_CATEGORIES),
    )


# ---------------------------------------------------------------------------
# Saver
# ---------------------------------------------------------------------------

_TOML_TEMPLATE = """\
[llm]
host        = {host!r}
model       = {model!r}
temperature = {temperature}
max_tokens  = {max_tokens}
keep_alive  = {keep_alive!r}

[llm.system_prompt]
text = \"\"\"
{system_prompt}
\"\"\"

[categories]
list = [
{category_lines}]
"""


def save_llm_config(config: LLMConfig, project_path: Path) -> tuple[bool, str]:
    """Serialise *config* to ``<project_path>/config/llm_categories.toml``.

    Returns ``(True, "")`` on success or ``(False, error_message)`` on failure.
    """
    cfg_file = project_path / "config" / _CONFIG_FILENAME
    category_lines = "".join(f'    "{c}",\n' for c in config.categories)
    content = _TOML_TEMPLATE.format(
        host=config.host,
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        keep_alive=config.keep_alive,
        system_prompt=config.system_prompt,
        category_lines=category_lines,
    )
    try:
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        cfg_file.write_text(content, encoding="utf-8")
        return True, ""
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        return False, str(exc)
