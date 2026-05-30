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

    xbmc.sleep(5000)
    check_for_updates()

    while not MONITOR.abortRequested():
        if MONITOR.waitForAbort(86400):
            break
        check_for_updates()
