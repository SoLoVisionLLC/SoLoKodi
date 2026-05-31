import json
import time
import urllib.error
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui

from . import build_config, build_ops, menu_layout, solotv_repo, status


def _wizard_heading(manifest=None):
    manifest = manifest or build_config.load_embedded_manifest()
    return build_config.build_info(manifest).get("name", "SoLoKodi") + " Setup"


def notify(message, heading=None, manifest=None):
    xbmcgui.Dialog().notification(
        heading or _wizard_heading(manifest),
        message,
        xbmcgui.NOTIFICATION_INFO,
        5000,
    )


def _progress(title, line):
    progress = xbmcgui.DialogProgress()
    progress.create(title, line)
    return progress


def _step_intro(step):
    intros = {
        "realdebrid": "Connect Real-Debrid so premium cached streams work in Xenon and other addons.",
        "tmdb": "Add a free TMDb API key so the add-on can browse kids movies and TV.",
        "solotv_repo": "Adds the SoLoTV file source and installs repository.solotv (SoLo-branded catalog).",
        "solotv_wizard": "Installs the SoLoTV Build Wizard from the SoLoTV repository.",
        "launch_wizard": "Opens the SoLoTV Build Wizard to install the Xenon interface and streaming add-ons.",
    }
    required = "Required" if step.get("required", True) else "Optional"
    body = intros.get(step["id"], "Continue with this step?")
    return xbmcgui.Dialog().yesno(
        step["label"],
        "{0} step\n\n{1}".format(required, body),
        yeslabel="Continue",
        nolabel="Skip" if not step.get("required", True) else "Cancel",
    )


def run_content_addons_step(manifest, progress, index, total):
    progress.update(int((index / total) * 100), "Installing sources...")
    installed, failed = build_ops.install_addons(build_config.content_addons(manifest))
    if failed:
        xbmcgui.Dialog().ok(
            "Some add-ons need manual install",
            "Install these from the Kodi official repository:\n" + "\n".join(failed),
        )
    return installed, failed


def run_solokodi_addons_step(manifest, progress, index, total):
    progress.update(int((index / total) * 100), "Installing SoLoKodi add-ons...")
    return build_ops.install_addons(build_config.solokodi_addons(manifest))


def choose_skin(manifest):
    options = build_config.skin_options(manifest)
    if len(options) <= 1:
        return options[0]["id"] if options else build_config.default_skin_id(manifest)

    labels = [option.get("label") or option.get("id") for option in options]
    preferred = xbmcaddon.Addon().getSetting("preferred_skin")
    preselect = 0
    for index, option in enumerate(options):
        if option.get("id") == preferred:
            preselect = index
            break

    choice = xbmcgui.Dialog().select(
        "Choose your home look",
        labels,
        preselect=preselect,
    )
    if choice < 0:
        return None
    return options[choice]["id"]


def run_theme_step(manifest, progress, index, total):
    progress.update(int((index / total) * 100), "Applying theme...")
    skin_id = choose_skin(manifest)
    if not skin_id:
        return False
    setup = xbmcaddon.Addon()
    setup.setSetting("preferred_skin", skin_id)
    return build_ops.apply_theme(manifest, skin_id=skin_id)


def run_favourites_step(manifest, progress, index, total):
    progress.update(int((index / total) * 100), "Creating shortcuts and home menu...")
    build_ops.write_favourites(manifest)
    menu_ready = menu_layout.apply_kids_home_menu(manifest)
    build_ops.sync_build_settings(manifest)
    return menu_ready


def run_realdebrid_step():
    from . import setup

    if status.step_realdebrid()["complete"]:
        return xbmcgui.Dialog().yesno("Real-Debrid", "Real-Debrid is already connected. Reconnect anyway?")
    setup.connect_real_debrid()
    return status.step_realdebrid()["complete"]


