from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QGridLayout

from openstan.components import (
    Qt,
    StanButton,
    StanCheckBox,
    StanRadioButton,
    StanWidget,
)
from openstan.paths import Paths


class ExportView(StanWidget):
    header = "#### Export Options"

    def __init__(self) -> None:
        super().__init__()
        layout = QGridLayout()
        # export format selection
        self.checkExcel = StanCheckBox("Export to Excel")
        self.checkExcel.setChecked(True)
        self.checkCSV = StanCheckBox("Export to CSV")
        self.checkCSV.setChecked(False)
        self.radioFull = StanRadioButton("Export Full Data")
        self.radioFull.setChecked(True)
        self.radioLatest = StanRadioButton("Export Latest Batch Only")
        self.radioLatest.setChecked(False)
        layout.addWidget(self.checkExcel, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.checkCSV, 0, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.radioFull, 0, 2, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.radioLatest, 0, 3, alignment=Qt.AlignmentFlag.AlignLeft)

        # Run Import Button
        self.buttonRunImport = StanButton("Run Data Export")
        self.buttonRunImport.setIcon(QIcon(Paths.icon("run.svg")))
        layout.addWidget(
            self.buttonRunImport, 1, 3, alignment=Qt.AlignmentFlag.AlignRight
        )

        self.setLayout(layout)
