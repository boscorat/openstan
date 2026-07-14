import os
import sys
from pathlib import Path
from uuid import uuid4

from bank_statement_parser import ProjectPaths
from PySide6.QtCore import QObject, QSysInfo, Qt, QThreadPool, Slot, qDebug
from PySide6.QtGui import (
    QFontDatabase,
    QIcon,
    QKeySequence,
    QShortcut,
)
from PySide6.QtSql import QSqlDatabase
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWhatsThis,
)

from openstan.components import (  # mostly widget subclasses
    StanErrorMessage,
    StanInfoMessage,
    StanLabel,
    StanWidget,
)
from openstan.data.create_gui_db import create_gui_db
from openstan.models import (
    BatchModel,
    FailureResultModel,
    ProjectModel,
    ReportModel,
    ReviewResultModel,
    SessionModel,
    StatementQueueModel,
    StatementQueueTreeModel,
    StatementResultModel,
    StatementResultPayloadModel,
    SuccessResultModel,
    UserModel,
)
from openstan.palettes import _dark_palette
from openstan.paths import Paths
from openstan.presenters import (
    AdminPresenter,
    AdvancedExportPresenter,
    ExportDataPresenter,
    ProjectPresenter,
    ProjectWelcomePresenter,
    RunReportsPresenter,
    SessionPresenter,
    StanPresenter,
    StatementQueuePresenter,
    StatementResultPresenter,
    UserPresenter,
)
from openstan.views import (
    AboutDialog,
    AdminView,
    ContentFrameView,
    ExportDataView,
    FooterView,
    ProjectInfoView,
    ProjectNavView,
    ProjectView,
    ProjectWelcomeView,
    RunReportsView,
    StatementQueueView,
    StatementResultView,
    TitleView,
)


def _detect_scheme_via_dbus() -> Qt.ColorScheme:
    """Detect the system colour scheme on Linux via the FreeDesktop portal.

    Reads ``org.freedesktop.appearance`` → ``color-scheme`` from the
    FreeDesktop Settings portal via ``gdbus``.  This is the same source
    that the Qt platform theme plugin reads internally, but queried
    synchronously so it is reliable at application startup — before the
    platform theme plugin has had a chance to query the system setting and
    make it available via ``QStyleHints.colorScheme()``.

    Return values from ``org.freedesktop.appearance`` ``color-scheme``:
        0 → no preference (treat as light)
        1 → dark
        2 → light

    Falls back to ``Qt.ColorScheme.Light`` on any error (gdbus not found,
    portal unavailable, timeout, unexpected output format, etc.).
    """
    import subprocess
    import sys

    if sys.platform != "linux":
        print("[openstan] _detect_scheme_via_dbus: skipped (not Linux) → Light")
        return Qt.ColorScheme.Light
    try:
        result = subprocess.run(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.freedesktop.portal.Desktop",
                "--object-path",
                "/org/freedesktop/portal/desktop",
                "--method",
                "org.freedesktop.portal.Settings.Read",
                "org.freedesktop.appearance",
                "color-scheme",
            ],
            capture_output=True,
            text=True,
            timeout=0.25,
        )
        print(
            f"[openstan] _detect_scheme_via_dbus: returncode={result.returncode}"
            f"  stdout={result.stdout.strip()!r}"
            f"  stderr={result.stderr.strip()!r}"
        )
        # Successful output looks like: (<uint32 1>,)
        # We treat any occurrence of "<uint32 1>" in the response as dark mode,
        # since the only values are 0 (no-pref), 1 (dark), and 2 (light).
        if result.returncode == 0 and "<uint32 1>" in result.stdout:
            print("[openstan] _detect_scheme_via_dbus: detected → Dark")
            return Qt.ColorScheme.Dark
        print("[openstan] _detect_scheme_via_dbus: detected → Light")
    except Exception as exc:
        print(f"[openstan] _detect_scheme_via_dbus: exception {type(exc).__name__}({exc}) → Light")
    return Qt.ColorScheme.Light


