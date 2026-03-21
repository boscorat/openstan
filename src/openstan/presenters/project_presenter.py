import shutil
import sqlite3
import sys
import tomllib
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import bank_statement_parser as bsp
import polars as pl
import tomli_w
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from openstan.models.project_model import ProjectModel
    from openstan.views.project_view import ProjectView

# Top-level config TOML files that may need merging when a non-default config
# subfolder is selected.  anonymise_example.toml is intentionally excluded.
_MERGE_TOML_FILES: tuple[str, ...] = ("account_types.toml", "standard_fields.toml")


def _merge_toplevel_tomls(new_config_dir: Path, source_config_dir: Path) -> None:
    """Merge top-level TOML config files from *source_config_dir* into *new_config_dir*.

    Rules:
    - ``account_types.toml``: any top-level key absent from the new project's file
      is appended.  Existing keys are never overwritten.
    - ``standard_fields.toml``: for each ``[STD_*]`` key, any ``std_refs`` entry
      whose ``statement_type`` value is not already present in the new project's list
      is appended.  Entirely new ``[STD_*]`` keys from the source are added wholesale.
    - ``anonymise_example.toml``: never touched.
    """
    for filename in _MERGE_TOML_FILES:
        new_file = new_config_dir / filename
        src_file = source_config_dir / filename
        if not src_file.exists():
            continue
        if not new_file.exists():
            # New project doesn't have this file at all — just copy it
            shutil.copy2(src_file, new_file)
            continue

        with new_file.open("rb") as fh:
            new_data: dict = tomllib.load(fh)
        with src_file.open("rb") as fh:
            src_data: dict = tomllib.load(fh)

        if filename == "account_types.toml":
            changed = False
            for key, value in src_data.items():
                if key not in new_data:
                    new_data[key] = value
                    changed = True
            if changed:
                with new_file.open("wb") as fh:
                    tomli_w.dump(new_data, fh)

        elif filename == "standard_fields.toml":
            changed = False
            for key, src_entry in src_data.items():
                if key not in new_data:
                    # Entire STD_* key is new — add it wholesale
                    new_data[key] = src_entry
                    changed = True
                else:
                    # Merge std_refs lists — add refs whose statement_type is absent
                    new_refs: list = new_data[key].get("std_refs", [])
                    src_refs: list = src_entry.get("std_refs", [])
                    existing_types: set[str] = {
                        r.get("statement_type", "") for r in new_refs
                    }
                    for ref in src_refs:
                        if ref.get("statement_type", "") not in existing_types:
                            new_refs.append(ref)
                            changed = True
                    if changed:
                        new_data[key]["std_refs"] = new_refs
            if changed:
                with new_file.open("wb") as fh:
                    tomli_w.dump(new_data, fh)


def _apply_config_selections(
    new_config_dir: Path,
    selections: dict[str, Path | None],
    default_config_dir: Path,
) -> None:
    """Apply the user's config subfolder selections to the newly scaffolded project.

    For each subfolder:
    - ``None``  → delete the BSP-scaffolded copy (user chose "Skip").
    - ``default_config_dir`` → no-op (BSP already placed the correct files).
    - any other Path → replace the BSP-scaffolded subfolder with a copy from that
      source, then merge top-level TOML files from that source.
    """
    # Track which non-default sources we have merged TOMLs from to avoid redundant
    # merges when multiple subfolders are drawn from the same source project.
    merged_sources: set[Path] = set()

    for subfolder, source_config_dir in selections.items():
        target = new_config_dir / subfolder

        if source_config_dir is None:
            # Skip — delete whatever BSP scaffolded
            if target.exists():
                shutil.rmtree(target)

        elif source_config_dir.resolve() == default_config_dir.resolve():
            # Default selected — BSP already placed the files, nothing to do
            pass

        else:
            # Non-default project — replace with chosen project's subfolder copy
            src_subfolder = source_config_dir / subfolder
            if not src_subfolder.is_dir():
                # Source subfolder no longer on disk — fall back to default/skip
                print(
                    f"Warning: source config subfolder '{src_subfolder}' not found; "
                    "keeping BSP default.",
                    file=sys.stderr,
                )
                continue
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(src_subfolder, target)

            # Merge top-level TOML files (once per unique source)
            if source_config_dir not in merged_sources:
                _merge_toplevel_tomls(new_config_dir, source_config_dir)
                merged_sources.add(source_config_dir)


