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
DEFAULT_PROFILE = Path.home() / "AppData" / "Roaming" / "Kodi" / "userdata" / "addon_data" / "script.skinshortcuts"
SKIN = "skin.bello.10"
ICONS = {
    "tvshows": "DefaultTVShows.png",
    "movies": "DefaultMovies.png",
    "livetv": "DefaultLiveTV.png",
    "videos": "DefaultVideo.png",
}


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
        action = f"ActivateWindow(Videos,plugin://{entry['id']}/,return)"
        lines.append(shortcut(label, slug(entry["id"]), action, ICONS.get(group, "DefaultAddonVideo.png")))
    if len(lines) == 2:
        lines.append(
            shortcut(fallback, "solokodi-empty", "ActivateWindow(Videos,Addons,return)", ICONS.get(group, "DefaultAddonVideo.png"))
        )
    lines.append("</shortcuts>")
    return "\n".join(lines) + "\n"


def mainmenu_xml() -> str:
    lines = ["<?xml version='1.0' encoding='UTF-8'?>", "<shortcuts>"]
    lines.append(shortcut("Kids TV Shows", "tvshows", "ActivateWindow(Videos,plugin://plugin.video.pbskids/,return)", "DefaultTVShows.png"))
    lines.append(shortcut("Live Kids TV", "livetv", "ActivateWindow(Videos,plugin://plugin.video.plutotv/,return)", "DefaultLiveTV.png"))
    lines.append(shortcut("Kids Movies", "movies", "ActivateWindow(Videos,plugin://plugin.video.solokodi.kidsrd/,return)", "DefaultMovies.png"))
    lines.append(shortcut("Explore", "videos", "ActivateWindow(Videos,plugin://plugin.video.youtube/,return)", "DefaultVideo.png"))
    lines.append(shortcut("All Kids Apps", "addons", "ActivateWindow(1170,return)", "DefaultAddon.png"))
    lines.append(shortcut("My Favourites", "favourites", "ActivateWindow(Favourites)", "icons/big/Favourites.png"))
    lines.append(shortcut("SoLoKodi Setup", "solokodi-setup", "RunAddon(plugin.program.solokodi.setup)", "DefaultProgram.png"))
    lines.append(shortcut("Settings", "settings", "ActivateWindow(Settings)", "icons/big/Settings.png"))
    lines.append("</shortcuts>")
    return "\n".join(lines) + "\n"


def main() -> int:
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PROFILE
    manifest = json.loads(BUILD.read_text(encoding="utf-8"))
    target_dir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "mainmenu": mainmenu_xml(),
        "tvshows": group_xml(manifest, "tvshows", "Kids TV Shows"),
        "livetv": group_xml(manifest, "livetv", "Live Kids TV"),
        "movies": group_xml(manifest, "movies", "Kids Movies"),
        "videos": group_xml(manifest, "videos", "Explore"),
    }

    for group, payload in payloads.items():
        path = target_dir / f"{SKIN}-{group}.DATA.xml"
        path.write_text(payload, encoding="utf-8")
        print(f"Wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
