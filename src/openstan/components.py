from PyQt6.QtCore import QAbstractTableModel, QSize, Qt
from PyQt6.QtGui import QPalette, QPixmap
from PyQt6.QtWidgets import (
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
    QToolButton,
    QToolTip,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)


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
        self.setModal(True)
        self.setAutoFillBackground(True)


class StanCheckBox(QCheckBox):
    def __init__(self, text="Checkbox") -> None:
        super().__init__(text)
        # self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(True)


class StanRadioButton(QRadioButton):
    def __init__(self, text="Radio Button") -> None:
        super().__init__(text)
        # self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(True)


class StanErrorMessage(QDialog):
    """A modal error dialog that shows a message without a 'don't show again' checkbox.

    Provides the same ``.showMessage(text)`` API as ``QErrorMessage`` so all
    existing callers need no changes.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Error")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(360)

        self._label = QLabel()
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.PlainText)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.addWidget(self._label)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def showMessage(self, message: str) -> None:  # noqa: N802
        """Display *message* in the dialog and exec it modally."""
        self._label.setText(message)
        self.exec()


class StanInfoMessage(QMessageBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Information")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.WindowModal)


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

    Uses the ``Mid`` palette role so the colour adapts to the active theme
    and high-contrast modes rather than relying on the hardcoded string "grey".
    """

    def __init__(self, text="Label") -> None:
        super().__init__(text)
        # Resolve the palette's Mid colour at construction time and apply it.
        # We use a stylesheet so the colour is visible immediately; the palette
        # role adapts to light/dark/high-contrast themes.
        color = self.palette().color(QPalette.ColorRole.Mid).name()
        self.setStyleSheet(f"color: {color};")


class StanButton(QPushButton):
    def __init__(self, text="Button", min_width: int = 200) -> None:
        super().__init__(text)
        # self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(True)
        self.setIconSize(QSize(16, 16))
        self.setMinimumWidth(min_width)


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
        """Load the themed info.svg and set it as the button icon."""
        from openstan.paths import Paths

        icon_path = Paths.themed_icon("info.svg")
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            from PyQt6.QtGui import QIcon

            self.setIcon(QIcon(pixmap))
            self.setIconSize(QSize(16, 16))
            self.setText("")
        else:
            # Fallback: render a text "?" if icon not found.
            self.setText("?")

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


class StanTableWidget(QTableWidget):
    def __init__(self, rows: int = 0, cols: int = 0, parent=None) -> None:
        super().__init__(rows, cols, parent)
        self.setAutoFillBackground(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setStretchLastSection(True)  # type: ignore[union-attr]
        self.verticalHeader().setVisible(False)  # type: ignore[union-attr]
