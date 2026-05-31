#!/usr/bin/env python3
"""
Build the SoLoTV Kodi build from the Diggz foundation, rebranded as SoLoVision.

Pipeline:
  1. Download the upstream foundation build zip(s) (cached in work/).
  2. Rebrand text files (Diggz -> SoLoTV / SoLoVision) and apply file overrides
     from src/solotv_build/overrides/ (for images and other binary assets).
  3. Repackage into public/solotv/builds/solotv-<version>-<kodi>.zip.
  4. Publish our own build list (builds.xml) plus the wizard's notify/videos/
     changelog text files so the SoLoTV Build Wizard points only at us.

Large zips are generated at (docker) build time and are not committed to git.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen
from xml.sax.saxutils import escape

WIZARD_USERVAR = "addons/plugin.program.chef21/uservar.py"
WIZARD_DOWNLOADER = "addons/plugin.program.chef21/resources/lib/modules/downloader.py"
WIZARD_BUILD_INSTALL = (
    "addons/plugin.program.chef21/resources/lib/modules/build_install.py"
)
SKIN_SHORTCUTS_DIR = "userdata/addon_data/script.skinshortcuts"

# Reuse the branding rules already used to rebrand the SoLoTV catalog.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mirror_solotv_repo import (  # noqa: E402
    PATCHED_WIZARD_DOWNLOADER,
    PATCH_INSIDE_ZIP_SUFFIXES,
    SOLOKODI_SETUP_ADDON,
    TEXT_REPLACEMENTS,
    patch_wizard_build_install_code,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src" / "solotv_build" / "build.json"
OVERRIDES_DIR = ROOT / "src" / "solotv_build" / "overrides"
CARD_SOURCE = (
    ROOT
    / "src"
    / "plugin.program.solokodi.setup"
    / "resources"
    / "media"
    / "cards"
    / "solotv.png"
)
WORK = ROOT / "work" / "solotv_build"
PUBLIC_SOLOTV = ROOT / "public" / "solotv"
PUBLIC_BUILDS = PUBLIC_SOLOTV / "builds"
PUBLIC_CARDS = PUBLIC_SOLOTV / "cards"
SOLOKIDS_TEXT_REPLACEMENTS = (
    (re.compile(r"\bDiggz Xenon 2\b", re.I), "SoLoKids TV Xenon 2"),
    (re.compile(r"\bDiggz Xenon\b", re.I), "SoLoKids TV Xenon"),
    (re.compile(r"\bDiggzFlix 2\b", re.I), "SoLoKids TV Flix 2"),
    (re.compile(r"\bDiggzFlix\b", re.I), "SoLoKids TV Flix"),
    (re.compile(r"\bDiggz Kidz\b", re.I), "SoLoKids TV Kids Skin"),
    (re.compile(r"\bDiggz 4K Wallpapers\b", re.I), "SoLoKids TV 4K Wallpapers"),
    (re.compile(r"\bDiggz TV Guide Lite\b", re.I), "SoLoKids TV Guide Lite"),
    (re.compile(r"\bDiggz Simple Clean\b", re.I), "SoLoKids TV Simple Clean"),
    (re.compile(r"\bDiggz Skin Switcher\b", re.I), "SoLoKids TV Skin Switcher"),
    (re.compile(r"\bDiggz Repository\b", re.I), "SoLoKids TV Repository"),
    (re.compile(r"\bChef Omega Wizard\b", re.I), "SoLoKids TV Build Wizard"),
    (re.compile(r"\bChef Wizard\b", re.I), "SoLoKids TV Build Wizard"),
    (re.compile(r"\bChef Omega\b", re.I), "SoLoKids TV Build Wizard"),
    (re.compile(r"\bDiggz\b"), "SoLoKids TV"),
    (re.compile(r"\bDIGGZ\b"), "SoLoVision"),
)
SOLOTV_SKIN_SHORTCUT_SKINS = (
    "skin.diggzflix2",
    "skin.auraflix",
    "skin.xenon",
    "skin.xenon2",
    "skin.arctic.horizon.2",
    "skin.eminence.2.mod",
)
SOLOTV_MENU_SECTIONS = (
    {
        "id": "movies",
        "label": "Movies",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/clapperboard.png",
        "action": 'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=dir_movie&tmdb_type=None&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D&widget=true",return)',
    },
    {
        "id": "tvshows",
        "label": "TV Shows",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/tv.png",
        "action": 'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=dir_tv&tmdb_type=None&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D&widget=true",return)',
    },
    {
        "id": "livetv",
        "label": "Live TV",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/antenna.png",
        "action": 'ActivateWindow(Videos,"plugin://plugin.video.playlistbrowser",return)',
    },
    {
        "id": "sports",
        "label": "Sports",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/sports.png",
        "action": 'ActivateWindow(Videos,"plugin://plugin.video.yt.kiosk/?action=chip&label=Sports&url=https%3A%2F%2Fwww.youtube.com%2Fsports%3Fgl%3DUS%26hl%3Den%26persist_gl%3D1%26persist_hl%3D1",return)',
    },
    {
        "id": "yourtrakt",
        "label": "Your Trakt",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/mylist.png",
        "action": 'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=dir_trakt&tmdb_type=None&widget=true&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D",return)',
    },
    {
        "id": "addons",
        "label": "Add-ons",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/defaultaddonfavourites.png",
        "action": "ActivateWindow(AddonBrowser)",
    },
    {
        "id": "solotvsetup",
        "label": "SoLoTV Setup",
        "icon": "special://home/addons/plugin.program.solokodi.setup/resources/media/icon.png",
        "action": "RunAddon(plugin.program.solokodi.setup)",
    },
    {
        "id": "settings",
        "label": "Settings",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/settings.png",
        "action": "ActivateWindow(Settings)",
    },
    {
        "id": "exit",
        "label": "Exit",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/power.png",
        "action": "ActivateWindow(shutdownmenu)",
    },
)
SOLOTV_SUBMENUS = {
    "movies": (
        (
            "Trending Movies",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=trending&tmdb_type=movie&widget=true&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D",return)',
        ),
        (
            "Popular Movies",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie&widget=true&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D",return)',
        ),
        (
            "Search Movies",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=movie",return)',
        ),
    ),
    "tvshows": (
        (
            "Trending TV Shows",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=trending&tmdb_type=tv&widget=true&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D",return)',
        ),
        (
            "Popular TV Shows",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=tv&widget=true&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D",return)',
        ),
        (
            "Search TV Shows",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=tv",return)',
        ),
    ),
    "livetv": (
        ("SoLoTV Guide Lite", 'ActivateWindow(Videos,"plugin://plugin.video.playlistbrowser",return)'),
        (
            "The TV App",
            'ActivateWindow(Videos,"plugin://plugin.video.playlistbrowser/?action=guide_now&src=100",return)',
        ),
        (
            "Refresh All Channels",
            'PlayMedia("plugin://plugin.video.playlistbrowser/?action=refresh_all")',
        ),
    ),
    "sports": (
        (
            "Sports on YouTube",
            'ActivateWindow(Videos,"plugin://plugin.video.yt.kiosk/?action=chip&label=Sports&url=https%3A%2F%2Fwww.youtube.com%2Fsports%3Fgl%3DUS%26hl%3Den%26persist_gl%3D1%26persist_hl%3D1",return)',
        ),
        (
            "Live Sports Channels",
            'ActivateWindow(Videos,"plugin://plugin.video.playlistbrowser/?action=channels_by_group&src=100&group=Sports",return)',
        ),
    ),
    "yourtrakt": (
        (
            "All Trakt",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=dir_trakt&tmdb_type=None&widget=true&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D",return)',
        ),
        (
            "In Progress",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=trakt_inprogress&tmdb_type=both&widget=true&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D",return)',
        ),
        (
            "Trakt Lists",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=trakt_userlists&tmdb_type=both&widget=true&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D",return)',
        ),
    ),
    "addons": (
        ("Video Add-ons", "ActivateWindow(Videos,addons://sources/video/,return)"),
        ("Program Add-ons", "ActivateWindow(Programs,addons://sources/executable/,return)"),
        ("Add-on Browser", "ActivateWindow(AddonBrowser)"),
    ),
    "solotvsetup": (
        ("Open SoLoTV Setup", "RunAddon(plugin.program.solokodi.setup)"),
        ("Open Build Wizard", "RunAddon(plugin.program.chef21)"),
    ),
    "settings": (
        ("Kodi Settings", "ActivateWindow(Settings)"),
        ("Skin Settings", "ActivateWindow(SkinSettings)"),
        ("File Manager", "ActivateWindow(FileManager)"),
    ),
    "exit": (
        ("Power Menu", "ActivateWindow(shutdownmenu)"),
        ("Quit Kodi", "Quit()"),
    ),
}
SOLOKIDS_TV_MENU_SECTIONS = (
    {
        "id": "kidsmovies",
        "label": "Kids Movies",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/clapperboard.png",
        "action": 'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=dir_movie&tmdb_type=None&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D&widget=true",return)',
    },
    {
        "id": "kidstv",
        "label": "Kids TV",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/tv.png",
        "action": 'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=dir_tv&tmdb_type=None&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D&widget=true",return)',
    },
    {
        "id": "livekids",
        "label": "Live Kids TV",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/antenna.png",
        "action": 'ActivateWindow(Videos,"plugin://plugin.video.playlistbrowser",return)',
    },
    {
        "id": "search",
        "label": "Search",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/search.png",
        "action": 'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=movie",return)',
    },
    {
        "id": "addons",
        "label": "Add-ons",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/defaultaddonfavourites.png",
        "action": "ActivateWindow(AddonBrowser)",
    },
    {
        "id": "solokidstvsetup",
        "label": "SoLoKids TV Setup",
        "icon": "special://home/addons/plugin.program.solokodi.setup/resources/media/icon.png",
        "action": "RunAddon(plugin.program.solokodi.setup)",
    },
    {
        "id": "settings",
        "label": "Settings",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/settings.png",
        "action": "ActivateWindow(Settings)",
    },
    {
        "id": "exit",
        "label": "Exit",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/power.png",
        "action": "ActivateWindow(shutdownmenu)",
    },
)
SOLOKIDS_TV_SUBMENUS = {
    "kidsmovies": (
        (
            "Family Movies",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie&widget=true&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D",return)',
        ),
        (
            "Animated Movies",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=trending&tmdb_type=movie&widget=true&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D",return)',
        ),
        (
            "Search Movies",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=movie",return)',
        ),
    ),
    "kidstv": (
        (
            "Family Shows",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=tv&widget=true&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D",return)',
        ),
        (
            "Animated Shows",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=trending&tmdb_type=tv&widget=true&reload=%24INFO%5BWindow%28Home%29.Property%28TMDbHelper.Widgets.Reload%29%5D",return)',
        ),
        (
            "Search TV Shows",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=tv",return)',
        ),
    ),
    "livekids": (
        ("TV Guide Lite", 'ActivateWindow(Videos,"plugin://plugin.video.playlistbrowser",return)'),
        (
            "Kids Channels",
            'ActivateWindow(Videos,"plugin://plugin.video.playlistbrowser/?action=channels_by_group&src=100&group=Kids",return)',
        ),
        (
            "Refresh Channels",
            'PlayMedia("plugin://plugin.video.playlistbrowser/?action=refresh_all")',
        ),
    ),
    "search": (
        (
            "Search Movies",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=movie",return)',
        ),
        (
            "Search TV Shows",
            'ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=tv",return)',
        ),
    ),
    "addons": (
        ("Video Add-ons", "ActivateWindow(Videos,addons://sources/video/,return)"),
        ("Program Add-ons", "ActivateWindow(Programs,addons://sources/executable/,return)"),
        ("Add-on Browser", "ActivateWindow(AddonBrowser)"),
    ),
    "solokidstvsetup": (
        ("Open SoLoKids TV Setup", "RunAddon(plugin.program.solokodi.setup)"),
        ("Open Build Wizard", "RunAddon(plugin.program.chef21)"),
    ),
    "settings": (
        ("Kodi Settings", "ActivateWindow(Settings)"),
        ("Skin Settings", "ActivateWindow(SkinSettings)"),
        ("File Manager", "ActivateWindow(FileManager)"),
    ),
    "exit": (
        ("Power Menu", "ActivateWindow(shutdownmenu)"),
        ("Quit Kodi", "Quit()"),
    ),
}


@dataclass(frozen=True)
class BuildContext:
    profile: str
    config_path: Path
    overrides_dir: Path
    card_source: Path
    work_dir: Path
    public_dir: Path
    builds_dir: Path
    cards_dir: Path
    output_prefix: str
    menu_sections: tuple[dict, ...]
    submenus: dict[str, tuple[tuple[str, str], ...]]
    text_replacements: tuple
    skin_shortcut_skins: tuple[str, ...] = SOLOTV_SKIN_SHORTCUT_SKINS

    @property
    def config(self) -> dict:
        return json.loads(self.config_path.read_text(encoding="utf-8"))


def load_build_context(profile: str = "solotv") -> BuildContext:
    profile = (profile or "solotv").lower()
    if profile in ("solotv", "solo-tv"):
        return BuildContext(
            profile="solotv",
            config_path=ROOT / "src" / "solotv_build" / "build.json",
            overrides_dir=ROOT / "src" / "solotv_build" / "overrides",
            card_source=CARD_SOURCE,
            work_dir=ROOT / "work" / "solotv_build",
            public_dir=PUBLIC_SOLOTV,
            builds_dir=PUBLIC_BUILDS,
            cards_dir=PUBLIC_CARDS,
            output_prefix="solotv",
            menu_sections=SOLOTV_MENU_SECTIONS,
            submenus=SOLOTV_SUBMENUS,
            text_replacements=TEXT_REPLACEMENTS,
        )
    if profile in ("solokids-tv", "solokidstv", "kids-tv"):
        public_dir = ROOT / "public" / "solokids-tv"
        return BuildContext(
            profile="solokids-tv",
            config_path=ROOT / "src" / "solokids_tv_build" / "build.json",
            overrides_dir=ROOT / "src" / "solokids_tv_build" / "overrides",
            card_source=(
                ROOT
                / "src"
                / "plugin.program.solokodi.setup"
                / "resources"
                / "media"
                / "cards"
                / "solokids-tv.png"
            ),
            work_dir=ROOT / "work" / "solokids_tv_build",
            public_dir=public_dir,
            builds_dir=public_dir / "builds",
            cards_dir=public_dir / "cards",
            output_prefix="solokids-tv",
            menu_sections=SOLOKIDS_TV_MENU_SECTIONS,
            submenus=SOLOKIDS_TV_SUBMENUS,
            text_replacements=SOLOKIDS_TEXT_REPLACEMENTS,
        )
    raise SystemExit("Unknown build profile: {0}".format(profile))


def load_config(context: BuildContext | None = None) -> dict:
    context = context or load_build_context()
    return json.loads(context.config_path.read_text(encoding="utf-8"))


def _source_urls(source: dict) -> list[str]:
    if source.get("urls"):
        return list(source["urls"])
    if source.get("url"):
        return [source["url"]]
    return []


def _download_one(url: str, dest: Path) -> None:
    print(f"  downloading {url}")
    with urlopen(url, timeout=600) as response, open(dest, "wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        read = 0
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)
            read += len(chunk)
            if total:
                pct = int(read / total * 100)
                print(f"\r  {pct:3d}%  {read // (1024 * 1024)}/{total // (1024 * 1024)} MB", end="")
    print(f"\r  downloaded {dest.name} ({dest.stat().st_size // (1024 * 1024)} MB)")


def download(urls: list[str], dest: Path, force: bool = False) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        print(f"  cached {dest.name} ({dest.stat().st_size // (1024 * 1024)} MB)")
        return
    last_error: Exception | None = None
    for url in urls:
        try:
            _download_one(url, dest)
            return
        except Exception as exc:  # noqa: BLE001 - try the next mirror
            last_error = exc
            print(f"\n  failed: {exc}")
            if dest.exists():
                dest.unlink()
    raise SystemExit(f"All download mirrors failed for {dest.name}: {last_error}")


def rebrand_bytes(name: str, data: bytes, context: BuildContext | None = None) -> bytes:
    if Path(name).suffix.lower() not in PATCH_INSIDE_ZIP_SUFFIXES:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    context = context or load_build_context()
    for pattern, replacement in context.text_replacements:
        text = pattern.sub(replacement, text)
    return text.encode("utf-8")


def repoint_uservar(data: bytes, wizard_sources: dict) -> bytes:
    """Rewrite the bundled wizard's uservar.py to read from SoLoVision URLs."""
    if not wizard_sources:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    for var_name, url in wizard_sources.items():
        if not url:
            continue
        pattern = r"(?m)^(\s*{0}\s*=\s*).*$".format(re.escape(var_name))
        text = re.sub(pattern, r"\g<1>'{0}'".format(url), text, count=1)
    if SOLOKODI_SETUP_ADDON not in text:
        text = re.sub(
            r"(?m)^(\s*excludes\s*=\s*\[)([^\]]*)(\].*)$",
            lambda match: "{0}{1}{2}'{3}'{4}".format(
                match.group(1),
                match.group(2),
                ", " if match.group(2).strip() else "",
                SOLOKODI_SETUP_ADDON,
                match.group(3),
            ),
            text,
            count=1,
        )
    return text.encode("utf-8")


