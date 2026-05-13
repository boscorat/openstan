"""make_installer_bitmaps.py — Generate WiX installer branding bitmaps.

Produces two BMP files used by the WiX WixUI_InstallDir theme:

  packaging/windows/banner.bmp   (493 × 58 px)
      Displayed at the top of every inner wizard page (e.g. folder selection,
      progress, ready-to-install).  Contains the app logo on the right and
      a dark-toned background matching the app colour scheme.

  packaging/windows/dialog.bmp   (493 × 312 px)
      Full background of the Welcome and Finish pages.  Contains a large
      centred logo watermark on the left panel and a gradient background.

Both bitmaps are generated from the app SVG using resvg (already on PATH on
the Windows CI runner) and Pillow (available via --with pillow in CI).

Usage
-----
    python packaging/windows/make_installer_bitmaps.py \\
        --svg src/openstan/icons/icon-square.svg \\
        --resvg path/to/resvg.exe   (optional; defaults to 'resvg' on PATH)

The script writes:
    packaging/windows/banner.bmp
    packaging/windows/dialog.bmp
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print(
        "ERROR: Pillow is required. Run with: uv run --with pillow python "
        "packaging/windows/make_installer_bitmaps.py",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Colour palette — matches the openstan app theme
# ---------------------------------------------------------------------------
# Background: deep charcoal matching the app's dark sidebar
_BG_DARK = (30, 33, 36)
# Mid-tone: slightly lighter for gradient
_BG_MID = (45, 49, 54)
# Accent: the teal/green accent used in the app logo area
_ACCENT = (72, 199, 142)
# Text: near-white
_TEXT_LIGHT = (240, 243, 246)


def _render_svg_to_png(svg: Path, size: int, resvg: str, out: Path) -> None:
    """Render *svg* at *size*×*size* pixels to *out* using resvg."""
    subprocess.run(
        [resvg, "--width", str(size), "--height", str(size), str(svg), str(out)],
        check=True,
    )


def _horizontal_gradient(img: Image.Image, left: tuple, right: tuple) -> None:
    """Fill *img* in-place with a horizontal gradient from *left* to *right* RGB."""
    w, h = img.size
    for x in range(w):
        t = x / max(w - 1, 1)
        r = int(left[0] + (right[0] - left[0]) * t)
        g = int(left[1] + (right[1] - left[1]) * t)
        b = int(left[2] + (right[2] - left[2]) * t)
        draw = ImageDraw.Draw(img)
        draw.line([(x, 0), (x, h - 1)], fill=(r, g, b))


def make_banner(svg: Path, resvg: str, out: Path) -> None:
    """Generate the 493×58 px banner bitmap."""
    W, H = 493, 58

    img = Image.new("RGB", (W, H), _BG_DARK)
    _horizontal_gradient(img, _BG_DARK, _BG_MID)

    # Render logo at 42 px and paste flush-right with 8 px margin
    logo_size = 42
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        _render_svg_to_png(svg, logo_size, resvg, tmp_path)
        logo = Image.open(tmp_path).convert("RGBA")
        # Paste using the alpha channel as mask
        x = W - logo_size - 8
        y = (H - logo_size) // 2
        img.paste(logo, (x, y), logo)
    finally:
        tmp_path.unlink(missing_ok=True)

    # Thin accent line at the bottom
    draw = ImageDraw.Draw(img)
    draw.line([(0, H - 2), (W, H - 2)], fill=_ACCENT, width=2)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), format="BMP")
    print(f"Written banner:  {out}  ({W}×{H})")


def make_dialog(svg: Path, resvg: str, out: Path) -> None:
    """Generate the 493×312 px Welcome/Finish dialog bitmap."""
    W, H = 493, 312
    # Left panel width (dark, contains logo watermark)
    PANEL_W = 170

    img = Image.new("RGB", (W, H), (248, 249, 250))  # light right panel

    # Left panel — dark gradient
    left_panel = Image.new("RGB", (PANEL_W, H), _BG_DARK)
    _horizontal_gradient(left_panel, _BG_DARK, _BG_MID)
    img.paste(left_panel, (0, 0))

    # Accent bar separating panels
    draw = ImageDraw.Draw(img)
    draw.line([(PANEL_W, 0), (PANEL_W, H)], fill=_ACCENT, width=3)

    # Logo watermark centred in the left panel (120 px)
    logo_size = 120
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        _render_svg_to_png(svg, logo_size, resvg, tmp_path)
        logo = Image.open(tmp_path).convert("RGBA")
        x = (PANEL_W - logo_size) // 2
        y = (H - logo_size) // 2 - 20
        img.paste(logo, (x, y), logo)
    finally:
        tmp_path.unlink(missing_ok=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), format="BMP")
    print(f"Written dialog:  {out}  ({W}×{H})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--svg",
        default="src/openstan/icons/icon-square.svg",
        help="Path to the app SVG icon (default: src/openstan/icons/icon-square.svg)",
    )
    parser.add_argument(
        "--resvg",
        default="resvg",
        help="Path to the resvg binary (default: 'resvg', assumed on PATH)",
    )
    parser.add_argument(
        "--out-dir",
        default="packaging/windows",
        help="Output directory for the bitmaps (default: packaging/windows)",
    )
    args = parser.parse_args()

    svg = Path(args.svg)
    if not svg.exists():
        print(f"ERROR: SVG not found: {svg}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir)
    make_banner(svg, args.resvg, out_dir / "banner.bmp")
    make_dialog(svg, args.resvg, out_dir / "dialog.bmp")


if __name__ == "__main__":
    main()
