# Development Plan

## Vision

SoLoKodi is a **family of Kodi builds** — each tuned for a different situation
(kids, sports, movies, etc.) with its own sources, theme, setup wizard, and
update manifest.

## Completed

### SoLoKodi Kids Build (v1.1.0)

- [x] Install all official kids sources from the Kodi repository (9 add-ons)
- [x] Generate favourites shortcuts for every kids source
- [x] Apply colorful Bello skin and bright accent colors
- [x] Kid-themed landing page with playful design
- [x] Guided setup wizard with progress and optional steps
- [x] Build status dashboard and repair flow
- [x] Hosted manifest + embedded manifest for update checks
- [x] Update Build Now — sync repo, add-ons, theme, shortcuts
- [x] Daily update check service with Kodi notification

### SoLoKodi Kids Real-Debrid (v0.1.0)

- [x] Custom `plugin.video.solokodi.kidsrd` add-on
- [x] Reads RD tokens from setup wizard (with token refresh)
- [x] Kids-filtered RD library browser
- [x] TMDb discover for G/PG movies and kids TV
- [x] Movie playback via RD cache + magnet resolver

## Next Up

- [ ] Add-on icons and fanart for SoLoKodi repo branding
- [ ] Curated YouTube playlist deep-links (kids channels by ID)
- [ ] TV show magnet resolver (currently library-match only)
- [ ] CI pipeline to build, verify, and deploy on push
- [ ] Second build profile (e.g. sports or movies)

## Build Profiles

| Profile | Status | Manifest |
|---------|--------|----------|
| **Kids** | v1.1.0 | `/builds/kids/manifest.json` |
| Sports | Planned | `/builds/sports/manifest.json` |
| Movies | Planned | `/builds/movies/manifest.json` |
