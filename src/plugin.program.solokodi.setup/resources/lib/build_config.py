import json

import xbmc
import xbmcaddon
import xbmcvfs

DEFAULT_PROFILE = "kids"


def addon():
    return xbmcaddon.Addon()


def profile_id():
    value = addon().getSetting("build_profile")
    return value or DEFAULT_PROFILE


def manifest_path(profile):
    base = addon().getAddonInfo("path")
    return xbmcvfs.translatePath(base + "/resources/builds/{0}.json".format(profile))


def load_embedded_manifest(profile=None):
    profile = profile or profile_id()
    path = manifest_path(profile)
    if not xbmcvfs.exists(path):
        raise RuntimeError("Build manifest missing for profile: {0}".format(profile))
    with xbmcvfs.File(path) as handle:
        return json.loads(handle.read())


def content_addons(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return manifest.get("content_addons") or []


def solokodi_addons(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return manifest.get("solokodi_addons") or []


def all_addons(manifest=None):
    manifest = manifest or load_embedded_manifest()
    items = []
    for entry in content_addons(manifest):
        items.append((entry["id"], entry["label"], entry.get("favourite", entry["label"]), "official"))
    for entry in solokodi_addons(manifest):
        items.append((entry["id"], entry["label"], entry.get("favourite", entry["label"]), "solokodi"))
    return items


def skin_config(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return manifest.get("skin") or {}


def skin_options(manifest=None):
    manifest = manifest or load_embedded_manifest()
    skin = skin_config(manifest)
    options = skin.get("options") or []
    if options:
        return options
    skin_id = skin.get("id")
    if skin_id:
        return [{"id": skin_id, "label": skin.get("name") or skin_id, "official": True}]
    return []


def default_skin_id(manifest=None):
    skin = skin_config(manifest)
    return skin.get("default_id") or skin.get("id") or "skin.bello.10"


def selected_skin_id(manifest=None):
    manifest = manifest or load_embedded_manifest()
    preferred = addon().getSetting("preferred_skin")
    if preferred:
        return preferred
    return default_skin_id(manifest)


def skin_option(skin_id, manifest=None):
    for option in skin_options(manifest):
        if option.get("id") == skin_id:
            return option
    return None


def build_info(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return manifest.get("build") or {}


def repository_info(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return manifest.get("repository") or {}


def manifest_url(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return manifest.get("manifest_url") or ""


def wizard_steps(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return manifest.get("wizard_steps") or []
