import sys
import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin

from . import build_config, builds, maintenance, setup, status, updater, wizard

ADDON_URL = sys.argv[0]
HANDLE = int(sys.argv[1])


def add_item(label, action, description, is_folder=False):
    url = ADDON_URL + "?" + urllib.parse.urlencode({"action": action})
    item = xbmcgui.ListItem(label=label)
    item.setInfo("video", {"title": label, "plot": description})
    xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=is_folder)


def show_menu():
    summary = status.completion_summary()
    build = build_config.build_info()
    manifest = build_config.load_embedded_manifest()
    is_solotv = build_config.is_streaming_build(manifest)
    build_name = build.get("name", "SoLoKodi")

    if summary["ready"]:
        headline = "Build ready — {0}/{1} required steps done".format(
            summary["required_done"], summary["required_total"]
        )
    else:
        headline = "Setup needed — {0}/{1} required steps done".format(
            summary["required_done"], summary["required_total"]
        )

    add_item(
        "Run Setup Wizard",
        "wizard",
        "Guided step-by-step setup for {0} v{1}. {2}".format(
            build_name,
            build.get("version", "?"),
            headline,
        ),
    )
    add_item(
        "Change Build",
        "pick_build",
        "Switch between SoLoKodi builds (Kids, SoLoTV, and more) and run its setup.",
    )
    add_item(
        "Build Status",
        "status",
        "See which setup steps are complete and what still needs attention.",
    )
    add_item(
        "Check for Updates",
        "check_updates",
        "Compare your installed build and add-ons against the latest SoLoKodi release.",
    )
    add_item(
        "Update Build Now",
        "update_build",
        "Install the latest SoLoKodi repository, add-ons, shortcuts, and theme.",
    )

    if is_solotv:
        config = build_config.streaming_repo_config(manifest)
        wizard_label = config.get("wizard_label") or "Build Wizard"
        add_item(
            "Open {0}".format(wizard_label),
            "open_chef",
            "Install or update the {0} interface and streaming add-ons.".format(build_name),
        )
    else:
        add_item(
            "Change Kids Skin",
            "change_skin",
            "Switch between Bello and Nimbus with the same kids home menu shortcuts.",
        )
        add_item(
            "Open Kids Real-Debrid",
            "open_kidsrd",
            "Browse and play kids movies and shows from your Real-Debrid library.",
        )

    add_item(
        "Repair Build",
        "repair",
        "Re-install missing pieces and refresh shortcuts without changing your settings.",
    )
    add_item(
        "Maintenance",
        "maintenance",
        "Clear cache, packages, and thumbnails, reset the build, or close Kodi.",
        is_folder=True,
    )
    add_item(
        "Connect Real-Debrid",
        "connect_rd",
        "Authorize this Kodi profile with Real-Debrid using the device flow.",
    )
    add_item(
        "Check Real-Debrid Account",
        "check_rd",
        "Confirm that the local Real-Debrid token works.",
    )
    add_item(
        "Set Trakt API Token",
        "set_trakt",
        "Save a Trakt token for setup and supported add-ons.",
    )
    add_item(
        "Set TMDb API Key",
        "set_tmdb",
        "Save a TMDb key for metadata lookups.",
    )

    if not is_solotv:
        add_item(
            "Parent Tips (Optional)",
            "parent_tips",
            "Optional profile and lock ideas if adults share this device.",
        )

    add_item(
        "Clear Real-Debrid Authorization",
        "clear_rd",
        "Remove Real-Debrid credentials from this Kodi profile.",
    )
    add_item(
        "Clear API Tokens",
        "clear_api",
        "Remove saved Trakt and TMDb credentials from this Kodi profile.",
    )

    xbmcplugin.endOfDirectory(HANDLE)


def show_maintenance_menu():
    add_item("Clear Cache", "maint_cache", "Delete temporary cache files to free up space.")
    add_item("Clear Packages", "maint_packages", "Delete downloaded add-on install files (.zip).")
    add_item("Clear Thumbnails", "maint_thumbs", "Delete cached artwork; it rebuilds automatically.")
    add_item(
        "Reset SoLoKodi Build",
        "maint_reset",
        "Clear build selection and setup progress (keeps Real-Debrid, Trakt, and TMDb).",
    )
    add_item("Force Close Kodi", "maint_quit", "Close Kodi to apply skin or build changes cleanly.")
    xbmcplugin.endOfDirectory(HANDLE)


def run():
    params = urllib.parse.parse_qs(sys.argv[2][1:])
    action = params.get("action", ["menu"])[0]

    if action == "menu":
        if not build_config.has_active_profile():
            builds.show_build_picker()
        if build_config.has_active_profile():
            show_menu()
        else:
            add_item(
                "Choose Your Build",
                "pick_build",
                "Pick a SoLoKodi build to install (Kids, SoLoTV, and more).",
            )
            xbmcplugin.endOfDirectory(HANDLE)
        return

    if action in ("wizard", "kids_setup"):
        wizard.run_setup_wizard()
    elif action == "pick_build":
        builds.show_build_picker()
    elif action == "maintenance":
        show_maintenance_menu()
    elif action == "maint_cache":
        maintenance.clear_cache()
    elif action == "maint_packages":
        maintenance.clear_packages()
    elif action == "maint_thumbs":
        maintenance.clear_thumbnails()
    elif action == "maint_reset":
        if maintenance.reset_build():
            builds.show_build_picker()
    elif action == "maint_quit":
        maintenance.force_close()
    elif action == "status":
        xbmcgui.Dialog().textviewer("Build Status", status.status_report())
    elif action == "check_updates":
        updates = updater.check_for_updates(include_remote=True)
        xbmcgui.Dialog().ok("SoLoKodi Updates", updater.update_report(updates))
        updater.record_update_check()
    elif action == "update_build":
        updater.apply_updates()
    elif action == "repair":
        wizard.run_quick_repair()
    elif action == "change_skin":
        wizard.run_change_skin()
    elif action == "open_chef":
        from . import solotv_repo

        manifest = build_config.load_embedded_manifest()
        config = build_config.streaming_repo_config(manifest)
        wizard_label = config.get("wizard_label") or "Build Wizard"
        if not solotv_repo.launch_build_wizard(manifest):
            xbmcgui.Dialog().ok(
                build_config.build_info(manifest).get("name", "Streaming Build"),
                "{0} is not installed yet.\n\nRun the setup wizard first.".format(wizard_label),
            )
    elif action == "connect_rd":
        setup.connect_real_debrid()
    elif action == "open_kidsrd":
        xbmc.executebuiltin("ActivateWindow(Videos,plugin://plugin.video.solokodi.kidsrd/,return)")
    elif action == "check_rd":
        setup.check_real_debrid()
    elif action == "set_trakt":
        wizard.run_trakt_step()
    elif action == "set_tmdb":
        wizard.run_tmdb_step()
    elif action == "parent_tips":
        setup.show_parent_tips()
    elif action == "clear_rd":
        setup.clear_real_debrid()
    elif action == "clear_api":
        setup.clear_api_credentials()
    else:
        show_menu()
