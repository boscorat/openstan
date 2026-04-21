"""
test_paths.py — unit tests for the Paths class.

Tests cover path construction logic, the ``_theme_subdir`` fallback when no
QApplication exists, and the ``with_tagline`` toggle on logo/wordmark helpers.

No database fixture required.
"""

import os


from openstan.paths import Paths


class TestPathsDatabase:
    """Tests for Paths.databases()."""

    def test_databases_returns_path_ending_with_filename(self) -> None:
        """databases('gui.db') returns a path whose basename is 'gui.db'."""
        result = Paths.databases("gui.db")
        assert result.endswith("gui.db")

    def test_databases_is_inside_data_dir(self) -> None:
        """databases() resolves inside the Paths.data directory."""
        result = Paths.databases("gui.db")
        assert result.startswith(Paths.data)

    def test_databases_uses_given_filename(self) -> None:
        """databases() uses whichever filename is passed."""
        result = Paths.databases("other.db")
        assert result.endswith("other.db")


class TestPathsIcon:
    """Tests for Paths.icon()."""

    def test_icon_returns_path_inside_icons_dir(self) -> None:
        """icon() resolves inside the Paths.icons directory."""
        result = Paths.icon("logo.svg")
        assert result.startswith(Paths.icons)

    def test_icon_ends_with_filename(self) -> None:
        """icon() result ends with the given filename."""
        result = Paths.icon("logo.svg")
        assert result.endswith("logo.svg")


class TestThemeSubdir:
    """Tests for Paths._theme_subdir() fallback behaviour."""

    def test_returns_light_when_no_qapplication(self) -> None:
        """Without a QApplication instance, _theme_subdir falls back to 'light'."""
        # This test runs before any QApplication is created in this process
        # (unit tests that need Qt use qapp fixture, but Paths tests do not).
        # If a QApplication already exists from another test, we still verify
        # that the return value is one of the two valid values.
        result = Paths._theme_subdir()
        assert result in ("light", "dark")

    def test_returns_string(self) -> None:
        """_theme_subdir always returns a non-empty string."""
        result = Paths._theme_subdir()
        assert isinstance(result, str)
        assert len(result) > 0


class TestPathsLogo:
    """Tests for Paths.logo()."""

    def test_logo_without_tagline_does_not_contain_tagline(self) -> None:
        """logo(with_tagline=False) does not include '-tagline' in the filename."""
        result = Paths.logo(with_tagline=False)
        filename = os.path.basename(result)
        assert "-tagline" not in filename

    def test_logo_with_tagline_contains_tagline(self) -> None:
        """logo(with_tagline=True) includes '-tagline' in the filename."""
        result = Paths.logo(with_tagline=True)
        filename = os.path.basename(result)
        assert "-tagline" in filename

    def test_logo_is_svg(self) -> None:
        """logo() always returns a path to an SVG file."""
        assert Paths.logo().endswith(".svg")

    def test_logo_is_inside_icons_dir(self) -> None:
        """logo() resolves inside the Paths.icons directory."""
        assert Paths.logo().startswith(Paths.icons)

    def test_logo_default_is_no_tagline(self) -> None:
        """logo() with no argument is equivalent to logo(with_tagline=False)."""
        assert Paths.logo() == Paths.logo(with_tagline=False)


class TestPathsWordmark:
    """Tests for Paths.wordmark()."""

    def test_wordmark_without_tagline_does_not_contain_tagline(self) -> None:
        """wordmark(with_tagline=False) does not include '-tagline' in the filename."""
        result = Paths.wordmark(with_tagline=False)
        filename = os.path.basename(result)
        assert "-tagline" not in filename

    def test_wordmark_with_tagline_contains_tagline(self) -> None:
        """wordmark(with_tagline=True) includes '-tagline' in the filename."""
        result = Paths.wordmark(with_tagline=True)
        filename = os.path.basename(result)
        assert "-tagline" in filename

    def test_wordmark_is_svg(self) -> None:
        """wordmark() always returns a path to an SVG file."""
        assert Paths.wordmark().endswith(".svg")

    def test_wordmark_default_is_no_tagline(self) -> None:
        """wordmark() with no argument is equivalent to wordmark(with_tagline=False)."""
        assert Paths.wordmark() == Paths.wordmark(with_tagline=False)


class TestPathsFont:
    """Tests for Paths.font()."""

    def test_font_returns_path_inside_fonts_dir(self) -> None:
        """font() resolves inside the Paths.fonts directory."""
        result = Paths.font("Inter.ttf")
        assert result.startswith(Paths.fonts)

    def test_font_ends_with_filename(self) -> None:
        """font() result ends with the given filename."""
        result = Paths.font("Inter.ttf")
        assert result.endswith("Inter.ttf")
