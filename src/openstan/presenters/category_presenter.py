"""category_presenter.py — Presenter, worker and signals for Transaction Categorisation.

Architecture
------------
CategoryWorker (QRunnable)
    Runs on a QThreadPool worker thread.  Calls Ollama for each uncategorised
    transaction, writes results immediately to project.db via the shim, and
    emits fine-grained progress signals so the UI stays responsive.

CategoryPresenter (QObject)
    Owns the CategoryView.  Wires all signals, manages the table model,
    handles manual category edits, and owns the config save/load cycle.

Signal flow
-----------
CategoryWorker.signals.progress  →  CategoryPresenter.on_category_progress
CategoryWorker.signals.item_done →  CategoryPresenter.on_item_done
CategoryWorker.signals.finished  →  CategoryPresenter.on_worker_finished
CategoryWorker.signals.error     →  CategoryPresenter.on_worker_error
"""

import json
import sys
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

import bank_statement_parser as bsp
import polars as pl
from ollama import Client as OllamaClient
from ollama import ResponseError as OllamaResponseError
from PyQt6.QtCore import QObject, QRunnable, QTimer, pyqtSignal, pyqtSlot

from openstan.llm_config import LLMConfig, load_llm_config, save_llm_config
from openstan.shim_annotations import (
    ensure_annotation_table,
    read_annotations,
    upsert_annotations,
)

if TYPE_CHECKING:
    from PyQt6.QtCore import QThreadPool

    from openstan.views.category_view import CategoryView


# ---------------------------------------------------------------------------
# Worker signals
# ---------------------------------------------------------------------------


class CategorySignals(QObject):
    """Cross-thread signals for CategoryWorker."""

    progress: pyqtSignal = pyqtSignal(int, int)  # (done, total)
    item_done: pyqtSignal = pyqtSignal(str, str)  # (id_transaction, category)
    finished: pyqtSignal = pyqtSignal(int, int)  # (categorised, skipped)
    error: pyqtSignal = pyqtSignal(str)  # human-readable message


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class CategoryWorker(QRunnable):
    """Background worker: calls Ollama to categorise bank transactions.

    Preserves manual overrides when *rerun_all* is False (default).
    Writes each annotation to project.db immediately after classification so
    that progress is preserved even if the application closes mid-run.
    """

    def __init__(
        self,
        project_path: Path,
        config: LLMConfig,
        rerun_all: bool = False,
    ) -> None:
        super().__init__()
        self._project_path: Path = project_path
        self._config: LLMConfig = config
        self._rerun_all: bool = rerun_all
        self.signals: CategorySignals = CategorySignals()

    @pyqtSlot()
    def run(self) -> None:
        # ── 1. Health-check Ollama ────────────────────────────────────────
        try:
            urllib.request.urlopen(self._config.host + "/", timeout=3)
        except urllib.error.URLError, OSError:
            self.signals.error.emit(
                f"Cannot reach Ollama at {self._config.host}.\n"
                "Make sure Ollama is running before starting categorisation."
            )
            return

        # ── 2. Ensure annotation table exists ────────────────────────────
        project_db = self._project_path / "database" / "project.db"
        ensure_annotation_table(project_db)

        # ── 3. Load transactions ──────────────────────────────────────────
        try:
            tx_df: pl.DataFrame = (
                bsp.db.FactTransaction(self._project_path)
                .all.select(["id_transaction", "transaction_desc"])
                .collect()
            )
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.signals.error.emit(
                "Could not load transactions from the project database.\n"
                "Make sure the data mart has been built (commit a batch first)."
            )
            return

        if tx_df.is_empty():
            self.signals.finished.emit(0, 0)
            return

        # ── 4. Determine which transactions to categorise ─────────────────
        ann_df = read_annotations(project_db)

        if not ann_df.is_empty() and not self._rerun_all:
            # Exclude transactions that already have any category assigned.
            already_done = set(ann_df["id_transaction"].to_list())
            tx_df = tx_df.filter(~pl.col("id_transaction").is_in(already_done))
        elif not ann_df.is_empty() and self._rerun_all:
            # Re-run AI on everything except manual overrides.
            manual_ids = set(
                ann_df.filter(pl.col("source") == "manual")["id_transaction"].to_list()
            )
            tx_df = tx_df.filter(~pl.col("id_transaction").is_in(manual_ids))

        total = tx_df.height
        if total == 0:
            skipped = (
                len(set(ann_df["id_transaction"].to_list()))
                if not ann_df.is_empty()
                else 0
            )
            self.signals.finished.emit(0, skipped)
            return

        # ── 5. Build system prompt with category list ─────────────────────
        category_list = "\n".join(f"- {c}" for c in self._config.categories)
        system_msg = f"{self._config.system_prompt}\n\nCategories:\n{category_list}"

        # ── 6. Warm the model (keep_alive so subsequent calls are fast) ───
        client = OllamaClient(host=self._config.host)
        try:
            client.chat(
                model=self._config.model,
                messages=[],
                options={"num_predict": 1},
                keep_alive=self._config.keep_alive,
            )
        except OllamaResponseError as exc:
            if exc.status_code == 404:
                self.signals.error.emit(
                    f"Ollama model '{self._config.model}' is not installed.\n"
                    f"Run: ollama pull {self._config.model}"
                )
            else:
                self.signals.error.emit(f"Ollama error during model warm-up: {exc}")
            return
        except Exception as exc:
            self.signals.error.emit(f"Unexpected error warming Ollama model: {exc}")
            return

        # ── 7. Classify each transaction ──────────────────────────────────
        done = 0
        skipped_count = total  # will be decremented as we go

        for row in tx_df.iter_rows(named=True):
            id_tx: str = row["id_transaction"]
            desc: str = row["transaction_desc"] or ""

            try:
                response = client.chat(
                    model=self._config.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": desc},
                    ],
                    format={
                        "type": "object",
                        "properties": {"category": {"type": "string"}},
                        "required": ["category"],
                    },
                    options={
                        "temperature": self._config.temperature,
                        "num_predict": self._config.max_tokens,
                    },
                    stream=False,
                )
                raw_content = response.message.content or ""
                # ollama structured output returns {"category": "..."}
                parsed = json.loads(raw_content)
                category = str(parsed.get("category", "Other")).strip()
            except Exception:
                traceback.print_exc(file=sys.stderr)
                category = "Other"

            # Validate against configured list; fall back to "Other"
            if category not in self._config.categories:
                category = "Other"

            # Write immediately (crash-safe)
            upsert_annotations(
                [
                    {
                        "id_transaction": id_tx,
                        "category": category,
                        "confidence": None,
                        "source": "llm",
                        "model": self._config.model,
                    }
                ],
                project_db,
            )

            done += 1
            skipped_count -= 1
            self.signals.item_done.emit(id_tx, category)
            self.signals.progress.emit(done, total)

        self.signals.finished.emit(done, skipped_count)


