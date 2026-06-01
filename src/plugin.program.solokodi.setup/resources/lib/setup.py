import json
import time
import urllib.error
import urllib.parse
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
RD_CLIENT_ID = "X245A4XAIBGVM"
RD_DEVICE_URL = "https://api.real-debrid.com/oauth/v2/device/code"
RD_CREDENTIALS_URL = "https://api.real-debrid.com/oauth/v2/device/credentials"
RD_TOKEN_URL = "https://api.real-debrid.com/oauth/v2/token"
RD_API_ROOT = "https://api.real-debrid.com/rest/1.0"
TRAKT_CLIENT_ID = "264f8ecd14c879e372548c61545f1d27ff56fccfc043c4fa2a49346df4b6e36f"
TRAKT_CLIENT_SECRET = "435917b748d065e26786f5f9af20d1279269eb25aa16d51f4af14ee311d0247c"
TRAKT_API_ROOT = "https://api.trakt.tv"
TRAKT_DEVICE_URL = TRAKT_API_ROOT + "/oauth/device/code"
TRAKT_TOKEN_URL = TRAKT_API_ROOT + "/oauth/device/token"


def notify(message, heading="SoLoKodi Kids"):
    xbmcgui.Dialog().notification(heading, message, xbmcgui.NOTIFICATION_INFO, 5000)


def request_json(url, data=None, headers=None, json_body=False):
    body = None
    request_headers = dict(headers or {})
    if data is not None:
        if json_body:
            body = json.dumps(data).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        else:
            body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=request_headers)
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
                RD_CREDENTIALS_URL
                + "?"
                + urllib.parse.urlencode({"client_id": RD_CLIENT_ID, "code": device_code})
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

    auth = request_json(
        RD_DEVICE_URL + "?" + urllib.parse.urlencode({"client_id": RD_CLIENT_ID, "new_credentials": "yes"})
    )
    xbmcgui.Dialog().ok(
        "Real-Debrid Device Code",
        "Go to: {0}\nEnter code: {1}".format(auth["verification_url"], auth["user_code"]),
    )

    credentials = poll_for_credentials(auth["device_code"], auth.get("interval", 5), auth.get("expires_in", 1800))
    if not credentials:
        xbmcgui.Dialog().ok("Real-Debrid", "Authorization timed out or was cancelled.")
        return

    token = request_json(
        RD_TOKEN_URL,
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
        user = request_json(RD_API_ROOT + "/user", headers=headers)
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


def trakt_headers(access_token=None):
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": TRAKT_CLIENT_ID,
    }
    if access_token:
        headers["Authorization"] = "Bearer " + access_token
    return headers


def _trakt_error_message(exc):
    messages = {
        400: "Still waiting for approval.",
        404: "The Trakt device code was not found. Start authorization again.",
        409: "This Trakt device code was already used. Start authorization again.",
        410: "The Trakt device code expired. Start authorization again.",
        418: "Trakt authorization was denied.",
        429: "Trakt asked us to slow down. Waiting before trying again.",
    }
    return messages.get(exc.code, "Trakt authorization failed: HTTP {0}".format(exc.code))


def poll_for_trakt_token(device_code, interval, expires_in):
    interval = max(1, int(interval))
    expires_in = max(1, int(expires_in))
    deadline = time.time() + min(expires_in, 1800)
    progress = xbmcgui.DialogProgress()
    progress.create("Trakt", "Waiting for authorization...")

    while time.time() < deadline and not progress.iscanceled():
        remaining = int(deadline - time.time())
        progress.update(max(0, min(99, 100 - int((remaining / expires_in) * 100))))
        try:
            token = request_json(
                TRAKT_TOKEN_URL,
                {
                    "code": device_code,
                    "client_id": TRAKT_CLIENT_ID,
                    "client_secret": TRAKT_CLIENT_SECRET,
                },
                headers=trakt_headers(),
                json_body=True,
            )
            progress.close()
            return token
        except urllib.error.HTTPError as exc:
            if exc.code == 400:
                xbmc.sleep(interval * 1000)
                continue
            if exc.code == 429:
                xbmc.sleep((interval + 5) * 1000)
                continue
            progress.close()
            xbmcgui.Dialog().ok("Trakt", _trakt_error_message(exc))
            return None
        except urllib.error.URLError:
            progress.close()
            xbmcgui.Dialog().ok("Trakt", "Could not reach Trakt. Check your internet connection.")
            return None
        except ValueError:
            progress.close()
            xbmcgui.Dialog().ok("Trakt", "Trakt returned an unreadable authorization response.")
            return None

    progress.close()
    return None


