# SoLoKodi Kids Real-Debrid Add-on

`plugin.video.solokodi.kidsrd` streams kids and family content through a
connected Real-Debrid account. It reads Real-Debrid authorization from
SoLoKodi Kids Setup and uses the add-on TMDb setting for discovery metadata.

## Setup

1. Run Kids Build Setup; it installs this add-on automatically.
2. In SoLoKodi Kids Setup, choose Connect Real-Debrid.
3. Save a free [TMDb API key](https://www.themoviedb.org/settings/api).
4. Open Kids Real-Debrid from favourites or the setup menu.
5. Check Real-Debrid Status in the add-on menu to confirm premium time and TMDb.

## Menu Sections

| Section | What it does |
|---------|--------------|
| Real-Debrid Status | Shows username, premium time left, and TMDb key status |
| My Kids Library | RD torrents/downloads filtered by kids keywords; pick a title, then pick a file/episode |
| Discover Kids Movies | Popular G/PG animation and family movies from TMDb |
| Discover Kids TV | Popular kids and animation series from TMDb; searches RD cache, then torrent sources |
| All Real-Debrid Torrents | Unfiltered view of your RD torrent list |

## Playback Flow

### Movies

1. Check your RD library for a title match and play if found.
2. Look up a magnet via YTS using TMDb/IMDb metadata.
3. If YTS fails, search public torrent metadata as a fallback.
4. Add to Real-Debrid, select video files, unrestrict, and play.

### TV Shows

1. Check your RD library for a title match.
2. If not cached, search for a family/TV torrent pack and add it to Real-Debrid.
3. If the torrent has multiple video files, choose the episode or file to play.

## Architecture

```text
plugin.program.solokodi.setup -> stores RD credentials
plugin.video.solokodi.kidsrd  -> reads RD credentials, browses TMDb, plays via RD
```

Key modules under `resources/lib/`:

- `rd_client.py` - Real-Debrid API and token refresh
- `tmdb_client.py` - Kids movie/TV discovery and metadata lookup
- `resolver.py` - Magnet lookup
- `player.py` - Select files, unrestrict, play
- `kids_filter.py` - Keyword filter for library browsing

## Development

```bash
python3 scripts/build_repo.py
python3 scripts/verify_repo.py
```

The add-on is bundled in the SoLoKodi repository ZIP.