def _skip_member(name: str) -> bool:
    """Drop stale compiled caches of patched wizard modules so our edits win."""
    lower = name.lower()
    if "plugin.program.chef21" not in lower or not lower.endswith(".pyc"):
        return False
    return (
        "uservar" in lower
        or "modules/downloader" in lower
        or "modules/build_install" in lower
    )


def load_overrides(context: BuildContext | None = None) -> dict[str, bytes]:
    context = context or load_build_context()
    overrides: dict[str, bytes] = {}
    if not context.overrides_dir.exists():
        return overrides
    for path in context.overrides_dir.rglob("*"):
        if path.is_file() and path.name != "README.md":
            rel = path.relative_to(context.overrides_dir).as_posix()
            overrides[rel] = path.read_bytes()
    return overrides


def _shortcut_xml(
    label: str,
    action: str,
    *,
    default_id: str = "",
    label2: str = "Custom item",
    icon: str = "DefaultShortcut.png",
    thumb: str = "",
) -> str:
    fields = (
        ("defaultID", default_id),
        ("label", label),
        ("label2", label2),
        ("icon", icon),
        ("thumb", thumb),
        ("action", action),
    )
    lines = ["\t<shortcut>"]
    for tag, value in fields:
        lines.append(f"\t\t<{tag}>{escape(value)}</{tag}>")
    lines.append("\t</shortcut>")
    return "\n".join(lines)


