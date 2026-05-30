import json
import time
import urllib.error
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui

from . import build_config, build_ops, menu_layout, status, wizard


def notify(message, heading="SoLoKodi Updates"):
    xbmcgui.Dialog().notification(heading, message, xbmcgui.NOTIFICATION_INFO, 5000)


def fetch_remote_manifest():
    manifest = build_config.load_embedded_manifest()
    url = build_config.manifest_url(manifest)
    if not url:
        raise RuntimeError("No manifest URL configured for this build.")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _version_tuple(value):
    parts = []
    for piece in (value or "0").split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def compare_versions(installed, target):
    if not installed:
        return -1
    if _version_tuple(installed) < _version_tuple(target):
        return -1
    if _version_tuple(installed) > _version_tuple(target):
        return 1
    return 0


def check_for_updates(include_remote=True):
    local = build_config.load_embedded_manifest()
    setup = xbmcaddon.Addon()
    installed_build = setup.getSetting("build_version_installed") or ""
    target_build = build_config.build_info(local).get("version", "")

    updates = {
        "build_version": None,
        "repository": None,
        "addons": [],
        "remote_checked": False,
        "remote_error": "",
    }

    if compare_versions(installed_build, target_build) < 0:
        updates["build_version"] = {
            "installed": installed_build or "none",
            "available": target_build,
        }

    repo = build_config.repository_info(local)
    repo_id = repo.get("id")
    if repo_id:
        installed_repo = build_ops.installed_version(repo_id)
        if compare_versions(installed_repo, repo.get("version", "")) < 0:
            updates["repository"] = {
                "id": repo_id,
                "installed": installed_repo or "none",
                "available": repo.get("version", ""),
            }

    manifest = local
    if include_remote:
        try:
            manifest = fetch_remote_manifest()
            updates["remote_checked"] = True
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, ValueError) as exc:
            updates["remote_error"] = str(exc)

    for entry in build_config.solokodi_addons(manifest):
        addon_id = entry["id"]
        installed = build_ops.installed_version(addon_id)
        target = entry.get("version", "")
        if compare_versions(installed, target) < 0:
            updates["addons"].append(
                {
                    "id": addon_id,
                    "label": entry.get("label", addon_id),
                    "installed": installed or "none",
                    "available": target,
                }
            )

    setup_addon = manifest.get("setup_addon") or {}
    setup_id = setup_addon.get("id")
    if setup_id:
        installed = build_ops.installed_version(setup_id)
        target = setup_addon.get("version", "")
        if compare_versions(installed, target) < 0:
            already = any(item["id"] == setup_id for item in updates["addons"])
            if not already:
                updates["addons"].append(
                    {
                        "id": setup_id,
                        "label": setup_addon.get("name", setup_id),
                        "installed": installed or "none",
                        "available": target,
                    }
                )

    remote_build = (manifest.get("build") or {}).get("version")
    if remote_build and compare_versions(target_build, remote_build) < 0:
        updates["build_version"] = {
            "installed": installed_build or target_build or "none",
            "available": remote_build,
        }

    updates["has_updates"] = bool(
        updates["build_version"] or updates["repository"] or updates["addons"]
    )
    return updates


def update_report(updates):
    lines = []
    if updates.get("remote_error"):
        lines.append("Remote check: {0}".format(updates["remote_error"]))
    elif updates.get("remote_checked"):
        lines.append("Remote manifest checked.")
    lines.append("")

    if not updates.get("has_updates"):
        lines.append("Everything looks up to date.")
        return "\n".join(lines)

    build_version = updates.get("build_version")
    if build_version:
        lines.append(
            "Build: {0} -> {1}".format(build_version["installed"], build_version["available"])
        )

    repository = updates.get("repository")
    if repository:
        lines.append(
            "Repository {0}: {1} -> {2}".format(
                repository["id"], repository["installed"], repository["available"]
            )
        )

    for addon in updates.get("addons") or []:
        lines.append(
            "{0}: {1} -> {2}".format(addon["label"], addon["installed"], addon["available"])
        )
    return "\n".join(lines)


def record_update_check():
    setup = xbmcaddon.Addon()
    setup.setSetting("last_update_check", str(int(time.time())))


def apply_updates():
    updates = check_for_updates(include_remote=True)
    if not updates.get("has_updates"):
        xbmcgui.Dialog().ok("SoLoKodi Updates", "Everything is already up to date.")
        record_update_check()
        return

    if not xbmcgui.Dialog().yesno(
        "Update SoLoKodi Build",
        "Updates are available:\n\n{0}\n\nInstall updates now?".format(update_report(updates)),
    ):
        return

    progress = xbmcgui.DialogProgress()
    progress.create("SoLoKodi Updates", "Updating build...")

    repo = build_config.repository_info()
    repo_id = repo.get("id")
    if repo_id and (updates.get("repository") or updates.get("addons")):
        progress.update(10, "Updating SoLoKodi repository...")
        build_ops.update_addon(repo_id)

    addon_ids = [item["id"] for item in updates.get("addons") or []]
    for index, addon_id in enumerate(addon_ids, start=1):
        progress.update(10 + int((index / max(len(addon_ids), 1)) * 50), "Updating {0}...".format(addon_id))
        build_ops.update_addon(addon_id)

    progress.update(70, "Refreshing build files...")
    try:
        remote = fetch_remote_manifest()
    except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, ValueError):
        remote = build_config.load_embedded_manifest()

    build_ops.install_addons(build_config.content_addons(remote))
    build_ops.install_addons(build_config.solokodi_addons(remote))
    build_ops.apply_theme(remote)
    build_ops.write_favourites(remote)
    menu_layout.apply_kids_home_menu(remote)

    build = remote.get("build") or build_config.build_info(remote)
    setup = xbmcaddon.Addon()
    setup.setSetting("build_version_installed", build.get("version", ""))
    setup.setSetting("setup_complete", "true")
    record_update_check()

    progress.update(100, "Done")
    time.sleep(0.3)
    progress.close()
    notify("Build updated")
    xbmcgui.Dialog().ok(
        "SoLoKodi Updates",
        "Update complete.\n\nRestart Kodi to load the latest build changes.",
    )


def maybe_notify_updates(force=False):
    setup = xbmcaddon.Addon()
    last_check = setup.getSetting("last_update_check") or "0"
    try:
        last = int(last_check)
    except ValueError:
        last = 0

    if not force and time.time() - last < 86400:
        return False

    try:
        updates = check_for_updates(include_remote=True)
    except Exception:
        return False

    record_update_check()
    if updates.get("has_updates"):
        notify("Updates available — open SoLoKodi Setup to update")
        return True
    return False
