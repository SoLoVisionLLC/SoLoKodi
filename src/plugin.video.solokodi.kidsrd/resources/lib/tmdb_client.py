import json
import urllib.error
import urllib.parse
import urllib.request

import xbmcaddon

from .cache import cache
from .constants import HTTP_HEADERS, SETUP_ADDON_ID, TMDB_API_ROOT, TMDB_IMAGE_ROOT

USER_AGENT = "SoLoKodi/1.1.0 (Kodi Build)"


class TmdbError(Exception):
    pass


class TmdbClient:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self._setup = None

    def _setup_addon(self):
        if self._setup is None:
            try:
                self._setup = xbmcaddon.Addon(SETUP_ADDON_ID)
            except RuntimeError:
                self._setup = False
        return self._setup

    def api_key(self):
        setup = self._setup_addon()
        key = setup.getSetting("tmdb_api_key") if setup else ""
        key = key or self.addon.getSetting("tmdb_api_key")
        if not key:
            raise TmdbError("Add your free TMDb API key in this add-on settings.")
        return key

    def _request(self, path, params=None, cache_ttl=3600):
        query = dict(params or {})
        query["api_key"] = self.api_key()
        url = TMDB_API_ROOT + path + "?" + urllib.parse.urlencode(query)

        cache_key = "tmdb:" + url
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        req_headers = dict(HTTP_HEADERS)
        req_headers["User-Agent"] = USER_AGENT
        req = urllib.request.Request(url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
                cache.set(cache_key, result, ttl=cache_ttl)
                return result
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise TmdbError("TMDb request failed: HTTP {0}".format(exc.code)) from exc
        except urllib.error.URLError as exc:
            raise TmdbError("Could not reach TMDb. Check your internet connection.") from exc
        except (TimeoutError, json.JSONDecodeError) as exc:
            raise TmdbError("TMDb request failed: {0}".format(exc)) from exc

    def discover_kids_movies(self, page=1):
        return self._request(
            "/discover/movie",
            {
                "with_genres": "16,10751",
                "certification_country": "US",
                "certification.lte": "PG",
                "sort_by": "popularity.desc",
                "page": page,
                "include_adult": "false",
            },
            cache_ttl=1800,
        )

    def discover_kids_tv(self, page=1, modern_only=False):
        params = {
            "with_genres": "16|10762|10751",
            "sort_by": "first_air_date.desc" if modern_only else "popularity.desc",
            "page": page,
            "include_adult": "false",
        }
        if modern_only:
            params["first_air_date.gte"] = "2015-01-01"
        return self._request("/discover/tv", params, cache_ttl=1800)

    def movie_details(self, movie_id):
        return self._request("/movie/{0}".format(movie_id), {"append_to_response": "external_ids"}, cache_ttl=86400)

    def tv_details(self, tv_id):
        return self._request("/tv/{0}".format(tv_id), {"append_to_response": "external_ids"}, cache_ttl=86400)

    @staticmethod
    def poster_url(path):
        if not path:
            return ""
        return TMDB_IMAGE_ROOT + path
