import json
import time
import urllib.error
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui

from . import build_config, build_ops, menu_layout, status


def notify(message, heading="SoLoKodi Wizard"):
    xbmcgui.Dialog().notification(heading, message, xbmcgui.NOTIFICATION_INFO, 5000)


def _progress(title, line):
    progress = xbmcgui.DialogProgress()
    progress.create(title, line)
    return progress


def _step_intro(step):
    intros = {
        "realdebrid": "Connect Real-Debrid so Kids Real-Debrid can stream cached movies and your library.",
        "tmdb": "Add a free TMDb API key so the add-on can browse kids movies and TV.",
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
    progress.update(int((index / total) * 100), "Installing kids sources...")
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
        "Choose your kids home look",
        labels,
        preselect=preselect,
    )
    if choice < 0:
        return None
    return options[choice]["id"]


def run_theme_step(manifest, progress, index, total):
    progress.update(int((index / total) * 100), "Applying kids theme...")
    skin_id = choose_skin(manifest)
    if not skin_id:
        return False
    setup = xbmcaddon.Addon()
    setup.setSetting("preferred_skin", skin_id)
    return build_ops.apply_theme(manifest, skin_id=skin_id)


def run_favourites_step(manifest, progress, index, total):
    progress.update(int((index / total) * 100), "Creating shortcuts and kids home menu...")
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
    if not xbmcgui.Dialog().yesno(
        "SoLoKodi Setup Wizard",
        "This guided wizard sets up {0} v{1} step by step.\n\nReady to start?".format(
            build.get("name", "SoLoKodi Kids"), build.get("version", "1")
        ),
    ):
        return

    steps = build_config.wizard_steps(manifest)
    progress = _progress("SoLoKodi Setup Wizard", "Starting...")
    total = len(steps)
    results = []

    for index, step in enumerate(steps, start=1):
        if progress.iscanceled():
            progress.close()
            notify("Setup wizard cancelled")
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
            results.append((step["label"], menu_ready, [] if menu_ready else ["home menu not configured"]))
        elif step_id == "realdebrid":
            progress.close()
            if _step_intro(step):
                ok = run_realdebrid_step()
                results.append((step["label"], ok, [] if ok else ["skipped"]))
            else:
                results.append((step["label"], False, ["skipped"]))
            progress = _progress("SoLoKodi Setup Wizard", "Continuing...")
        elif step_id == "tmdb":
            progress.close()
            if _step_intro(step):
                ok = run_tmdb_step()
                results.append((step["label"], ok, [] if ok else ["skipped"]))
            else:
                results.append((step["label"], False, ["skipped"]))
            progress = _progress("SoLoKodi Setup Wizard", "Continuing...")
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
    lines.append("Restart Kodi if the new skin is not visible yet.")
    xbmcgui.Dialog().ok("SoLoKodi Setup Wizard", "\n".join(lines))


def run_change_skin():
    manifest = build_config.load_embedded_manifest()
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
        xbmcgui.Dialog().ok(
            "Change Kids Skin",
            "The skin could not be activated automatically.\n\nTry Repair Build or restart Kodi.",
        )


def run_quick_repair():
    manifest = build_config.load_embedded_manifest()
    progress = _progress("Repair Build", "Re-syncing your kids build...")
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
    notify("Build repaired")
    xbmcgui.Dialog().ok("Repair Build", "Your kids build shortcuts, home menu, theme, and add-ons were refreshed.")
