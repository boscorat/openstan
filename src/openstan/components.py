import re
from urllib.parse import urlencode

from PySide6.QtCore import QAbstractTableModel, QEvent, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTableView,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QToolTip,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)


def _load_themed_icon_pixmap(
    svg_path: str, size: int = 24, palette: QPalette | None = None
) -> QPixmap:
    """Load SVG icon with palette colors replacing currentColor.

    This function reads an SVG file that uses `stroke="currentColor"`,
    replaces currentColor with the actual palette text color, renders it,
    and returns a QPixmap. This ensures icons adapt to light/dark themes.

    Parameters
    ----------
    svg_path:
        Path to the SVG file.
    size:
        Icon size in pixels (default 24).
    palette:
        QPalette to use for color. If None, uses QApplication.palette().

    Returns
    -------
    QPixmap
        Rendered icon pixmap with palette colors applied.
    """
    if palette is None:
        palette = QApplication.palette()

    # Get text color from palette
    text_color = palette.color(QPalette.ColorRole.WindowText)
    color_hex = (
        f"#{text_color.red():02x}{text_color.green():02x}{text_color.blue():02x}"
    )

    # Read SVG and replace currentColor
    with open(svg_path, "r") as f:
        svg_content = f.read()

    # Replace all currentColor with actual color (both stroke and fill)
    modified_svg = re.sub(
        r'stroke="currentColor"', f'stroke="{color_hex}"', svg_content
    )
    modified_svg = re.sub(r'fill="currentColor"', f'fill="{color_hex}"', modified_svg)

    # Render SVG to pixmap
    renderer = QSvgRenderer()
    renderer.load(modified_svg.encode("utf-8"))

    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return pixmap


class StanProgressBar(QProgressBar):
    def __init__(self) -> None:
        super().__init__()
        self.setAutoFillBackground(True)


class StanPolarsModel(QAbstractTableModel):
    def __init__(self, df):
        super().__init__()
        self.df = df

    def rowCount(self, parent=None) -> int:
        return self.df.height

    def columnCount(self, parent=None) -> int:
        return self.df.width

    def data(self, index, role=Qt.ItemDataRole.DisplayRole) -> str | None:
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.df.item(index.row(), index.column()))
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role=Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        """Override method from QAbstractTableModel

        Return dataframe index as vertical header data and columns as horizontal header data.
        """
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Vertical:
                return str(self.df.item(section, 0))
            elif orientation == Qt.Orientation.Horizontal:
                return str(self.df.columns[section])

        return None


