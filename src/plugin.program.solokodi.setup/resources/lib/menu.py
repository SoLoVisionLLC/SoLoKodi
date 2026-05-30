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
        "Run Family Setup",
        "family_setup",
        "Install official kid-safe add-ons and create SoLoKodi shortcuts.",
    )
    add_item(
        "Connect Real-Debrid",
        "connect_rd",
        "Authorize this Kodi profile with Real-Debrid using the device flow.",
    )
    add_item(
        "Check Real-Debrid Account",
        "check_rd",
        "Confirm that the local Real-Debrid token works.",
    )
    add_item(
        "Show Parent Lock Checklist",
        "lock_checklist",
        "Open the profile, source, and settings lock checklist.",
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

    if action == "family_setup":
        setup.run_family_setup()
    elif action == "connect_rd":
        setup.connect_real_debrid()
    elif action == "check_rd":
        setup.check_real_debrid()
    elif action == "lock_checklist":
        setup.show_lock_checklist()
    elif action == "clear_rd":
        setup.clear_real_debrid()
    else:
        show_menu()
