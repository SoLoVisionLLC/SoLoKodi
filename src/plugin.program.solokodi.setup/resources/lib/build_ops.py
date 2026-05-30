import json
import re
import xml.sax.saxutils

import xbmc
import xbmcaddon
import xbmcvfs

from . import build_config


def json_rpc(method, params=None):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    result = xbmc.executeJSONRPC(json.dumps(payload))
    try:
        return json.loads(result)
    except ValueError:
        return {"error": {"message": result}}


def json_rpc_ok(response):
    if response.get("error"):
        return False
    result = response.get("result")
    return result is True or result == "true"


def active_skin():
    response = json_rpc("Settings.GetSettingValue", {"setting": "lookandfeel.skin"})
    result = response.get("result") or {}
    value = result.get("value")
    if isinstance(value, dict):
        return value.get("value") or value.get("string") or ""
    return str(value or "")


def addon_installed(addon_id):
    return xbmc.getCondVisibility("System.HasAddon({0})".format(addon_id))


def wait_for_addon(addon_id, timeout_ms=60000, interval_ms=500):
    elapsed = 0
    while elapsed < timeout_ms:
        if addon_installed(addon_id):
            return True
        xbmc.sleep(interval_ms)
        elapsed += interval_ms
    return addon_installed(addon_id)


def installed_version(addon_id):
    if not addon_installed(addon_id):
        return None
    response = json_rpc(
        "Addons.GetAddonDetails",
        {"addonid": addon_id, "properties": ["version", "name", "enabled"]},
    )
    result = response.get("result") or {}
    addon = result.get("addon") or {}
    return addon.get("version")


def install_addon(addon_id):
    if not addon_installed(addon_id):
        xbmc.executebuiltin("InstallAddon({0})".format(addon_id), True)
        xbmc.sleep(500)
    json_rpc("Addons.SetAddonEnabled", {"addonid": addon_id, "enabled": True})
    return addon_installed(addon_id)


def update_addon(addon_id):
    xbmc.executebuiltin("UpdateAddon({0})".format(addon_id))
    xbmc.sleep(1500)
    if not addon_installed(addon_id):
        install_addon(addon_id)
    return addon_installed(addon_id)


def install_addons(entries):
    installed = []
    failed = []
    for entry in entries:
        addon_id = entry["id"]
        label = entry["label"]
        if install_addon(addon_id):
            installed.append(label)
        else:
            failed.append(label)
    return installed, failed


def apply_theme(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()
    skin = build_config.skin_config(manifest)
    skin_id = skin.get("id")
    if not skin_id:
        return False

    for setting, value in skin.get("colors") or []:
        json_rpc("Settings.SetSettingValue", {"setting": setting, "value": value})

    if not addon_installed(skin_id):
        xbmc.executebuiltin("InstallAddon({0})".format(skin_id), True)
        if not wait_for_addon(skin_id):
            xbmc.log("SoLoKodi: timed out waiting for skin {0}".format(skin_id), xbmc.LOGWARNING)
            return False

    json_rpc("Addons.SetAddonEnabled", {"addonid": skin_id, "enabled": True})

    response = json_rpc(
        "Settings.SetSettingValue",
        {"setting": "lookandfeel.skin", "value": skin_id},
    )
    if not json_rpc_ok(response):
        xbmc.log("SoLoKodi: skin SetSettingValue failed: {0}".format(response), xbmc.LOGWARNING)

    xbmc.sleep(1000)
    xbmc.executebuiltin("SendClick(11)", True)
    xbmc.sleep(500)

    if active_skin() == skin_id:
        return True

    if _persist_skin_in_guisettings(skin_id):
        response = json_rpc(
            "Settings.SetSettingValue",
            {"setting": "lookandfeel.skin", "value": skin_id},
        )
        if json_rpc_ok(response):
            xbmc.sleep(1000)
            xbmc.executebuiltin("SendClick(11)", True)
            xbmc.sleep(500)

    return active_skin() == skin_id


def _persist_skin_in_guisettings(skin_id):
    path = xbmcvfs.translatePath("special://profile/guisettings.xml")
    if not xbmcvfs.exists(path):
        return False

    with xbmcvfs.File(path) as handle:
        content = handle.read()

    pattern = r'(<setting id="lookandfeel\.skin"[^>]*>)([^<]*)(</setting>)'
    updated, count = re.subn(pattern, r"\g<1>{0}\g<3>".format(skin_id), content, count=1)
    if count == 0:
        return False

    updated = updated.replace(
        '<setting id="lookandfeel.skin" default="true">',
        '<setting id="lookandfeel.skin">',
    )

    with xbmcvfs.File(path, "w") as handle:
        handle.write(updated)
    return True


def theme_is_active(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()
    skin_id = (build_config.skin_config(manifest) or {}).get("id")
    return bool(skin_id and active_skin() == skin_id)


def build_favourites_xml(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()
    lines = ["<favourites>"]
    for entry in build_config.content_addons(manifest):
        name = xml.sax.saxutils.escape(entry.get("favourite", entry["label"]))
        lines.append(
            '    <favourite name="{0}">ActivateWindow(Videos,plugin://{1}/,return)</favourite>'.format(
                name, entry["id"]
            )
        )
    for entry in build_config.solokodi_addons(manifest):
        name = xml.sax.saxutils.escape(entry.get("favourite", entry["label"]))
        lines.append(
            '    <favourite name="{0}">ActivateWindow(Videos,plugin://{1}/,return)</favourite>'.format(
                name, entry["id"]
            )
        )
    setup_name = manifest.get("setup_favourite") or "SoLoKodi Kids Setup"
    lines.append('    <favourite name="{0}">RunAddon(plugin.program.solokodi.setup)</favourite>'.format(setup_name))
    lines.append("</favourites>")
    return "\n".join(lines) + "\n"


def write_favourites(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()
    profile_dir = xbmcvfs.translatePath("special://profile/")
    target = profile_dir.rstrip("/\\") + "/favourites.xml"
    with xbmcvfs.File(target, "w") as handle:
        handle.write(build_favourites_xml(manifest))
    return target


def sync_build_settings(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()
    setup = xbmcaddon.Addon()
    build = build_config.build_info(manifest)
    setup.setSetting("setup_complete", "true")
    setup.setSetting("build_profile", build.get("id", "kids"))
    setup.setSetting("build_version_installed", build.get("version", ""))