def _fmt_date(s: str) -> str:
    """Convert an ISO date string (YYYY-MM-DD) to DD/MM/YYYY, or return '' on failure."""
    if not s:
        return ""
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return s


@dataclass(frozen=True, slots=True)
class ProjectInfo:
    """Snapshot of project-level datamart summary data.

    All date strings are formatted as DD/MM/YYYY; empty string means no data.
    Monetary amounts are stored as whole integers.
    # TODO: include currency symbol/code in datamart (bsp) — see project info panel
    """

    tx_count: int
    stmt_count: int
    acc_count: int
    earliest_date: str
    latest_date: str
    account_rows: pl.DataFrame
    gap_count: int
    gap_rows: pl.DataFrame


def get_project_info(project_path: Path) -> "ProjectInfo | None":
    """Query project.db mart tables and return a structured :class:`ProjectInfo`.

    Returns ``None`` when the mart has not yet been built, all counts are zero,
    or any exception occurs — so the caller never receives a broken value.
    """
    try:
        tx_count: int = (
            bsp.db.FactTransaction(project_path).all.select(pl.len()).collect().item()
        )
        stmt_count: int = (
            bsp.db.DimStatement(project_path).all.select(pl.len()).collect().item()
        )
        acc_count: int = (
            bsp.db.DimAccount(project_path).all.select(pl.len()).collect().item()
        )
    except sqlite3.OperationalError, bsp.StatementError:
        # Mart tables not yet built, or project.db missing — return nothing.
        return None
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return None

    if tx_count == 0 and stmt_count == 0 and acc_count == 0:
        return None

    try:
        # ── Date range (from DimStatement) ────────────────────────────────────
        date_agg = (
            bsp.db.DimStatement(project_path)
            .all.select(
                [
                    pl.col("statement_date").min().alias("earliest"),
                    pl.col("statement_date").max().alias("latest"),
                ]
            )
            .collect()
        )
        earliest_date = _fmt_date(date_agg["earliest"][0] or "")
        latest_date = _fmt_date(date_agg["latest"][0] or "")

        # ── Per-account summary ───────────────────────────────────────────────
        stmt_agg = (
            bsp.db.DimStatement(project_path)
            .all.group_by("account_number", "account_holder", "account_type")
            .agg(
                [
                    pl.len().alias("statements"),
                    pl.col("statement_date").min().alias("from_date"),
                    pl.col("statement_date").max().alias("to_date"),
                    pl.col("payments_in").sum().alias("total_in"),
                    pl.col("payments_out").sum().alias("total_out"),
                ]
            )
        )
        dim_acc = bsp.db.DimAccount(project_path).all.select(
            ["id_account", "account_number", "account_holder", "account_type"]
        )
        latest_bal = (
            bsp.db.FactBalance(project_path)
            .all.filter(pl.col("outside_date") == 0)
            .sort("id_date", descending=True)
            .group_by("id_account")
            .agg(pl.col("closing_balance").first().alias("latest_balance"))
        )
        account_rows = (
            stmt_agg.join(
                dim_acc,
                on=["account_number", "account_holder", "account_type"],
                how="left",
            )
            .join(latest_bal, on="id_account", how="left")
            .select(
                [
                    pl.col("id_account").alias("account"),
                    pl.col("account_holder").alias("holder"),
                    pl.col("statements"),
                    pl.col("from_date").map_elements(_fmt_date, return_dtype=pl.String),
                    pl.col("to_date").map_elements(_fmt_date, return_dtype=pl.String),
                    # TODO: include currency symbol/code in datamart (bsp) — see project info panel
                    pl.col("total_in").cast(pl.Int64),
                    pl.col("total_out").cast(pl.Int64),
                    pl.col("latest_balance"),
                ]
            )
            .sort("account")
            .collect()
        )

        # ── Gap report ────────────────────────────────────────────────────────
        # Compute prev_statement_date by shifting within each account group so
        # the view can show "missing between <prev> and <current>" per gap row.
        gr = bsp.db.GapReport(project_path)
        gap_rows = (
            gr.all.sort(["account_type", "account_number", "statement_date"])
            .with_columns(
                pl.col("statement_date")
                .shift(1)
                .over(["account_type", "account_number"])
                .alias("prev_statement_date")
            )
            .filter(pl.col("gap_flag") == "GAP")
            .select(
                [
                    pl.col("account_type"),
                    pl.col("account_number"),
                    pl.col("account_holder"),
                    pl.col("prev_statement_date").map_elements(
                        _fmt_date, return_dtype=pl.String
                    ),
                    pl.col("statement_date").map_elements(
                        _fmt_date, return_dtype=pl.String
                    ),
                    pl.col("opening_balance"),
                    pl.col("closing_balance"),
                ]
            )
            .collect()
        )
        gap_count = gap_rows.height

    except Exception:
        traceback.print_exc(file=sys.stderr)
        return None

    return ProjectInfo(
        tx_count=tx_count,
        stmt_count=stmt_count,
        acc_count=acc_count,
        earliest_date=earliest_date,
        latest_date=latest_date,
        account_rows=account_rows,
        gap_count=gap_count,
        gap_rows=gap_rows,
    )


