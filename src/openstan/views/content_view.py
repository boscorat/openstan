from PyQt6.QtWidgets import QGridLayout

from openstan.components import Qt, StanFrame


class ContentFrameView(StanFrame):
    def __init__(self, widgets, stretch_content: bool = False) -> None:
        """Framed container for a header label + content widget.

        Args:
            widgets: list of (widget, row, col) tuples passed to the grid.
            stretch_content: when True the content row (row 1) is given
                ``rowStretch=1`` so it expands to fill available vertical
                space instead of being pinned to the top.  Use this for
                the queue and results blocks.
        """
        super().__init__()
        self.widgets = widgets
        layout = QGridLayout()
        for w in self.widgets:
            row = w[1]
            if stretch_content and row == 1:
                # No alignment flag — let the widget fill the cell
                layout.addWidget(w[0], row, w[2])
            else:
                layout.addWidget(w[0], row, w[2], alignment=Qt.AlignmentFlag.AlignTop)
        if stretch_content:
            layout.setRowStretch(1, 1)
        self.setLayout(layout)
