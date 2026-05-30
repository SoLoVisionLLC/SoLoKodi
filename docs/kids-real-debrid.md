# SoLoKodi Kids Real-Debrid Add-on

`plugin.video.solokodi.kidsrd` streams kids and family content through a
connected Real-Debrid account. It reads RD tokens from **SoLoKodi Kids Setup**
— no separate RD login required.

## Setup

1. Run **Kids Build Setup** (installs this add-on automatically).
2. In **SoLoKodi Kids Setup**, choose **Connect Real-Debrid**.
3. Open **Kids Real-Debrid** settings and add a free [TMDb API key](https://www.themoviedb.org/settings/api).
4. Open **Kids Real-Debrid** from favourites or the setup menu.

## Menu Sections

| Section | What it does |
|---------|----------------|
| **My Kids Library** | Plays torrents/downloads already in your RD account, filtered by kids keywords |
| **Discover Kids Movies** | Browses popular G/PG animation and family movies (TMDb) |
| **Discover Kids TV** | Browses kids and animation series (TMDb) |
| **All Real-Debrid Torrents** | Unfiltered view of your RD torrent list |

## Playback Flow

### Movies

1. Check your RD library for a title match → play if found.
2. Otherwise look up a magnet via YTS (using TMDb/IMDb metadata).
3. Add to Real-Debrid, select the largest video file, unrestrict, and play.

### TV shows

TV discovery matches against your existing RD library by title. Add series
torrents to Real-Debrid first, then pick them from **Discover Kids TV** or
**My Kids Library**.

## Architecture

```
plugin.program.solokodi.setup   → stores RD OAuth tokens
plugin.video.solokodi.kidsrd    → reads tokens, TMDb browse, RD playback
```

Key modules under `resources/lib/`:

- `rd_client.py` — Real-Debrid API + token refresh
- `tmdb_client.py` — Kids movie/TV discovery
- `resolver.py` — Magnet lookup for movies
- `player.py` — Select files, unrestrict, play
- `kids_filter.py` — Keyword filter for library browsing

## Development

```bash
python3 scripts/build_repo.py
python3 scripts/verify_repo.py
```

The add-on is bundled in the SoLoKodi repository ZIP (`repository.solokodi-0.4.2.zip`).
