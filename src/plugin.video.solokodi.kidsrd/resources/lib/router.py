import sys
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from .kids_filter import looks_like_kids_content
from .player import KidsPlayer
from .rd_client import RealDebridAuthError, RealDebridClient, RealDebridError
from .resolver import ResolverError
from .tmdb_client import TmdbClient, TmdbError

ADDON = xbmcaddon.Addon()
ADDON_URL = sys.argv[0]
HANDLE = int(sys.argv[1])
ADDON_ID = ADDON.getAddonInfo("id")


def build_url(**params):
    return ADDON_URL + "?" + urllib.parse.urlencode(params)


def end_directory():
    xbmcplugin.setContent(HANDLE, "videos")
    xbmcplugin.endOfDirectory(HANDLE)


def notify(message):
    xbmcgui.Dialog().notification("SoLoKodi Kids RD", message, xbmcgui.NOTIFICATION_INFO, 4000)


def require_real_debrid():
    try:
        RealDebridClient().get_user()
        return True
    except RealDebridAuthError as exc:
        xbmcgui.Dialog().ok(
            "Real-Debrid Required",
            "{0}\n\nOpen SoLoKodi Kids Setup and choose Connect Real-Debrid.".format(exc),
        )
        return False
    except RealDebridError as exc:
        xbmcgui.Dialog().ok("Real-Debrid Error", str(exc))
        return False


def add_folder(label, description, **params):
    url = build_url(**params)
    item = xbmcgui.ListItem(label=label)
    item.setInfo("video", {"title": label, "plot": description})
    xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)


def add_playable(label, description, art=None, **params):
    url = build_url(**params)
    item = xbmcgui.ListItem(label=label, path=url)
    item.setInfo("video", {"title": label, "plot": description})
    item.setProperty("IsPlayable", "true")
    if art:
        item.setArt(art)
    xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=False)


def show_root_menu():
    add_folder(
        "My Kids Library",
        "Movies and shows already in your Real-Debrid account, filtered for kids.",
        action="library_kids",
    )
    add_folder(
        "Discover Kids Movies",
        "Popular G and PG animated and family movies from TMDb.",
        action="discover_movies",
        page=1,
    )
    add_folder(
        "Discover Kids TV",
        "Popular kids and animation series from TMDb.",
        action="discover_tv",
        page=1,
    )
    add_folder(
        "All Real-Debrid Torrents",
        "Browse everything in your Real-Debrid torrent list.",
        action="library_all",
    )
    end_directory()


def show_library(kids_only):
    if not require_real_debrid():
        return

    rd = RealDebridClient()
    torrents = rd.list_torrents() or []
    downloads = rd.list_downloads() or []

    if not torrents and not downloads:
        xbmcgui.Dialog().ok("Kids Library", "Your Real-Debrid library is empty.")
        return

    item_count = 0
    for torrent in torrents:
        title = torrent.get("filename") or torrent.get("original_filename") or "Torrent"
        if kids_only and not looks_like_kids_content(title):
            continue
        status = torrent.get("status") or "unknown"
        add_playable(
            title,
            "Status: {0}".format(status),
            action="play_torrent",
            torrent_id=torrent.get("id"),
        )
        item_count += 1

    for download in downloads:
        title = download.get("filename") or "Download"
        if kids_only and not looks_like_kids_content(title):
            continue
        add_playable(
            title,
            "Direct download from Real-Debrid.",
            action="play_download",
            link=download.get("download") or download.get("link"),
        )
        item_count += 1

    if kids_only and item_count == 0:
        xbmcgui.Dialog().ok(
            "Kids Library",
            "Nothing in your Real-Debrid account matched kids keywords yet. "
            "Try Discover Kids Movies or add family titles to Real-Debrid first.",
        )
    end_directory()


