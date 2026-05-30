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
