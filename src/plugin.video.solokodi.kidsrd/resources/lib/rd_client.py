import json
import time
import urllib.error
import urllib.parse
import urllib.request

import xbmcaddon

from .constants import RD_API_ROOT, RD_TOKEN_URL, SETUP_ADDON_ID


class RealDebridError(Exception):
    pass


class RealDebridAuthError(RealDebridError):
    pass


def _request_json(url, data=None, headers=None, method=None):
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RealDebridError("HTTP {0}: {1}".format(exc.code, detail or exc.reason)) from exc
    except urllib.error.URLError as exc:
        raise RealDebridError("Could not reach Real-Debrid. Check your internet connection.") from exc
    except (TimeoutError, json.JSONDecodeError) as exc:
        raise RealDebridError("Real-Debrid request failed: {0}".format(exc)) from exc
    if not raw:
        return {}
    return json.loads(raw)


class RealDebridClient:
    def __init__(self):
        self._setup = None

    def _setup_addon(self):
        if self._setup is None:
            try:
                self._setup = xbmcaddon.Addon(SETUP_ADDON_ID)
            except RuntimeError as exc:
                raise RealDebridAuthError("Install SoLoKodi Kids Setup and connect Real-Debrid first.") from exc
        return self._setup

    def _refresh_token_if_needed(self):
        setup = self._setup_addon()
        token = setup.getSetting("rd_access_token")
        if not token:
            raise RealDebridAuthError("Real-Debrid is not connected. Use SoLoKodi Kids Setup to authorize.")

        expires_at = setup.getSetting("rd_expires_at") or "0"
        try:
            expires = int(expires_at)
        except ValueError:
            expires = 0

        if expires and time.time() < expires - 120:
            return token

        refresh_token = setup.getSetting("rd_refresh_token")
        client_id = setup.getSetting("rd_client_id")
        client_secret = setup.getSetting("rd_client_secret")
        if not refresh_token or not client_id or not client_secret:
            return token

        payload = _request_json(
            RD_TOKEN_URL,
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        new_token = payload.get("access_token")
        if not new_token:
            return token

        setup.setSetting("rd_access_token", new_token)
        if payload.get("refresh_token"):
            setup.setSetting("rd_refresh_token", payload.get("refresh_token"))
        setup.setSetting("rd_expires_at", str(int(time.time()) + int(payload.get("expires_in", 0))))
        return new_token

    def _headers(self):
        token = self._refresh_token_if_needed()
        return {"Authorization": "Bearer " + token}

    def get_user(self):
        return _request_json(RD_API_ROOT + "/user", headers=self._headers())

    def list_torrents(self):
        return _request_json(RD_API_ROOT + "/torrents", headers=self._headers())

    def list_downloads(self):
        return _request_json(RD_API_ROOT + "/downloads", headers=self._headers())

    def get_torrent(self, torrent_id):
        return _request_json(RD_API_ROOT + "/torrents/info/" + str(torrent_id), headers=self._headers())

    def instant_available(self, info_hash):
        info_hash = info_hash.lower()
        return _request_json(RD_API_ROOT + "/torrents/instantAvailability/" + info_hash, headers=self._headers())

    def add_magnet(self, magnet):
        return _request_json(
            RD_API_ROOT + "/torrents/addMagnet",
            data={"magnet": magnet},
            headers=self._headers(),
        )

    def select_files(self, torrent_id, file_ids):
        if file_ids == "all":
            payload = "all"
        else:
            payload = ",".join(str(file_id) for file_id in file_ids)
        return _request_json(
            RD_API_ROOT + "/torrents/selectFiles/" + str(torrent_id),
            data={"files": payload},
            headers=self._headers(),
        )

    def unrestrict_link(self, link):
        return _request_json(
            RD_API_ROOT + "/unrestrict/link",
            data={"link": link},
            headers=self._headers(),
        )

    def wait_for_links(self, torrent_id, timeout=120):
        deadline = time.time() + timeout
        while time.time() < deadline:
            info = self.get_torrent(torrent_id)
            status = info.get("status", "")
            links = info.get("links") or []
            if status == "error":
                raise RealDebridError("Real-Debrid could not fetch this torrent.")
            if links and status in ("downloaded", "dead"):
                return info
            time.sleep(2)
        raise RealDebridError("Timed out waiting for Real-Debrid links.")
