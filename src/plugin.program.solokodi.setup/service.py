import xbmc
import xbmcaddon

if __name__ == "__main__":
    ADDON = xbmcaddon.Addon()
    MONITOR = xbmc.Monitor()

    def check_for_updates():
        if ADDON.getSetting("setup_complete") != "true":
            return
        from resources.lib import updater

        updater.maybe_notify_updates(force=False)

    def ensure_theme():
        if ADDON.getSetting("setup_complete") != "true":
            return
        from resources.lib import build_config, build_ops, menu_layout

        try:
            manifest = build_config.load_embedded_manifest()
            skin_id = build_config.selected_skin_id(manifest)
            if skin_id and build_ops.addon_installed(skin_id) and not build_ops.theme_is_active(manifest):
                build_ops.apply_theme(manifest)
            if not menu_layout.menu_files_present(manifest):
                menu_layout.apply_kids_home_menu(manifest)
        except RuntimeError:
            pass

    xbmc.sleep(5000)
    ensure_theme()
    check_for_updates()

    while not MONITOR.abortRequested():
        if MONITOR.waitForAbort(86400):
            break
        check_for_updates()
