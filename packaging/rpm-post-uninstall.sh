#!/bin/sh
# Post-uninstall script for openstan RPM/DEB package.
# Removes the .desktop entry and icon, then refreshes caches.

set -e

rm -f /usr/share/applications/openstan.desktop
rm -f /usr/share/icons/hicolor/scalable/apps/openstan.svg
rm -f /usr/share/icons/hicolor/256x256/apps/openstan.png

if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache > /dev/null 2>&1; then
    gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
fi