def _shortcuts_xml(shortcuts: list[str]) -> bytes:
    body = "\n".join(shortcuts)
    return f"<shortcuts>\n{body}\n</shortcuts>\n".encode("utf-8")


def build_solotv_skin_shortcut_overrides(
    context: BuildContext | None = None,
) -> dict[str, bytes]:
    """Provide every bundled skin with the same branded home sections."""
    context = context or load_build_context()
    overrides: dict[str, bytes] = {}
    mainmenu = _shortcuts_xml(
        [
            _shortcut_xml(
                section["label"],
                section["action"],
                default_id=section["id"],
                icon=section["icon"],
                thumb=section["icon"],
            )
            for section in context.menu_sections
        ]
    )
    for skin_id in context.skin_shortcut_skins:
        base = f"{SKIN_SHORTCUTS_DIR}/{skin_id}"
        overrides[f"{base}-mainmenu.DATA.xml"] = mainmenu
        for section_id, entries in context.submenus.items():
            overrides[f"{base}-{section_id}.DATA.xml"] = _shortcuts_xml(
                [
                    _shortcut_xml(
                        label,
                        action,
                        default_id=re.sub(r"[^a-z0-9]+", "", label.lower()),
                        label2="Video Add-On" if "plugin.video." in action else "Custom item",
                    )
                    for label, action in entries
                ]
            )
    return overrides


