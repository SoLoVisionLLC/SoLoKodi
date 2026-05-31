import xbmc

from . import build_config, build_ops


def diggz_config(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()
    return manifest.get("diggz") or {}


def install_diggz_repository(manifest=None):
    config = diggz_config(manifest)
    option = {
        "repository_id": config.get("repository_id"),
        "repository_url": config.get("file_source_url"),
        "repository_name": config.get("file_source_name"),
        "repository_zip": config.get("repository_zip"),
    }
    if not option["repository_id"] or not option["repository_zip"]:
        xbmc.log("SoLoTV: Diggz repository settings are incomplete", xbmc.LOGERROR)
        return False
    if build_ops.addon_installed(option["repository_id"]):
        return True
    return build_ops.install_repository_from_zip(option)


def install_chef_wizard(manifest=None):
    config = diggz_config(manifest)
    wizard_id = config.get("wizard_addon_id")
    if not wizard_id:
        return False
    if not install_diggz_repository(manifest):
        return False
    build_ops.refresh_addon_repositories()
    if build_ops.install_addon(wizard_id):
        return True
    return build_ops.wait_for_addon(wizard_id, timeout_ms=90000)


def launch_chef_wizard(manifest=None):
    config = diggz_config(manifest)
    wizard_id = config.get("wizard_addon_id")
    if not wizard_id or not build_ops.addon_installed(wizard_id):
        return False
    xbmc.executebuiltin("RunAddon({0})".format(wizard_id))
    return True
