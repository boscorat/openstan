import os
import sys
from pathlib import Path


def _base_dir() -> str:
    """Return the root directory that contains the ``openstan`` package data.

    In a normal (development) run this is the directory that holds this file,
    i.e. ``src/openstan/``.

    When the application is **frozen** the package data is extracted alongside
    the executable rather than sitting next to a ``.py`` source file:

    * **PyInstaller** (both one-file and one-dir modes) sets ``sys._MEIPASS``
      to the temporary directory where all bundled files are extracted.  Data
      added via the ``datas`` list in the ``.spec`` file lands inside a
      ``openstan/`` sub-directory there, mirroring the original layout.

    * **cx_Freeze** sets ``sys.frozen = True`` and places the frozen package
      alongside the executable.  ``sys.executable`` is the path to the exe, so
      ``os.path.dirname(sys.executable)`` gives the install root, and the
      package data lives in an ``openstan/`` sub-directory of that root.

    Both cases produce the same logical structure; only the root anchor differs.
    """
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            # PyInstaller
            return os.path.join(sys._MEIPASS, "openstan")  # type: ignore[attr-defined]
        # cx_Freeze: executable is in <install_root>/, package data is in
        # <install_root>/lib/openstan/
        return os.path.join(os.path.dirname(sys.executable), "lib", "openstan")
    # Normal / development run
    return os.path.dirname(__file__)


class Paths:
    base: str = _base_dir()
    icons: str = os.path.join(base, "icons")
    data: str = os.path.join(base, "data")
    fonts: str = os.path.join(data, "fonts")

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    @classmethod
    def _theme_subdir(cls) -> str:
        """Return 'dark' or 'light' based on the current application palette."""
        from PyQt6.QtGui import QPalette
        from PyQt6.QtWidgets import QApplication

        instance = QApplication.instance()
        app = instance if isinstance(instance, QApplication) else None
        if app is not None:
            bg = app.palette().color(QPalette.ColorRole.Window)
            return "dark" if bg.lightness() < 128 else "light"
        return "light"

    # ------------------------------------------------------------------ #
    # Public icon resolvers                                                #
    # ------------------------------------------------------------------ #

    @classmethod
    def icon(cls, filename: str) -> str:
        """Resolve a path in the flat icons root (theme-neutral assets)."""
        return os.path.join(cls.icons, filename)

    @classmethod
    def themed_icon(cls, filename: str) -> str:
        """Resolve filename from the light/ or dark/ subdir based on the
        current application palette.  Falls back to 'light' if no
        QApplication exists yet."""
        return os.path.join(cls.icons, cls._theme_subdir(), filename)

    @classmethod
    def logo(cls, with_tagline: bool = False) -> str:
        """Return the theme-appropriate full logo (book icon + wordmark)."""
        suffix = "-tagline" if with_tagline else ""
        filename = f"logo-{cls._theme_subdir()}{suffix}.svg"
        return os.path.join(cls.icons, filename)

    @classmethod
    def wordmark(cls, with_tagline: bool = False) -> str:
        """Return the theme-appropriate wordmark (no book icon)."""
        suffix = "-tagline" if with_tagline else ""
        filename = f"wordmark-{cls._theme_subdir()}{suffix}.svg"
        return os.path.join(cls.icons, filename)

    # ------------------------------------------------------------------ #
    # Database resolver                                                    #
    # ------------------------------------------------------------------ #

    @classmethod
    def databases(cls, filename: str) -> str:
        """Resolve a path for a database file.

        When frozen (installed .deb/.rpm/.msi/.dmg) the bundled ``data/``
        directory is inside a read-only system prefix, so databases must live
        in a user-writable location instead.  We use
        ``~/.local/share/openstan/`` on all platforms (XDG-compatible on Linux,
        acceptable on macOS and Windows too).

        In development (unfrozen) we keep the original behaviour of storing
        databases next to the package source so the dev environment stays
        self-contained.
        """
        if getattr(sys, "frozen", False):
            user_data = Path.home() / ".local" / "share" / "openstan"
            user_data.mkdir(parents=True, exist_ok=True)
            return str(user_data / filename)
        return os.path.join(cls.data, filename)

    # ------------------------------------------------------------------ #
    # Font resolver                                                        #
    # ------------------------------------------------------------------ #

    @classmethod
    def font(cls, filename: str) -> str:
        """Resolve a path to a bundled font file in data/fonts/."""
        return os.path.join(cls.fonts, filename)
