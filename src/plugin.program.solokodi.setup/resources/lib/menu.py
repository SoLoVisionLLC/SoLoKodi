import sys
import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin

from . import build_config, setup, status, updater, wizard

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
    is_solotv = build_config.is_diggz_build(manifest)
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
        add_item(
            "Open Chef Omega Wizard",
            "open_chef",
            "Install or update the Xenon 4K interface and streaming addons.",
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
        "Connect Real-Debrid",
        "connect_rd",
        "Authorize this Kodi profile with Real-Debrid using the device flow.",
    )
    add_item(
        "Check Real-Debrid Account",
        "check_rd",
        "Confirm that the local Real-Debrid token works.",
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

    profiles = build_config.list_profile_manifests()
    if len(profiles) > 1:
        other = "kids" if build_config.profile_id() == "solotv" else "solotv"
        if other in profiles:
            label = "Switch to SoLoKodi Kids" if other == "kids" else "Switch to SoLoTV"
            add_item(
                label,
                "switch_{0}".format(other),
                "Change the active build profile and run its setup wizard.",
            )

    xbmcplugin.endOfDirectory(HANDLE)


def run():
    params = urllib.parse.parse_qs(sys.argv[2][1:])
    action = params.get("action", ["menu"])[0]

    if action in ("wizard", "kids_setup", "family_setup"):
        wizard.run_setup_wizard()
    elif action == "init_solotv":
        wizard.run_solotv_setup()
    elif action == "switch_solotv":
        wizard.run_solotv_setup()
    elif action == "switch_kids":
        build_config.set_active_profile("kids")
        wizard.run_setup_wizard()
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
        from . import diggz_ops

        manifest = build_config.load_embedded_manifest()
        if not diggz_ops.launch_chef_wizard(manifest):
            xbmcgui.Dialog().ok(
                "SoLoTV",
                "Chef Omega Wizard is not installed yet.\n\nRun the SoLoTV Setup Wizard first.",
            )
    elif action == "connect_rd":
        setup.connect_real_debrid()
    elif action == "open_kidsrd":
        xbmc.executebuiltin("ActivateWindow(Videos,plugin://plugin.video.solokodi.kidsrd/,return)")
    elif action == "check_rd":
        setup.check_real_debrid()
    elif action in ("parent_tips", "lock_checklist"):
        setup.show_parent_tips()
    elif action == "clear_rd":
        setup.clear_real_debrid()
    else:
        show_menu()