def inspect_build(src_zip: Path) -> None:
    """Print branded paths and the largest images to seed overrides."""
    keywords = ("diggz", "xenon", "chef")
    branded = []
    images = []
    with zipfile.ZipFile(src_zip) as archive:
        for item in archive.infolist():
            lower = item.filename.lower()
            if any(word in lower for word in keywords):
                branded.append(item.filename)
            if lower.endswith((".png", ".jpg", ".jpeg", ".gif")):
                images.append((item.file_size, item.filename))
    print(f"\n=== Branded paths (diggz/xenon/chef) in {src_zip.name}: {len(branded)} ===")
    for name in sorted(branded)[:80]:
        print(f"  {name}")
    print(f"\n=== Largest images in {src_zip.name} ===")
    for size, name in sorted(images, reverse=True)[:40]:
        print(f"  {size // 1024:6d} KB  {name}")


def process_source(
    source: dict,
    version: str,
    overrides: dict[str, bytes],
    wizard_sources: dict,
    force: bool,
    context: BuildContext | None = None,
) -> str:
    context = context or load_build_context()
    kodi = source["kodi"]
    src_zip = context.work_dir / f"foundation-{kodi}.zip"
    download(_source_urls(source), src_zip, force=force)

    out_name = f"{context.output_prefix}-{version}-{kodi}.zip"
    out_path = context.builds_dir / out_name
    context.builds_dir.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    print(f"  rebranding -> {out_name}")
    applied = 0
    written_overrides: set[str] = set()
    with zipfile.ZipFile(src_zip) as zin, zipfile.ZipFile(
        out_path, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            rel = item.filename
            if _skip_member(rel):
                continue
            data = zin.read(rel)
            if rel in overrides:
                data = overrides[rel]
                written_overrides.add(rel)
                applied += 1
            elif rel == WIZARD_USERVAR:
                data = repoint_uservar(rebrand_bytes(rel, data, context), wizard_sources)
            elif rel == WIZARD_DOWNLOADER:
                data = PATCHED_WIZARD_DOWNLOADER.encode("utf-8")
            elif rel == WIZARD_BUILD_INSTALL:
                data = patch_wizard_build_install_code(rel, data)
            else:
                data = rebrand_bytes(rel, data, context)
            zout.writestr(item, data)
        for rel, data in sorted(overrides.items()):
            if rel in written_overrides:
                continue
            zout.writestr(rel, data)
            applied += 1
    print(f"  wrote {out_name} ({out_path.stat().st_size // (1024 * 1024)} MB, {applied} overrides applied)")
    return out_name


def write_build_list(
    config: dict,
    produced: list[tuple[str, str]],
    context: BuildContext | None = None,
) -> None:
    context = context or load_build_context()
    base = config["base_url"].rstrip("/")
    parts = ["<builds>", ""]
    for kodi, out_name in produced:
        parts += [
            "<build>",
            f"<name>{config['name']}</name>",
            f"<version>{config['version']}</version>",
            f"<kodi>{kodi}</kodi>",
            f"<url>{base}/{out_name}</url>",
            f"<icon>{config['icon']}</icon>",
            f"<fanart>{config['fanart']}</fanart>",
            f"<description>{config['description']}</description>",
            "</build>",
            "",
        ]
    parts.append("</builds>")
    context.public_dir.mkdir(parents=True, exist_ok=True)
    (context.public_dir / "builds.xml").write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"  wrote builds.xml ({len(produced)} build(s))")


