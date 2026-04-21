"""Update checker for openstan.

Provides ``UpdateChecker``, a lightweight ``QObject`` that performs a silent
background check against the GitHub Releases API on application startup and
emits a signal when a newer version is available.  The UI layer is responsible
for presenting the notification to the user — no automatic downloads or
installations are performed.

Design constraints
------------------
* Background thread only — never blocks the Qt event loop.
* Silent failure — network errors, timeouts, and JSON parse errors are all
  swallowed.  The user should never see a crash or an error dialog caused by
  the update check.
* User-prompted — the ``update_available`` signal carries the latest version
  string and release URL so the caller can show a dialog and open a browser on
  demand.
* Zero new runtime dependencies — uses only the standard library (``urllib``,
  ``json``, ``threading``, ``importlib.metadata``) and PyQt6.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from urllib.error import URLError
from urllib.request import Request, urlopen

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GITHUB_OWNER = "boscorat"
_GITHUB_REPO = "openstan"
_API_URL = (
    f"https://api.github.com/repos/{_GITHUB_OWNER}/{_GITHUB_REPO}/releases/latest"
)
_RELEASES_URL = f"https://github.com/{_GITHUB_OWNER}/{_GITHUB_REPO}/releases/latest"

# Timeout for the HTTP request in seconds.  Short enough that a slow network
# does not delay the application startup noticeably.
_REQUEST_TIMEOUT = 5


def _current_version() -> str:
    """Return the installed version string, or ``"0.0.0"`` if unavailable."""
    try:
        return _pkg_version("openstan")
    except PackageNotFoundError:
        return "0.0.0"


def _parse_version(tag: str) -> tuple[int, ...]:
    """Convert a version / tag string to a comparable tuple of ints.

    Handles ``v1.2.3`` and ``1.2.3`` forms.  Non-numeric pre-release suffixes
    (e.g. ``1.2.3a9``) are stripped so that release versions always sort higher.
    """
    tag = tag.lstrip("v")
    # Take only the numeric prefix of each component
    parts: list[int] = []
    for segment in tag.split(".")[:3]:
        numeric = ""
        for ch in segment:
            if ch.isdigit():
                numeric += ch
            else:
                break
        parts.append(int(numeric) if numeric else 0)
    # Pad to 3 components
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


# ---------------------------------------------------------------------------
# Update dialog
# ---------------------------------------------------------------------------


class _UpdateDialog(QDialog):
    """Modal dialog shown when a newer release is available.

    Presents the new version number and a changelog/release notes link.
    The user can choose to open the releases page or dismiss the dialog.
    """

    def __init__(
        self,
        current: str,
        latest: str,
        release_url: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Update Available")
        self._release_url = release_url

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        message = QLabel(
            f"<b>openstan {latest}</b> is available.<br>"
            f"You are running version <b>{current}</b>.<br><br>"
            "Open the releases page to view the changes and download the update."
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        buttons = QDialogButtonBox(self)
        self._open_btn = buttons.addButton(
            "View Release Notes", QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.addButton("Not Now", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._open_releases)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setMinimumWidth(380)
        self.setModal(True)

    def _open_releases(self) -> None:
        webbrowser.open(self._release_url)
        self.accept()


# ---------------------------------------------------------------------------
# UpdateChecker
# ---------------------------------------------------------------------------


class UpdateChecker(QObject):
    """Background update checker.

    Emit ``update_available(latest_version, release_url)`` from the worker
    thread; connect it to ``show_update_dialog`` (or any slot) on the main
    thread to present the UI.

    Typical usage in ``StanPresenter.__init__``::

        self._update_checker = UpdateChecker(parent=self)
        self._update_checker.update_available.connect(
            self._on_update_available
        )
        self._update_checker.check_async()

    Signals
    -------
    update_available : (str, str)
        Emitted when a newer version is found.  Arguments are the latest
        version string and the HTML URL of the release.
    """

    update_available = pyqtSignal(str, str)  # (latest_version, release_url)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def check_async(self) -> None:
        """Start the background check.  Returns immediately."""
        t = threading.Thread(target=self._check, daemon=True, name="UpdateChecker")
        t.start()

    def _check(self) -> None:
        """Worker: fetch the latest release and compare versions.

        All exceptions are caught — a failed update check must never surface
        to the user as an error.
        """
        try:
            req = Request(
                _API_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "openstan",
                },
            )
            with urlopen(req, timeout=_REQUEST_TIMEOUT) as response:  # noqa: S310
                data: dict = json.loads(response.read())

            tag: str = data.get("tag_name", "")
            release_url: str = data.get("html_url", _RELEASES_URL)

            if not tag:
                return

            latest = _parse_version(tag)
            current = _parse_version(_current_version())

            if latest > current:
                self.update_available.emit(tag.lstrip("v"), release_url)

        except URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError:
            # Network unavailable, rate-limited, or malformed response — silently ignore
            pass
        except Exception:  # noqa: BLE001
            # Catch-all: update check must never crash the application
            pass

    @pyqtSlot(str, str)
    def show_update_dialog(
        self,
        latest_version: str,
        release_url: str,
        parent: QWidget | None = None,
    ) -> None:
        """Present the update dialog to the user.

        Connect ``update_available`` to this slot (passing ``parent`` manually
        is not supported in signal/slot connections — use a lambda or a bound
        method on the presenter that supplies the parent widget).
        """
        dialog = _UpdateDialog(
            current=_current_version(),
            latest=latest_version,
            release_url=release_url,
            parent=parent,
        )
        dialog.exec()