# ---------------------------------------------------------------------------
# Presenter
# ---------------------------------------------------------------------------


class CategoryPresenter(QObject):
    """Presenter for the Transaction Categories panel.

    Responsibilities
    ----------------
    - Load and display the joined transaction + annotation table.
    - Submit CategoryWorker to the threadpool.
    - Handle in-flight item_done updates (live row refresh).
    - Persist manual category edits via the shim.
    - Load/save llm_categories.toml.
    - Poll Ollama health and update the status indicator.
    """

    def __init__(
        self,
        view: "CategoryView",
        threadpool: "QThreadPool",
    ) -> None:
        super().__init__()
        self._view: "CategoryView" = view
        self._threadpool: "QThreadPool" = threadpool
        self._project_path: Path | None = None
        self._config: LLMConfig = LLMConfig()
        self._worker_running: bool = False

        # Polars DataFrame backing the table — built in refresh()
        self._df: pl.DataFrame = pl.DataFrame()

        # Ollama health-check timer (~5 s interval)
        self._health_timer = QTimer(self)
        self._health_timer.setInterval(5000)
        self._health_timer.timeout.connect(self._check_ollama_health)

        # Wire view signals
        self._view.button_run.clicked.connect(self._on_run_clicked)
        self._view.button_save_manual.clicked.connect(self._on_save_manual_clicked)
        self._view.button_save_config.clicked.connect(self._on_save_config_clicked)
        self._view.combo_filter_category.currentTextChanged.connect(self._apply_filter)
        self._view.combo_filter_source.currentTextChanged.connect(self._apply_filter)

    # ── Project lifecycle ─────────────────────────────────────────────────

    def set_project(self, project_path: Path | None) -> None:
        """Called by StanPresenter whenever the selected project changes."""
        self._project_path = project_path
        self._config = load_llm_config(project_path) if project_path else LLMConfig()
        self._populate_config_panel()
        self.refresh()
        if project_path and not self._health_timer.isActive():
            self._health_timer.start()
        elif not project_path:
            self._health_timer.stop()
            self._view.label_ollama_status.setText("● No project selected")

    def refresh(self) -> None:
        """Reload the transaction + annotation table from project.db."""
        if self._project_path is None:
            self._df = pl.DataFrame()
            self._update_table(self._df)
            self._update_counts()
            return

        project_db = self._project_path / "database" / "project.db"

        try:
            tx_df = (
                bsp.db.FactTransaction(self._project_path)
                .all.select(
                    [
                        "id_transaction",
                        "id_date",
                        "id_account",
                        "transaction_desc",
                    ]
                )
                .collect()
            )
        except Exception:
            traceback.print_exc(file=sys.stderr)
            tx_df = pl.DataFrame(
                {
                    "id_transaction": pl.Series([], dtype=pl.Utf8),
                    "id_date": pl.Series([], dtype=pl.Utf8),
                    "id_account": pl.Series([], dtype=pl.Utf8),
                    "transaction_desc": pl.Series([], dtype=pl.Utf8),
                }
            )

        ann_df = read_annotations(project_db).select(
            ["id_transaction", "category", "source"]
        )

        if tx_df.is_empty():
            self._df = pl.DataFrame()
            self._update_table(self._df)
            self._update_counts()
            return

        # Join — left join so uncategorised rows still appear
        if ann_df.is_empty():
            joined = tx_df.with_columns(
                pl.lit(None).cast(pl.Utf8).alias("category"),
                pl.lit("").cast(pl.Utf8).alias("source"),
            )
        else:
            joined = tx_df.join(ann_df, on="id_transaction", how="left").with_columns(
                pl.col("category").fill_null(""),
                pl.col("source").fill_null(""),
            )

        # Rename columns for display
        self._df = joined.rename(
            {
                "id_date": "Date",
                "id_account": "Account",
                "transaction_desc": "Description",
                "category": "Category",
                "source": "Source",
            }
        ).select(
            ["id_transaction", "Date", "Account", "Description", "Category", "Source"]
        )

        self._update_table(self._df)
        self._update_counts()
        self._refresh_category_filter()

    # ── Table display ─────────────────────────────────────────────────────

    def _update_table(self, df: pl.DataFrame) -> None:
        """Push *df* into the view's table model."""
        from openstan.views.category_view import CategoryTableModel  # avoids cycle

        id_series = df["id_transaction"] if "id_transaction" in df.columns else None
        display_df = df.drop("id_transaction") if "id_transaction" in df.columns else df
        model = CategoryTableModel(display_df, self._config.categories, id_series)
        self._view.table.setModel(model)
        self._view.table.horizontalHeader().setStretchLastSection(True)  # type: ignore[union-attr]
        self._view.table.resizeColumnsToContents()

    def _update_counts(self) -> None:
        """Refresh the uncategorised count label."""
        if self._df.is_empty():
            self._view.label_counts.setText("No transactions loaded")
            self._view.button_run.setDisabled(True)
            return

        total = self._df.height
        categorised = self._df.filter(pl.col("Category") != "").height
        uncategorised = total - categorised
        self._view.label_counts.setText(
            f"{total:,} transactions — {categorised:,} categorised, "
            f"{uncategorised:,} uncategorised"
        )
        self._view.button_run.setDisabled(self._worker_running)

    def _refresh_category_filter(self) -> None:
        """Repopulate the category filter combo with current values."""
        self._view.combo_filter_category.blockSignals(True)
        current = self._view.combo_filter_category.currentText()
        self._view.combo_filter_category.clear()
        self._view.combo_filter_category.addItem("All categories")
        if "Category" in self._df.columns:
            cats = (
                self._df["Category"]
                .drop_nulls()
                .filter(pl.Series(self._df["Category"].drop_nulls()) != "")
                .unique()
                .sort()
                .to_list()
            )
            for c in cats:
                self._view.combo_filter_category.addItem(c)
        idx = self._view.combo_filter_category.findText(current)
        self._view.combo_filter_category.setCurrentIndex(max(0, idx))
        self._view.combo_filter_category.blockSignals(False)

    def _apply_filter(self) -> None:
        """Filter the displayed rows by category and/or source."""
        if self._df.is_empty():
            return
        filtered = self._df.clone()
        cat_filter = self._view.combo_filter_category.currentText()
        src_filter = self._view.combo_filter_source.currentText()

        if cat_filter != "All categories":
            filtered = filtered.filter(pl.col("Category") == cat_filter)
        if src_filter == "AI only":
            filtered = filtered.filter(pl.col("Source") == "llm")
        elif src_filter == "Manual only":
            filtered = filtered.filter(pl.col("Source") == "manual")
        elif src_filter == "Uncategorised":
            filtered = filtered.filter(pl.col("Category") == "")

        self._update_table(filtered)

    # ── Ollama health check ───────────────────────────────────────────────

    def _check_ollama_health(self) -> None:
        host = self._config.host if self._config else "http://localhost:11434"
        try:
            urllib.request.urlopen(host + "/", timeout=2)
            self._view.label_ollama_status.setText(
                f"● Ollama: running  |  model: {self._config.model}"
            )
            self._view.button_run.setDisabled(self._worker_running)
        except urllib.error.URLError, OSError:
            self._view.label_ollama_status.setText("● Ollama: not running")
            self._view.button_run.setDisabled(True)

    # ── Run categorisation ────────────────────────────────────────────────

    @pyqtSlot()
    def _on_run_clicked(self) -> None:
        if self._project_path is None or self._worker_running:
            return
        rerun_all = self._view.check_rerun_all.isChecked()
        self._config = self._read_config_from_panel()
        worker = CategoryWorker(self._project_path, self._config, rerun_all)
        worker.signals.progress.connect(self._on_worker_progress)
        worker.signals.item_done.connect(self._on_item_done)
        worker.signals.finished.connect(self._on_worker_finished)
        worker.signals.error.connect(self._on_worker_error)
        self._worker_running = True
        self._view.button_run.setDisabled(True)
        self._view.progressBar.setValue(0)
        self._view.progressBar.setVisible(True)
        self._threadpool.start(worker)

    @pyqtSlot(int, int)
    def _on_worker_progress(self, done: int, total: int) -> None:
        pct = int(100 * done / total) if total else 100
        self._view.progressBar.setValue(pct)

    @pyqtSlot(str, str)
    def _on_item_done(self, id_transaction: str, category: str) -> None:
        """Live-update the in-memory DataFrame row and refresh the model."""
        if "id_transaction" not in self._df.columns:
            return
        self._df = self._df.with_columns(
            pl.when(pl.col("id_transaction") == id_transaction)
            .then(pl.lit(category))
            .otherwise(pl.col("Category"))
            .alias("Category"),
            pl.when(pl.col("id_transaction") == id_transaction)
            .then(pl.lit("llm"))
            .otherwise(pl.col("Source"))
            .alias("Source"),
        )
        self._apply_filter()
        self._update_counts()

    @pyqtSlot(int, int)
    def _on_worker_finished(self, categorised: int, skipped: int) -> None:
        self._worker_running = False
        self._view.progressBar.setVisible(False)
        self._view.button_run.setDisabled(False)
        self._view.label_counts.setText(
            self._view.label_counts.text()
            + f"  (run complete: {categorised:,} new, {skipped:,} skipped)"
        )
        self._refresh_category_filter()

    @pyqtSlot(str)
    def _on_worker_error(self, message: str) -> None:
        self._worker_running = False
        self._view.progressBar.setVisible(False)
        self._view.button_run.setDisabled(False)
        from openstan.components import StanErrorMessage

        dlg = StanErrorMessage(self._view)
        dlg.showMessage(message)

    # ── Manual edits ──────────────────────────────────────────────────────

    @pyqtSlot()
    def _on_save_manual_clicked(self) -> None:
        """Persist any manual overrides from the table model to project.db."""
        if self._project_path is None:
            return
        from openstan.views.category_view import CategoryTableModel  # local import

        model = self._view.table.model()
        if not isinstance(model, CategoryTableModel):
            return
        edits = model.pending_edits()
        if not edits:
            return
        project_db = self._project_path / "database" / "project.db"
        annotations = [
            {
                "id_transaction": id_tx,
                "category": cat,
                "confidence": None,
                "source": "manual",
                "model": None,
            }
            for id_tx, cat in edits.items()
        ]
        upsert_annotations(annotations, project_db)
        model.clear_pending_edits()
        self.refresh()

    # ── Config panel ──────────────────────────────────────────────────────

    def _populate_config_panel(self) -> None:
        """Push current LLMConfig values into the settings widgets."""
        self._view.edit_host.setText(self._config.host)
        self._view.edit_model.setText(self._config.model)
        self._view.edit_system_prompt.setPlainText(self._config.system_prompt)
        self._view.edit_categories.setPlainText("\n".join(self._config.categories))

    def _read_config_from_panel(self) -> LLMConfig:
        """Read current settings widget values back into an LLMConfig."""
        cats = [
            c.strip()
            for c in self._view.edit_categories.toPlainText().splitlines()
            if c.strip()
        ]
        return LLMConfig(
            host=self._view.edit_host.text().strip() or self._config.host,
            model=self._view.edit_model.text().strip() or self._config.model,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            keep_alive=self._config.keep_alive,
            system_prompt=self._view.edit_system_prompt.toPlainText().strip(),
            categories=cats or self._config.categories,
        )

    @pyqtSlot()
    def _on_save_config_clicked(self) -> None:
        if self._project_path is None:
            return
        self._config = self._read_config_from_panel()
        ok, msg = save_llm_config(self._config, self._project_path)
        if ok:
            from openstan.components import StanInfoMessage

            dlg = StanInfoMessage(self._view)
            dlg.setText("Configuration saved to llm_categories.toml")
            dlg.exec()
        else:
            from openstan.components import StanErrorMessage

            dlg = StanErrorMessage(self._view)
            dlg.showMessage(f"Failed to save configuration:\n{msg}")
