# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for openstan.

Usage (run from the repository root with the uv-managed venv active):

    uv run pyinstaller openstan.spec

This produces a one-directory build under ``dist/openstan/``.  Wrap it with
platform installers as follows:

    Windows:  NSIS or WiX (see .github/workflows/release.yml)
    macOS:    create-dmg (see .github/workflows/release.yml)
    Linux:    fpm        (see .github/workflows/release.yml)

Notes
-----
* The app icon must be pre-generated before running this spec:
    - ``build/icons/openstan.ico``   (Windows, multi-resolution)
    - ``build/icons/openstan.icns``  (macOS)
  The CI workflow produces these from ``src/openstan/icons/icon-square.svg``
  via cairosvg.  They are not committed to the repository.
* The ``datas`` list mirrors the include_files in ``cx_freeze_setup.py``.  Both
  must be kept in sync when adding new assets.
* Hidden imports cover Qt plugins and modules that PyInstaller's hook may miss
  depending on the platform and PyQt6 version.
"""

import sys
from pathlib import Path

HERE = Path(SPECPATH)  # noqa: F821 — SPECPATH is injected by PyInstaller
SRC_PKG = HERE / "src" / "openstan"
BUILD_ICONS = HERE / "build" / "icons"

# ---------------------------------------------------------------------------
# Data files
# ---------------------------------------------------------------------------
# Tuples of (source, destination_inside_bundle).  The destination mirrors the
# original package layout so that the _base_dir() helper in paths.py resolves
# assets identically in frozen and unfrozen modes.

datas = [
    (str(SRC_PKG / "icons"), "openstan/icons"),
    (str(SRC_PKG / "data" / "fonts"), "openstan/data/fonts"),
    (str(SRC_PKG / "data" / "sql_files"), "openstan/data/sql_files"),
    (str(SRC_PKG / "data" / "gui.db"), "openstan/data"),
]

# ---------------------------------------------------------------------------
# Hidden imports
# ---------------------------------------------------------------------------
# PyInstaller's PyQt6 hooks handle the vast majority of Qt modules, but these
# are commonly missed on at least one platform.

hiddenimports = [
    "PyQt6.QtSql",
    "PyQt6.QtSvg",
    "PyQt6.QtSvgWidgets",
    "PyQt6.sip",
    # Qt SQL drivers — the SQLite driver must be present for QSqlDatabase
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    # bank_statement_parser and its heavier deps
    "bank_statement_parser",
    "polars",
]

# ---------------------------------------------------------------------------
# Platform icon
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    icon = str(BUILD_ICONS / "openstan.ico") if (BUILD_ICONS / "openstan.ico").exists() else None
elif sys.platform == "darwin":
    icon = str(BUILD_ICONS / "openstan.icns") if (BUILD_ICONS / "openstan.icns").exists() else None
else:
    icon = None

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

a = Analysis(  # noqa: F821
    [str(SRC_PKG / "__main__.py")],
    pathex=[str(HERE / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="openstan",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # no console window for a GUI application
    icon=icon,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="openstan",
)

# macOS .app bundle (ignored on Windows/Linux by PyInstaller)
app = BUNDLE(  # noqa: F821
    coll,
    name="openstan.app",
    icon=icon,
    bundle_identifier="org.openstan.app",
    info_plist={
        "CFBundleDisplayName": "openstan",
        "CFBundleShortVersionString": "0.1.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,  # allow dark mode
    },
)
