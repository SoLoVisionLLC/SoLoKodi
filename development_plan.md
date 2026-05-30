# Development Plan

## Vision

SoLoKodi is a **family of Kodi builds** — each tuned for a different situation
(kids, sports, movies, etc.) with its own sources, theme, setup wizard, and
update manifest.

## Completed

### SoLoKodi Kids Build (v1.3.0)

- [x] Install all official kids sources from the Kodi repository (9 add-ons)
- [x] Generate favourites shortcuts for every kids source
- [x] Pre-configure Bello home menu and TV/Movies submenus with kids add-ons
- [x] Force Bello skinshortcuts rebuild (hash invalidation + widget properties)
- [x] Pre-configure Nimbus home menu widgets via `script.nimbus.helper`
- [x] Choose Bello or Nimbus skin during setup; switch later from setup menu
- [x] Apply colorful theme and bright accent colors
- [x] Kid-themed landing page with playful design
- [x] Guided setup wizard with progress and optional steps
- [x] Build status dashboard and repair flow
- [x] Hosted manifest + embedded manifest for update checks
- [x] Update Build Now — sync repo, add-ons, theme, shortcuts
- [x] Daily update check service with Kodi notification
- [x] Kodi 21 settings format (control tags) for setup and kidsrd add-ons
- [x] Build script MD5 checksum matches on-disk `addons.xml` (CRLF-safe)
- [x] Repo verification ensures embedded `kids.json` is packaged in setup ZIP
- [x] Skin activation confirms Kodi dialog and verifies active skin (Bello)

### SoLoKodi Kids Real-Debrid (v0.2.0)

- [x] Custom `plugin.video.solokodi.kidsrd` add-on
- [x] Reads RD tokens from setup wizard (with token refresh)
- [x] Kids-filtered RD library browser with episode/file picker
- [x] TMDb discover for G/PG movies and kids TV
- [x] Movie playback via RD cache + YTS/fallback magnet resolver
- [x] TV playback via RD library match + torrent search fallback
- [x] Real-Debrid status screen (premium time + TMDb key)

## Next Up

- [ ] Add-on icons and fanart for SoLoKodi repo branding
- [ ] Curated YouTube playlist deep-links (kids channels by ID)
- [ ] CI pipeline to build, verify, and deploy on push
- [ ] Second build profile (e.g. sports or movies)

## Build Profiles

| Profile | Status | Manifest |
|---------|--------|----------|
| **Kids** | v1.3.0 | `/builds/kids/manifest.json` |
| Sports | Planned | `/builds/sports/manifest.json` |
| Movies | Planned | `/builds/movies/manifest.json` |
