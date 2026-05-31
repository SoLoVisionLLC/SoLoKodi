import json

import xbmc
import xbmcaddon
import xbmcvfs

DEFAULT_PROFILE = "kids"
BUILD_PROFILES = ("kids", "solotv", "solokids-tv")


def addon():
    return xbmcaddon.Addon()


def profile_id():
    """Return the profile the user explicitly selected, or empty if none yet."""
    return addon().getSetting("build_profile") or ""


def has_active_profile():
    """True once a build profile has been chosen via the picker or wizard."""
    return profile_id() in BUILD_PROFILES


def active_profile_id():
    """Profile to load manifests for, falling back to the default for previews."""
    return profile_id() or DEFAULT_PROFILE


def manifest_path(profile):
    base = addon().getAddonInfo("path")
    return xbmcvfs.translatePath(base + "/resources/builds/{0}.json".format(profile))


def card_image_path(filename):
    """Resolve a build-card image bundled in the setup add-on resources."""
    if not filename:
        return ""
    base = addon().getAddonInfo("path")
    return xbmcvfs.translatePath(base + "/resources/media/cards/{0}".format(filename))


def load_embedded_manifest(profile=None):
    profile = profile or active_profile_id()
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
    return build_type(manifest) == "streaming"


def streaming_repo_config(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return manifest.get("streaming_repo") or {}


def branding(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return manifest.get("branding") or {}


def requires_debrid(manifest=None):
    manifest = manifest or load_embedded_manifest()
    return bool(manifest.get("requires_debrid"))


def list_profile_manifests():
    base = addon().getAddonInfo("path")
    builds_dir = xbmcvfs.translatePath(base + "/resources/builds/")
    profiles = []
    for profile in BUILD_PROFILES:
        path = builds_dir.rstrip("/\\") + "/{0}.json".format(profile)
        if xbmcvfs.exists(path):
            profiles.append(profile)
    return profiles


def profile_card(profile):
    """Return display metadata for the build picker for a single profile."""
    manifest = load_embedded_manifest(profile)
    build = build_info(manifest)
    return {
        "id": build.get("id", profile),
        "name": build.get("name", profile.title()),
        "version": build.get("version", "?"),
        "description": build.get("description", ""),
        "tagline": manifest.get("tagline") or branding(manifest).get("tagline", ""),
        "requires_debrid": bool(manifest.get("requires_debrid")),
        "card_image": card_image_path(manifest.get("card_image", "")),
    }


def build_cards():
    """Return display metadata for every installed build profile."""
    return [profile_card(profile) for profile in list_profile_manifests()]


def set_active_profile(profile):
    addon().setSetting("build_profile", profile)
    addon().setSetting("setup_complete", "false")
