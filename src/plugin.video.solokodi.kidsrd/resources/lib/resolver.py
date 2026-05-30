import json
import re
import urllib.error
import urllib.parse
import urllib.request

from .constants import YTS_API_ROOT


class ResolverError(Exception):
    pass


def _request_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ResolverError("Lookup failed: HTTP {0}".format(exc.code)) from exc


def _best_torrent(torrents):
    if not torrents:
        return None
    return max(torrents, key=lambda item: int(item.get("seeds") or 0))


def _magnet_from_torrent(torrent):
    if torrent.get("url"):
        return torrent["url"]
    if torrent.get("hash"):
        return "magnet:?xt=urn:btih:{0}".format(torrent["hash"])
    return ""


def find_movie_magnet(title, year=None, imdb_id=None):
    if imdb_id:
        imdb_id = imdb_id if imdb_id.startswith("tt") else "tt{0}".format(str(imdb_id).zfill(7))
        url = YTS_API_ROOT + "/movie_details.json?" + urllib.parse.urlencode({"imdb_id": imdb_id})
        payload = _request_json(url)
        movie = ((payload.get("data") or {}).get("movie")) or {}
        torrent = _best_torrent(movie.get("torrents") or [])
        if torrent:
            return {
                "title": movie.get("title") or title,
                "year": movie.get("year") or year,
                "hash": (torrent.get("hash") or "").lower(),
                "magnet": _magnet_from_torrent(torrent),
                "quality": torrent.get("quality") or "",
            }

    params = {"query_term": title, "limit": 5}
    if year:
        params["year"] = year
    url = YTS_API_ROOT + "/list_movies.json?" + urllib.parse.urlencode(params)
    payload = _request_json(url)
    movies = ((payload.get("data") or {}).get("movies")) or []
    if not movies:
        raise ResolverError("No torrent source found for {0}.".format(title))

    chosen = movies[0]
    if year:
        for movie in movies:
            if str(movie.get("year")) == str(year):
                chosen = movie
                break

    torrent = _best_torrent(chosen.get("torrents") or [])
    if not torrent:
        raise ResolverError("No torrent files found for {0}.".format(title))

    return {
        "title": chosen.get("title") or title,
        "year": chosen.get("year") or year,
        "hash": (torrent.get("hash") or "").lower(),
        "magnet": _magnet_from_torrent(torrent),
        "quality": torrent.get("quality") or "",
    }


def hash_from_magnet(magnet):
    match = re.search(r"btih:([a-fA-F0-9]{40})", magnet or "")
    return match.group(1).lower() if match else ""
