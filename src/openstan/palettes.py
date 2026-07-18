from PySide6.QtGui import QColor, QPalette


def _dark_palette() -> QPalette:
    """Return a standard dark palette for the Fusion style.

    Builds the palette from explicit colour values so it works correctly in
    frozen binaries where the Qt platform theme plugin may not load (causing
    Qt to silently fall back to a light palette regardless of the OS setting).
    Colours match the well-known dark Fusion palette used by KDE/GNOME.
    """
    p = QPalette()

    window = QColor(53, 53, 53)
    window_text = QColor(255, 255, 255)
    base = QColor(35, 35, 35)
    alt_base = QColor(53, 53, 53)
    tooltip_base = QColor(25, 25, 25)
    tooltip_text = QColor(255, 255, 255)
    text = QColor(255, 255, 255)
    button = QColor(53, 53, 53)
    button_text = QColor(255, 255, 255)
    bright_text = QColor(255, 0, 0)
    link = QColor(42, 130, 218)
    highlight = QColor(42, 130, 218)
    highlight_text = QColor(35, 35, 35)
    mid = QColor(40, 40, 40)
    dark = QColor(35, 35, 35)
    shadow = QColor(20, 20, 20)
    light = QColor(80, 80, 80)
    midlight = QColor(65, 65, 65)

    p.setColor(QPalette.ColorRole.Window, window)
    p.setColor(QPalette.ColorRole.WindowText, window_text)
    p.setColor(QPalette.ColorRole.Base, base)
    p.setColor(QPalette.ColorRole.AlternateBase, alt_base)
    p.setColor(QPalette.ColorRole.ToolTipBase, tooltip_base)
    p.setColor(QPalette.ColorRole.ToolTipText, tooltip_text)
    p.setColor(QPalette.ColorRole.Text, text)
    p.setColor(QPalette.ColorRole.Button, button)
    p.setColor(QPalette.ColorRole.ButtonText, button_text)
    p.setColor(QPalette.ColorRole.BrightText, bright_text)
    p.setColor(QPalette.ColorRole.Link, link)
    p.setColor(QPalette.ColorRole.Highlight, highlight)
    p.setColor(QPalette.ColorRole.HighlightedText, highlight_text)
    p.setColor(QPalette.ColorRole.Mid, mid)
    p.setColor(QPalette.ColorRole.Dark, dark)
    p.setColor(QPalette.ColorRole.Shadow, shadow)
    p.setColor(QPalette.ColorRole.Light, light)
    p.setColor(QPalette.ColorRole.Midlight, midlight)

    # Disabled roles — slightly dimmed versions of the active colours
    p.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        QColor(127, 127, 127),
    )
    p.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127)
    )
    p.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor(127, 127, 127),
    )
    p.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor(80, 80, 80)
    )
    p.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.HighlightedText,
        QColor(127, 127, 127),
    )

    return p