class ProjectPresenter(QObject):
    path_or_name_changed: pyqtSignal = pyqtSignal()

    def __init__(
        self: "ProjectPresenter", model: "ProjectModel", view: "ProjectView"
    ) -> None:
        super().__init__()
        self.sessionID: str | None = None  # to be set by StanPresenter
        self.model: "ProjectModel" = model
        self.view: "ProjectView" = view
        self.view.selection.setModel(self.model)
        self.view.selection.setModelColumn(1)  # project_name column
        self.view.selection.setEditable(False)

        # Connect signals — new project wizard
        self.view.button_new.clicked.connect(self.open_new_project_wizard)
        self.view.wizard.page_basic.location_button.clicked.connect(
            self.open_folder_selection_dialog
        )
        self.view.wizard.page_basic.name_row.textChanged.connect(self.name_changed)
        self.path_or_name_changed.connect(self.update_location_label)
        self.view.wizard.new_project_required.connect(self.handle_project_required)

        # Connect signals — existing project wizard
        self.view.button_existing.clicked.connect(self.open_existing_project_wizard)
        self.view.wizard_existing.page_basic.location_button.clicked.connect(
            self.open_folder_selection_dialog
        )
        self.view.wizard_existing.page_basic.name_row.textChanged.connect(
            self.path_or_name_changed.emit
        )
        self.view.wizard_existing.new_project_required.connect(
            self.handle_project_required
        )

    # ---------------------------------------------------------------------------
    # Wizard dispatch — single slot handles both modes
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def handle_project_required(self) -> None:
        """Dispatch to the correct handler based on which wizard emitted the signal."""
        wizard = self.sender()
        if wizard is self.view.wizard_existing:
            self.connect_existing_project()
        else:
            self.create_new_project()

    # ---------------------------------------------------------------------------
    # New project
    # ---------------------------------------------------------------------------

    def _collect_config_sources(self) -> dict[str, Path]:
        """Build an ordered sources dict for the config selection page.

        The dict maps display key → config/ directory path.  The BSP default
        comes first (key ``"default"``), followed by all currently registered
        projects whose ``project_location`` is a readable directory on disk,
        ordered by ``project_name``.
        """
        sources: dict[str, Path] = {
            "default": bsp.ProjectPaths.resolve().config,
        }
        for row in range(self.model.rowCount()):
            record = self.model.record(row)
            name: str = record.value("project_name") or ""
            location: str = record.value("project_location") or ""
            if not name or not location:
                continue
            config_dir = Path(location) / "config"
            if config_dir.is_dir():
                sources[name] = config_dir
        return sources

    @pyqtSlot()
    def open_new_project_wizard(self) -> None:
        self.view.wizard.page_basic.location_button.setDisabled(True)
        self.view.wizard.page_basic.newProjectID = uuid4().hex
        self.view.wizard.page_basic.id_row.setText(
            self.view.wizard.page_basic.newProjectID
        )
        if self.view.wizard.page_config is not None:
            self.view.wizard.page_config.prepare_config_page(
                self._collect_config_sources()
            )
        self.view.wizard.exec()

    @pyqtSlot()
    def create_new_project(self) -> bool:
        wizard = self.view.wizard
        project_name: str = wizard.page_basic.field("projectName")
        full_path: Path | None = wizard.full_project_path

        if full_path is None:
            wizard.failure_dialog.showMessage("No project folder path set.")
            return False

        # Create the root project folder first (bsp requires it to exist before scaffolding)
        try:
            full_path.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            error = f"Folder '{full_path}' already exists. Choose a different name or location."
            wizard.back()
            print(error)
            wizard.failure_dialog.showMessage(error)
            return False
        except Exception as e:
            error = f"Failed to create project folder: {e}"
            wizard.back()
            print(error)
            wizard.failure_dialog.showMessage(error)
            return False

        # bsp scaffolds subfolders, database and default config automatically
        try:
            bsp.validate_or_initialise_project(full_path)
        except Exception as e:
            # Clean up the folder we just created so we don't leave a partial project
            try:
                full_path.rmdir()
            except Exception:
                pass
            error = f"Failed to initialise project: {e}"
            wizard.back()
            print(error)
            wizard.failure_dialog.showMessage(error)
            return False

        # Apply the user's config subfolder selections (PM-7).
        # This runs after BSP scaffolding so we can remove/replace as needed.
        if wizard.page_config is not None:
            try:
                selections = wizard.page_config.get_config_selections()
                _apply_config_selections(
                    new_config_dir=full_path / "config",
                    selections=selections,
                    default_config_dir=bsp.ProjectPaths.resolve().config,
                )
            except Exception as e:
                # Config customisation failed — the project is still valid (BSP
                # scaffolded it successfully) but warn the user.
                print(f"Warning: config selection could not be fully applied: {e}")
                traceback.print_exc(file=sys.stderr)
                wizard.failure_dialog.showMessage(
                    f"Project created but config customisation failed:\n{e}"
                )

        new_pro: tuple[bool, str, str] = self.model.add_record(
            wizard.page_basic.newProjectID,
            project_name,
            str(full_path),
            self.sessionID,
        )
        if new_pro[0]:
            info = (
                f"Project '{project_name}' created successfully!\nLocation: {full_path}"
            )
            wizard.success_dialog.setText("Project Created Successfully")
            wizard.success_dialog.setDetailedText(info)
            if wizard.success_dialog.exec():
                wizard.project_created = True
                self.model.select()
                new_index = self.model.rowCount() - 1
                self.view.selection.setCurrentIndex(new_index)
                wizard.accept()
                return True
        else:
            if new_pro[2].startswith("UNIQUE constraint failed: project.project_name"):
                error = f"Project with name '{project_name}' already exists."
            else:
                error = f"Failed to create project: {new_pro[2]}"
            wizard.back()
            print(error)
            wizard.failure_dialog.showMessage(error)
            return False
        return False

    # ---------------------------------------------------------------------------
    # Existing project
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def open_existing_project_wizard(self) -> None:
        self.view.wizard_existing.page_basic.newProjectID = uuid4().hex
        self.view.wizard_existing.page_basic.id_row.setText(
            self.view.wizard_existing.page_basic.newProjectID
        )
        self.view.wizard_existing.exec()

    @pyqtSlot()
    def connect_existing_project(self) -> bool:
        wizard = self.view.wizard_existing
        project_name: str = wizard.page_basic.name_row.text()
        full_path: Path | None = wizard.full_project_path

        if full_path is None:
            wizard.failure_dialog.showMessage("No project folder selected.")
            return False

        # Validate the selected folder is a usable bsp project (may scaffold missing pieces)
        try:
            bsp.validate_or_initialise_project(full_path)
        except Exception as e:
            error = f"The selected folder does not appear to be a valid project: {e}"
            wizard.back()
            print(error)
            wizard.failure_dialog.showMessage(error)
            return False

        new_pro: tuple[bool, str, str] = self.model.add_record(
            wizard.page_basic.newProjectID,
            project_name,
            str(full_path),
            self.sessionID,
        )
        if new_pro[0]:
            info = (
                f"Project '{project_name}' added successfully!\nLocation: {full_path}"
            )
            wizard.success_dialog.setText("Project Added Successfully")
            wizard.success_dialog.setDetailedText(info)
            if wizard.success_dialog.exec():
                wizard.project_created = True
                self.model.select()
                new_index = self.model.rowCount() - 1
                self.view.selection.setCurrentIndex(new_index)
                wizard.accept()
                return True
        else:
            if new_pro[2].startswith("UNIQUE constraint failed: project.project_name"):
                error = f"Project with name '{project_name}' already exists."
            else:
                error = f"Failed to add project: {new_pro[2]}"
            wizard.back()
            print(error)
            wizard.failure_dialog.showMessage(error)
            return False
        return False

    # ---------------------------------------------------------------------------
    # Shared folder selection and label update
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def open_folder_selection_dialog(self) -> None:
        """Handles folder selection for both wizards — detects caller via sender()."""
        # Determine which wizard's page triggered this
        sender_button = self.sender()
        if sender_button is self.view.wizard_existing.page_basic.location_button:
            page = self.view.wizard_existing.page_basic
            wizard = self.view.wizard_existing
        else:
            page = self.view.wizard.page_basic
            wizard = self.view.wizard

        if page.folder_selection_dialog.exec() == 1:
            selected: Path = Path(page.folder_selection_dialog.selectedFiles()[0])
            page.folder_path = selected

            if wizard.mode == "existing":
                # Path is the project folder itself; pre-populate name from folder name
                wizard.full_project_path = selected
                page.name_row.setDisabled(False)
                page.name_row.setPlaceholderText("")
                page.name_row.setText(selected.name)
                page.location_label.setText(str(selected.absolute()))
                page.location_label.show()
            else:
                self.path_or_name_changed.emit()

    @pyqtSlot()
    def name_changed(self) -> None:
        """Only used by the new-project wizard to gate the location button."""
        name: str = self.view.wizard.page_basic.name_row.text()
        self.view.wizard.page_basic.location_button.setDisabled(len(name) == 0)
        self.path_or_name_changed.emit()

    @pyqtSlot()
    def update_location_label(self) -> None:
        """Updates the full-path label for the new-project wizard."""
        folder: Path | None = self.view.wizard.page_basic.folder_path
        name: str = self.view.wizard.page_basic.name_row.text()
        if folder and len(name) > 0:
            self.view.wizard.full_project_path = folder.joinpath(name)
            self.view.wizard.page_basic.location_label.setText(
                str(self.view.wizard.full_project_path.absolute())
            )
            self.view.wizard.page_basic.location_label.show()
        else:
            self.view.wizard.page_basic.location_label.hide()
