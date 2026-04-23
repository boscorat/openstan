"""Entry point for ``python -m openstan`` and cx_Freeze frozen builds.

Environment variables are set here, *before* any other import, so that
third-party packages that read env vars at module-level pick them up correctly.

BSP_DEFAULT_PROJECT_ROOT
    Redirects bank_statement_parser's default project root (used for bundled
    config templates) to a user-writable, platform-appropriate location:

    * **Windows** — ``%APPDATA%\\openstan\\bsp\\``
    * **macOS**   — ``~/Library/Application Support/openstan/bsp/``
    * **Linux**   — ``~/.local/share/openstan/bsp/``

    Without this, bsp tries to create directories inside its own install
    prefix on first import, which fails with PermissionError when installed
    into a read-only system prefix such as /usr/lib (Linux .deb/.rpm) or
    the macOS .app bundle.

    IMPORTANT: bsp derives BASE_CONFIG_IMPORT/EXPORT/REPORT from this path at
    module-import time, so the redirected directory must be pre-seeded with the
    template files from the bsp package before any project scaffolding occurs.
    _seed_bsp_default_project() below handles this on first run.

BSP_SKIP_DEFAULT_PROJECT_INIT
    Tells bsp not to call ProjectPaths.resolve().ensure_dirs() at import time
    for the default project root.  The host application (openstan) manages the
    project directory lifecycle via validate_or_initialise_project() instead.
"""

import os
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve the bsp package install location BEFORE setting the env var redirect,
# so we always have the real source regardless of BSP_DEFAULT_PROJECT_ROOT.
# ---------------------------------------------------------------------------

# bank_statement_parser.__file__ == .../bank_statement_parser/__init__.py
# We derive the path without importing the package yet (avoids module-level
# side-effects running before env vars are set).
import importlib.util as _ilu

from openstan.paths import _user_data_dir

_bsp_spec = _ilu.find_spec("bank_statement_parser")
_BSP_PKG_PROJECT: Path | None = (
    Path(_bsp_spec.origin).parent / "project"
    if _bsp_spec and _bsp_spec.origin
    else None
)

# ---------------------------------------------------------------------------
# Set env vars BEFORE importing bank_statement_parser.
# ---------------------------------------------------------------------------

_BSP_USER_ROOT = _user_data_dir() / "bsp"

os.environ.setdefault("BSP_DEFAULT_PROJECT_ROOT", str(_BSP_USER_ROOT))
os.environ.setdefault("BSP_SKIP_DEFAULT_PROJECT_INIT", "1")


def _seed_bsp_default_project() -> None:
    """Copy bsp's bundled project/ tree into the redirected user root.

    Called once at startup (before the Qt app is created).  Uses the package's
    own ``project/`` subtree — located relative to ``bank_statement_parser``'s
    ``__file__`` and therefore immune to the ``BSP_DEFAULT_PROJECT_ROOT``
    redirect — as the authoritative template source.

    Strategy: copy any file that is present in the package source but absent
    from the user root, so upgrades add new templates without clobbering any
    user edits.
    """
    if _BSP_PKG_PROJECT is None or not _BSP_PKG_PROJECT.exists():
        return  # can't locate package source; nothing to seed

    for src in _BSP_PKG_PROJECT.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(_BSP_PKG_PROJECT)
        dst = _BSP_USER_ROOT / rel
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


_seed_bsp_default_project()

from openstan import main  # noqa: E402

if __name__ == "__main__":
    main()
