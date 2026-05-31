import os

import xbmc
import xbmcgui

from .constants import VIDEO_EXTENSIONS
from .kids_filter import titles_match
from .rd_client import RealDebridClient, RealDebridError
from .resolver import ResolverError, find_movie_magnet, find_tv_magnet, hash_from_magnet


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
    file_ids = [
        item.get("id")
        for item in files or []
        if any((item.get("path") or "").lower().endswith(ext) for ext in VIDEO_EXTENSIONS)
    ]
    if not file_ids:
        return links[0]
    try:
        index = file_ids.index(file_id)
        return links[index] if index < len(links) else links[0]
    except ValueError:
        return links[0]


def _play_url(url, title):
    item = xbmcgui.ListItem(path=url, label=title)
    item.setInfo("video", {"title": title})
    xbmc.Player().play(item, False)


class KidsPlayer:
    def __init__(self):
        self.rd = RealDebridClient()

    def list_video_files(self, torrent_id):
        info = self.rd.get_torrent(torrent_id)
        return _video_files(info.get("files") or []), info

    def play_torrent_id(self, torrent_id, file_id=None):
        info = self.rd.get_torrent(torrent_id)
        video_files = _video_files(info.get("files") or [])
        if file_id is None and len(video_files) == 1:
            file_id = video_files[0]["id"]
        if file_id is not None:
            self.rd.select_files(torrent_id, [file_id])
            info = self.rd.wait_for_links(torrent_id)
            return self._play_torrent_info(info, preferred_file_id=file_id)
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
            progress.update(70, "Starting stream...")
            result = self._play_magnet_source(source, progress=progress)
            progress.close()
            return result
        except (ResolverError, RealDebridError):
            progress.close()
            raise
        except Exception:
            progress.close()
            raise

    def play_tv(self, title, year=None, imdb_id=None):
        library_match = self.find_library_match(title, year)
        if library_match:
            return self.play_torrent_id(library_match["id"])

        progress = xbmcgui.DialogProgress()
        progress.create("SoLoKodi Kids RD", "Finding {0}...".format(title))
        try:
            source = find_tv_magnet(title, year=year, imdb_id=imdb_id)
            progress.update(70, "Starting stream...")
            result = self._play_magnet_source(source, progress=progress)
            progress.close()
            return result
        except (ResolverError, RealDebridError):
            progress.close()
            raise
        except Exception:
            progress.close()
            raise

    def find_library_match(self, title, year=None):
        torrents = self.rd.list_torrents() or []
        year_text = str(year) if year else ""
        title_match = None
        for torrent in torrents:
            torrent_title = torrent.get("filename") or torrent.get("original_filename") or ""
            if not titles_match(title, torrent_title):
                continue
            if year_text and year_text in torrent_title:
                return torrent
            if title_match is None:
                title_match = torrent
        return title_match

    def _play_magnet_source(self, source, progress=None):
        if progress:
            progress.update(25, "Checking Real-Debrid cache...")
        info_hash = source.get("hash") or hash_from_magnet(source.get("magnet"))
        if info_hash:
            self.rd.instant_available(info_hash)

        if progress:
            progress.update(45, "Adding to Real-Debrid...")
        added = self.rd.add_magnet(source["magnet"])
        torrent_id = added.get("id")
        if not torrent_id:
            raise RealDebridError("Real-Debrid did not accept this magnet.")

        if progress:
            progress.update(60, "Selecting video files...")
        info = self.rd.get_torrent(torrent_id)
        video_files = _video_files(info.get("files") or [])
        if not video_files:
            raise RealDebridError("No video files found in this torrent.")
        if len(video_files) == 1:
            self.rd.select_files(torrent_id, [video_files[0]["id"]])
            if progress:
                progress.update(80, "Preparing stream...")
            info = self.rd.wait_for_links(torrent_id)
            return self._play_torrent_info(info, preferred_file_id=video_files[0]["id"])
        return torrent_id

    def _play_torrent_info(self, info, preferred_file_id=None):
        links = info.get("links") or []
        files = info.get("files") or []
        if not links:
            video_files = _video_files(files)
            if video_files and info.get("id"):
                selected = preferred_file_id or video_files[0]["id"]
                self.rd.select_files(info["id"], [selected])
                info = self.rd.wait_for_links(info["id"], timeout=180)
                links = info.get("links") or []
                files = info.get("files") or []
                preferred_file_id = selected

        if not links:
            raise RealDebridError("No playable links are ready for this title yet.")

        video_files = _video_files(files)
        file_id = preferred_file_id or (video_files[0]["id"] if video_files else None)
        link = _pick_link_for_file(links, files, file_id)
        filename = info.get("filename") or info.get("original_filename") or "Kids Video"
        if file_id and video_files:
            for item in video_files:
                if item.get("id") == file_id and item.get("path"):
                    filename = os.path.basename(item["path"])
                    break
        return self.play_download_link(link, filename=filename)
