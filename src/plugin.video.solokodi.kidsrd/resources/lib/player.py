import xbmc
import xbmcgui

from .constants import VIDEO_EXTENSIONS
from .kids_filter import titles_match
from .rd_client import RealDebridClient, RealDebridError
from .resolver import ResolverError, find_movie_magnet, hash_from_magnet


def _video_files(files):
    selected = []
    for item in files or []:
        path = (item.get("path") or "").lower()
        if any(path.endswith(ext) for ext in VIDEO_EXTENSIONS):
            selected.append(item)
    return sorted(selected, key=lambda item: int(item.get("bytes") or 0), reverse=True)


def _pick_link_for_file(links, files, file_id):
    if not links:
        return ""
    file_ids = [item.get("id") for item in files or [] if any((item.get("path") or "").lower().endswith(ext) for ext in VIDEO_EXTENSIONS)]
    if not file_ids:
        return links[0]
    try:
        index = file_ids.index(file_id)
        return links[index] if index < len(links) else links[0]
    except ValueError:
        return links[0]


class KidsPlayer:
    def __init__(self):
        self.rd = RealDebridClient()

    def play_torrent_id(self, torrent_id):
        info = self.rd.get_torrent(torrent_id)
        return self._play_torrent_info(info)

    def play_download_link(self, link, filename=""):
        direct = self.rd.unrestrict_link(link)
        stream = direct.get("download") or direct.get("link")
        if not stream:
            raise RealDebridError("Real-Debrid did not return a playable link.")
        _play_url(stream, filename or direct.get("filename") or "Kids Video")
        return True

    def play_movie(self, title, year=None, imdb_id=None):
        library_match = self.find_library_match(title, year)
        if library_match:
            return self.play_torrent_id(library_match["id"])

        progress = xbmcgui.DialogProgress()
        progress.create("SoLoKodi Kids RD", "Finding {0}...".format(title))
        try:
            source = find_movie_magnet(title, year=year, imdb_id=imdb_id)
            progress.update(25, "Checking Real-Debrid cache...")
            info_hash = source.get("hash") or hash_from_magnet(source.get("magnet"))
            if info_hash:
                self.rd.instant_available(info_hash)

            progress.update(45, "Adding to Real-Debrid...")
            added = self.rd.add_magnet(source["magnet"])
            torrent_id = added.get("id")
            if not torrent_id:
                raise RealDebridError("Real-Debrid did not accept this magnet.")

            progress.update(60, "Selecting video files...")
            info = self.rd.get_torrent(torrent_id)
            video_files = _video_files(info.get("files") or [])
            if not video_files:
                raise RealDebridError("No video files found in this torrent.")
            self.rd.select_files(torrent_id, [video_files[0]["id"]])

            progress.update(80, "Preparing stream...")
            info = self.rd.wait_for_links(torrent_id)
            progress.close()
            return self._play_torrent_info(info)
        except (ResolverError, RealDebridError):
            progress.close()
            raise
        except Exception:
            progress.close()
            raise

    def play_tv_from_library(self, title):
        match = self.find_library_match(title)
        if not match:
            raise RealDebridError(
                "{0} is not in your Real-Debrid library yet. Add the show there, then try again.".format(title)
            )
        return self.play_torrent_id(match["id"])

    def find_library_match(self, title, year=None):
        torrents = self.rd.list_torrents() or []
        year_text = str(year) if year else ""
        best = None
        for torrent in torrents:
            torrent_title = torrent.get("filename") or torrent.get("original_filename") or ""
            if titles_match(title, torrent_title):
                if year_text and year_text not in torrent_title:
                    continue
                best = torrent
                break
        return best

    def _play_torrent_info(self, info):
        links = info.get("links") or []
        files = info.get("files") or []
        if not links:
            video_files = _video_files(files)
            if video_files and info.get("id"):
                self.rd.select_files(info["id"], [video_files[0]["id"]])
                info = self.rd.wait_for_links(info["id"], timeout=180)
                links = info.get("links") or []
                files = info.get("files") or []

        if not links:
            raise RealDebridError("No playable links are ready for this title yet.")

        video_files = _video_files(files)
        file_id = video_files[0]["id"] if video_files else None
        link = _pick_link_for_file(links, files, file_id)
        filename = info.get("filename") or info.get("original_filename") or "Kids Video"
        return self.play_download_link(link, filename=filename)


def _play_url(url, title):
    item = xbmcgui.ListItem(path=url, label=title)
    item.setInfo("video", {"title": title})
    xbmc.Player().play(item, False)
