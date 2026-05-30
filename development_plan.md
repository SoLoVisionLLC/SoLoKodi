# Development Plan

## Vision

SoLoKodi is a **family of Kodi builds** — each tuned for a different situation
(kids, sports, movies, etc.) with its own sources, theme, and setup wizard.

## Completed

### SoLoKodi Kids Build (v0.2.0)

- [x] Install all official kids sources from the Kodi repository (9 add-ons)
- [x] Generate favourites shortcuts for every kids source
- [x] Apply colorful Bello skin and bright accent colors
- [x] Remove restrictive guardrails (no mandatory lock checklist, no piracy warnings)
- [x] Kid-themed landing page with playful design
- [x] Rename from "Family Build" to "Kids Build" across repo and add-on metadata

### SoLoKodi Kids Real-Debrid (v0.1.0)

- [x] Custom `plugin.video.solokodi.kidsrd` add-on
- [x] Reads RD tokens from setup wizard (with token refresh)
- [x] Kids-filtered RD library browser
- [x] TMDb discover for G/PG movies and kids TV
- [x] Movie playback via RD cache + magnet resolver
- [x] Wired into kids setup, favourites, and repo v0.3.0

## Next Up

- [ ] Add-on icons and fanart for SoLoKodi repo branding
- [ ] Curated YouTube playlist deep-links (kids channels by ID)
- [ ] TV show magnet resolver (currently library-match only)
- [ ] Automate Kodi profile creation via JSON-RPC
- [ ] Second build profile (e.g. sports or movies)
- [ ] CI pipeline to build and deploy on push

## Build Profiles (Planned)

| Profile | Status | Focus |
|---------|--------|-------|
| **Kids** | Done (v0.2.0) | Cartoons, learning, space, free kids TV |
| Sports | Planned | Live sports sources |
| Movies | Planned | Personal media + RD |
| Default | Planned | General-purpose SoLoVision build |