def _apply_palette(app: QApplication, scheme: Qt.ColorScheme) -> None:
    """Apply or remove the explicit dark palette based on *scheme*.

    ``Qt.ColorScheme.Unknown`` is treated as Light (the dbus portal is now
    queried directly at the call site before this function is called, so
    Unknown should not reach here in practice).
    """
    if scheme == Qt.ColorScheme.Dark:
        print("[openstan] _apply_palette: applying Dark palette")
        app.setPalette(_dark_palette())
    else:
        print(f"[openstan] _apply_palette: scheme={scheme.name}  applying Light palette")
        # Restore Fusion's default (light) palette
        app.setPalette(app.style().standardPalette())


class _ThemeManager(QObject):
    """Helper to manage theme switching with named slots instead of lambdas."""

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app

    @Slot(Qt.ColorScheme)
    def on_color_scheme_changed(self, scheme: Qt.ColorScheme) -> None:
        """Handle color scheme change from system preferences."""
        _apply_palette(self.app, scheme)


# def _make_splash(app: QApplication) -> QSplashScreen:
#     """Create a theme-aware splash screen with the app logo and version number.

#     The splash is sized at 2× the native SVG dimensions (300×84 → 600×168)
#     with 40 px padding on all sides, giving a 680×248 logical-pixel window.
#     On HiDPI displays the backing pixmap is scaled by the primary screen's
#     device-pixel ratio so the logo renders crisp.

#     The background colour is taken from the current application palette so
#     the splash blends seamlessly with the window that follows it.
#     """
#     import importlib.metadata

#     from PySide6.QtSvg import QSvgRenderer

#     dpr: float = app.primaryScreen().devicePixelRatio() if app.primaryScreen() else 1.0

#     # Logical dimensions: 2× native SVG size (300×84) plus uniform padding
#     logo_w, logo_h = 600, 168
#     pad = 40
#     pix_w = logo_w + pad * 2
#     pix_h = logo_h + pad * 2

#     # Physical backing-store size for HiDPI correctness
#     phys_w = round(pix_w * dpr)
#     phys_h = round(pix_h * dpr)

#     bg = app.palette().color(QPalette.ColorRole.Window)
#     fg = app.palette().color(QPalette.ColorRole.WindowText)

#     logo_path = Paths.logo(with_tagline=True)
#     import os as _os

#     logo_exists = _os.path.isfile(logo_path)
#     print(f"[openstan] _make_splash: dpr={dpr}  logical={pix_w}x{pix_h}  physical={phys_w}x{phys_h}")
#     print(f"[openstan] _make_splash: logo={logo_path!r}  exists={logo_exists}  palette_bg=#{bg.red():02x}{bg.green():02x}{bg.blue():02x}")

#     pixmap = QPixmap(phys_w, phys_h)
#     pixmap.setDevicePixelRatio(dpr)
#     pixmap.fill(bg)

#     painter = QPainter(pixmap)
#     painter.setRenderHint(QPainter.RenderHint.Antialiasing)
#     painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

#     renderer = QSvgRenderer(logo_path)
#     if renderer.isValid():
#         renderer.render(painter, QRectF(pad, pad, logo_w, logo_h))
#         print("[openstan] _make_splash: SVG rendered OK")
#     else:
#         print("[openstan] _make_splash: QSvgRenderer reports invalid — splash will have blank logo")

#     # Version string — bottom-right corner, slightly muted
#     try:
#         ver_text = f"v{importlib.metadata.version('openstan')}"
#     except importlib.metadata.PackageNotFoundError:
#         ver_text = ""
#         print("[openstan] _make_splash: version not found via importlib.metadata")

#     if ver_text:
#         font = painter.font()
#         font.setPointSize(9)
#         painter.setFont(font)
#         painter.setPen(fg)
#         painter.setOpacity(0.55)
#         metrics = painter.fontMetrics()
#         text_w = metrics.horizontalAdvance(ver_text)
#         painter.drawText(pix_w - text_w - 12, pix_h - 12, ver_text)
#         print(f"[openstan] _make_splash: version text={ver_text!r}")

#     painter.end()

#     return QSplashScreen(pixmap)


