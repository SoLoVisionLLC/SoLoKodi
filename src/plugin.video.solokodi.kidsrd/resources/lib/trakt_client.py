import json
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import xbmcaddon
except ImportError:
    xbmcaddon = None

from .cache import cache
from .constants import SETUP_ADDON_ID

TRAKT_API_ROOT = "https://api.trakt.tv"
DEFAULT_TRAKT_CLIENT_ID = "c55e97fb5825a07c39050d2bc4a8996e8d19356cb6d22efdf3f3edb9bd93ef53"
USER_AGENT = "SoLoKodi/1.1.0 (Kodi Build)"


class TraktError(Exception):
    pass


class TraktAuthError(TraktError):
    pass


class TraktClient:
    def __init__(self, client_id=None):
        self.client_id = client_id or DEFAULT_TRAKT_CLIENT_ID
        self._setup = None

    def _setup_addon(self):
        if self._setup is None and xbmcaddon is not None:
            try:
                self._setup = xbmcaddon.Addon(SETUP_ADDON_ID)
            except RuntimeError:
                try:
                    self._setup = xbmcaddon.Addon("plugin.video.solokodi.kidsrd")
                except RuntimeError:
                    self._setup = None
        return self._setup

    def get_access_token(self):
        setup = self._setup_addon()
        if not setup:
            return ""
        return setup.getSetting("trakt_access_token") or ""

    def _headers(self, with_auth=True):
        headers = {
            "Content-Type": "application/json",
            "trakt-api-version": "2",
            "trakt-api-key": self.client_id,
            "User-Agent": USER_AGENT,
        }
        if with_auth:
            token = self.get_access_token()
            if token:
                headers["Authorization"] = "Bearer " + token
        return headers

    def _request(self, path, data=None, method=None, with_auth=False, use_cache=False, cache_ttl=1800):
        url = TRAKT_API_ROOT + path
        cache_key = "trakt:" + url + ":" + str(data)

        if use_cache and not data and method in (None, "GET"):
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(
            url,
            data=body,
            headers=self._headers(with_auth=with_auth),
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read().decode("utf-8")
                res = json.loads(raw) if raw else {}
                if use_cache and not data and method in (None, "GET"):
                    cache.set(cache_key, res, ttl=cache_ttl)
                return res
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            if exc.code in (401, 403):
                raise TraktAuthError(
                    "Trakt HTTP {0} Forbidden: Check Trakt API Key / Connect Trakt account.".format(exc.code)
                ) from exc
            raise TraktError("Trakt API error HTTP {0}: {1}".format(exc.code, detail or exc.reason)) from exc
        except Exception as exc:
            raise TraktError("Trakt network request failed: {0}".format(exc)) from exc

    def get_device_code(self):
        return self._request(
            "/oauth/device/code",
            data={"client_id": self.client_id},
            method="POST",
            with_auth=False,
        )

    def poll_device_token(self, device_code, client_secret=""):
        return self._request(
            "/oauth/device/token",
            data={
                "code": device_code,
                "client_id": self.client_id,
                "client_secret": client_secret,
            },
            method="POST",
            with_auth=False,
        )

    def get_user_watchlist(self, item_type="movies"):
        return self._request(
            "/sync/watchlist/" + item_type,
            with_auth=True,
            use_cache=True,
            cache_ttl=900,
        )

    def get_user_collection(self, item_type="movies"):
        return self._request(
            "/sync/collection/" + item_type,
            with_auth=True,
            use_cache=True,
            cache_ttl=900,
        )

    def scrobble_start(self, title, progress_pct=0, imdb_id=None, tmdb_id=None):
        movie_meta = {"title": title}
        if imdb_id:
            movie_meta["ids"] = {"imdb": imdb_id}
        elif tmdb_id:
            movie_meta["ids"] = {"tmdb": int(tmdb_id)}

        payload = {"movie": movie_meta, "progress": progress_pct}
        return self._request("/scrobble/start", data=payload, method="POST", with_auth=True)

    def scrobble_stop(self, title, progress_pct=100, imdb_id=None, tmdb_id=None):
        movie_meta = {"title": title}
        if imdb_id:
            movie_meta["ids"] = {"imdb": imdb_id}
        elif tmdb_id:
            movie_meta["ids"] = {"tmdb": int(tmdb_id)}

        payload = {"movie": movie_meta, "progress": progress_pct}
        return self._request("/scrobble/stop", data=payload, method="POST", with_auth=True)
