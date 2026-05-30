import os
import sqlite3

import xbmc
import xbmcvfs

from . import build_config, build_ops

NIMBUS_SKIN_ID = "skin.nimbus"
NIMBUS_HELPER_ID = "script.nimbus.helper"
NIMBUS_REPO_ID = "repository.ivarbrandt"
NIMBUS_REPO_URL = "https://ivarbrandt.github.io/"
WIDGET_TYPE = "WidgetListCategory"
WIDGET_STYLE = "Square"


def _helper_data_dir():
    return xbmcvfs.translatePath(
        "special://profile/addon_data/{0}/".format(NIMBUS_HELPER_ID)
    )


def _database_path():
    return os.path.join(_helper_data_dir(), "cpath_cache.db")


def _plugin_path(addon_id):
    return "plugin://{0}/".format(addon_id)


def _widget_label(label):
    return "{0} | {1}".format(label, WIDGET_STYLE)


def _entries_for_group(manifest, group_name):
    entries = []
    for entry in build_config.content_addons(manifest):
        if entry.get("menu_group") == group_name:
            entries.append(entry)
    for entry in build_config.solokodi_addons(manifest):
        if entry.get("menu_group") == group_name:
            entries.append(entry)
    return entries


def _seed_rows(manifest):
    rows = []

    def add_main_menu(media_key, label, path):
        rows.append((media_key, path, label, "", ""))

    def add_widgets(media_key, entries):
        for index, entry in enumerate(entries, start=1):
            label = entry.get("favourite") or entry["label"]
            setting = "{0}.widget.{1}".format(media_key, index)
            rows.append(
                (
                    setting,
                    _plugin_path(entry["id"]),
                    label,
                    WIDGET_TYPE,
                    _widget_label(label),
                )
            )

    tv_entries = _entries_for_group(manifest, "tvshows")
    live_entries = _entries_for_group(manifest, "livetv")
    movie_entries = _entries_for_group(manifest, "movies")
    video_entries = _entries_for_group(manifest, "videos")

    if tv_entries:
        first = tv_entries[0]
        add_main_menu(
            "tvshow.main_menu",
            "Kids TV Shows",
            _plugin_path(first["id"]),
        )
        add_widgets("tvshow", tv_entries)

    if movie_entries:
        first = movie_entries[0]
        add_main_menu(
            "movie.main_menu",
            "Kids Movies",
            _plugin_path(first["id"]),
        )
        add_widgets("movie", movie_entries)

    if live_entries:
        first = live_entries[0]
        add_main_menu(
            "custom1.main_menu",
            "Live Kids TV",
            _plugin_path(first["id"]),
        )
        add_widgets("custom1", live_entries)

    if video_entries:
        first = video_entries[0]
        add_main_menu(
            "custom2.main_menu",
            "Explore",
            _plugin_path(first["id"]),
        )
        add_widgets("custom2", video_entries)

    add_main_menu("custom3.main_menu", "My Favourites", "favourites://")
    rows.append(
        (
            "custom3.widget.1",
            "favourites://",
            "My Favourites",
            WIDGET_TYPE,
            _widget_label("My Favourites"),
        )
    )
    rows.append(
        (
            "custom3.widget.2",
            "plugin://{0}/".format("plugin.program.solokodi.setup"),
            "SoLoKodi Setup",
            WIDGET_TYPE,
            _widget_label("SoLoKodi Setup"),
        )
    )

    return rows


def _write_database(rows):
    directory = _helper_data_dir()
    if not xbmcvfs.exists(directory):
        xbmcvfs.mkdirs(directory)

    connection = sqlite3.connect(_database_path(), timeout=20)
    cursor = connection.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS custom_paths "
        "(cpath_setting text unique, cpath_path text, cpath_header text, cpath_type text, cpath_label text)"
    )

    prefixes = (
        "movie.main_menu",
        "tvshow.main_menu",
        "custom1.main_menu",
        "custom2.main_menu",
        "custom3.main_menu",
        "movie.widget.",
        "tvshow.widget.",
        "custom1.widget.",
        "custom2.widget.",
        "custom3.widget.",
    )
    for prefix in prefixes:
        cursor.execute(
            "DELETE FROM custom_paths WHERE cpath_setting = ? OR cpath_setting LIKE ?",
            (prefix.rstrip("."), prefix + "%"),
        )

    for setting, path, header, ctype, label in rows:
        cursor.execute(
            "INSERT OR REPLACE INTO custom_paths VALUES (?, ?, ?, ?, ?)",
            (setting, path, header, ctype, label),
        )

    connection.commit()
    connection.close()


def _rebuild_nimbus_menu():
    if not build_ops.addon_installed(NIMBUS_HELPER_ID):
        return False
    xbmc.executebuiltin(
        "RunScript({0},mode=remake_all_cpaths)".format(NIMBUS_HELPER_ID),
        True,
    )
    return True


def menu_configured(manifest=None):
    if not xbmcvfs.exists(_database_path()):
        return False
    connection = sqlite3.connect(_database_path(), timeout=20)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT cpath_header FROM custom_paths WHERE cpath_setting = ?",
        ("tvshow.main_menu",),
    )
    row = cursor.fetchone()
    connection.close()
    return bool(row and row[0] == "Kids TV Shows")


def apply_nimbus_menu(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()

    if not build_ops.addon_installed(NIMBUS_SKIN_ID):
        xbmc.log(
            "SoLoKodi: {0} is not installed; skipping Nimbus menu setup".format(NIMBUS_SKIN_ID),
            xbmc.LOGINFO,
        )
        return False

    if not build_ops.addon_installed(NIMBUS_HELPER_ID):
        build_ops.install_addon(NIMBUS_HELPER_ID)
        if not build_ops.wait_for_addon(NIMBUS_HELPER_ID):
            return False

    rows = _seed_rows(manifest)
    if not rows:
        return False

    _write_database(rows)
    return _rebuild_nimbus_menu()