def main() -> None:
    qDebug("Starting openstan GUI application...")

    print(f"[openstan] startup: sys.frozen={getattr(sys, 'frozen', False)}  platform={sys.platform}")

    # On Linux, frozen binaries bundle libqxdgdesktopportal.so / libqgtk3.so but
    # their system library dependencies are typically absent on users' machines.
    # Qt's plugin loader probes for these at startup and the repeated failed
    # dlopen() attempts cause a multi-second delay before Qt silently falls back.
    # Suppress the platform theme plugin in frozen builds; our explicit palette
    # logic (_apply_palette / _detect_scheme_via_dbus) handles dark mode instead.
    if getattr(sys, "frozen", False) and sys.platform == "linux":
        _before = os.environ.get("QT_QPA_PLATFORMTHEME", "<unset>")
        os.environ["QT_QPA_PLATFORMTHEME"] = "_none_"
        print(
            f"[openstan] QT_QPA_PLATFORMTHEME: {_before!r} → '_none_'"
            " (frozen Linux: suppressing platform theme plugin to avoid startup delay)"
        )
    else:
        print(
            f"[openstan] QT_QPA_PLATFORMTHEME={os.environ.get('QT_QPA_PLATFORMTHEME', '<unset>')!r}"
            " (not overriding — not a frozen Linux build)"
        )

    app: QApplication = QApplication(sys.argv)
    print("[openstan] QApplication constructed")

    # set application style based on OS
    if QSysInfo.productType() == "windows":
        app.setStyle("Windows")
        print("[openstan] style: Windows")
    elif QSysInfo.productType() in ("ios", "tvos", "watchos", "macos", "darwin"):
        app.setStyle("macOS")
        print("[openstan] style: macOS")
    else:
        app.setStyle("Fusion")
        print(f"[openstan] style: Fusion  productType={QSysInfo.productType()!r}")
        # On Linux the Fusion style has no built-in dark mode — it relies on
        # the Qt platform theme plugin (libqxdgdesktopportal / libqgtk3) to
        # inject the correct palette.  In frozen binaries the plugin's system
        # library dependencies are often absent, causing Qt to silently fall
        # back to a light palette regardless of the OS setting.
        #
        # Additionally, even when the platform theme plugin loads successfully,
        # QStyleHints.colorScheme() may return an incorrect value immediately
        # after QApplication() is constructed — before the plugin has had a
        # chance to query the system colour setting.  We therefore always read
        # the system colour scheme directly via the FreeDesktop portal (gdbus)
        # for the initial palette rather than relying on colorScheme().
        #
        # colorSchemeChanged is kept connected for live theme switching, which
        # works correctly once the event loop is running and the plugin has
        # fully initialised.
        hints = app.styleHints()
        qt_scheme = hints.colorScheme()
        print(f"[openstan] colorScheme() at startup={qt_scheme.name!r} (may be unreliable — using dbus for initial detection)")
        _apply_palette(app, _detect_scheme_via_dbus())
        theme_manager = _ThemeManager(app)
        hints.colorSchemeChanged.connect(theme_manager.on_color_scheme_changed)
        print("[openstan] colorSchemeChanged connected for live theme switching")

    # # ── Splash screen ─────────────────────────────────────────────────────
    # # Shown immediately after the palette is applied (so the correct themed
    # # logo is used) and dismissed just before the main window appears.
    # # app.processEvents() flushes the paint event so the splash is visible
    # # during the synchronous model/view/presenter construction that follows.
    # splash = _make_splash(app)
    # splash.show()
    # app.processEvents()
    # print("[openstan] splash shown")

    # ── Application / window icon ─────────────────────────────────────────
    app.setWindowIcon(QIcon(Paths.icon("icon-square.svg")))

    # ── Bundled fonts ─────────────────────────────────────────────────────
    # Register Inter (OFL 1.1) so Qt's SVG renderer can find it by name.
    # Without this, Qt treats the whole CSS font-family stack as a single
    # unknown family name and emits a slow alias-lookup warning on startup.
    QFontDatabase.addApplicationFont(Paths.font("Inter-Regular.ttf"))
    QFontDatabase.addApplicationFont(Paths.font("Inter-SemiBold.ttf"))

    # ── Bootstrap ─────────────────────────────────────────────────────────
    gui_db_path = Path(Paths.databases("gui.db"))
    if not gui_db_path.exists():
        create_gui_db(gui_db_path)

    gui_db: QSqlDatabase = QSqlDatabase("QSQLITE")
    gui_db.setDatabaseName(Paths.databases("gui.db"))
    gui_db.open()

    username: str = os.path.expanduser("~").split(os.sep)[-1]
    sessionID: str = uuid4().hex

    window: Stan = Stan(gui_db=gui_db, sessionID=sessionID, username=username)
    print("[openstan] Stan.__init__ complete")
    # splash.close()
    # print("[openstan] splash closed — calling window.show()")
    window.show()

    app.exec()

    window.gui_db.close()


