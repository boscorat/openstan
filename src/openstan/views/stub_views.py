"""stub_views.py — Placeholder panel views for features not yet implemented.

Each view is a minimal ``StanWidget`` that displays a 'coming soon' message.
They exist solely so the navigator can switch to a real widget for each panel;
they will be replaced by functional implementations in future milestones.
"""

from PyQt6.QtWidgets import QVBoxLayout

from openstan.components import Qt, StanMutedLabel, StanWidget


class _StubView(StanWidget):
    """Base class for placeholder panels.

    Displays a single centred muted description line.  The section header is
    supplied externally by ``ContentFrameView`` in ``main.py`` — consistent
    with all other panel views.
    """

    def __init__(self, description: str) -> None:
        super().__init__()
        body = StanMutedLabel(description)
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(body)
        self.setLayout(layout)

    # Public attribute expected by ContentFrameView / StanPresenter
    header: str = ""


class ExportDataView(_StubView):
    """Placeholder for the Export Data panel (not yet implemented)."""

    header = "##### Export Data"

    def __init__(self) -> None:
        super().__init__(
            description="Export project transactions and reports — coming soon.",
        )


class RunReportsView(_StubView):
    """Placeholder for the Run Reports panel (not yet implemented)."""

    header = "##### Run Reports"

    def __init__(self) -> None:
        super().__init__(
            description="Generate and view project reports — coming soon.",
        )