def run_tmdb_step():
    if status.step_tmdb()["complete"]:
        ok = xbmcgui.Dialog().yesno("TMDb", "TMDb API key is already saved. Enter a new one?")
        if not ok:
            return True
    key = xbmcgui.Dialog().input("Enter your free TMDb API key", type=xbmcgui.INPUT_ALPHANUM)
    if not key:
        return False
    try:
        kidsrd = xbmcaddon.Addon("plugin.video.solokodi.kidsrd")
        kidsrd.setSetting("tmdb_api_key", key.strip())
        notify("TMDb API key saved")
        return True
    except RuntimeError:
        xbmcgui.Dialog().ok("TMDb", "Install SoLoKodi Kids Real-Debrid first, then try again.")
        return False


def run_setup_wizard():
    manifest = build_config.load_embedded_manifest()
    build = build_config.build_info(manifest)
    heading = _wizard_heading(manifest)
    tagline = build_config.branding(manifest).get("tagline", "")
    intro = "This guided wizard sets up {0} v{1} step by step.".format(
        build.get("name", "SoLoKodi"),
        build.get("version", "1"),
    )
    if tagline:
        intro = "{0}\n\n{1}".format(intro, tagline)
    if not xbmcgui.Dialog().yesno(heading, intro + "\n\nReady to start?"):
        return

    steps = build_config.wizard_steps(manifest)
    progress = _progress(heading, "Starting...")
    total = len(steps)
    results = []

    for index, step in enumerate(steps, start=1):
        if progress.iscanceled():
            progress.close()
            notify("Setup wizard cancelled", manifest=manifest)
            return

        step_id = step["id"]
        if step_id == "content_addons":
            installed, failed = run_content_addons_step(manifest, progress, index, total)
            results.append((step["label"], not failed, failed))
        elif step_id == "solokodi_addons":
            installed, failed = run_solokodi_addons_step(manifest, progress, index, total)
            results.append((step["label"], not failed, failed))
        elif step_id == "theme":
            themed = run_theme_step(manifest, progress, index, total)
            results.append((step["label"], themed, [] if themed else ["skin not activated"]))
        elif step_id == "favourites":
            menu_ready = run_favourites_step(manifest, progress, index, total)
            detail = [] if menu_ready else ["shortcuts not configured"]
            results.append((step["label"], menu_ready, detail))
        elif step_id == "solotv_repo":
            progress.update(int((index / total) * 100), "Installing SoLoTV repository...")
            ok = solotv_repo.install_streaming_repository(manifest)
            results.append((step["label"], ok, [] if ok else ["SoLoTV repository"]))
        elif step_id == "solotv_wizard":
            progress.update(int((index / total) * 100), "Installing SoLoTV Build Wizard...")
            ok = solotv_repo.install_build_wizard(manifest)
            results.append((step["label"], ok, [] if ok else ["SoLoTV Build Wizard"]))
        elif step_id == "launch_wizard":
            progress.close()
            config = build_config.streaming_repo_config(manifest)
            hint = config.get("recommended_build_hint", "")
            if _step_intro(step):
                ok = solotv_repo.launch_build_wizard(manifest)
                if ok and hint:
                    xbmcgui.Dialog().ok(
                        heading,
                        "SoLoTV Build Wizard is open.\n\n{0}\n\n"
                        "When the interface finishes installing, restart Kodi.".format(hint),
                    )
                results.append((step["label"], ok, [] if ok else ["SoLoTV Build Wizard"]))
            else:
                results.append((step["label"], False, ["skipped"]))
            progress = _progress(heading, "Continuing...")
        elif step_id == "realdebrid":
            progress.close()
            if _step_intro(step):
                ok = run_realdebrid_step()
                results.append((step["label"], ok, [] if ok else ["skipped"]))
            else:
                results.append((step["label"], False, ["skipped"]))
            progress = _progress(heading, "Continuing...")
        elif step_id == "tmdb":
            progress.close()
            if _step_intro(step):
                ok = run_tmdb_step()
                results.append((step["label"], ok, [] if ok else ["skipped"]))
            else:
                results.append((step["label"], False, ["skipped"]))
            progress = _progress(heading, "Continuing...")
        else:
            progress.update(int((index / total) * 100), step.get("label", step_id))

    progress.close()
    build_ops.sync_build_settings(manifest)

    lines = ["Setup wizard finished!", ""]
    for label, ok, detail in results:
        mark = "OK" if ok else "Needs attention"
        lines.append("{0}: {1}".format(label, mark))
        if detail:
            lines.append("  - " + ", ".join(detail))
    lines.append("")
    if build_config.is_streaming_build(manifest):
        lines.append("Open SoLoTV Build Wizard from favourites to finish the interface setup.")
    else:
        lines.append("Restart Kodi if the new skin is not visible yet.")
    xbmcgui.Dialog().ok(heading, "\n".join(lines))


