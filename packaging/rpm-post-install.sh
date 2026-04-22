#!/bin/sh
# Post-install script for openstan RPM/DEB package.
# Installs the .desktop entry and application icon into system locations,
# then refreshes the desktop and icon caches.

set -e

INSTALL_DIR="/usr/lib/openstan"
ICON_SRC="${INSTALL_DIR}/lib/openstan/icons/icon-square.svg"
DESKTOP_SRC="${INSTALL_DIR}/share/openstan.desktop"

# Install .desktop entry
if [ -f "$DESKTOP_SRC" ]; then
    install -Dm644 "$DESKTOP_SRC" /usr/share/applications/openstan.desktop
fi

# Install SVG icon into hicolor theme
if [ -f "$ICON_SRC" ]; then
    install -Dm644 "$ICON_SRC" /usr/share/icons/hicolor/scalable/apps/openstan.svg
fi

# Install PNG icon if present (produced by CI icon conversion step)
PNG_SRC="${INSTALL_DIR}/share/openstan.png"
if [ -f "$PNG_SRC" ]; then
    install -Dm644 "$PNG_SRC" /usr/share/icons/hicolor/256x256/apps/openstan.png
fi

# Refresh caches (best-effort — may not be present in all environments)
if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache > /dev/null 2>&1; then
    gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
fi
