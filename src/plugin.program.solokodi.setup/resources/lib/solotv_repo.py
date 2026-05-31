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


def repoint_wizard_sources(manifest=None, wizard_id=WIZARD_ADDON_ID):
    """Point the installed Build Wizard at SoLoVision-hosted build sources.

    Rewrites the wizard's uservar.py so it reads our build list, notifications,
    videos, and changelog instead of the upstream Diggz endpoints.
    """
    config = streaming_repo_config(manifest)
    overrides = {
        "buildfile": config.get("build_list_url"),
        "notify_url": config.get("notify_url"),
        "videos_url": config.get("videos_url"),
        "changelog_dir": config.get("changelog_dir"),
    }
    overrides = {key: value for key, value in overrides.items() if value}
    if not overrides:
        return False
    if not build_ops.addon_installed(wizard_id):
        return False

    uservar_path = xbmcvfs.translatePath(
        "special://home/addons/{0}/uservar.py".format(wizard_id)
    )
    if not xbmcvfs.exists(uservar_path):
        return False

    with xbmcvfs.File(uservar_path) as handle:
        content = handle.read()

    updated = content
    for var_name, url in overrides.items():
        pattern = r"(?m)^(\s*{0}\s*=\s*).*$".format(re.escape(var_name))
        replacement = r"\g<1>'{0}'".format(url)
        updated, count = re.subn(pattern, replacement, updated, count=1)
        if count == 0:
            xbmc.log(
                "SoLoTV: could not repoint wizard var {0}".format(var_name),
                xbmc.LOGWARNING,
            )

    if updated == content:
        return True

    with xbmcvfs.File(uservar_path, "w") as handle:
        handle.write(updated)
    xbmc.log("SoLoTV: repointed Build Wizard sources to SoLoVision", xbmc.LOGINFO)
    return True


def install_streaming_repository(manifest=None):
    config = streaming_repo_config(manifest)
    repo_id = config.get("repository_id")
    if not repo_id:
        xbmc.log("SoLoTV: streaming repository id is missing", xbmc.LOGERROR)
        return False
    if build_ops.addon_installed(repo_id):
        return True

    # Preferred path: repository.solotv ships inside the already-installed
    # SoLoKodi repository, so install it directly. This avoids InstallZip and
    # the "Unknown sources" prompt entirely.
    build_ops.refresh_addon_repositories()
    if build_ops.install_addon(repo_id) or build_ops.wait_for_addon(repo_id, timeout_ms=60000):
        xbmc.log("SoLoTV: installed {0} from SoLoKodi repository".format(repo_id), xbmc.LOGINFO)
        return True

    # Fallback: install from the hosted repository zip / file source.
    zip_name = config.get("repository_zip")
    if not zip_name:
        xbmc.log("SoLoTV: no repository zip fallback configured", xbmc.LOGERROR)
        return False
    option = {
        "repository_id": repo_id,
        "repository_url": config.get("file_source_url"),
        "repository_name": config.get("file_source_name"),
        "repository_zip": zip_name,
    }
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
        repoint_wizard_sources(manifest, wizard_id)
        return True
    if build_ops.wait_for_addon(wizard_id, timeout_ms=90000):
        rebrand_installed_wizard(wizard_id)
        repoint_wizard_sources(manifest, wizard_id)
        return True
    return False


def launch_build_wizard(manifest=None):
    config = streaming_repo_config(manifest)
    wizard_id = config.get("wizard_addon_id") or WIZARD_ADDON_ID
    if not wizard_id or not build_ops.addon_installed(wizard_id):
        return False
    rebrand_installed_wizard(wizard_id)
    repoint_wizard_sources(manifest, wizard_id)
    xbmc.executebuiltin("RunAddon({0})".format(wizard_id))
    return True
