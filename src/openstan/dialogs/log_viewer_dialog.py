"""Read-only log viewer dialog with privacy warnings.

Displays log files with privacy warnings, file path indicators, and standard
controls for refreshing and copying log contents.
"""

from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtGui import QClipboard, QTextCursor
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QVBoxLayout

from openstan.components import (
    StanButton,
    StanDialog,
    StanLabel,
    StanMutedLabel,
)

__all__: list[str] = ["LogViewerDialog"]

# Max lines to display (last N lines of file)
_MAX_DISPLAY_LINES = 500


class LogViewerDialog(StanDialog):
    """Read-only modal dialog for viewing log files.

    Displays log file contents with:
    - Privacy warning banner at top (always shown)
    - Current log file path indicator
    - Read-only scrollable text area (last 500 lines)
    - Truncation notice if file contains more than 500 lines
    - Refresh button (reload from disk)
    - Copy button (copy all text to clipboard)
    - Close button

    Design:
        - Modal: True
        - Always on top: True (inherited from StanDialog)
        - Scrollable: True
        - Size: 700x500 (reasonable for log viewing)
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("View Log")
        self.setGeometry(100, 100, 700, 500)

        # Enable scrollable layout BEFORE creating widgets
        self.make_scrollable()

        # Current log file path (set by show_log)
        self._log_path: Path | None = None

        # ── Create widgets ──────────────────────────────────────────────

        # Privacy warning banner (markdown enabled)
        privacy_label = StanLabel()
        privacy_label.setText(
            "**⚠ Privacy Notice:** This log may contain sensitive bank account "
            "information. Be cautious when sharing with others."
        )

        # Current file path indicator
        self._path_label = StanMutedLabel()
        self._path_label.setText("(No log file loaded)")

        # Log display (read-only)
        self._log_display = QPlainTextEdit()
        self._log_display.setReadOnly(True)
        self._log_display.setFont(
            self._log_display.font()  # Keep default monospace
        )

        # Truncation notice (hidden by default)
        self._truncation_label = StanMutedLabel()
        self._truncation_label.setText("⚠ Showing last 500 lines (file is larger)")
        self._truncation_label.hide()

        # ── Buttons ─────────────────────────────────────────────────────

        button_refresh = StanButton("Refresh")
        button_refresh.clicked.connect(self.on_refresh)

        button_copy = StanButton("Copy")
        button_copy.clicked.connect(self.on_copy)

        button_close = StanButton("Close")
        button_close.clicked.connect(self.close)

        # ── Layout ──────────────────────────────────────────────────────

        layout = QVBoxLayout()
        layout.addWidget(privacy_label)
        layout.addWidget(self._path_label)
        layout.addSpacing(10)
        layout.addWidget(self._log_display)
        layout.addWidget(self._truncation_label)
        layout.addSpacing(10)

        # Button row
        button_layout = QVBoxLayout()
        button_layout.addWidget(button_refresh)
        button_layout.addWidget(button_copy)
        button_layout.addWidget(button_close)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def show_log(self, log_path: Path) -> None:
        """Load and display a log file.

        Loads the last 500 lines of the log file. If the file contains more
        lines, displays a truncation notice.

        Args:
            log_path: Path to the log file to display.
        """
        self._log_path = Path(log_path)

        # Update path label
        self._path_label.setText(f"**Log file:** `{self._log_path}`")

        # Load log file (last N lines)
        try:
            if not self._log_path.exists():
                self._log_display.setPlainText(
                    f"[Log file not found: {self._log_path}]"
                )
                self._truncation_label.hide()
                return

            # Read file and get last N lines
            with open(self._log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Check if we need to truncate
            total_lines = len(lines)
            if total_lines > _MAX_DISPLAY_LINES:
                display_lines = lines[-_MAX_DISPLAY_LINES:]
                self._truncation_label.show()
            else:
                display_lines = lines
                self._truncation_label.hide()

            # Display the lines
            self._log_display.setPlainText("".join(display_lines))

            # Move cursor to top for better UX
            cursor = self._log_display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self._log_display.setTextCursor(cursor)

        except OSError as e:
            self._log_display.setPlainText(f"[Error reading log file: {e}]")
            self._truncation_label.hide()

    @Slot()
    def on_refresh(self) -> None:
        """Reload log file from disk."""
        if self._log_path:
            self.show_log(self._log_path)

    @Slot()
    def on_copy(self) -> None:
        """Copy log display contents to clipboard."""
        text = self._log_display.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text, QClipboard.Mode.Clipboard)
