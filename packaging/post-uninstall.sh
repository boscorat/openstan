#!/bin/sh
# Post-uninstall script for openstan RPM/DEB package.
# Removes the .desktop entry and icon, then refreshes caches.
#
# On upgrade the new package's post-install.sh runs first, then this script
# runs as part of removing the old package.  If any openstan-* versioned
# directory still exists under /usr/lib, we are mid-upgrade and must not
# tear down desktop integration — the new version handles that.

set -e

# If another openstan version directory exists with a valid binary,
# this is an upgrade — skip cleanup.  The new package's post-install.sh
# will handle desktop integration.
for _d in /usr/lib/openstan-*; do
    if [ -d "$_d/openstan" ] && [ -x "$_d/openstan/openstan" ]; then
        exit 0
    fi
done

rm -f /usr/bin/openstan
rm -f /usr/share/applications/openstan.desktop
rm -f /usr/share/icons/hicolor/scalable/apps/openstan.svg
rm -f /usr/share/icons/hicolor/256x256/apps/openstan.png

if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache > /dev/null 2>&1; then
    gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
fi
