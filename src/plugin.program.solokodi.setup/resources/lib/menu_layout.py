import json
import re
import xml.sax.saxutils

import xbmc
import xbmcgui
import xbmcvfs

from . import build_config, build_ops, nimbus_layout

BELLO_SKIN_ID = "skin.bello.10"
SHORTCUTS_ADDON = "script.skinshortcuts"
GROUP_ICONS = {
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


def _bello_submenu_key(item):
    return item["addon_id"]


def _first_entry_for_group(manifest, menu_group):
    entries = _entries_for_group(manifest, menu_group)
    return entries[0] if entries else None


def _build_bello_mainmenu_xml(manifest):
    setup_id = "plugin.program.solokodi.setup"
    lines = ['<?xml version=\'1.0\' encoding=\'UTF-8\'?>', "<shortcuts>"]
    for item in MAINMENU_ITEMS:
        action = "ActivateWindow(Videos,plugin://{0}/,return)".format(item["addon_id"])
        lines.append(_shortcut(item["label"], item["default_id"], action, item["icon"]))
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
    return "\n".join(lines) + "\n"


def _build_bello_properties(manifest):
    properties = []
    for item in MAINMENU_ITEMS:
        default_id = item["default_id"]
        entry = _first_entry_for_group(manifest, item["menu_group"]) or {"id": item["addon_id"]}
        widget_path = "plugin://{0}/".format(entry["id"])
        widget_name = item["label"]
        properties.extend(
            [
                ["mainmenu", "", "widget", "Addon", default_id],
                ["mainmenu", "", "widgetName", widget_name, default_id],
                ["mainmenu", "", "widgetType", "video", default_id],
                ["mainmenu", "", "widgetTarget", "videos", default_id],
                ["mainmenu", "", "widgetPath", widget_path, default_id],
                ["mainmenu", "", "widgetRatio", "Square", default_id],
                ["mainmenu", "", "widgetAutoHide", "OFF", default_id],
                ["mainmenu", "", "hasSubmenu", "True", default_id],
            ]
        )
    return properties


def _shortcuts_data_dir():
    return xbmcvfs.translatePath("special://profile/addon_data/{0}/".format(SHORTCUTS_ADDON))


def _shortcuts_data_path(skin_id, group):
    filename = "{0}-{1}.DATA.xml".format(skin_id, group)
    return _shortcuts_data_dir().rstrip("/\\") + "/" + filename


def _properties_path(skin_id):
    return _shortcuts_data_dir().rstrip("/\\") + "/{0}.properties".format(skin_id)


def _hash_path(skin_id):
    return _shortcuts_data_dir().rstrip("/\\") + "/{0}.hash".format(skin_id)


def _includes_path():
    return xbmcvfs.translatePath(
        "special://skin/720p/script-skinshortcuts-includes.xml"
    )


def _write_shortcuts_file(skin_id, group, payload):
    target = _shortcuts_data_path(skin_id, group)
    directory = target.rsplit("/", 1)[0]
    if not xbmcvfs.exists(directory):
        xbmcvfs.mkdirs(directory)
    with xbmcvfs.File(target, "w") as handle:
        handle.write(payload)
    return target


def _write_properties_file(skin_id, properties):
    target = _properties_path(skin_id)
    directory = target.rsplit("/", 1)[0]
    if not xbmcvfs.exists(directory):
        xbmcvfs.mkdirs(directory)
    with xbmcvfs.File(target, "w") as handle:
        handle.write(json.dumps(properties, indent=4) + "\n")
    return target


def _invalidate_bello_shortcuts_cache():
    hash_path = _hash_path(BELLO_SKIN_ID)
    if xbmcvfs.exists(hash_path):
        xbmcvfs.delete(hash_path)
    try:
        xbmcgui.Window(10000).setProperty("skinshortcuts-reloadmainmenu", "True")
    except RuntimeError:
        pass


def _rebuild_bello_menu():
    if not build_ops.addon_installed(SHORTCUTS_ADDON):
        return False

    _invalidate_bello_shortcuts_cache()
    xbmc.executebuiltin(
        "RunScript({0},type=buildxml,mode=single,options=clonewidgets,mainmenuID=20)".format(
            SHORTCUTS_ADDON
        ),
        True,
    )
    if build_ops.active_skin() == BELLO_SKIN_ID:
        xbmc.executebuiltin("ReloadSkin()")
    return bello_includes_built()


def bello_includes_built():
    path = _includes_path()
    if not xbmcvfs.exists(path):
        return False
    with xbmcvfs.File(path) as handle:
        content = handle.read()
    return "Kids TV Shows" in content and "plugin.video.pbskids" in content


def bello_menu_present():
    if not xbmcvfs.exists(_shortcuts_data_path(BELLO_SKIN_ID, "mainmenu")):
        return False
    for item in MAINMENU_ITEMS:
        if not xbmcvfs.exists(_shortcuts_data_path(BELLO_SKIN_ID, _bello_submenu_key(item))):
            return False
    return bello_includes_built()


def apply_bello_menu(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()

    if not build_ops.addon_installed(SHORTCUTS_ADDON):
        xbmc.log(
            "SoLoKodi: {0} is required for the Bello kids home menu".format(SHORTCUTS_ADDON),
            xbmc.LOGWARNING,
        )
        return False

    _write_shortcuts_file(BELLO_SKIN_ID, "mainmenu", _build_bello_mainmenu_xml(manifest))
    for item in MAINMENU_ITEMS:
        group_xml = _build_group_xml(
            _entries_for_group(manifest, item["menu_group"]),
            item["label"],
            item["icon"],
        )
        _write_shortcuts_file(BELLO_SKIN_ID, _bello_submenu_key(item), group_xml)
    _write_properties_file(BELLO_SKIN_ID, _build_bello_properties(manifest))

    return _rebuild_bello_menu()


def menu_files_present(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()
    skin_id = build_config.selected_skin_id(manifest)
    if skin_id == nimbus_layout.NIMBUS_SKIN_ID:
        return nimbus_layout.menu_configured(manifest)
    return bello_menu_present()


def apply_kids_home_menu(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()
    if build_config.is_streaming_build(manifest):
        return True
    skin_id = build_config.selected_skin_id(manifest)
    if skin_id == nimbus_layout.NIMBUS_SKIN_ID:
        return nimbus_layout.apply_nimbus_menu(manifest)
    return apply_bello_menu(manifest)