def run_change_skin():
    manifest = build_config.load_embedded_manifest()
    if build_config.is_streaming_build(manifest):
        xbmcgui.Dialog().ok(
            _wizard_heading(manifest),
            "SoLoTV uses the Xenon interface from the SoLoTV Build Wizard.\n\n"
            "Open SoLoTV Build Wizard to change skins or rebuild.",
        )
        solotv_repo.launch_build_wizard(manifest)
        return
    skin_id = choose_skin(manifest)
    if not skin_id:
        return
    setup = xbmcaddon.Addon()
    setup.setSetting("preferred_skin", skin_id)
    progress = _progress("Change Kids Skin", "Installing and applying skin...")
    progress.update(40, "Applying skin...")
    themed = build_ops.apply_theme(manifest, skin_id=skin_id)
    progress.update(80, "Refreshing home menu...")
    menu_layout.apply_kids_home_menu(manifest)
    progress.update(100, "Done")
    time.sleep(0.3)
    progress.close()
    if themed:
        notify("Skin changed — restart Kodi if the home screen looks wrong")
        xbmcgui.Dialog().ok(
            "Change Kids Skin",
            "Your preferred skin was saved.\n\nRestart Kodi if the new look is not visible yet.",
        )
    else:
        option = build_config.skin_option(skin_id, manifest) or {}
        label = option.get("label") or skin_id
        xbmcgui.Dialog().ok(
            "Change Kids Skin",
            "The {0} skin could not be installed.\n\n"
            "For Nimbus, make sure Kodi can reach ivarbrandt.github.io, then try "
            "Repair Build or restart Kodi.".format(label),
        )


def run_quick_repair():
    manifest = build_config.load_embedded_manifest()
    build = build_config.build_info(manifest)
    progress = _progress("Repair Build", "Re-syncing {0}...".format(build.get("name", "build")))
    if build_config.is_streaming_build(manifest):
        progress.update(20, "Checking SoLoTV repository...")
        solotv_repo.install_streaming_repository(manifest)
        progress.update(45, "Checking SoLoTV Build Wizard...")
        solotv_repo.install_build_wizard(manifest)
        progress.update(70, "Refreshing SoLoTV shortcuts...")
        build_ops.apply_theme(manifest)
        build_ops.write_favourites(manifest)
    else:
        progress.update(20, "Installing missing add-ons...")
        build_ops.install_addons(build_config.content_addons(manifest))
        build_ops.install_addons(build_config.solokodi_addons(manifest))
        progress.update(55, "Refreshing theme, shortcuts, and home menu...")
        build_ops.apply_theme(manifest)
        build_ops.write_favourites(manifest)
        menu_layout.apply_kids_home_menu(manifest)
    build_ops.sync_build_settings(manifest)
    progress.update(100, "Done")
    time.sleep(0.3)
    progress.close()
    notify("Build repaired", manifest=manifest)
    xbmcgui.Dialog().ok(
        "Repair Build",
        "Your {0} shortcuts, theme, and add-ons were refreshed.".format(build.get("name", "build")),
    )
