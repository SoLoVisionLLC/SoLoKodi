#!/usr/bin/env python3
"""Generate Bello skin shortcut files for the SoLoKodi Kids build."""
from __future__ import annotations

import json
import re
import sys
import xml.sax.saxutils
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "src" / "builds" / "kids.json"
DEFAULT_PROFILE = (
    Path.home()
    / "AppData"
    / "Roaming"
    / "Kodi"
    / "userdata"
    / "addon_data"
    / "script.skinshortcuts"
)
SKIN = "skin.bello.10"
ICONS = {
    "tvshows": "DefaultTVShows.png",
    "movies": "DefaultMovies.png",
    "livetv": "DefaultLiveTV.png",
    "videos": "DefaultVideo.png",
}
MAINMENU_ITEMS = (
    {
        "label": "Kids TV Shows",
        "default_id": "tvshows",
        "menu_group": "tvshows",
        "icon": "DefaultTVShows.png",
        "addon_id": "plugin.video.pbskids",
    },
    {
        "label": "Live Kids TV",
        "default_id": "livetv",
        "menu_group": "livetv",
        "icon": "DefaultLiveTV.png",
        "addon_id": "plugin.video.plutotv",
    },
    {
        "label": "Kids Movies",
        "default_id": "movies",
        "menu_group": "movies",
        "icon": "DefaultMovies.png",
        "addon_id": "plugin.video.solokodi.kidsrd",
    },
    {
        "label": "Explore",
        "default_id": "videos",
        "menu_group": "videos",
        "icon": "DefaultVideo.png",
        "addon_id": "plugin.video.youtube",
    },
)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def esc(text: str) -> str:
    return xml.sax.saxutils.escape(text or "")


def shortcut(label: str, default_id: str, action: str, icon: str) -> str:
    return (
        " <shortcut>\n"
        f"  <label>{esc(label)}</label>\n"
        "  <label2>32024</label2>\n"
        f"  <defaultID>{esc(default_id)}</defaultID>\n"
        f"  <icon>{esc(icon)}</icon>\n"
        "  <thumb />\n"
        f"  <action>{esc(action)}</action>\n"
        " </shortcut>\n"
    )


def entries(manifest: dict, group: str) -> list[dict]:
    items = []
    for entry in manifest.get("content_addons", []):
        if entry.get("menu_group") == group:
            items.append(entry)
    for entry in manifest.get("solokodi_addons", []):
        if entry.get("menu_group") == group:
            items.append(entry)
    return items


def group_xml(manifest: dict, group: str, fallback: str) -> str:
    lines = ["<?xml version='1.0' encoding='UTF-8'?>", "<shortcuts>"]
    for entry in entries(manifest, group):
        label = entry.get("favourite") or entry["label"]
        action = entry.get("action") or f"ActivateWindow(Videos,plugin://{entry['id']}/,return)"
        lines.append(shortcut(label, slug(entry["id"]), action, ICONS.get(group, "DefaultAddonVideo.png")))
    if len(lines) == 2:
        lines.append(
            shortcut(fallback, "solokodi-empty", "ActivateWindow(Videos,Addons,return)", ICONS.get(group, "DefaultAddonVideo.png"))
        )
    lines.append("</shortcuts>")
    return "\n".join(lines) + "\n"


def mainmenu_xml() -> str:
    lines = ["<?xml version='1.0' encoding='UTF-8'?>", "<shortcuts>"]
    for item in MAINMENU_ITEMS:
        action = item.get("action") or f"ActivateWindow(Videos,plugin://{item['addon_id']}/,return)"
        lines.append(shortcut(item["label"], item["default_id"], action, item["icon"]))
    lines.append(shortcut("All Kids Apps", "addons", "ActivateWindow(1170,return)", "DefaultAddon.png"))
    lines.append(shortcut("My Favourites", "favourites", "ActivateWindow(Favourites)", "icons/big/Favourites.png"))
    lines.append(shortcut("SoLoKodi Setup", "solokodi-setup", "RunAddon(plugin.program.solokodi.setup)", "DefaultProgram.png"))
    lines.append(shortcut("Settings", "settings", "ActivateWindow(Settings)", "icons/big/Settings.png"))
    lines.append("</shortcuts>")
    return "\n".join(lines) + "\n"


def properties_json(manifest: dict) -> list[list[str]]:
    properties: list[list[str]] = []
    for item in MAINMENU_ITEMS:
        group_entries = entries(manifest, item["menu_group"])
        addon_id = group_entries[0]["id"] if group_entries else item.get("addon_id", "plugin.video.solokodi.kidsrd")
        default_id = item["default_id"]
        widget_path = group_entries[0].get("path") if group_entries else f"plugin://{addon_id}/"
        properties.extend(
            [
                ["mainmenu", "", "widget", "Addon", default_id],
                ["mainmenu", "", "widgetName", item["label"], default_id],
                ["mainmenu", "", "widgetType", "video", default_id],
                ["mainmenu", "", "widgetTarget", "videos", default_id],
                ["mainmenu", "", "widgetPath", widget_path, default_id],
                ["mainmenu", "", "widgetRatio", "Square", default_id],
                ["mainmenu", "", "widgetAutoHide", "OFF", default_id],
                ["mainmenu", "", "hasSubmenu", "True", default_id],
            ]
        )
    return properties


def main() -> int:
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PROFILE
    manifest = json.loads(BUILD.read_text(encoding="utf-8"))
    target_dir.mkdir(parents=True, exist_ok=True)

    (target_dir / f"{SKIN}-mainmenu.DATA.xml").write_text(mainmenu_xml(), encoding="utf-8")
    for item in MAINMENU_ITEMS:
        submenu_key = item.get("addon_id") or item["default_id"]
        path = target_dir / f"{SKIN}-{submenu_key}.DATA.xml"
        path.write_text(group_xml(manifest, item["menu_group"], item["label"]), encoding="utf-8")
        print(f"Wrote {path}")

    props_path = target_dir / f"{SKIN}.properties"
    props_path.write_text(json.dumps(properties_json(manifest), indent=4) + "\n", encoding="utf-8")
    print(f"Wrote {props_path}")

    hash_path = target_dir / f"{SKIN}.hash"
    if hash_path.exists():
        hash_path.unlink()
        print(f"Removed {hash_path}")

    legacy_groups = ("tvshows", "livetv", "movies", "videos")
    for group in legacy_groups:
        legacy = target_dir / f"{SKIN}-{group}.DATA.xml"
        if legacy.exists():
            legacy.unlink()
            print(f"Removed legacy {legacy}")

    print(f"Wrote {target_dir / f'{SKIN}-mainmenu.DATA.xml'}")
    print("Restart Kodi or run Repair Build to rebuild the Bello home menu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
