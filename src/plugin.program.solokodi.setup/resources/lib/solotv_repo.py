import re

import xbmc
import xbmcvfs

from . import build_config, build_ops

WIZARD_ADDON_ID = "plugin.program.chef21"
WIZARD_DOWNLOADER_REL = "resources/lib/modules/downloader.py"
WIZARD_BUILD_INSTALL_REL = "resources/lib/modules/build_install.py"

PATCHED_WIZARD_DOWNLOADER = r'''import os
import sys
import zipfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ICON = ADDON.getAddonInfo('icon')

class Downloader:
    def __init__(self, url):
        self.url = url
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Referer": "https://github.com/",
            "Connection": "close",
        }

    def _open(self):
        request = Request(self.url, headers=self.headers)
        return urlopen(request, timeout=120)

    def get_length(self, response):
        length = response.headers.get('Content-Length')
        return int(length) if length else None

    def download_build(self, name, zippath):
        dp = xbmcgui.DialogProgress()
        cancelled = False
        chunksize = 1000000
        size = 0

        try:
            response = self._open()
        except (HTTPError, URLError, OSError) as exc:
            xbmcgui.Dialog().ok(ADDON_NAME, 'Download failed: {0}'.format(exc))
            raise

        with response:
            length = self.get_length(response)
            if length is not None:
                length2 = int(length / 1000000)
                dp.create(f'{name} - {length2}MB', 'Downloading your build...')
            else:
                length2 = 'Unknown Size'
                dp.create(f'{name} - {length2}', 'Downloading your build...')

            dp.update(0, 'Downloading your build...')
            with open(zippath, 'wb') as f:
                while True:
                    chunk = response.read(chunksize)
                    if not chunk:
                        break
                    size += len(chunk)
                    size2 = int(size / 1000000)
                    f.write(chunk)
                    if length:
                        perc = int(size / length * 100)
                        dp.update(perc, f'Downloading your build...\n{size2}/{length2} MB')
                    else:
                        dp.update(50, f'Downloading your build...\n{size2} MB')
                    if dp.iscanceled():
                        cancelled = True
                        break

        if cancelled is True:
            dp.close()
            if os.path.exists(zippath):
                os.unlink(zippath)
            dialog = xbmcgui.Dialog()
            dialog.notification(ADDON_NAME, 'Download Cancelled', icon=ICON)
            sys.exit()

        if length is not None and size != length:
            dp.close()
            if os.path.exists(zippath):
                os.unlink(zippath)
            xbmcgui.Dialog().ok(
                ADDON_NAME,
                'Download incomplete: {0}/{1} bytes'.format(size, length),
            )
            raise IOError('Downloaded build was incomplete')

        if not zipfile.is_zipfile(zippath):
            dp.close()
            if os.path.exists(zippath):
                os.unlink(zippath)
            xbmcgui.Dialog().ok(ADDON_NAME, 'Downloaded build is not a valid ZIP file.')
            raise zipfile.BadZipFile('Downloaded build is not a valid ZIP file')

        if length is not None:
            dp.update(100, f'Downloading your build...Done!\n{int(size/1000000)}/{length2} MB')
        else:
            dp.update(100, f'Downloading your build...Done!\n{int(size/1000000)} MB')

        xbmc.sleep(500)
        dp.close()
'''


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


def patch_wizard_downloader(wizard_id=WIZARD_ADDON_ID):
    """Make the wizard's build downloader independent of requests and proxies."""
    if not build_ops.addon_installed(wizard_id):
        return False
    path = xbmcvfs.translatePath(
        "special://home/addons/{0}/{1}".format(wizard_id, WIZARD_DOWNLOADER_REL)
    )
    if not xbmcvfs.exists(path):
        return False

    with xbmcvfs.File(path) as handle:
        content = handle.read()

    if content == PATCHED_WIZARD_DOWNLOADER:
        return True

    with xbmcvfs.File(path, "w") as handle:
        handle.write(PATCHED_WIZARD_DOWNLOADER)
    xbmc.log("SoLoTV: patched Build Wizard downloader", xbmc.LOGINFO)
    return True


def patch_wizard_build_install(wizard_id=WIZARD_ADDON_ID):
    """Validate the downloaded ZIP before the wizard clears the Kodi profile."""
    if not build_ops.addon_installed(wizard_id):
        return False
    path = xbmcvfs.translatePath(
        "special://home/addons/{0}/{1}".format(wizard_id, WIZARD_BUILD_INSTALL_REL)
    )
    if not xbmcvfs.exists(path):
        return False

    with xbmcvfs.File(path) as handle:
        content = handle.read()

    updated = content.replace(
        "from zipfile import ZipFile",
        "from zipfile import ZipFile, is_zipfile",
        1,
    )
    marker = "    download_build(name, url)\n    save_backup_restore('backup')"
    replacement = (
        "    download_build(name, url)\n"
        "    if not is_zipfile(zippath):\n"
        "        if os.path.exists(zippath):\n"
        "            os.unlink(zippath)\n"
        "        dialog.ok(addon_name, 'Downloaded build is not a valid ZIP file.')\n"
        "        return\n"
        "    save_backup_restore('backup')"
    )
    if marker in updated and "if not is_zipfile(zippath):" not in updated:
        updated = updated.replace(marker, replacement, 1)

    if updated == content:
        return True

    with xbmcvfs.File(path, "w") as handle:
        handle.write(updated)
    xbmc.log("SoLoTV: patched Build Wizard install validation", xbmc.LOGINFO)
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
        patch_wizard_downloader(wizard_id)
        patch_wizard_build_install(wizard_id)
        return True
    if build_ops.wait_for_addon(wizard_id, timeout_ms=90000):
        rebrand_installed_wizard(wizard_id)
        repoint_wizard_sources(manifest, wizard_id)
        patch_wizard_downloader(wizard_id)
        patch_wizard_build_install(wizard_id)
        return True
    return False


def launch_build_wizard(manifest=None):
    config = streaming_repo_config(manifest)
    wizard_id = config.get("wizard_addon_id") or WIZARD_ADDON_ID
    if not wizard_id or not build_ops.addon_installed(wizard_id):
        return False
    rebrand_installed_wizard(wizard_id)
    repoint_wizard_sources(manifest, wizard_id)
    patch_wizard_downloader(wizard_id)
    patch_wizard_build_install(wizard_id)
    xbmc.executebuiltin("RunAddon({0})".format(wizard_id))
    return True
