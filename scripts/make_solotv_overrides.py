#!/usr/bin/env python3
"""Regenerate SoLoTV brand override images from two master images.

The two masters live in ``src/solotv_build/brand/`` and every branded asset in
the build is derived from them at the exact dimensions Kodi expects. Edit a
master (keep the brand palette) and re-run to refresh all overrides at once::

    python scripts/make_solotv_overrides.py

Brand palette: Dark Navy ``#1B2232``, Deep Red ``#BC2026``,
Cool Light Grey ``#A9B2BC``, White ``#FFFFFF``.

After running, rebuild the build so the new art is baked in::

    python scripts/build_solotv_build.py K21
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "src" / "solotv_build" / "brand"
OVERRIDES = ROOT / "src" / "solotv_build" / "overrides"
SETUP_CARD = (
    ROOT
    / "src"
    / "plugin.program.solokodi.setup"
    / "resources"
    / "media"
    / "cards"
    / "solotv.png"
)
PUBLIC_CARD = ROOT / "public" / "solotv" / "cards" / "solotv.png"

# Branded backgrounds / fanart / gifs -> derived from the wide background master.
BG_TARGETS = [
    ("addons/resource.images.skinbackgrounds.xenon/resources/Diggz/diggz.png", 1700, 956),
    # Active skin (Aeon Tajo) home background — has the baked-in "PLANET DIGGZ" wordmark.
    ("addons/skin.aeon.tajo/backgrounds/default_bg.jpg", 1700, 956),
    ("addons/plugin.program.chef21/resources/fanart.jpg", 1268, 664),
    ("addons/script.diggzskins/fanart.jpg", 1920, 1080),
    ("addons/script.diggzskins/resources/skins/Default/1080i/bg.jpg", 1920, 1080),
    ("addons/plugin.program.chef21/resources/skins/Default/media/bg_screen.jpg", 2048, 2070),
    ("addons/plugin.program.chef21/resources/skins/Default/media/background.png", 1280, 720),
    ("addons/resource.images.skinicons.wide/resources/diggzflix_back.jpg", 467, 263),
    ("addons/resource.images.skinicons.wide/resources/diggzflixintro.gif", 760, 428),
    ("addons/resource.images.skinicons.wide/resources/diggzflixspinner.gif", 320, 180),
]

# Branded icons -> derived from the square icon master.
ICON_TARGETS = [
    ("addons/plugin.program.chef21/resources/icon.png", 570, 500),
    ("addons/resource.images.skinicons.wide/resources/chef.png", 570, 500),
    ("addons/resource.images.skinicons.wide/resources/icons/chef.png", 570, 500),
    ("addons/resource.images.skinicons.wide/resources/icons/chefdoc.png", 570, 500),
    ("addons/repository.diggz/icon.png", 570, 500),
    ("addons/resource.images.skinicons.wide/resources/icons/diggztvguide.png", 828, 849),
    ("addons/resource.images.skinicons.wide/resources/icons/diggzsports.png", 225, 225),
    ("addons/resource.images.skinicons.wide/resources/icons/diggzwiki.png", 135, 135),
    ("addons/resource.images.skinicons.wide/resources/icons/xenon.png", 487, 441),
    ("addons/resource.images.skinicons.wide/resources/icons/3d-logo-1.png", 550, 550),
    ("addons/script.diggzskins/icon.png", 287, 287),
    ("addons/plugin.program.diggzflavors/resources/icon.png", 287, 287),
]


def _save(img: Image.Image, dest: Path, width: int, height: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fitted = ImageOps.fit(img, (width, height), Image.LANCZOS)
    ext = dest.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        fitted.convert("RGB").save(dest, "JPEG", quality=88, optimize=True)
    elif ext == ".gif":
        fitted.convert("P", palette=Image.ADAPTIVE).save(dest, "GIF")
    else:
        fitted.convert("RGBA").save(dest, "PNG", optimize=True)


def main() -> int:
    bg = Image.open(BRAND / "solotv_bg_master.png").convert("RGB")
    icon = Image.open(BRAND / "solotv_icon_master.png").convert("RGB")

    for rel, w, h in BG_TARGETS:
        _save(bg, OVERRIDES / rel, w, h)
    for rel, w, h in ICON_TARGETS:
        _save(icon, OVERRIDES / rel, w, h)

    # Build-picker / CDN card (16:9 crop of the background master).
    for card in (SETUP_CARD, PUBLIC_CARD):
        _save(bg, card, 640, 427)

    total = len(BG_TARGETS) + len(ICON_TARGETS)
    print(f"Wrote {total} override images + 2 cards from masters in {BRAND}")
    print("Next: python scripts/build_solotv_build.py   (all targets, refresh builds.xml)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
