import sys
import urllib.parse
import os

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


def finish_directory(succeeded=True):
    xbmcplugin.setContent(HANDLE, "videos")
    xbmcplugin.endOfDirectory(HANDLE, succeeded=succeeded)


def end_directory():
    finish_directory(succeeded=True)


def notify(message):
    xbmcgui.Dialog().notification("SoLoKodi Kids RD", message, xbmcgui.NOTIFICATION_INFO, 4000)


def _premium_seconds(user):
    try:
        return int(user.get("premium") or 0)
    except (TypeError, ValueError):
        return 0


def require_real_debrid():
    try:
        user = RealDebridClient().get_user()
    except RealDebridAuthError as exc:
        xbmcgui.Dialog().ok(
            "Real-Debrid Required",
            "{0}\n\nOpen SoLoKodi Kids Setup and choose Connect Real-Debrid.".format(exc),
        )
        return False
    except RealDebridError as exc:
        xbmcgui.Dialog().ok("Real-Debrid Error", str(exc))
        return False

    if _premium_seconds(user) <= 0:
        xbmcgui.Dialog().ok(
            "Real-Debrid Subscription",
            "Your Real-Debrid account is connected as {0}, but premium time is not active.\n\n"
            "Renew at real-debrid.com, then try again.".format(user.get("username", "unknown")),
        )
        return False
    return True


def add_folder(label, description, **params):
    url = build_url(**params)
    item = xbmcgui.ListItem(label=label)
    item.setInfo("video", {"title": label, "plot": description})
    xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)


def add_action(label, description, art=None, **params):
    url = build_url(**params)
    item = xbmcgui.ListItem(label=label)
    item.setInfo("video", {"title": label, "plot": description})
    if art:
        item.setArt(art)
    xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=False)


def show_status():
    try:
        user = RealDebridClient().get_user()
    except RealDebridAuthError as exc:
        xbmcgui.Dialog().ok("Real-Debrid Status", str(exc))
        finish_directory(succeeded=False)
        return
    except RealDebridError as exc:
        xbmcgui.Dialog().ok("Real-Debrid Status", str(exc))
        finish_directory(succeeded=False)
        return

    premium = _premium_seconds(user)
    tmdb_ready = bool(ADDON.getSetting("tmdb_api_key"))
    lines = [
        "User: {0}".format(user.get("username", "unknown")),
        "Account type: {0}".format(user.get("type", "unknown")),
        "Premium seconds remaining: {0}".format(premium),
        "TMDb key saved: {0}".format("yes" if tmdb_ready else "no — add one in this add-on settings"),
        "",
        "Discover Movies/TV needs a free TMDb API key.",
        "Playback uses your Real-Debrid cache first, then searches for family titles.",
    ]
    xbmcgui.Dialog().ok("Real-Debrid Status", "\n".join(lines))
    finish_directory(succeeded=False)


