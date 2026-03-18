import shutil
import sqlite3
import sys
import tomllib
import traceback
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


def get_project_summary(project_path: Path) -> str:
    """Query project.db mart tables and return a human-readable summary string.

    Returns an empty string when the mart has not yet been built, all counts are
    zero, or any error occurs — so the caller never receives a broken value.
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
        # Mart tables not yet built, or project.db missing — show nothing.
        return ""
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return ""

    if tx_count == 0 and stmt_count == 0 and acc_count == 0:
        return ""

    return (
        f"{tx_count:,} transactions in {stmt_count:,} statements"
        f" across {acc_count:,} {'account' if acc_count == 1 else 'accounts'}"
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
