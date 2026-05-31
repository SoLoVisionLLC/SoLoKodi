import re

import xbmc
import xbmcvfs

from . import build_config, build_ops

WIZARD_ADDON_ID = "plugin.program.chef21"


def streaming_repo_config(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()
    return manifest.get("streaming_repo") or manifest.get("diggz") or {}


def rebrand_installed_wizard(wizard_id=WIZARD_ADDON_ID):
    """Patch installed wizard add-on metadata so Kodi shows SoLoTV, not Diggz."""
    if not build_ops.addon_installed(wizard_id):
        return False

    addon_path = xbmcvfs.translatePath("special://home/addons/{0}/addon.xml".format(wizard_id))
    if not xbmcvfs.exists(addon_path):
        return False

    with xbmcvfs.File(addon_path) as handle:
        content = handle.read()

    updated = content
    updated = re.sub(r'name="[^"]*"', 'name="SoLoTV Build Wizard"', updated, count=1)
    updated = updated.replace("Diggz", "SoLoTV")
    updated = re.sub(
        r"(<summary[^>]*>)(.*?)(</summary>)",
        r"\1Install and update the SoLoTV interface (movies, TV, live TV).\3",
        updated,
        count=1,
        flags=re.S | re.I,
    )
    updated = re.sub(
        r"(<description[^>]*>)(.*?)(</description>)",
        r"\1SoLoTV build wizard from SoLoVision. Choose your interface and streaming add-ons.\3",
        updated,
        count=1,
        flags=re.S | re.I,
    )
    updated = updated.replace('provider-name="Diggz"', 'provider-name="SoLoVision"')

    if updated == content:
        return True

    with xbmcvfs.File(addon_path, "w") as handle:
        handle.write(updated)
    xbmc.log("SoLoTV: rebranded installed wizard metadata", xbmc.LOGINFO)
    return True


def install_streaming_repository(manifest=None):
    config = streaming_repo_config(manifest)
    option = {
        "repository_id": config.get("repository_id"),
        "repository_url": config.get("file_source_url"),
        "repository_name": config.get("file_source_name"),
        "repository_zip": config.get("repository_zip"),
    }
    if not option["repository_id"] or not option["repository_zip"]:
        xbmc.log("SoLoTV: streaming repository settings are incomplete", xbmc.LOGERROR)
        return False
    if build_ops.addon_installed(option["repository_id"]):
        return True
    return build_ops.install_repository_from_zip(option)


def install_build_wizard(manifest=None):
    config = streaming_repo_config(manifest)
    wizard_id = config.get("wizard_addon_id") or WIZARD_ADDON_ID
    if not wizard_id:
        return False
    if not install_streaming_repository(manifest):
        return False
    build_ops.refresh_addon_repositories()
    if build_ops.install_addon(wizard_id):
        rebrand_installed_wizard(wizard_id)
        return True
    if build_ops.wait_for_addon(wizard_id, timeout_ms=90000):
        rebrand_installed_wizard(wizard_id)
        return True
    return False


def launch_build_wizard(manifest=None):
    config = streaming_repo_config(manifest)
    wizard_id = config.get("wizard_addon_id") or WIZARD_ADDON_ID
    if not wizard_id or not build_ops.addon_installed(wizard_id):
        return False
    rebrand_installed_wizard(wizard_id)
    xbmc.executebuiltin("RunAddon({0})".format(wizard_id))
    return True