class Stan(QMainWindow):
    def __init__(self, gui_db, sessionID, username) -> None:
        super().__init__()
        self.threadpool = QThreadPool()
        self.gui_db = gui_db
        self.userID = None
        self.sessionID = sessionID
        self.username = username
        self.current_project_name = None
        self.current_project_id = None
        self.current_project_paths: ProjectPaths | None = None
        self._app: QApplication | None = None  # Store app reference for theme switching

        # error message dialogs
        self.error_db_lock = StanErrorMessage(self)
        self.error_db_lock.accepted.connect(self.close)

        # ── Models ────────────────────────────────────────────────────────
        self.user_model = UserModel(db=gui_db)
        self.session_model = SessionModel(db=gui_db)
        self.project_model = ProjectModel(db=gui_db)
        self.statement_queue_model = StatementQueueModel(db=gui_db)
        self.statement_queue_tree_model = StatementQueueTreeModel(db=gui_db)
        self.success_result_model = SuccessResultModel()
        self.review_result_model = ReviewResultModel()
        self.failure_result_model = FailureResultModel()
        self.statement_result_model = StatementResultModel(db=gui_db)
        self.statement_result_payload_model = StatementResultPayloadModel(db=gui_db)
        self.batch_model = BatchModel(db=gui_db)
        self.report_model = ReportModel()

        # ── Views ─────────────────────────────────────────────────────────
        self.stan = StanWidget()
        self.title_view = TitleView()
        self.project_view = ProjectView(parent=self)
        self.project_nav_view = ProjectNavView()
        self.footer_view = FooterView()
        self.admin_view = AdminView(parent=self)

        self.project_info_view = ProjectInfoView()
        self.statement_queue_view = StatementQueueView()
        self.export_data_view = ExportDataView()
        self.run_reports_view = RunReportsView()
        self.statement_result_view = StatementResultView()
        self.welcome_view = ProjectWelcomeView()

        # Each panel is wrapped in a ContentFrameView (header label + content).
        # Index constants mirror the order panels are added to the stacked widget.
        self.project_info_block = ContentFrameView(
            widgets=[
                (StanLabel(self.project_info_view.header), 0, 0),
                (self.project_info_view, 1, 0),
            ],
            stretch_content=True,
        )
        self.statement_queue_block = ContentFrameView(
            widgets=[
                (StanLabel(self.statement_queue_view.header), 0, 0),
                (self.statement_queue_view, 1, 0),
            ],
            stretch_content=True,
        )
        self.export_data_block = ContentFrameView(
            widgets=[
                (StanLabel(self.export_data_view.header), 0, 0),
                (self.export_data_view, 1, 0),
            ],
            stretch_content=True,
        )
        self.run_reports_block = ContentFrameView(
            widgets=[
                (StanLabel(self.run_reports_view.header), 0, 0),
                (self.run_reports_view, 1, 0),
            ],
            stretch_content=True,
        )
        self.statement_result_block = ContentFrameView(
            widgets=[
                (StanLabel(self.statement_result_view.header), 0, 0),
                (self.statement_result_view, 1, 0),
            ],
            stretch_content=True,
        )

        # Stacked widget — one slot per panel.
        # nav_idx_* constants are used by StanPresenter to switch panels.
        self.content_stack = QStackedWidget()
        self.nav_idx_welcome: int = self.content_stack.addWidget(self.welcome_view)
        self.nav_idx_info: int = self.content_stack.addWidget(self.project_info_block)
        self.nav_idx_import: int = self.content_stack.addWidget(self.statement_queue_block)
        self.nav_idx_export: int = self.content_stack.addWidget(self.export_data_block)
        self.nav_idx_reports: int = self.content_stack.addWidget(self.run_reports_block)
        self.nav_idx_results: int = self.content_stack.addWidget(self.statement_result_block)

        # ── Presenters ────────────────────────────────────────────────────
        self.user_presenter = UserPresenter(model=self.user_model, view=None)
        self.session_presenter = SessionPresenter(model=self.session_model, view=None)
        self.project_presenter = ProjectPresenter(model=self.project_model, view=self.project_view)
        self.project_welcome_presenter = ProjectWelcomePresenter(project_presenter=self.project_presenter, view=self.welcome_view)
        self.statement_queue_presenter = StatementQueuePresenter(
            model=self.statement_queue_model,
            view=self.statement_queue_view,
            tree_model=self.statement_queue_tree_model,
            threadpool=self.threadpool,
        )
        self.statement_result_presenter = StatementResultPresenter(
            success_model=self.success_result_model,
            review_model=self.review_result_model,
            failure_model=self.failure_result_model,
            result_model=self.statement_result_model,
            payload_model=self.statement_result_payload_model,
            queue_model=self.statement_queue_model,
            batch_model=self.batch_model,
            view=self.statement_result_view,
        )
        self.admin_presenter = AdminPresenter(
            model=self.project_model,
            view=self.admin_view,
            stan=self,  # type: ignore[arg-type]
        )
        self.export_data_presenter = ExportDataPresenter(
            view=self.export_data_view,
            threadpool=self.threadpool,
            batch_model=self.batch_model,
        )
        self.advanced_export_presenter = AdvancedExportPresenter(
            view=self.export_data_view.advanced,
            threadpool=self.threadpool,
        )
        self.run_reports_presenter = RunReportsPresenter(
            model=self.report_model,
            view=self.run_reports_view,
            threadpool=self.threadpool,
        )
        self.stan_presenter = StanPresenter(stan=self)  # type: ignore[arg-type]

        # ── About dialog ──────────────────────────────────────────────────
        # Pure display — no presenter needed.  Wired here rather than in
        # StanPresenter because it carries no business logic or model access.
        self.title_view.about_requested.connect(self._on_about_requested)

        # ── Layout ────────────────────────────────────────────────────────
        # VBox: title → project selector → nav bar → stacked content → footer
        # The stacked content row has stretch=1 so it absorbs all extra
        # vertical space when the window is resized.  Footer has stretch=0
        # so it stays pinned to the bottom.
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.title_view, stretch=0)
        layout.addWidget(self.project_view, stretch=0, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.project_nav_view, stretch=0)
        layout.addWidget(self.content_stack, stretch=1)
        layout.addWidget(self.footer_view, stretch=0)
        self.project_view.setVisible(False)  # Hide until project is selected
        self.project_nav_view.setVisible(False)  # Hide until project is selected

        self.stan.setLayout(layout)
        self.setCentralWidget(self.stan)
        self.setMinimumSize(1400, 900)
        self.resize(1400, 900)

        # Status bar — used by StanPresenter to display transient contextual messages.
        status_bar = self.statusBar()
        assert status_bar is not None
        status_bar.setSizeGripEnabled(False)

        # Shift+F1 activates What's This? mode (standard Qt convention).
        whats_this_shortcut = QShortcut(QKeySequence("Shift+F1"), self)
        whats_this_shortcut.activated.connect(QWhatsThis.enterWhatsThisMode)

    def closeEvent(self, a0) -> None:
        # Warn the user if an import is currently in progress
        # (guard against closeEvent before stan_presenter is initialized)
        if (
            hasattr(self, "stan_presenter") and self.stan_presenter.statement_result_presenter._importing  # noqa: SLF001
        ):
            warn = StanInfoMessage(self)
            warn.setText("An import is currently in progress.\n\nClosing now will abandon the current batch. Are you sure?")
            warn.setStandardButtons(StanInfoMessage.StandardButton.Yes | StanInfoMessage.StandardButton.Cancel)
            warn.setDefaultButton(StanInfoMessage.StandardButton.Cancel)
            if warn.exec() != StanInfoMessage.StandardButton.Yes:
                if a0:
                    a0.ignore()
                return
        if self.sessionID:
            self.stan_presenter.cleanup_before_exit()
        if a0:
            a0.accept()

    @Slot()
    def _on_about_requested(self) -> None:
        """Handle request to show the About dialog."""
        AboutDialog(self).exec()


if __name__ == "__main__":
    main()