def prune_stale_build_zips(
    produced: list[tuple[str, str]],
    context: BuildContext | None = None,
) -> None:
    context = context or load_build_context()
    keep = {name for _, name in produced}
    removed = 0
    for path in context.builds_dir.glob(f"{context.output_prefix}-*.zip"):
        if path.name not in keep:
            path.unlink()
            removed += 1
    if removed:
        print(f"  removed {removed} stale {config_name(context)} build zip(s)")


def config_name(context: BuildContext) -> str:
    try:
        return load_config(context).get("name", context.profile)
    except (OSError, json.JSONDecodeError):
        return context.profile


def write_wizard_text_files(config: dict, context: BuildContext | None = None) -> None:
    context = context or load_build_context()
    context.public_dir.mkdir(parents=True, exist_ok=True)
    # Notification shown in the wizard (blank = no nag). Format: [COLOR ...]msg[/COLOR]
    (context.public_dir / "notify.txt").write_text("", encoding="utf-8")
    # Optional promo videos list (none).
    (context.public_dir / "videos.txt").write_text("", encoding="utf-8")
    # Changelog the wizard can display.
    changelog = (
        f"{config['name']} v{config['version']}\n"
        "- SoLoVision-branded build, maintained in the SoLoKodi repo.\n"
    )
    (context.public_dir / "changelog.txt").write_text(changelog, encoding="utf-8")
    print("  wrote notify.txt, videos.txt, changelog.txt")