class StanTableView(QTableView):
    def __init__(self) -> None:
        super().__init__()
        self.setAutoFillBackground(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setShowGrid(False)
        self.setMinimumHeight(200)
        self.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setStretchLastSection(True)  # type: ignore[union-attr]
        self.verticalHeader().setVisible(False)  # type: ignore[union-attr]


class StanTreeView(QTreeView):
    def __init__(self) -> None:
        super().__init__()
        self.setAutoFillBackground(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        self.setUniformRowHeights(True)
        self.setAnimated(False)


class StanDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setModal(False)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAutoFillBackground(True)
        self._scrollable: bool = False

    def setLayout(self, layout) -> None:  # noqa: N802
        """Set the dialog's layout, optionally wrapped in a scroll area.

        If _scrollable is True, wraps the layout in a StanScrollArea so
        scrollbars appear when content exceeds the visible area.
        """
        if not self._scrollable:
            super().setLayout(layout)
            return

        # Wrap the layout in a scroll area
        container = QWidget()
        container.setLayout(layout)

        scroll = StanScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(scroll)

    def make_scrollable(self) -> None:
        """Enable scrollable content for this dialog.

        Call this method before setLayout(). Subsequent calls to setLayout()
        will automatically wrap the content in a scroll area, so scrollbars
        appear only when content exceeds the visible area.
        """
        self._scrollable = True


class StanCheckBox(QCheckBox):
    def __init__(self, text="Checkbox") -> None:
        super().__init__(text)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(True)


class StanRadioButton(QRadioButton):
    def __init__(self, text="Radio Button") -> None:
        super().__init__(text)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(True)


class StanErrorMessage(QDialog):
    """A modal error dialog with copy and GitHub issue reporting features.

    Provides a `.showMessage(text, context_object=None)` API so existing callers
    need no changes. New optional `context_object` parameter allows including
    context information when opening a GitHub issue.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Error")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(360)

        # Create icon and message header
        icon_label = QLabel()
        icon_label.setPixmap(
            self.style()
            .standardIcon(self.style().StandardPixmap.SP_MessageBoxCritical)
            .pixmap(48, 48)
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = StanScrollAreaLabel()
        self._error_message = ""
        self._context_object: str | None = None

        # Create button box with Copy, Open GitHub Issue, and Ok buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        copy_btn = buttons.addButton("Copy", QDialogButtonBox.ButtonRole.ActionRole)
        github_btn = buttons.addButton(
            "Open GitHub Issue", QDialogButtonBox.ButtonRole.ActionRole
        )

        copy_btn.clicked.connect(self._copy_to_clipboard)
        github_btn.clicked.connect(self._open_github_issue)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.addWidget(icon_label)
        layout.addWidget(self._label)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def showMessage(self, message: str, context_object: str | None = None) -> None:  # noqa: N802
        """Display message in the dialog and exec it modally.

        Parameters
        ----------
        message : str
            The error message to display.
        context_object : str, optional
            A string describing the object/context that triggered the error.
            Example: "ProjectModel.delete_record(project_id=123)"
            This will be included in the GitHub issue if the user chooses to
            open one.
        """
        self._error_message = message
        self._context_object = context_object
        self._label.setText(message)
        self.exec()

    def _copy_to_clipboard(self) -> None:
        """Copy error message to clipboard and show brief notification."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self._error_message)
            self._show_status_message("Copied to clipboard!", timeout_ms=2000)

    def _show_status_message(self, message: str, timeout_ms: int = 2000) -> None:
        """Display a brief message in the main window's status bar."""
        # Walk up the parent hierarchy to find the top-level main window
        widget = self.parent()
        while widget is not None:
            if hasattr(widget, "statusBar"):
                widget.statusBar().showMessage(message, timeout_ms)
                return
            widget = widget.parent() if hasattr(widget, "parent") else None

    def _open_github_issue(self) -> None:
        """Open GitHub new issue form with pre-filled error message."""
        url = self._build_github_issue_url(self._error_message, self._context_object)
        QDesktopServices.openUrl(QUrl(url))

    def _build_github_issue_url(
        self, error_message: str, context_object: str | None = None
    ) -> str:
        """Build GitHub new issue URL with pre-filled error details.

        Parameters
        ----------
        error_message : str
            The error message text
        context_object : str, optional
            Additional context information

        Returns
        -------
        str
            Full GitHub issues URL with encoded body parameter
        """
        import platform
        import sys

        # Get app version
        app_version = self._get_app_version()

        # System info
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        platform_info = platform.system()

        # Get PySide6 version
        try:
            from importlib.metadata import version as get_version

            pyside_version = get_version("PySide6")
        except Exception:
            pyside_version = "unknown"

        # Build issue body
        body_lines = [
            "## Error Message",
            error_message,
            "",
            "## System Information",
            f"- **App Version:** {app_version}",
            f"- **Python:** {python_version}",
            f"- **Platform:** {platform_info}",
            f"- **PySide6:** {pyside_version}",
        ]

        if context_object:
            body_lines.extend(
                [
                    "",
                    "## Context",
                    context_object,
                ]
            )

        body_lines.extend(
            [
                "",
                "## Steps to Reproduce",
                "(Please describe what you were doing when this error occurred)",
            ]
        )

        body = "\n".join(body_lines)

        # Extract first line of error for title (max ~50 chars)
        error_title = error_message.split("\n")[0][:50]

        # Build URL with proper encoding
        params = {
            "title": f"Error: {error_title}",
            "body": body,
            "labels": "UI Error Message",
        }

        base_url = "https://github.com/boscorat/openstan/issues/new"
        query_string = urlencode(params)
        return f"{base_url}?{query_string}"

    def _get_app_version(self) -> str:
        """Get app version from package metadata.

        Returns
        -------
        str
            The installed package version, or "unknown" if unavailable
        """
        try:
            from importlib.metadata import version

            return version("openstan")
        except Exception:
            return "unknown"


class StanInfoMessage(QMessageBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Information")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setStandardButtons(QMessageBox.StandardButton.Ok)
        self.setDefaultButton(QMessageBox.StandardButton.Ok)


class StanForm(QFormLayout):
    def __init__(self) -> None:
        super().__init__()
        self.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setHorizontalSpacing(15)
        self.setVerticalSpacing(15)


class StanFrame(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameStyle(
            QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken | QFrame.Shape.Panel
        )
        self.setAutoFillBackground(True)


class StanWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setAutoFillBackground(True)
        # self.setMinimumSize(10, 10)


class StanLabel(QLabel):
    def __init__(self, text="Label") -> None:
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setTextFormat(Qt.TextFormat.MarkdownText)


class StanHeaderLabel(StanLabel):
    """A StanLabel rendered in bold — used for column/section headers."""

    def __init__(self, text="Label") -> None:
        super().__init__(text)
        self.setStyleSheet("font-weight: bold;")


class StanMutedLabel(StanLabel):
    """A StanLabel rendered in a muted colour — used for placeholder/absent cells.

    The muted colour is derived from the ``WindowText`` palette role at reduced
    opacity (55 %), so it is always a legible but de-emphasised variant of the
    normal foreground colour on both light and dark themes.

    The colour is re-resolved whenever the application palette changes so that
    switching between light and dark themes at runtime is reflected immediately.
    """

    def __init__(self, text="Label") -> None:
        super().__init__(text)
        self._refresh_color()

    def _refresh_color(self) -> None:
        """Re-derive the muted colour from WindowText and apply it via palette."""
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        base = (
            app.palette().color(QPalette.ColorRole.WindowText)
            if isinstance(app, QApplication)
            else self.palette().color(QPalette.ColorRole.WindowText)
        )
        base.setAlphaF(0.55)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.WindowText, base)
        self.setPalette(palette)

    def changeEvent(self, a0: QEvent) -> None:  # noqa: N802
        """Re-apply the muted colour whenever the palette changes."""
        if (
            not getattr(self, "_refreshing_color", False)
            and a0 is not None
            and a0.type()
            in (
                QEvent.Type.ApplicationPaletteChange,
                QEvent.Type.PaletteChange,
            )
        ):
            self._refreshing_color = True
            self._refresh_color()
            self._refreshing_color = False
        super().changeEvent(a0)


class StanThemedPixmapLabel(StanLabel):
    """A StanLabel that renders a theme-sensitive icon as a pixmap.

    Icons use Tabler Icons with `currentColor` so they automatically adapt to
    the application palette. No theme-specific file swapping is needed.

    Parameters
    ----------
    filename:
        Basename of the icon file (e.g. ``"project.svg"``), resolved through
        :meth:`Paths.themed_icon`.
    size:
        Side length in pixels for the square pixmap (default 64).
    """

    def __init__(self, filename: str, size: int = 64) -> None:
        super().__init__()
        self._filename = filename
        self._size = size
        self._refresh_pixmap()

    def _refresh_pixmap(self) -> None:
        """Load the icon and render it at the specified size."""
        from openstan.paths import Paths

        icon_path = Paths.themed_icon(self._filename)
        pixmap = _load_themed_icon_pixmap(
            icon_path, size=self._size, palette=self.palette()
        )
        self.setPixmap(pixmap)

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802
        """Refresh pixmap when palette changes (theme switch)."""
        if event is not None and event.type() in (
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
        ):
            self._refresh_pixmap()
        super().changeEvent(event)


class StanButton(QPushButton):
    def __init__(self, text="Button", min_width: int = 200) -> None:
        super().__init__(text)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(True)
        self.setIconSize(QSize(16, 16))
        self.setMinimumWidth(min_width)
        self._themed_icon_filename: str | None = None

    def set_themed_icon(self, filename: str) -> None:
        """Set the button icon from a themed SVG.

        Icons use Tabler Icons with `currentColor` so they automatically adapt
        to the application palette without requiring theme change hooks.

        Parameters
        ----------
        filename:
            Basename of the icon (e.g. ``"run.svg"``), resolved via
            :meth:`Paths.themed_icon`.
        """
        self._themed_icon_filename = filename
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        """Resolve and apply the themed icon."""
        if self._themed_icon_filename is None:
            return
        from openstan.paths import Paths

        icon_path = Paths.themed_icon(self._themed_icon_filename)
        pixmap = _load_themed_icon_pixmap(icon_path, size=16, palette=self.palette())
        self.setIcon(QIcon(pixmap))

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802
        """Refresh icon when palette changes (theme switch)."""
        if event is not None and event.type() in (
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
        ):
            self._refresh_icon()
        super().changeEvent(event)


class StanWizardPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setAutoFillBackground(True)


class StanWizard(QWizard):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        # ModernStyle renders entirely via Qt's style engine and therefore
        # respects the application palette on all platforms including Windows
        # dark mode.  The Windows default (AeroStyle) hard-paints a white
        # gradient header at the OS compositor level, bypassing the palette
        # and making the wizard header unreadable in dark mode.
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)


class StanHelpIcon(QPushButton):
    """A small themed info icon that shows a tooltip on hover, click, and keyboard activation.

    Subclasses ``QPushButton`` so that it is focusable via Tab and can be
    activated with Space / Enter — making help text accessible without a mouse.

    Parameters
    ----------
    help_text:
        The explanatory text shown when the user hovers over, clicks, or
        keyboard-activates the icon.
    """

    def __init__(self, help_text: str) -> None:
        super().__init__()
        self._help_text = help_text
        self.setAutoFillBackground(True)
        self.setFixedSize(20, 20)
        self.setFlat(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.setToolTip(help_text)
        self.setAccessibleName("Help")
        self.setAccessibleDescription(help_text)
        self.clicked.connect(self._show_tooltip)
        self._load_icon()

    def _load_icon(self) -> None:
        """Load the themed info icon and set it as the button icon."""
        from openstan.paths import Paths

        icon_path = Paths.themed_icon("info.svg")
        pixmap = _load_themed_icon_pixmap(icon_path, size=16, palette=self.palette())
        if not pixmap.isNull():
            self.setIcon(QIcon(pixmap))
            self.setIconSize(QSize(16, 16))
            self.setText("")
        else:
            # Fallback: render a text "?" if icon not found.
            self.setText("?")

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802
        """Refresh icon when palette changes (theme switch)."""
        if event is not None and event.type() in (
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
        ):
            self._load_icon()
        super().changeEvent(event)

    def _show_tooltip(self) -> None:
        """Show the tooltip at the centre of the button (click or keyboard)."""
        QToolTip.showText(self.mapToGlobal(self.rect().center()), self._help_text, self)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        """Show the tooltip at the cursor position on click."""
        QToolTip.showText(self.mapToGlobal(self.rect().center()), self._help_text, self)
        super().mousePressEvent(e)


class StanComboBox(QComboBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)


class StanLineEdit(QLineEdit):
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setAutoFillBackground(True)


class StanDateEdit(QDateEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setCalendarPopup(True)
        self.setDisplayFormat("yyyy-MM-dd")


class StanTabWidget(QTabWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)


class StanListWidget(QListWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setAlternatingRowColors(True)


class StanGroupBox(QGroupBox):
    def __init__(self, title: str = "", parent=None) -> None:
        super().__init__(title, parent)
        self.setAutoFillBackground(True)


class StanToolButton(QToolButton):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)


class StanScrollArea(QScrollArea):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)


class StanScrollAreaLabel(StanScrollArea):
    """A word-wrapped, selectable text area inside a scroll area.

    Scrollbars appear only when the text exceeds the visible area.
    Text is read-only but selectable (allows copy to clipboard via Ctrl+C).
    Delegates all text editing methods to the underlying QTextEdit for transparent usage.
    """

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._label = QTextEdit(text)
        self._label.setReadOnly(True)
        self.setWidgetResizable(True)
        self.setWidget(self._label)

    def setText(self, text: str) -> None:
        """Set the text content."""
        self._label.setPlainText(text)

    def text(self) -> str:
        """Get the text content as plain text."""
        return self._label.toPlainText()

    def __getattr__(self, name: str):
        """Delegate all unknown attributes to the underlying QTextEdit."""
        return getattr(self._label, name)


class StanTableWidget(QTableWidget):
    def __init__(self, rows: int = 0, cols: int = 0, parent=None) -> None:
        super().__init__(rows, cols, parent)
        self.setAutoFillBackground(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setStretchLastSection(True)  # type: ignore[union-attr]
        self.verticalHeader().setVisible(False)  # type: ignore[union-attr]