def trakt_username(access_token):
    try:
        user = request_json(TRAKT_API_ROOT + "/users/me", headers=trakt_headers(access_token))
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
        return ""
    return user.get("username", "")


def sync_seren_trakt_settings(token, username):
    try:
        seren = xbmcaddon.Addon("plugin.video.seren")
    except RuntimeError:
        return False

    seren.setSetting("trakt.clientid", TRAKT_CLIENT_ID)
    seren.setSetting("trakt.secret", TRAKT_CLIENT_SECRET)
    seren.setSetting("trakt.auth", token.get("access_token", ""))
    seren.setSetting("trakt.refresh", token.get("refresh_token", ""))
    seren.setSetting("trakt.expires", _trakt_expires_at(token))
    seren.setSetting("trakt.username", username)
    return True


def _trakt_expires_at(token):
    created_at = int(token.get("created_at") or time.time())
    return str(created_at + int(token.get("expires_in", 0)))


def save_trakt_oauth(token):
    access_token = token.get("access_token", "")
    if not access_token:
        return False

    username = trakt_username(access_token)
    ADDON.setSetting("trakt_client_id", TRAKT_CLIENT_ID)
    ADDON.setSetting("trakt_client_secret", TRAKT_CLIENT_SECRET)
    ADDON.setSetting("trakt_access_token", access_token)
    ADDON.setSetting("trakt_refresh_token", token.get("refresh_token", ""))
    ADDON.setSetting("trakt_expires_at", _trakt_expires_at(token))
    ADDON.setSetting("trakt_username", username)
    ADDON.setSetting("trakt_api_token", access_token)
    sync_seren_trakt_settings(token, username)
    return True


def connect_trakt():
    ok = xbmcgui.Dialog().yesno(
        "Authorize Trakt",
        "Authorize Trakt for this Kodi profile using a device code. Tokens stay local on this device. Continue?",
    )
    if not ok:
        return False

    try:
        auth = request_json(
            TRAKT_DEVICE_URL,
            {"client_id": TRAKT_CLIENT_ID},
            headers=trakt_headers(),
            json_body=True,
        )
    except urllib.error.HTTPError as exc:
        xbmcgui.Dialog().ok("Trakt", "Could not start Trakt authorization: HTTP {0}".format(exc.code))
        return False
    except urllib.error.URLError:
        xbmcgui.Dialog().ok("Trakt", "Could not reach Trakt. Check your internet connection.")
        return False

    for key in ("verification_url", "user_code", "device_code"):
        if key not in auth:
            xbmcgui.Dialog().ok("Trakt", "Trakt returned an incomplete authorization response.")
            return False

    xbmcgui.Dialog().ok(
        "Trakt Device Code",
        "Go to: {0}\nEnter code: {1}".format(auth["verification_url"], auth["user_code"]),
    )

    token = poll_for_trakt_token(auth["device_code"], auth.get("interval", 5), auth.get("expires_in", 600))
    if not token:
        xbmcgui.Dialog().ok("Trakt", "Authorization timed out or was cancelled.")
        return False

    if not save_trakt_oauth(token):
        xbmcgui.Dialog().ok("Trakt", "Trakt did not return an access token.")
        return False

    username = ADDON.getSetting("trakt_username")
    suffix = " as {0}".format(username) if username else ""
    notify("Trakt connected{0}".format(suffix), heading="Trakt")
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
    if not xbmcgui.Dialog().yesno("Accounts", "Remove saved Trakt authorization and TMDb credentials from this Kodi profile?"):
        return
    for key in (
        "trakt_client_id",
        "trakt_client_secret",
        "trakt_access_token",
        "trakt_refresh_token",
        "trakt_expires_at",
        "trakt_username",
        "trakt_api_token",
        "tmdb_api_key",
    ):
        ADDON.setSetting(key, "")
    try:
        seren = xbmcaddon.Addon("plugin.video.seren")
        for key in ("trakt.auth", "trakt.refresh", "trakt.expires", "trakt.username"):
            seren.setSetting(key, "")
    except RuntimeError:
        pass
    try:
        kidsrd = xbmcaddon.Addon("plugin.video.solokodi.kidsrd")
        kidsrd.setSetting("tmdb_api_key", "")
    except RuntimeError:
        pass
    notify("Account credentials cleared")


def clear_real_debrid():
    if not xbmcgui.Dialog().yesno("Real-Debrid", "Remove saved Real-Debrid credentials from this Kodi profile?"):
        return
    for key in ("rd_client_id", "rd_client_secret", "rd_access_token", "rd_refresh_token", "rd_expires_at"):
        ADDON.setSetting(key, "")
    notify("Real-Debrid authorization cleared")