def publish_card_icon(context: BuildContext | None = None) -> None:
    context = context or load_build_context()
    if context.card_source.exists():
        context.cards_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(context.card_source, context.cards_dir / context.card_source.name)
        print(f"  published cards/{context.card_source.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the rebranded SoLoTV build.")
    parser.add_argument(
        "--profile",
        default="solotv",
        help="Build profile to package: solotv or solokids-tv.",
    )
    parser.add_argument("kodi", nargs="?", help="Only build this Kodi target (e.g. K21).")
    parser.add_argument("--force", action="store_true", help="Re-download foundation zips.")
    parser.add_argument("--inspect", action="store_true", help="List branded paths/images and exit.")
    parser.add_argument(
        "--xml-only",
        action="store_true",
        help="Only (re)write builds.xml + wizard text files (no download/repackage).",
    )
    args = parser.parse_args()

    context = load_build_context(args.profile)
    config = load_config(context)
    sources = config["sources"]
    if args.kodi:
        sources = [s for s in sources if s["kodi"].lower() == args.kodi.lower()]
        if not sources:
            print(f"No source for Kodi target {args.kodi!r}")
            return 1

    if args.inspect:
        for source in sources:
            src_zip = context.work_dir / f"foundation-{source['kodi']}.zip"
            download(_source_urls(source), src_zip, force=args.force)
            inspect_build(src_zip)
        return 0

    if args.xml_only:
        produced = [
            (s["kodi"], f"{context.output_prefix}-{config['version']}-{s['kodi']}.zip")
            for s in sources
        ]
        write_build_list(config, produced, context)
        write_wizard_text_files(config, context)
        publish_card_icon(context)
        return 0

    file_overrides = load_overrides(context)
    skin_menu_overrides = build_solotv_skin_shortcut_overrides(context)
    overrides = {**file_overrides, **skin_menu_overrides}
    print(
        f"Loaded {len(file_overrides)} file override(s) from {context.overrides_dir} "
        f"and {len(skin_menu_overrides)} generated skin menu override(s)"
    )
    wizard_sources = config.get("wizard_sources") or {}

    produced: list[tuple[str, str]] = []
    for source in sources:
        print(f"\n[{source['kodi']}] building from foundation...")
        out_name = process_source(
            source, config["version"], overrides, wizard_sources, args.force, context
        )
        produced.append((source["kodi"], out_name))

    write_build_list(config, produced, context)
    prune_stale_build_zips(produced, context)
    write_wizard_text_files(config, context)
    publish_card_icon(context)
    print(f"\nDone. Published {len(produced)} {config['name']} build(s) to {context.builds_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
