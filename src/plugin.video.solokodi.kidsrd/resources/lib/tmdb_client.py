import json
import urllib.error
import urllib.parse
import urllib.request

import xbmcaddon

from .constants import TMDB_API_ROOT, TMDB_IMAGE_ROOT


class TmdbError(Exception):
    pass


class TmdbClient:
    def __init__(self):
        self.addon = xbmcaddon.Addon()

    def api_key(self):
        key = self.addon.getSetting("tmdb_api_key")
        if not key:
            raise TmdbError("Add your free TMDb API key in this add-on settings.")
        return key

    def _request(self, path, params=None):
        query = dict(params or {})
        query["api_key"] = self.api_key()
        url = TMDB_API_ROOT + path + "?" + urllib.parse.urlencode(query)
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
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
        )

    def discover_kids_tv(self, page=1):
        return self._request(
            "/discover/tv",
            {
                "with_genres": "16,10762",
                "sort_by": "popularity.desc",
                "page": page,
                "include_adult": "false",
            },
        )

    def movie_details(self, movie_id):
        return self._request("/movie/{0}".format(movie_id), {"append_to_response": "external_ids"})

    def tv_details(self, tv_id):
        return self._request("/tv/{0}".format(tv_id), {"append_to_response": "external_ids"})

    @staticmethod
    def poster_url(path):
        if not path:
            return ""
        return TMDB_IMAGE_ROOT + path
