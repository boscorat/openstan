---
description: "Install openstan on Windows, macOS, or Linux. Self-contained native installers — no Python required."
---

# Installation

openstan is distributed as a self-contained native installer for each supported platform. No Python installation is required — all dependencies are bundled.

---

## Windows

1. Download the latest `openstan-<version>.msi` from the [GitHub Releases](https://github.com/boscorat/openstan/releases) page.
2. Double-click the `.msi` file to launch the installer.
3. Follow the on-screen prompts. openstan is installed per-user by default (no administrator rights needed).
4. Launch **openstan** from the Start menu or desktop shortcut.

!!! note "Windows SmartScreen"
    Windows installers are code-signed via [Certum](https://www.certum.eu/) Open Source Code
    Signing certificate. SmartScreen may still show a warning on first run for newly
    signed applications. Click **More info → Run anyway** to proceed.
    See the [Code signing policy](codesigning.md) for details.

---

## macOS

1. Download the latest `openstan-<version>.dmg` from the [GitHub Releases](https://github.com/boscorat/openstan/releases) page.
2. Open the `.dmg` and drag **openstan** into your `Applications` folder.
3. Double-click to launch openstan. The app is signed and notarized by Apple, so Gatekeeper will trust it automatically.

!!! note "Gatekeeper"
    openstan macOS builds are signed with an Apple Developer ID certificate and
    notarized by Apple. You can launch the app normally — no right-click workaround
    is required. See the [Code signing policy](codesigning.md) for details.

---

## Linux (Debian / Ubuntu)

Download the latest `openstan-<version>.deb` from the [GitHub Releases](https://github.com/boscorat/openstan/releases) page and install it:

```bash
sudo apt install ./openstan-<version>.deb
```

After installation, launch openstan from your application menu, or run `openstan` in a terminal.

Both x86_64 and ARM64 packages are available.

### Dependencies installed automatically

The `.deb` package declares `libxcb-cursor0` as a runtime dependency; `apt` will install it automatically. All other libraries (Qt, Python, OpenSSL, etc.) are bundled inside the installer.

---

## Linux (Fedora / RHEL / CentOS)

Download the latest `openstan-<version>.rpm` from the [GitHub Releases](https://github.com/boscorat/openstan/releases) page and install it:

```bash
sudo dnf install ./openstan-<version>.rpm
```

Both x86_64 and ARM64 packages are available.

---

## Running from source

If you prefer to run openstan directly from the source code (for development or to use the very latest changes):

### Prerequisites

- Python 3.14 or later
- [`uv`](https://docs.astral.sh/uv/) package manager

### Steps

```bash
# Clone the repository
git clone https://github.com/boscorat/openstan.git
cd openstan

# Install all dependencies
uv sync

# Run the application
uv run openstan
```

On Linux you will also need the Qt XCB system libraries:

```bash
sudo apt-get install -y \
  libegl1 libgles2 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
  libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0 \
  libdbus-1-3 libfontconfig1 libfreetype6
```

---

## Upgrading

To upgrade to a newer version, download the new installer and run it — it will replace the previous installation. Your project data is stored in separate project folders and is not affected by upgrades.

---

## Uninstalling

=== "Windows"
    Go to **Settings → Apps → Installed apps**, find **openstan**, and click **Uninstall**.

=== "macOS"
    Drag the **openstan** app from `Applications` to the Trash.

=== "Linux (deb)"
    ```bash
    sudo apt remove openstan
    ```

=== "Linux (rpm)"
    ```bash
    sudo dnf remove openstan
    ```

!!! warning "Project data"
    Uninstalling openstan does **not** delete your project folders or data. These are stored wherever you chose when creating each project.

---

## Code signing

All platform installers are code-signed to verify authenticity and integrity.
See the [Code signing policy](codesigning.md) for full details on Windows, macOS,
and the build process.
