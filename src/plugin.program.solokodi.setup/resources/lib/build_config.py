import json

import xbmc
import xbmcaddon
import xbmcvfs

DEFAULT_PROFILE = "kids"
BUILD_PROFILES = ("kids", "solotv")


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


def build_type(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return manifest.get("build_type") or "kids"


def is_streaming_build(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return build_type(manifest) in ("streaming", "diggz")


def is_diggz_build(manifest=None):
    """Backward-compatible alias."""
    return is_streaming_build(manifest)


def streaming_repo_config(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return manifest.get("streaming_repo") or manifest.get("diggz") or {}


def diggz_config(manifest=None):
    return streaming_repo_config(manifest)


def branding(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return manifest.get("branding") or {}


def list_profile_manifests():
    base = addon().getAddonInfo("path")
    builds_dir = xbmcvfs.translatePath(base + "/resources/builds/")
    profiles = []
    for profile_id in BUILD_PROFILES:
        path = builds_dir.rstrip("/\\") + "/{0}.json".format(profile_id)
        if xbmcvfs.exists(path):
            profiles.append(profile_id)
    return profiles


def set_active_profile(profile_id):
    addon().setSetting("build_profile", profile_id)
    addon().setSetting("setup_complete", "false")
