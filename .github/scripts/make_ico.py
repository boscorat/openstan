"""Assemble a multi-resolution .ico from per-size PNGs produced by Inkscape.

Usage (called from the Windows release CI step):
    python .github/scripts/make_ico.py
"""

from PIL import Image

SIZES = [16, 32, 48, 64, 128, 256]
imgs = [Image.open(f"build/icons/icon_{sz}.png") for sz in SIZES]
imgs[0].save(
    "build/icons/openstan.ico",
    format="ICO",
    sizes=[(sz, sz) for sz in SIZES],
    append_images=imgs[1:],
)
print("Icon written to build/icons/openstan.ico")
