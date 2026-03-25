import os


class Paths:
    base: str = os.path.dirname(__file__)
    icons: str = os.path.join(base, "icons")
    data: str = os.path.join(base, "data")

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
        return os.path.join(cls.data, filename)
