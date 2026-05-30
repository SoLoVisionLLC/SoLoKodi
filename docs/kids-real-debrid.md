# SoLoKodi Kids Real-Debrid Add-on

`plugin.video.solokodi.kidsrd` streams kids and family content through a
connected Real-Debrid account. It reads RD tokens from **SoLoKodi Kids Setup**
— no separate RD login required.

## Setup

1. Run **Kids Build Setup** (installs this add-on automatically).
2. In **SoLoKodi Kids Setup**, choose **Connect Real-Debrid**.
3. Open **Kids Real-Debrid** settings and add a free [TMDb API key](https://www.themoviedb.org/settings/api).
4. Open **Kids Real-Debrid** from favourites or the setup menu.
5. Check **Real-Debrid Status** in the add-on menu to confirm premium time and TMDb.

## Menu Sections

| Section | What it does |
|---------|----------------|
| **Real-Debrid Status** | Shows username, premium time left, and TMDb key status |
| **My Kids Library** | RD torrents/downloads filtered by kids keywords — pick a title, then pick a file/episode |
| **Discover Kids Movies** | Popular G/PG animation and family movies (TMDb) |
| **Discover Kids TV** | Popular kids and animation series (TMDb) — searches RD cache, then torrent sources |
| **All Real-Debrid Torrents** | Unfiltered view of your RD torrent list |

## Playback Flow

### Movies

1. Check your RD library for a title match → play if found.
2. Look up a magnet via YTS (using TMDb/IMDb metadata).
3. If YTS fails, search public torrent metadata (Apibay) as a fallback.
4. Add to Real-Debrid, select video files, unrestrict, and play.

### TV shows

1. Check your RD library for a title match.
2. If not cached, search for a family/TV torrent pack and add it to Real-Debrid.
3. If the torrent has multiple video files, choose the episode or file to play.

## Architecture

```
plugin.program.solokodi.setup   → stores RD OAuth tokens
plugin.video.solokodi.kidsrd    → reads tokens, TMDb browse, RD playback
```

Key modules under `resources/lib/`:

- `rd_client.py` — Real-Debrid API + token refresh
- `tmdb_client.py` — Kids movie/TV discovery
- `resolver.py` — Magnet lookup (YTS + Apibay fallback)
- `player.py` — Select files, unrestrict, play
- `kids_filter.py` — Keyword filter for library browsing

## Development

```bash
python3 scripts/build_repo.py
python3 scripts/verify_repo.py
```

The add-on is bundled in the SoLoKodi repository ZIP (`repository.solokodi-0.4.8.zip`).
