"""make_wix_fragments.py — Harvest dist/openstan/ into a WiX component group.

Called by the CI release workflow after cx_Freeze has produced dist/openstan/.
Writes packaging/windows/files.wxs containing a <ComponentGroup Id="ApplicationFiles">
that lists every file in the frozen application directory as a WiX component.

WiX v4 does not ship a separate heat.exe harvesting tool — component authoring
is done inline or via a custom harvester.  This script replicates heat's
essential behaviour in pure Python so there is no extra tooling dependency.

Usage
-----
    python packaging/windows/make_wix_fragments.py [--app-dir dist/openstan] \\
                                                    [--out packaging/windows/files.wxs]

The generated files.wxs is consumed by openstan.wxs via:
    <ComponentGroupRef Id="ApplicationFiles" />

All GUIDs are deterministic (UUID v5 in the openstan namespace) so rebuilds
of the same version produce identical output and MSI patch chains work correctly.
"""

from __future__ import annotations

import argparse
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Deterministic GUID namespace — a fixed UUID v5 seed for openstan.
# GUIDs are derived from the relative file path within the application
# directory, so the same file always gets the same component GUID across
# builds.  This is required for MSI patch / upgrade correctness.
# ---------------------------------------------------------------------------
_OPENSTAN_NS = uuid.UUID("7f3e1a2b-4c5d-6e7f-8a9b-0c1d2e3f4a5b")


def _component_guid(rel_path: str) -> str:
    """Return a braced, upper-case UUID v5 deterministic GUID for *rel_path*."""
    return "{" + str(uuid.uuid5(_OPENSTAN_NS, rel_path.lower())).upper() + "}"


def _component_id(rel_path: str) -> str:
    """Return a WiX-safe component identifier derived from *rel_path*."""
    # Replace path separators and dots with underscores; prefix with 'c_' to
    # ensure the identifier starts with a letter (WiX requirement).
    safe = rel_path.replace("\\", "_").replace("/", "_").replace(".", "_")
    return "c_" + safe


def _file_id(rel_path: str) -> str:
    """Return a WiX-safe file identifier derived from *rel_path*."""
    safe = rel_path.replace("\\", "_").replace("/", "_").replace(".", "_")
    return "f_" + safe


def _dir_id(rel_path: str) -> str:
    """Return a WiX-safe directory identifier derived from *rel_path*."""
    if not rel_path:
        return "INSTALLFOLDER"
    safe = rel_path.replace("\\", "_").replace("/", "_").replace(".", "_")
    return "d_" + safe


def harvest(app_dir: Path, out_path: Path) -> None:
    """Walk *app_dir* and write a WiX fragment to *out_path*."""

    # Collect all files relative to app_dir, sorted for deterministic output.
    all_files: list[Path] = sorted(p for p in app_dir.rglob("*") if p.is_file())

    if not all_files:
        print(f"ERROR: No files found in {app_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Harvesting {len(all_files)} files from {app_dir} -> {out_path}")

    # Build directory tree so we can emit <DirectoryRef> elements per unique dir.
    dirs_seen: set[str] = set()
    # Map of relative-dir-string → list of file Path objects
    dir_files: dict[str, list[Path]] = {}
    for f in all_files:
        rel = f.relative_to(app_dir)
        rel_dir = str(rel.parent) if str(rel.parent) != "." else ""
        dir_files.setdefault(rel_dir, []).append(f)
        # Register all ancestor directories
        parts = Path(rel_dir).parts if rel_dir else []
        for i in range(len(parts) + 1):
            dirs_seen.add("/".join(parts[:i]))

    # Build the XML document.
    root = ET.Element(
        "Wix",
        {
            "xmlns": "http://wixtoolset.org/schemas/v4/wxs",
        },
    )
    fragment = ET.SubElement(root, "Fragment")

    # ── Directory declarations ────────────────────────────────────────────
    # WiX v4 requires all directories referenced by components to be declared
    # somewhere.  We emit them as a hierarchy rooted at INSTALLFOLDER.
    def _emit_dir_tree(parent_el: ET.Element, prefix: str) -> None:
        """Recursively emit Directory elements for children of *prefix*."""
        children = sorted(
            d
            for d in dirs_seen
            if d != prefix
            and d.startswith((prefix + "/") if prefix else "")
            and "/" not in d[len(prefix) + 1 if prefix else 0 :]
        )
        for child in children:
            name = child.split("/")[-1] if "/" in child else child
            if not name:
                continue
            sub = ET.SubElement(
                parent_el,
                "Directory",
                {"Id": _dir_id(child), "Name": name},
            )
            _emit_dir_tree(sub, child)

    install_folder_el = ET.SubElement(
        fragment,
        "DirectoryRef",
        {"Id": "INSTALLFOLDER"},
    )
    _emit_dir_tree(install_folder_el, "")

    # ── ComponentGroup ────────────────────────────────────────────────────
    cg = ET.SubElement(fragment, "ComponentGroup", {"Id": "ApplicationFiles"})

    for rel_dir, files in sorted(dir_files.items()):
        dir_id = _dir_id(rel_dir)
        for f in sorted(files):
            rel = f.relative_to(app_dir)
            rel_str = str(rel).replace("\\", "/")
            cid = _component_id(rel_str)
            cguid = _component_guid(rel_str)
            fid = _file_id(rel_str)

            comp_el = ET.SubElement(
                cg,
                "Component",
                {
                    "Id": cid,
                    "Guid": cguid,
                    "Directory": dir_id,
                },
            )
            file_attrs: dict[str, str] = {
                "Id": fid,
                "Source": str(f),
                "KeyPath": "yes",
            }
            # Mark openstan.exe so the icon reference in openstan.wxs resolves.
            if f.name.lower() == "openstan.exe" and rel_dir == "":
                file_attrs["Id"] = "openstan.exe"
            ET.SubElement(comp_el, "File", file_attrs)

    # Serialise with indentation (Python 3.9+).
    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        fh.write(
            "<!-- AUTO-GENERATED by make_wix_fragments.py — do not edit by hand -->\n"
        )
        tree.write(fh, encoding="unicode", xml_declaration=False)
        fh.write("\n")

    print(f"Written: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--app-dir",
        default="dist/openstan",
        help="Path to the cx_Freeze output directory (default: dist/openstan)",
    )
    parser.add_argument(
        "--out",
        default="packaging/windows/files.wxs",
        help="Output .wxs fragment path (default: packaging/windows/files.wxs)",
    )
    args = parser.parse_args()

    app_dir = Path(args.app_dir)
    if not app_dir.exists():
        print(
            f"ERROR: Application directory not found: {app_dir}\n"
            "Run 'uv run --with cx-freeze python cx_freeze_setup.py build' first.",
            file=sys.stderr,
        )
        sys.exit(1)

    harvest(app_dir, Path(args.out))


if __name__ == "__main__":
    main()