def show_root_menu():
    status_line = "Check Real-Debrid connection and TMDb setup"
    try:
        user = RealDebridClient().get_user()
        premium = _premium_seconds(user)
        if premium > 0:
            hours = max(1, premium // 3600)
            status_line = "Connected as {0} — about {1} hours of premium left".format(
                user.get("username", "unknown"),
                hours,
            )
        else:
            status_line = "Connected as {0}, but premium is not active".format(user.get("username", "unknown"))
    except RealDebridError:
        status_line = "Real-Debrid is not connected — use SoLoKodi Setup"

    add_folder("Real-Debrid Status", status_line, action="status")
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
        "Popular kids, family, and animation series from TMDb.",
        action="discover_tv",
        page=1,
    )
    add_folder(
        "Modern Kids TV (2015+)",
        "Recent kids and family series — Bluey, Gabby's Dollhouse, and more.",
        action="discover_tv_modern",
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
        finish_directory(succeeded=False)
        return

    rd = RealDebridClient()
    try:
        torrents = rd.list_torrents() or []
        downloads = rd.list_downloads() or []
    except RealDebridError as exc:
        xbmcgui.Dialog().ok("Real-Debrid Library", str(exc))
        finish_directory(succeeded=False)
        return

    if not torrents and not downloads:
        xbmcgui.Dialog().ok(
            "Real-Debrid Library",
            "Your Real-Debrid library is empty.\n\n"
            "Try Discover Kids Movies, or add family titles at real-debrid.com first.",
        )
        finish_directory(succeeded=False)
        return

    item_count = 0
    skipped = 0
    for torrent in torrents:
        title = torrent.get("filename") or torrent.get("original_filename") or "Torrent"
        if kids_only and not looks_like_kids_content(title):
            skipped += 1
            continue
        status = torrent.get("status") or "unknown"
        add_folder(
            title,
            "Status: {0} — choose a video file to play".format(status),
            action="torrent_files",
            torrent_id=torrent.get("id"),
        )
        item_count += 1

    for download in downloads:
        title = download.get("filename") or "Download"
        if kids_only and not looks_like_kids_content(title):
            skipped += 1
            continue
        add_action(
            title,
            "Direct download from Real-Debrid.",
            action="play_download",
            link=download.get("download") or download.get("link"),
        )
        item_count += 1

    if item_count == 0:
        if kids_only and skipped:
            xbmcgui.Dialog().ok(
                "Kids Library",
                "You have {0} Real-Debrid item(s), but none matched kids keywords.\n\n"
                "Try All Real-Debrid Torrents, or use Discover Kids Movies.".format(skipped),
            )
        else:
            xbmcgui.Dialog().ok("Kids Library", "Nothing matched this view yet.")
        finish_directory(succeeded=False)
        return
    end_directory()


def show_torrent_files(torrent_id):
    if not require_real_debrid():
        finish_directory(succeeded=False)
        return

    player = KidsPlayer()
    try:
        video_files, info = player.list_video_files(torrent_id)
    except RealDebridError as exc:
        xbmcgui.Dialog().ok("Real-Debrid", str(exc))
        finish_directory(succeeded=False)
        return

    if not video_files:
        xbmcgui.Dialog().ok("Real-Debrid", "No video files are available in this torrent yet.")
        finish_directory(succeeded=False)
        return

    title = info.get("filename") or info.get("original_filename") or "Torrent"
    if len(video_files) == 1:
        try:
            player.play_torrent_id(torrent_id, file_id=video_files[0]["id"])
            notify("Playing {0}".format(title))
        except RealDebridError as exc:
            xbmcgui.Dialog().ok("Playback", str(exc))
        finish_directory(succeeded=False)
        return

    for video in video_files:
        path = video.get("path") or "Video"
        label = os.path.basename(path)
        size_mb = int(int(video.get("bytes") or 0) / (1024 * 1024))
        plot = "{0} — {1} MB".format(title, size_mb) if size_mb else title
        add_action(
            label,
            plot,
            action="play_torrent_file",
            torrent_id=torrent_id,
            file_id=video.get("id"),
        )
    end_directory()


def show_discover_movies(page):
    if not require_real_debrid():
        finish_directory(succeeded=False)
        return

    try:
        payload = TmdbClient().discover_kids_movies(page=page)
    except TmdbError as exc:
        xbmcgui.Dialog().ok("TMDb Setup", str(exc))
        finish_directory(succeeded=False)
        return

    for movie in payload.get("results") or []:
        title = movie.get("title") or "Movie"
        year = (movie.get("release_date") or "")[:4]
        label = "{0} ({1})".format(title, year) if year else title
        plot = movie.get("overview") or ""
        poster = TmdbClient.poster_url(movie.get("poster_path"))
        add_action(
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


def show_discover_tv(page, modern_only=False):
    if not require_real_debrid():
        finish_directory(succeeded=False)
        return

    try:
        payload = TmdbClient().discover_kids_tv(page=page, modern_only=modern_only)
    except TmdbError as exc:
        xbmcgui.Dialog().ok("TMDb Setup", str(exc))
        finish_directory(succeeded=False)
        return

    for show in payload.get("results") or []:
        title = show.get("name") or "Series"
        year = (show.get("first_air_date") or "")[:4]
        label = "{0} ({1})".format(title, year) if year else title
        plot = (show.get("overview") or "") + (
            "\n\nChecks your Real-Debrid library first, then searches for a torrent."
        )
        poster = TmdbClient.poster_url(show.get("poster_path"))
        add_action(
            label,
            plot,
            art={"thumb": poster, "poster": poster},
            action="play_tv",
            tmdb_id=show.get("id"),
        )

    total_pages = int(payload.get("total_pages") or 1)
    next_action = "discover_tv_modern" if modern_only else "discover_tv"
    if page < total_pages:
        add_folder(
            "Next page",
            "More kids TV",
            action=next_action,
            page=page + 1,
        )
    end_directory()


def handle_play_movie(tmdb_id):
    if not require_real_debrid():
        return
    try:
        details = TmdbClient().movie_details(tmdb_id)
        title = details.get("title") or "Movie"
        year = (details.get("release_date") or "")[:4] or None
        imdb_id = ((details.get("external_ids") or {}).get("imdb_id")) or None
        result = KidsPlayer().play_movie(title, year=year, imdb_id=imdb_id)
        if isinstance(result, str):
            show_torrent_files(result)
            return
        notify("Playing {0}".format(title))
    except (TmdbError, RealDebridError, ResolverError) as exc:
        xbmcgui.Dialog().ok("Playback", str(exc))


def handle_play_tv(tmdb_id):
    if not require_real_debrid():
        return
    try:
        details = TmdbClient().tv_details(tmdb_id)
        title = details.get("name") or "Series"
        year = (details.get("first_air_date") or "")[:4] or None
        imdb_id = ((details.get("external_ids") or {}).get("imdb_id")) or None
        result = KidsPlayer().play_tv(title, year=year, imdb_id=imdb_id)
        if isinstance(result, str):
            show_torrent_files(result)
            return
        notify("Playing {0}".format(title))
    except (TmdbError, RealDebridError, ResolverError) as exc:
        xbmcgui.Dialog().ok("Playback", str(exc))


def handle_play_torrent(torrent_id):
    show_torrent_files(torrent_id)


def handle_play_torrent_file(torrent_id, file_id):
    if not require_real_debrid():
        return
    try:
        KidsPlayer().play_torrent_id(torrent_id, file_id=file_id)
        notify("Starting playback")
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

    if action == "status":
        show_status()
    elif action == "library_kids":
        show_library(kids_only=True)
    elif action == "library_all":
        show_library(kids_only=False)
    elif action == "discover_movies":
        show_discover_movies(page)
    elif action == "discover_tv":
        show_discover_tv(page, modern_only=False)
    elif action == "discover_tv_modern":
        show_discover_tv(page, modern_only=True)
    elif action == "torrent_files":
        show_torrent_files(params.get("torrent_id", [""])[0])
    elif action == "play_movie":
        handle_play_movie(params.get("tmdb_id", [""])[0])
    elif action == "play_tv":
        handle_play_tv(params.get("tmdb_id", [""])[0])
    elif action == "play_torrent":
        handle_play_torrent(params.get("torrent_id", [""])[0])
    elif action == "play_torrent_file":
        handle_play_torrent_file(
            params.get("torrent_id", [""])[0],
            params.get("file_id", [""])[0],
        )
    elif action == "play_download":
        handle_play_download(params.get("link", [""])[0])
    else:
        show_root_menu()
