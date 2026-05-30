import re
import xml.sax.saxutils

import xbmc
import xbmcvfs

from . import build_config, build_ops

BELLO_SKIN_ID = "skin.bello.10"
SHORTCUTS_ADDON = "script.skinshortcuts"
GROUP_ICONS = {
    "tvshows": "DefaultTVShows.png",
    "movies": "DefaultMovies.png",
    "livetv": "DefaultLiveTV.png",
    "videos": "DefaultVideo.png",
}


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _escape(text):
    return xml.sax.saxutils.escape(text or "")


def _shortcut(label, default_id, action, icon):
    return (
        " <shortcut>\n"
        "  <label>{0}</label>\n"
        "  <label2>32024</label2>\n"
        "  <defaultID>{1}</defaultID>\n"
        "  <icon>{2}</icon>\n"
        "  <thumb />\n"
        "  <action>{3}</action>\n"
        " </shortcut>\n"
    ).format(_escape(label), _escape(default_id), _escape(icon), _escape(action))


def _addon_shortcut(entry, icon=None):
    addon_id = entry["id"]
    label = entry.get("favourite") or entry["label"]
    action = "ActivateWindow(Videos,plugin://{0}/,return)".format(addon_id)
    return _shortcut(label, _slug(addon_id), action, icon or "DefaultAddonVideo.png")


def _entries_for_group(manifest, group_name):
    entries = []
    for entry in build_config.content_addons(manifest):
        if entry.get("menu_group") == group_name:
            entries.append(entry)
    for entry in build_config.solokodi_addons(manifest):
        if entry.get("menu_group") == group_name:
            entries.append(entry)
    return entries


def _build_group_xml(entries, fallback_label, fallback_icon):
    if not entries:
        return (
            '<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n'
            "<shortcuts>\n"
            + _shortcut(
                fallback_label,
                "solokodi-empty",
                "ActivateWindow(Videos,Addons,return)",
                fallback_icon,
            )
            + "</shortcuts>\n"
        )

    lines = ['<?xml version=\'1.0\' encoding=\'UTF-8\'?>', "<shortcuts>"]
    for entry in entries:
        icon = GROUP_ICONS.get(entry.get("menu_group"), "DefaultAddonVideo.png")
        lines.append(_addon_shortcut(entry, icon=icon))
    lines.append("</shortcuts>")
    return "\n".join(lines) + "\n"


def _build_mainmenu_xml(manifest):
    skin_id = (build_config.skin_config(manifest) or {}).get("id", BELLO_SKIN_ID)
    setup_id = "plugin.program.solokodi.setup"
    lines = ['<?xml version=\'1.0\' encoding=\'UTF-8\'?>', "<shortcuts>"]
    lines.append(
        _shortcut(
            "Kids TV Shows",
            "tvshows",
            "ActivateWindow(Videos,plugin://plugin.video.pbskids/,return)",
            "DefaultTVShows.png",
        )
    )
    lines.append(
        _shortcut(
            "Live Kids TV",
            "livetv",
            "ActivateWindow(Videos,plugin://plugin.video.plutotv/,return)",
            "DefaultLiveTV.png",
        )
    )
    lines.append(
        _shortcut(
            "Kids Movies",
            "movies",
            "ActivateWindow(Videos,plugin://plugin.video.solokodi.kidsrd/,return)",
            "DefaultMovies.png",
        )
    )
    lines.append(
        _shortcut(
            "Explore",
            "videos",
            "ActivateWindow(Videos,plugin://plugin.video.youtube/,return)",
            "DefaultVideo.png",
        )
    )
    lines.append(
        _shortcut(
            "All Kids Apps",
            "addons",
            "ActivateWindow(1170,return)",
            "DefaultAddon.png",
        )
    )
    lines.append(
        _shortcut(
            "My Favourites",
            "favourites",
            "ActivateWindow(Favourites)",
            "icons/big/Favourites.png",
        )
    )
    lines.append(
        _shortcut(
            "SoLoKodi Setup",
            "solokodi-setup",
            "RunAddon({0})".format(setup_id),
            "DefaultProgram.png",
        )
    )
    lines.append(
        _shortcut(
            "Settings",
            "settings",
            "ActivateWindow(Settings)",
            "icons/big/Settings.png",
        )
    )
    lines.append("</shortcuts>")
    return "\n".join(lines) + "\n", skin_id


def _shortcuts_data_dir():
    return xbmcvfs.translatePath("special://profile/addon_data/{0}/".format(SHORTCUTS_ADDON))


def _shortcuts_data_path(skin_id, group):
    filename = "{0}-{1}.DATA.xml".format(skin_id, group)
    return _shortcuts_data_dir().rstrip("/\\") + "/" + filename


def _write_shortcuts_file(skin_id, group, payload):
    target = _shortcuts_data_path(skin_id, group)
    directory = target.rsplit("/", 1)[0]
    if not xbmcvfs.exists(directory):
        xbmcvfs.mkdirs(directory)
    with xbmcvfs.File(target, "w") as handle:
        handle.write(payload)
    return target


def _rebuild_bello_menu():
    if not build_ops.addon_installed(SHORTCUTS_ADDON):
        return False
    xbmc.executebuiltin(
        "RunScript({0},type=buildxml,mode=single,options=clonewidgets,mainmenuID=20)".format(
            SHORTCUTS_ADDON
        ),
        True,
    )
    xbmc.executebuiltin("ReloadSkin()")
    return True


def menu_files_present(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()
    skin_id = (build_config.skin_config(manifest) or {}).get("id", BELLO_SKIN_ID)
    for group in ("mainmenu", "tvshows", "livetv", "movies", "videos"):
        if not xbmcvfs.exists(_shortcuts_data_path(skin_id, group)):
            return False
    return True


def apply_kids_home_menu(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()
    skin_id = (build_config.skin_config(manifest) or {}).get("id", BELLO_SKIN_ID)

    if skin_id != BELLO_SKIN_ID:
        xbmc.log("SoLoKodi: home menu layout only supports {0} for now".format(BELLO_SKIN_ID), xbmc.LOGINFO)
        return False

    if not build_ops.addon_installed(SHORTCUTS_ADDON):
        xbmc.log("SoLoKodi: {0} is required for the kids home menu".format(SHORTCUTS_ADDON), xbmc.LOGWARNING)
        return False

    mainmenu_xml, _skin = _build_mainmenu_xml(manifest)
    groups = {
        "mainmenu": mainmenu_xml,
        "tvshows": _build_group_xml(_entries_for_group(manifest, "tvshows"), "Kids TV Shows", "DefaultTVShows.png"),
        "livetv": _build_group_xml(_entries_for_group(manifest, "livetv"), "Live Kids TV", "DefaultLiveTV.png"),
        "movies": _build_group_xml(_entries_for_group(manifest, "movies"), "Kids Movies", "DefaultMovies.png"),
        "videos": _build_group_xml(_entries_for_group(manifest, "videos"), "Explore", "DefaultVideo.png"),
    }

    for group, payload in groups.items():
        _write_shortcuts_file(skin_id, group, payload)

    return _rebuild_bello_menu()
