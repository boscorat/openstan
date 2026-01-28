from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QErrorMessage,
    QFormLayout,
    QFrame,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTreeView,
    QWidget,
)


class StanTreeView(QTreeView):
    def __init__(self) -> None:
        super().__init__()
        self.setAutoFillBackground(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        self.setUniformRowHeights(True)
        self.setAnimated(True)


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
    def __init__(self) -> None:
        super().__init__()
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken | QFrame.Shape.Panel)
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


class StanButton(QPushButton):
    def __init__(self, text="Button") -> None:
        super().__init__(text)
        # self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(True)
        self.setIconSize(QSize(10, 10))
        self.setMinimumWidth(200)
