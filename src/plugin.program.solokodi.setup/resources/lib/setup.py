import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.sax.saxutils

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
BUILD_PROFILE = "kids"
CLIENT_ID = "X245A4XAIBGVM"
DEVICE_URL = "https://api.real-debrid.com/oauth/v2/device/code"
CREDENTIALS_URL = "https://api.real-debrid.com/oauth/v2/device/credentials"
TOKEN_URL = "https://api.real-debrid.com/oauth/v2/token"
API_ROOT = "https://api.real-debrid.com/rest/1.0"

# Official Kodi repo add-ons with kids, family, or educational content.
KIDS_ADDONS = [
    ("plugin.video.pbskids", "PBS Kids", "PBS Kids"),
    ("plugin.video.tvokids", "TV Ontario Kids", "TVO Kids"),
    ("plugin.video.youtube", "YouTube", "YouTube"),
    ("plugin.video.plutotv", "Pluto TV", "Pluto TV"),
    ("plugin.video.nasa", "NASA", "NASA Space"),
    ("plugin.video.esa", "ESA", "ESA Space"),
    ("plugin.video.iplayerwww", "BBC iPlayer", "CBeebies and CBBC"),
    ("plugin.video.wdrmaus", "WDR Maus", "Die Maus"),
    ("plugin.video.zdftivi", "ZDF Tivi", "ZDF Tivi"),
]

KIDS_SKIN = "skin.bello.10"
KIDS_THEME_COLORS = [
    ("lookandfeel.skincolor", "FF42A5F5"),
    ("lookandfeel.skincolors", "FFFF7043"),
]


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


def json_rpc(method, params=None):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    result = xbmc.executeJSONRPC(json.dumps(payload))
    try:
        return json.loads(result)
    except ValueError:
        return {"error": {"message": result}}


def build_kids_favourites():
    lines = ["<favourites>"]
    for addon_id, _label, favourite_name in KIDS_ADDONS:
        escaped_name = xml.sax.saxutils.escape(favourite_name)
        lines.append(
            '    <favourite name="{0}">ActivateWindow(Videos,plugin://{1}/,return)</favourite>'.format(
                escaped_name, addon_id
            )
        )
    lines.append('    <favourite name="SoLoKodi Kids Setup">RunAddon(plugin.program.solokodi.setup)</favourite>')
    lines.append("</favourites>")
    return "\n".join(lines) + "\n"


def install_kids_addons():
    installed = []
    failed = []
    for addon_id, label, _favourite_name in KIDS_ADDONS:
        if not xbmc.getCondVisibility("System.HasAddon({0})".format(addon_id)):
            xbmc.executebuiltin("InstallAddon({0})".format(addon_id), True)
        response = json_rpc("Addons.SetAddonEnabled", {"addonid": addon_id, "enabled": True})
        if "error" in response or not xbmc.getCondVisibility("System.HasAddon({0})".format(addon_id)):
            failed.append(label)
        else:
            installed.append(label)
    return installed, failed


def apply_kids_theme():
    for setting, value in KIDS_THEME_COLORS:
        json_rpc("Settings.SetSettingValue", {"setting": setting, "value": value})

    if not xbmc.getCondVisibility("System.HasAddon({0})".format(KIDS_SKIN)):
        xbmc.executebuiltin("InstallAddon({0})".format(KIDS_SKIN), True)

    if xbmc.getCondVisibility("System.HasAddon({0})".format(KIDS_SKIN)):
        json_rpc("Addons.SetAddonEnabled", {"addonid": KIDS_SKIN, "enabled": True})
        json_rpc("Settings.SetSettingValue", {"setting": "lookandfeel.skin", "value": KIDS_SKIN})
        xbmc.executebuiltin("ReloadSkin()")
        return True
    return False


def write_kids_favourites():
    profile_dir = xbmcvfs.translatePath("special://profile/")
    target = profile_dir.rstrip("/\\") + "/favourites.xml"
    with xbmcvfs.File(target, "w") as handle:
        handle.write(build_kids_favourites())
    return target


def run_kids_setup():
    ok = xbmcgui.Dialog().yesno(
        "SoLoKodi Kids Build",
        "Welcome! This installs every official kids source we could find, "
        "creates fun shortcuts on your home screen, and applies a colorful theme. Ready?",
    )
    if not ok:
        return

    installed, failed = install_kids_addons()
    write_kids_favourites()
    themed = apply_kids_theme()
    ADDON.setSetting("setup_complete", "true")
    ADDON.setSetting("build_profile", BUILD_PROFILE)

    lines = ["Kids build setup complete!"]
    if installed:
        lines.append("Enabled: " + ", ".join(installed))
    if failed:
        lines.append("Install manually from the Kodi official repo: " + ", ".join(failed))
    if themed:
        lines.append("Applied the Bello kids-friendly skin and bright colors.")
    else:
        lines.append("Bright accent colors applied. Install skin.bello.10 from the official repo for the full look.")
    lines.append("Restart Kodi to see all shortcuts and the new theme.")
    xbmcgui.Dialog().ok("SoLoKodi Kids Build", "\n".join(lines))


def run_family_setup():
    run_kids_setup()


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
                "3. Real-Debrid (optional) stays in this menu for parent-managed media.",
                "",
                "That's it. Let the kids explore PBS, TVO, NASA, CBeebies, and more!",
            ]
        ),
    )


def show_lock_checklist():
    show_parent_tips()


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


def clear_real_debrid():
    if not xbmcgui.Dialog().yesno("Real-Debrid", "Remove saved Real-Debrid credentials from this Kodi profile?"):
        return
    for key in ("rd_client_id", "rd_client_secret", "rd_access_token", "rd_refresh_token", "rd_expires_at"):
        ADDON.setSetting(key, "")
    notify("Real-Debrid authorization cleared")