def show_discover_movies(page):
    if not require_real_debrid():
        return

    try:
        payload = TmdbClient().discover_kids_movies(page=page)
    except TmdbError as exc:
        xbmcgui.Dialog().ok("TMDb Setup", str(exc))
        return

    for movie in payload.get("results") or []:
        title = movie.get("title") or "Movie"
        year = (movie.get("release_date") or "")[:4]
        label = "{0} ({1})".format(title, year) if year else title
        plot = movie.get("overview") or ""
        poster = TmdbClient.poster_url(movie.get("poster_path"))
        add_playable(
            label,
            plot,
            art={"thumb": poster, "poster": poster},
            action="play_movie",
            tmdb_id=movie.get("id"),
        )

    total_pages = int(payload.get("total_pages") or 1)
    if page < total_pages:
        add_folder("Next page", "More kids movies", action="discover_movies", page=page + 1)
    end_directory()


def show_discover_tv(page):
    if not require_real_debrid():
        return

    try:
        payload = TmdbClient().discover_kids_tv(page=page)
    except TmdbError as exc:
        xbmcgui.Dialog().ok("TMDb Setup", str(exc))
        return

    for show in payload.get("results") or []:
        title = show.get("name") or "Series"
        year = (show.get("first_air_date") or "")[:4]
        label = "{0} ({1})".format(title, year) if year else title
        plot = show.get("overview") or ""
        poster = TmdbClient.poster_url(show.get("poster_path"))
        add_playable(
            label,
            plot,
            art={"thumb": poster, "poster": poster},
            action="play_tv",
            tmdb_id=show.get("id"),
        )

    total_pages = int(payload.get("total_pages") or 1)
    if page < total_pages:
        add_folder("Next page", "More kids TV", action="discover_tv", page=page + 1)
    end_directory()


def handle_play_movie(tmdb_id):
    if not require_real_debrid():
        return
    try:
        details = TmdbClient().movie_details(tmdb_id)
        title = details.get("title") or "Movie"
        year = (details.get("release_date") or "")[:4] or None
        imdb_id = ((details.get("external_ids") or {}).get("imdb_id")) or None
        KidsPlayer().play_movie(title, year=year, imdb_id=imdb_id)
        notify("Playing {0}".format(title))
    except (TmdbError, RealDebridError, ResolverError) as exc:
        xbmcgui.Dialog().ok("Playback", str(exc))


def handle_play_tv(tmdb_id):
    if not require_real_debrid():
        return
    try:
        details = TmdbClient().tv_details(tmdb_id)
        title = details.get("name") or "Series"
        KidsPlayer().play_tv_from_library(title)
        notify("Playing {0}".format(title))
    except (TmdbError, RealDebridError) as exc:
        xbmcgui.Dialog().ok("Playback", str(exc))


def handle_play_torrent(torrent_id):
    if not require_real_debrid():
        return
    try:
        KidsPlayer().play_torrent_id(torrent_id)
    except RealDebridError as exc:
        xbmcgui.Dialog().ok("Playback", str(exc))


def handle_play_download(link):
    if not require_real_debrid():
        return
    try:
        KidsPlayer().play_download_link(link)
    except RealDebridError as exc:
        xbmcgui.Dialog().ok("Playback", str(exc))


def run():
    params = urllib.parse.parse_qs(sys.argv[2][1:])
    action = params.get("action", ["menu"])[0]
    page = int(params.get("page", ["1"])[0])

    if action == "library_kids":
        show_library(kids_only=True)
    elif action == "library_all":
        show_library(kids_only=False)
    elif action == "discover_movies":
        show_discover_movies(page)
    elif action == "discover_tv":
        show_discover_tv(page)
    elif action == "play_movie":
        handle_play_movie(params.get("tmdb_id", [""])[0])
    elif action == "play_tv":
        handle_play_tv(params.get("tmdb_id", [""])[0])
    elif action == "play_torrent":
        handle_play_torrent(params.get("torrent_id", [""])[0])
    elif action == "play_download":
        handle_play_download(params.get("link", [""])[0])
    else:
        show_root_menu()
