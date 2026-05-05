"""AboutDialog — application identity and external links.

Pure display: no presenter, no model access, no business logic.
Opened directly from Stan.__init__ when TitleView emits about_requested.
"""

from importlib.metadata import PackageNotFoundError, version

from PyQt6.QtCore import Qt
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QDialogButtonBox, QVBoxLayout

from openstan.components import StanDialog, StanLabel, StanMutedLabel
from openstan.paths import Paths

_WEBSITE_URL = "https://openstan.org"
_GITHUB_URL = "https://github.com/boscorat/openstan"
_LICENSE_URL = "https://www.gnu.org/licenses/gpl-3.0.html"
_BSP_GITHUB_URL = "https://github.com/boscorat/bank_statement_parser"
_COPYRIGHT = "Copyright \u00a9 2025 Jason Farrar"


def _app_version() -> str:
    try:
        return version("openstan")
    except PackageNotFoundError:
        return "unknown"


def _bsp_version() -> str:
    try:
        return version("uk-bank-statement-parser")
    except PackageNotFoundError:
        return "unknown"


class AboutDialog(StanDialog):
    """Modal dialog showing the full logo, version, and external links."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About openstan")
        self.setFixedWidth(480)
        self.setSizeGripEnabled(False)
        # Remove the '?' help button that Qt adds by default on some platforms.
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        # ── Logo ──────────────────────────────────────────────────────────
        # Use the theme-aware full logo with tagline at its natural 1× size
        # (300×84 matches the SVG viewBox).  QSvgWidget handles HiDPI
        # scaling automatically via the device pixel ratio.
        logo = QSvgWidget(Paths.logo(with_tagline=True))
        logo.setFixedSize(300, 84)
        logo.setAccessibleName("openstan — secure statement analysis")

        # ── Version ───────────────────────────────────────────────────────
        version_label = StanLabel(f"Version {_app_version()}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Links ─────────────────────────────────────────────────────────
        # setOpenExternalLinks(True) routes clicks to QDesktopServices
        # internally — no extra wiring needed, and no network calls are
        # made by the application itself (NFR-5 compliant).
        website_label = StanLabel(f'<a href="{_WEBSITE_URL}">{_WEBSITE_URL}</a>')
        website_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        website_label.setOpenExternalLinks(True)
        website_label.setTextFormat(Qt.TextFormat.RichText)
        website_label.setAccessibleName("openstan website")

        github_label = StanLabel(f'<a href="{_GITHUB_URL}">{_GITHUB_URL}</a>')
        github_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github_label.setOpenExternalLinks(True)
        github_label.setTextFormat(Qt.TextFormat.RichText)
        github_label.setAccessibleName("openstan GitHub repository")

        # ── Powered-by ────────────────────────────────────────────────────
        powered_by_label = StanMutedLabel(
            f"Powered by bank\\_statement\\_parser {_bsp_version()}"
        )
        powered_by_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bsp_label = StanLabel(f'<a href="{_BSP_GITHUB_URL}">{_BSP_GITHUB_URL}</a>')
        bsp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bsp_label.setOpenExternalLinks(True)
        bsp_label.setTextFormat(Qt.TextFormat.RichText)
        bsp_label.setAccessibleName("bank_statement_parser GitHub repository")

        # ── Copyright & license ───────────────────────────────────────────
        copyright_label = StanMutedLabel(_COPYRIGHT)
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        license_label = StanLabel(
            f'Licensed under the <a href="{_LICENSE_URL}">'
            "GNU General Public License v3 or later</a>"
        )
        license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        license_label.setOpenExternalLinks(True)
        license_label.setTextFormat(Qt.TextFormat.RichText)
        license_label.setAccessibleName("GPL v3 or later license")

        # ── Close button ──────────────────────────────────────────────────
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        # ── Layout ────────────────────────────────────────────────────────
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(4)
        layout.addWidget(version_label)
        layout.addWidget(website_label)
        layout.addWidget(github_label)
        layout.addSpacing(4)
        layout.addWidget(powered_by_label)
        layout.addWidget(bsp_label)
        layout.addSpacing(4)
        layout.addWidget(copyright_label)
        layout.addWidget(license_label)
        layout.addSpacing(4)
        layout.addWidget(buttons)
        self.setLayout(layout)
