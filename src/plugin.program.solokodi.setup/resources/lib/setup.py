import json
import time
import urllib.error
import urllib.parse
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
CLIENT_ID = "X245A4XAIBGVM"
DEVICE_URL = "https://api.real-debrid.com/oauth/v2/device/code"
CREDENTIALS_URL = "https://api.real-debrid.com/oauth/v2/device/credentials"
TOKEN_URL = "https://api.real-debrid.com/oauth/v2/token"
API_ROOT = "https://api.real-debrid.com/rest/1.0"


def notify(message, heading="SoLoKodi Kids"):
    xbmcgui.Dialog().notification(heading, message, xbmcgui.NOTIFICATION_INFO, 5000)


def request_json(url, data=None, headers=None):
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def show_parent_tips():
    xbmcgui.Dialog().textviewer(
        "Parent Tips (Optional)",
        "\n".join(
            [
                "SoLoKodi Kids is built for fun — no restrictions on kid content sources.",
                "",
                "Optional ideas if you share this device with adults:",
                "1. Create a separate Kids profile in Kodi.",
                "2. Use Master Lock if you want to hide settings from little hands.",
                "3. Real-Debrid (optional) powers Kids Real-Debrid streaming.",
                "",
                "Use Setup Wizard anytime to repair shortcuts or finish optional steps.",
            ]
        ),
    )


def poll_for_credentials(device_code, interval, expires_in):
    deadline = time.time() + min(int(expires_in), 1800)
    progress = xbmcgui.DialogProgress()
    progress.create("Real-Debrid", "Waiting for authorization...")

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


def save_trakt_api_token(token):
    value = (token or "").strip()
    if not value:
        return False
    ADDON.setSetting("trakt_api_token", value)
    notify("Trakt API token saved")
    return True


def save_tmdb_api_key(key):
    value = (key or "").strip()
    if not value:
        return False
    ADDON.setSetting("tmdb_api_key", value)
    try:
        kidsrd = xbmcaddon.Addon("plugin.video.solokodi.kidsrd")
        kidsrd.setSetting("tmdb_api_key", value)
    except RuntimeError:
        pass
    notify("TMDb API key saved")
    return True


def clear_api_credentials():
    if not xbmcgui.Dialog().yesno("API Tokens", "Remove saved Trakt and TMDb credentials from this Kodi profile?"):
        return
    for key in ("trakt_api_token", "tmdb_api_key"):
        ADDON.setSetting(key, "")
    try:
        kidsrd = xbmcaddon.Addon("plugin.video.solokodi.kidsrd")
        kidsrd.setSetting("tmdb_api_key", "")
    except RuntimeError:
        pass
    notify("API credentials cleared")


def clear_real_debrid():
    if not xbmcgui.Dialog().yesno("Real-Debrid", "Remove saved Real-Debrid credentials from this Kodi profile?"):
        return
    for key in ("rd_client_id", "rd_client_secret", "rd_access_token", "rd_refresh_token", "rd_expires_at"):
        ADDON.setSetting(key, "")
    notify("Real-Debrid authorization cleared")
