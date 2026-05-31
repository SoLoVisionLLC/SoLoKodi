import json
import re
import urllib.error
import urllib.parse
import urllib.request

from .constants import APIBAY_API_ROOTS, HTTP_HEADERS, YTS_API_ROOTS
from .kids_filter import normalize_title


class ResolverError(Exception):
    pass


def _request_json(url):
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ResolverError("Lookup failed: HTTP {0}".format(exc.code)) from exc
    except urllib.error.URLError as exc:
        raise ResolverError("Could not reach torrent lookup service. Check your internet connection.") from exc
    except (TimeoutError, json.JSONDecodeError) as exc:
        raise ResolverError("Torrent lookup failed: {0}".format(exc)) from exc


def _request_json_first(urls):
    errors = []
    for url in urls:
        try:
            return _request_json(url)
        except ResolverError as exc:
            errors.append(str(exc))
    if errors:
        raise ResolverError(errors[-1])
    raise ResolverError("No torrent lookup endpoints are available.")


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


def _magnet_from_apibay(entry):
    info_hash = (entry.get("info_hash") or "").strip()
    if not info_hash or info_hash == "0000000000000000000000000000000000000000":
        return ""
    name = entry.get("name") or "Kids Video"
    return "magnet:?xt=urn:btih:{0}&dn={1}".format(
        info_hash,
        urllib.parse.quote(name),
    )


def _apibay_search(query, categories=None):
    params = {"q": query}
    if categories:
        params["cat"] = categories
    query_string = "?" + urllib.parse.urlencode(params)
    urls = [root + query_string for root in APIBAY_API_ROOTS]
    payload = _request_json_first(urls)
    if not isinstance(payload, list):
        return []
    return [entry for entry in payload if isinstance(entry, dict) and entry.get("name")]


def _pick_apibay_result(title, year, entries, prefer_tv=False):
    target = normalize_title(title)
    year_text = str(year) if year else ""
    scored = []
    for entry in entries:
        name = entry.get("name") or ""
        haystack = normalize_title(name)
        if not haystack or target not in haystack:
            overlap = set(target.split()) & set(haystack.split())
            if len(overlap) < min(2, len(target.split())):
                continue
        if year_text and year_text not in name:
            continue
        if prefer_tv and not re.search(r"s\d{1,2}|season|complete|series", name, re.I):
            continue
        seeders = int(entry.get("seeders") or 0)
        if seeders < 1:
            continue
        scored.append((seeders, entry))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def _source_from_apibay(title, year=None, prefer_tv=False):
    categories = "205,207" if prefer_tv else "201,208,200"
    queries = []
    if year:
        queries.append("{0} {1}".format(title, year))
    queries.append(title)
    if prefer_tv:
        queries.insert(0, "{0} complete series".format(title))
        queries.insert(0, "{0} season 1".format(title))

    seen = set()
    for query in queries:
        if query in seen:
            continue
        seen.add(query)
        entry = _pick_apibay_result(title, year, _apibay_search(query, categories), prefer_tv=prefer_tv)
        if not entry:
            continue
        magnet = _magnet_from_apibay(entry)
        if not magnet:
            continue
        return {
            "title": title,
            "year": year,
            "hash": (entry.get("info_hash") or "").lower(),
            "magnet": magnet,
            "quality": entry.get("name") or "",
            "source": "apibay",
        }
    return None


def _movie_from_yts_payload(payload, title, year):
    movie = ((payload.get("data") or {}).get("movie")) or {}
    torrent = _best_torrent(movie.get("torrents") or [])
    if not torrent:
        return None
    return {
        "title": movie.get("title") or title,
        "year": movie.get("year") or year,
        "hash": (torrent.get("hash") or "").lower(),
        "magnet": _magnet_from_torrent(torrent),
        "quality": torrent.get("quality") or "",
        "source": "yts",
    }


def _movie_from_yts_list(payload, title, year):
    movies = ((payload.get("data") or {}).get("movies")) or []
    if not movies:
        return None
    chosen = movies[0]
    if year:
        for movie in movies:
            if str(movie.get("year")) == str(year):
                chosen = movie
                break
    torrent = _best_torrent(chosen.get("torrents") or [])
    if not torrent:
        return None
    return {
        "title": chosen.get("title") or title,
        "year": chosen.get("year") or year,
        "hash": (torrent.get("hash") or "").lower(),
        "magnet": _magnet_from_torrent(torrent),
        "quality": torrent.get("quality") or "",
        "source": "yts",
    }


def find_movie_magnet(title, year=None, imdb_id=None):
    errors = []
    if imdb_id:
        imdb_id = imdb_id if imdb_id.startswith("tt") else "tt{0}".format(str(imdb_id).zfill(7))
        query = urllib.parse.urlencode({"imdb_id": imdb_id})
        urls = ["{0}/movie_details.json?{1}".format(root, query) for root in YTS_API_ROOTS]
        try:
            source = _movie_from_yts_payload(_request_json_first(urls), title, year)
            if source:
                return source
        except ResolverError as exc:
            errors.append(str(exc))

    params = {"query_term": title, "limit": 5}
    if year:
        params["year"] = year
    query = urllib.parse.urlencode(params)
    urls = ["{0}/list_movies.json?{1}".format(root, query) for root in YTS_API_ROOTS]
    try:
        source = _movie_from_yts_list(_request_json_first(urls), title, year)
        if source:
            return source
    except ResolverError as exc:
        errors.append(str(exc))

    fallback = _source_from_apibay(title, year=year, prefer_tv=False)
    if fallback:
        return fallback

    detail = errors[-1] if errors else "No torrent source found."
    if any("403" in item for item in errors):
        detail = (
            "Torrent lookup sites blocked this request. "
            "Try My Kids Library for titles already on Real-Debrid, "
            "or add the movie at real-debrid.com first."
        )
    raise ResolverError("No torrent source found for {0}. {1}".format(title, detail))


def find_tv_magnet(title, year=None):
    fallback = _source_from_apibay(title, year=year, prefer_tv=True)
    if fallback:
        return fallback
    raise ResolverError(
        "No TV torrent source found for {0}. Add the series to Real-Debrid from the web app, "
        "then try My Kids Library.".format(title)
    )


def hash_from_magnet(magnet):
    match = re.search(r"btih:([a-fA-F0-9]{40})", magnet or "")
    return match.group(1).lower() if match else ""
