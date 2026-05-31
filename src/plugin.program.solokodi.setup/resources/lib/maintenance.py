import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

CACHE_DIR = "special://home/cache/"
PACKAGES_DIR = "special://home/addons/packages/"
THUMBNAILS_DIR = "special://thumbnails/"


def _notify(message, heading="SoLoKodi Maintenance"):
    xbmcgui.Dialog().notification(heading, message, xbmcgui.NOTIFICATION_INFO, 4000)


def _delete_contents(path):
    """Recursively delete everything under a special:// directory.

    Returns the number of files removed.
    """
    removed = 0
    if not xbmcvfs.exists(path):
        return removed

    dirs, files = xbmcvfs.listdir(path)
    base = path.rstrip("/\\") + "/"
    for name in files:
        if xbmcvfs.delete(base + name):
            removed += 1
    for name in dirs:
        sub = base + name + "/"
        removed += _delete_contents(sub)
        xbmcvfs.rmdir(sub)
    return removed


def clear_cache():
    if not xbmcgui.Dialog().yesno(
        "Clear Cache",
        "Delete temporary cache files? This is safe and can free up space.",
    ):
        return
    removed = _delete_contents(CACHE_DIR)
    _notify("Cleared {0} cache file(s)".format(removed))


def clear_packages():
    if not xbmcgui.Dialog().yesno(
        "Clear Packages",
        "Delete downloaded add-on install files (.zip packages)? "
        "Installed add-ons are not affected.",
    ):
        return
    removed = _delete_contents(PACKAGES_DIR)
    _notify("Removed {0} package file(s)".format(removed))


def clear_thumbnails():
    if not xbmcgui.Dialog().yesno(
        "Clear Thumbnails",
        "Delete cached artwork thumbnails? They rebuild automatically.\n\n"
        "Restart Kodi afterwards for a clean refresh.",
    ):
        return
    removed = _delete_contents(THUMBNAILS_DIR)
    _notify("Removed {0} thumbnail file(s)".format(removed))


def reset_build():
    if not xbmcgui.Dialog().yesno(
        "Reset SoLoKodi Build",
        "This clears your SoLoKodi build selection and setup progress so you can "
        "start fresh.\n\nReal-Debrid and TMDb credentials are kept. Continue?",
        yeslabel="Reset",
        nolabel="Cancel",
    ):
        return False

    setup = xbmcaddon.Addon()
    setup.setSetting("setup_complete", "false")
    setup.setSetting("build_profile", "")
    setup.setSetting("build_version_installed", "")

    profile_dir = xbmcvfs.translatePath("special://profile/")
    favourites = profile_dir.rstrip("/\\") + "/favourites.xml"
    if xbmcvfs.exists(favourites):
        xbmcvfs.delete(favourites)

    _notify("Build reset — choose a build to start again")
    return True


def force_close():
    if not xbmcgui.Dialog().yesno(
        "Force Close Kodi",
        "Close Kodi now? Use this to apply skin or build changes cleanly.",
        yeslabel="Close",
        nolabel="Cancel",
    ):
        return
    time.sleep(0.2)
    xbmc.executebuiltin("Quit")
