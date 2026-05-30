import json
import time
import urllib.error
import urllib.parse
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
CLIENT_ID = "X245A4XAIBGVM"
DEVICE_URL = "https://api.real-debrid.com/oauth/v2/device/code"
CREDENTIALS_URL = "https://api.real-debrid.com/oauth/v2/device/credentials"
TOKEN_URL = "https://api.real-debrid.com/oauth/v2/token"
API_ROOT = "https://api.real-debrid.com/rest/1.0"

OFFICIAL_ADDONS = [
    ("plugin.video.pbskids", "PBS Kids"),
    ("plugin.video.youtube", "YouTube"),
]

FAMILY_FAVOURITES = """<favourites>
    <favourite name="PBS Kids">ActivateWindow(Videos,plugin://plugin.video.pbskids/,return)</favourite>
    <favourite name="YouTube Family Playlists">ActivateWindow(Videos,plugin://plugin.video.youtube/,return)</favourite>
    <favourite name="SoLoKodi Family Setup">RunAddon(plugin.program.solokodi.setup)</favourite>
</favourites>
"""


def notify(message, heading="SoLoKodi"):
    xbmcgui.Dialog().notification(heading, message, xbmcgui.NOTIFICATION_INFO, 5000)


def request_json(url, data=None, headers=None):
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def json_rpc(method, params=None):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    result = xbmc.executeJSONRPC(json.dumps(payload))
    try:
        return json.loads(result)
    except ValueError:
        return {"error": {"message": result}}


def install_official_addons():
    installed = []
    failed = []
    for addon_id, label in OFFICIAL_ADDONS:
        if not xbmc.getCondVisibility("System.HasAddon({0})".format(addon_id)):
            xbmc.executebuiltin("InstallAddon({0})".format(addon_id), True)
        response = json_rpc("Addons.SetAddonEnabled", {"addonid": addon_id, "enabled": True})
        if "error" in response or not xbmc.getCondVisibility("System.HasAddon({0})".format(addon_id)):
            failed.append(label)
        else:
            installed.append(label)
    return installed, failed


def write_family_favourites():
    profile_dir = xbmcvfs.translatePath("special://profile/")
    target = profile_dir.rstrip("/\\") + "/favourites.xml"
    with xbmcvfs.File(target, "w") as handle:
        handle.write(FAMILY_FAVOURITES)
    return target


def run_family_setup():
    ok = xbmcgui.Dialog().yesno(
        "SoLoKodi Family Setup",
        "This setup installs official kid-friendly add-ons and creates family shortcuts. It does not install piracy repositories or provider scrapers.",
    )
    if not ok:
        return

    installed, failed = install_official_addons()
    write_family_favourites()
    ADDON.setSetting("setup_complete", "true")

    lines = []
    if installed:
        lines.append("Enabled: " + ", ".join(installed))
    if failed:
        lines.append("Install manually from Kodi official repo: " + ", ".join(failed))
    lines.append("Restart Kodi, then apply the parent lock checklist.")
    xbmcgui.Dialog().ok("SoLoKodi Family Setup", "\n".join(lines))
    show_lock_checklist()


def show_lock_checklist():
    xbmcgui.Dialog().textviewer(
        "Parent Lock Checklist",
        "\n".join(
            [
                "1. Create or switch to a Kids profile.",
                "2. Set the Kids profile to separate media sources.",
                "3. Enable Master Lock with a parent PIN.",
                "4. Lock settings, file manager, add-ons, and source editing.",
                "5. Remove Videos > Files from the Kids home screen if your skin allows it.",
                "6. Keep Real-Debrid authorization only in the parent-managed profile.",
                "7. Add only approved local folders and the SoLoKodi favourites to the Kids profile.",
                "",
                "Real-Debrid is for lawful personal media access only. Do not add piracy repositories or scraper add-ons to the Kids profile.",
            ]
        ),
    )


def poll_for_credentials(device_code, interval, expires_in):
    deadline = time.time() + min(int(expires_in), 1800)
    progress = xbmcgui.DialogProgress()
    progress.create("Real-Debrid", "Waiting for parent authorization...")

    while time.time() < deadline and not progress.iscanceled():
        remaining = int(deadline - time.time())
        progress.update(max(0, min(99, 100 - int((remaining / int(expires_in)) * 100))))
        try:
            credentials = request_json(
                CREDENTIALS_URL
                + "?"
                + urllib.parse.urlencode({"client_id": CLIENT_ID, "code": device_code})
            )
            progress.close()
            return credentials
        except urllib.error.HTTPError:
            xbmc.sleep(int(interval) * 1000)
    progress.close()
    return None


def connect_real_debrid():
    ok = xbmcgui.Dialog().yesno(
        "Connect Real-Debrid",
        "Authorize Real-Debrid for this Kodi profile. Tokens stay local on this device. Continue?",
    )
    if not ok:
        return

    auth = request_json(DEVICE_URL + "?" + urllib.parse.urlencode({"client_id": CLIENT_ID, "new_credentials": "yes"}))
    xbmcgui.Dialog().ok(
        "Real-Debrid Device Code",
        "Go to: {0}\nEnter code: {1}".format(auth["verification_url"], auth["user_code"]),
    )

    credentials = poll_for_credentials(auth["device_code"], auth.get("interval", 5), auth.get("expires_in", 1800))
    if not credentials:
        xbmcgui.Dialog().ok("Real-Debrid", "Authorization timed out or was cancelled.")
        return

    token = request_json(
        TOKEN_URL,
        {
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "code": auth["device_code"],
            "grant_type": "http://oauth.net/grant_type/device/1.0",
        },
    )
    expires_at = str(int(time.time()) + int(token.get("expires_in", 0)))

    ADDON.setSetting("rd_client_id", credentials["client_id"])
    ADDON.setSetting("rd_client_secret", credentials["client_secret"])
    ADDON.setSetting("rd_access_token", token.get("access_token", ""))
    ADDON.setSetting("rd_refresh_token", token.get("refresh_token", ""))
    ADDON.setSetting("rd_expires_at", expires_at)
    notify("Real-Debrid connected")


def auth_headers():
    token = ADDON.getSetting("rd_access_token")
    if not token:
        return None
    return {"Authorization": "Bearer " + token}


def check_real_debrid():
    headers = auth_headers()
    if not headers:
        xbmcgui.Dialog().ok("Real-Debrid", "No Real-Debrid authorization is saved in this Kodi profile.")
        return
    try:
        user = request_json(API_ROOT + "/user", headers=headers)
    except urllib.error.HTTPError as exc:
        xbmcgui.Dialog().ok("Real-Debrid", "Authorization check failed: HTTP {0}".format(exc.code))
        return
    xbmcgui.Dialog().ok(
        "Real-Debrid Connected",
        "User: {0}\nType: {1}\nPremium seconds remaining: {2}".format(
            user.get("username", "unknown"),
            user.get("type", "unknown"),
            user.get("premium", "unknown"),
        ),
    )


def clear_real_debrid():
    if not xbmcgui.Dialog().yesno("Real-Debrid", "Remove saved Real-Debrid credentials from this Kodi profile?"):
        return
    for key in ("rd_client_id", "rd_client_secret", "rd_access_token", "rd_refresh_token", "rd_expires_at"):
        ADDON.setSetting(key, "")
    notify("Real-Debrid authorization cleared")
