import sys
import urllib.parse

import xbmcgui
import xbmcplugin

from . import setup

ADDON_URL = sys.argv[0]
HANDLE = int(sys.argv[1])


def add_item(label, action, description):
    url = ADDON_URL + "?" + urllib.parse.urlencode({"action": action})
    item = xbmcgui.ListItem(label=label)
    item.setInfo("video", {"title": label, "plot": description})
    xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=False)


def show_menu():
    add_item(
        "Run Kids Build Setup",
        "kids_setup",
        "Install every official kids source, create shortcuts, and apply a fun colorful theme.",
    )
    add_item(
        "Open Kids Real-Debrid",
        "open_kidsrd",
        "Browse and play kids movies and shows from your Real-Debrid library.",
    )
    add_item(
        "Connect Real-Debrid",
        "connect_rd",
        "Optional: authorize this Kodi profile with Real-Debrid using the device flow.",
    )
    add_item(
        "Check Real-Debrid Account",
        "check_rd",
        "Confirm that the local Real-Debrid token works.",
    )
    add_item(
        "Parent Tips (Optional)",
        "parent_tips",
        "Optional profile and lock ideas if adults share this device.",
    )
    add_item(
        "Clear Real-Debrid Authorization",
        "clear_rd",
        "Remove Real-Debrid credentials from this Kodi profile.",
    )
    xbmcplugin.endOfDirectory(HANDLE)


def run():
    params = urllib.parse.parse_qs(sys.argv[2][1:])
    action = params.get("action", ["menu"])[0]

    if action in ("kids_setup", "family_setup"):
        setup.run_kids_setup()
    elif action == "connect_rd":
        setup.connect_real_debrid()
    elif action == "open_kidsrd":
        import xbmc
        xbmc.executebuiltin("ActivateWindow(Videos,plugin://plugin.video.solokodi.kidsrd/,return)")
    elif action == "check_rd":
        setup.check_real_debrid()
    elif action in ("parent_tips", "lock_checklist"):
        setup.show_parent_tips()
    elif action == "clear_rd":
        setup.clear_real_debrid()
    else:
        show_menu()
