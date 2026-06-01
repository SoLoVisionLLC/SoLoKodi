import xbmcaddon
import xbmcvfs

from . import build_config, build_ops, menu_layout


def _addon_entries(kind):
    manifest = build_config.load_embedded_manifest()
    if kind == "content":
        return build_config.content_addons(manifest)
    if kind == "solokodi":
        return build_config.solokodi_addons(manifest)
    return []


def _missing_addons(entries):
    missing = []
    for entry in entries:
        if not build_ops.addon_installed(entry["id"]):
            missing.append(entry["label"])
    return missing


def step_content_addons():
    missing = _missing_addons(_addon_entries("content"))
    return {"complete": not missing, "missing": missing, "label": "Kids sources"}


def step_solokodi_addons():
    missing = _missing_addons(_addon_entries("solokodi"))
    return {"complete": not missing, "missing": missing, "label": "SoLoKodi add-ons"}


def step_theme():
    manifest = build_config.load_embedded_manifest()
    skin_id = build_config.selected_skin_id(manifest)
    option = build_config.skin_option(skin_id, manifest) or {}
    label = option.get("label") or skin_id or "Kids theme"
    if not skin_id:
        return {"complete": False, "missing": ["theme"], "label": "Kids theme"}
    if not build_ops.addon_installed(skin_id):
        return {"complete": False, "missing": [label], "label": "Kids theme"}
    active = build_ops.theme_is_active(manifest)
    return {
        "complete": active,
        "missing": [] if active else ["activate {0}".format(label)],
        "label": "Kids theme",
    }


def step_favourites():
    setup = xbmcaddon.Addon()
    manifest = build_config.load_embedded_manifest()
    setup_name = manifest.get("setup_favourite") or "SoLoKodi Setup"
    if build_config.is_streaming_build(manifest):
        build = build_config.build_info(manifest)
        profile_dir = xbmcvfs.translatePath("special://profile/")
        target = profile_dir.rstrip("/\\") + "/favourites.xml"
        if not xbmcvfs.exists(target):
            return {"complete": False, "missing": ["shortcuts"], "label": "{0} shortcuts".format(build.get("name", "Streaming"))}
        with xbmcvfs.File(target) as handle:
            content = handle.read()
        shortcuts_ok = setup_name in content
        return {
            "complete": shortcuts_ok,
            "missing": [] if shortcuts_ok else ["shortcuts"],
            "label": "{0} shortcuts".format(build.get("name", "Streaming")),
        }

    if setup.getSetting("setup_complete") == "true" and menu_layout.menu_files_present(manifest):
        return {"complete": True, "missing": [], "label": "Home shortcuts"}

    profile_dir = xbmcvfs.translatePath("special://profile/")
    target = profile_dir.rstrip("/\\") + "/favourites.xml"
    if not xbmcvfs.exists(target):
        return {"complete": False, "missing": ["shortcuts"], "label": "Home shortcuts"}

    with xbmcvfs.File(target) as handle:
        content = handle.read()
    shortcuts_ok = "PBS Kids" in content and setup_name in content
    menu_ok = menu_layout.menu_files_present(manifest)
    complete = shortcuts_ok and menu_ok
    missing = []
    if not shortcuts_ok:
        missing.append("shortcuts")
    if not menu_ok:
        missing.append("home menu")
    return {
        "complete": complete,
        "missing": missing,
        "label": "Home shortcuts",
    }


def step_solotv_repo():
    manifest = build_config.load_embedded_manifest()
    config = build_config.streaming_repo_config(manifest)
    repo_id = config.get("repository_id")
    label = config.get("repository_label") or repo_id or "streaming repository"
    if repo_id and build_ops.addon_installed(repo_id):
        return {"complete": True, "missing": [], "label": label}
    return {"complete": False, "missing": [label], "label": label}


def step_solotv_wizard():
    manifest = build_config.load_embedded_manifest()
    config = build_config.streaming_repo_config(manifest)
    wizard_id = config.get("wizard_addon_id")
    label = config.get("wizard_label") or "SoLoTV Build Wizard"
    if wizard_id and build_ops.addon_installed(wizard_id):
        return {"complete": True, "missing": [], "label": label}
    return {"complete": False, "missing": [label], "label": label}


