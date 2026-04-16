from PyQt6.QtCore import QAbstractTableModel, QSize, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QErrorMessage,
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


class StanErrorMessage(QErrorMessage):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Error")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.WindowModal)


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
    """A StanLabel rendered in a muted (grey) colour — used for placeholder/absent cells."""

    def __init__(self, text="Label") -> None:
        super().__init__(text)
        self.setStyleSheet("color: grey;")


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


class StanHelpIcon(QLabel):
    """A small themed info icon that shows a tooltip on hover and click.

    Uses the ``info.svg`` icon from the themed icon directory (dark/light).
    The help text is displayed via ``QToolTip`` so it works on both hover
    and click without needing a separate popup widget.

    Parameters
    ----------
    help_text:
        The explanatory text shown when the user hovers over or clicks the
        icon.
    """

    def __init__(self, help_text: str) -> None:
        super().__init__()
        self._help_text = help_text
        self.setAutoFillBackground(True)
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.setToolTip(help_text)
        self._load_icon()

    def _load_icon(self) -> None:
        """Load the themed info.svg and set it as the label pixmap."""
        from openstan.paths import Paths

        icon_path = Paths.themed_icon("info.svg")
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            self.setPixmap(
                pixmap.scaled(
                    16,
                    16,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            # Fallback: render a text "?" if icon not found.
            self.setText("?")
            self.setAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )

    def mousePressEvent(self, ev) -> None:  # noqa: N802
        """Show the tooltip at the cursor position on click."""
        QToolTip.showText(self.mapToGlobal(self.rect().center()), self._help_text, self)
        super().mousePressEvent(ev)


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
