"""Entry point for ``python -m openstan`` and cx_Freeze frozen builds.

Environment variables are set here, *before* any other import, so that
third-party packages that read env vars at module-level pick them up correctly.

BSP_DEFAULT_PROJECT_ROOT
    Redirects bank_statement_parser's default project root (used for bundled
    config templates) to a user-writable location.  Without this, bsp tries to
    create directories inside its own install prefix on first import, which
    fails with PermissionError when installed into a read-only system prefix
    such as /usr/lib (e.g. after installing the .deb or .rpm package).

BSP_SKIP_DEFAULT_PROJECT_INIT
    Tells bsp not to call ProjectPaths.resolve().ensure_dirs() at import time
    for the default project root.  The host application (openstan) manages the
    project directory lifecycle via validate_or_initialise_project() instead.
"""

import os
from pathlib import Path

# Redirect bsp's default project root to ~/.local/share/openstan/bsp/
# before bank_statement_parser is imported (it reads this at module level).
os.environ.setdefault(
    "BSP_DEFAULT_PROJECT_ROOT",
    str(Path.home() / ".local" / "share" / "openstan" / "bsp"),
)
os.environ.setdefault("BSP_SKIP_DEFAULT_PROJECT_INIT", "1")

from openstan import main  # noqa: E402

if __name__ == "__main__":
    main()