def step_launch_wizard():
    manifest = build_config.load_embedded_manifest()
    config = build_config.streaming_repo_config(manifest)
    wizard_id = config.get("wizard_addon_id")
    build = build_config.build_info(manifest)
    label = "{0} interface".format(build.get("name", "Streaming"))
    if not wizard_id or not build_ops.addon_installed(wizard_id):
        return {"complete": False, "missing": ["open {0}".format(config.get("wizard_label") or "Build Wizard")], "label": label}
    return {"complete": True, "missing": [], "label": label}


def step_realdebrid():
    setup = xbmcaddon.Addon()
    complete = bool(setup.getSetting("rd_access_token"))
    return {"complete": complete, "missing": [] if complete else ["Real-Debrid"], "label": "Real-Debrid"}


def step_trakt():
    setup = xbmcaddon.Addon()
    complete = bool(setup.getSetting("trakt_access_token"))
    username = setup.getSetting("trakt_username")
    if not complete:
        try:
            seren = xbmcaddon.Addon("plugin.video.seren")
            complete = bool(seren.getSetting("trakt.auth"))
            username = username or seren.getSetting("trakt.username")
        except RuntimeError:
            pass
    label = "Trakt account"
    if username:
        label = "Trakt account ({0})".format(username)
    return {"complete": complete, "missing": [] if complete else ["Trakt authorization"], "label": label}


def step_tmdb():
    setup = xbmcaddon.Addon()
    complete = bool(setup.getSetting("tmdb_api_key"))
    try:
        kidsrd = xbmcaddon.Addon("plugin.video.solokodi.kidsrd")
        complete = complete or bool(kidsrd.getSetting("tmdb_api_key"))
    except RuntimeError:
        pass
    return {"complete": complete, "missing": [] if complete else ["TMDb API key"], "label": "TMDb API key"}


STEP_CHECKS = {
    "content_addons": step_content_addons,
    "solokodi_addons": step_solokodi_addons,
    "theme": step_theme,
    "favourites": step_favourites,
    "realdebrid": step_realdebrid,
    "trakt": step_trakt,
    "tmdb": step_tmdb,
    "solotv_repo": step_solotv_repo,
    "solotv_wizard": step_solotv_wizard,
    "launch_wizard": step_launch_wizard,
}


def step_status(step_id):
    checker = STEP_CHECKS.get(step_id)
    if not checker:
        return {"complete": False, "missing": [step_id], "label": step_id}
    return checker()


def all_steps():
    manifest = build_config.load_embedded_manifest()
    results = []
    for step in build_config.wizard_steps(manifest):
        status = step_status(step["id"])
        results.append(
            {
                "id": step["id"],
                "label": step.get("label") or status["label"],
                "required": step.get("required", True),
                "complete": status["complete"],
                "missing": status["missing"],
            }
        )
    return results


def required_complete():
    return all(step["complete"] for step in all_steps() if step["required"])


def completion_summary():
    steps = all_steps()
    required = [step for step in steps if step["required"]]
    optional = [step for step in steps if not step["required"]]
    required_done = sum(1 for step in required if step["complete"])
    optional_done = sum(1 for step in optional if step["complete"])
    return {
        "steps": steps,
        "required_done": required_done,
        "required_total": len(required),
        "optional_done": optional_done,
        "optional_total": len(optional),
        "ready": required_done == len(required),
    }


def status_report():
    summary = completion_summary()
    build = build_config.build_info()
    setup = xbmcaddon.Addon()
    lines = [
        "Build: {0} v{1}".format(build.get("name", "SoLoKodi Kids"), build.get("version", "?")),
        "Installed build version: {0}".format(setup.getSetting("build_version_installed") or "not recorded"),
        "",
        "Required steps: {0}/{1}".format(summary["required_done"], summary["required_total"]),
        "Optional steps: {0}/{1}".format(summary["optional_done"], summary["optional_total"]),
        "",
    ]
    for step in summary["steps"]:
        mark = "[x]" if step["complete"] else "[ ]"
        suffix = "" if step["required"] else " (optional)"
        lines.append("{0} {1}{2}".format(mark, step["label"], suffix))
        if step["missing"]:
            lines.append("    Missing: {0}".format(", ".join(step["missing"])))
    return "\n".join(lines)
