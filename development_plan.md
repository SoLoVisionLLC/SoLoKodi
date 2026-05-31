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
- [x] v0.3.7 — install ivarbrandt repo from zip (fixes Nimbus not appearing in skin list)
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

### SoLoKodi Kids Real-Debrid (v0.2.1)

- [x] Custom `plugin.video.solokodi.kidsrd` add-on
- [x] Reads RD tokens from setup wizard (with token refresh)
- [x] Kids-filtered RD library browser with episode/file picker
- [x] TMDb discover for G/PG movies and kids TV
- [x] Movie playback via RD cache + YTS/fallback magnet resolver
- [x] TV playback via RD library match + torrent search fallback
- [x] Real-Debrid status screen (premium time + TMDb key)
- [x] v0.2.1 — always call `endOfDirectory` on empty/error paths (fixes library browse failures)
- [x] v0.2.1 — remove `IsPlayable` on plugin action items (fixes “skipping unplayable item” on Discover)
- [x] v0.2.3 — Modern Kids TV browse (2015+), IMDB TV search, relaxed torrent matching

### SoLoKodi Setup (v0.5.1) — SoLoTV install fix

- [x] Install `repository.solotv` via `InstallAddon` from the installed SoLoKodi repo
      (was failing on `InstallZip` from a file source — required "Unknown sources")
- [x] Hosted-zip install kept as a fallback only
- [x] First-run build picker renders a proper plugin directory (no `GetDirectory` error)

### SoLoKodi Setup (v0.5.0) — Build chooser & maintenance

- [x] Visual **build chooser** (rich `useDetails` cards w/ art, version, tagline) — no Kids default
- [x] First-run detection: picker shown until a build is chosen
- [x] **Change Build** action on the dashboard re-opens the chooser
- [x] **Maintenance** menu — clear cache, clear packages, clear thumbnails, reset build, force close
- [x] Branded build-card art (`resources/media/cards/kids.png`, `solotv.png`)
- [x] De-kids-ified shared wizard strings (build-agnostic progress/dialogs)
- [x] Removed legacy `diggz_*` aliases and dead `run_family_setup`/`show_lock_checklist`
- [x] `streaming_repo.repository_zip` auto-derived from repo add-on version at build time (no hardcoded version)

### SoLoTV Build (v1.0.3)

- [x] Build manifest `src/builds/solotv.json`
- [x] `repository.solotv` — SoLo-branded repo (not `repository.diggz`)
- [x] SoLo-branded `addons.xml` mirror at `/solotv/repo/`
- [x] SoLoTV Build Wizard — post-install metadata patch (`plugin.program.chef21`)
- [x] Setup wizard UI — no “Installing Diggz repository” messaging
- [x] Profile switcher (Kids ↔ SoLoTV) in setup add-on
- [x] Landing page at `/solotv/`
- [x] Full CDN mirror of catalog ZIPs (`scripts/mirror_solotv_repo.py`) — 58 packages, Diggz repos excluded, ZIP metadata patched
- [x] Docker build runs full SoLoTV mirror (Coolify deploy on `git push`)
- [ ] **Push** latest `main` and confirm Coolify build succeeds (live CDN may still be pre-mirror until redeploy)

## Next Up
- [ ] Add-on icons and fanart for SoLoKodi repo branding
- [ ] Curated YouTube playlist deep-links (kids channels by ID)
- [ ] CI pipeline to build, verify, and deploy on push
- [ ] Sports build profile

## Build Profiles

| Profile | Status | Manifest |
|---------|--------|----------|
| **Kids** | v1.3.1 | `/builds/kids/manifest.json` |
| **SoLoTV** | v1.0.3 | `/builds/solotv/manifest.json` |
| Sports | Planned | `/builds/sports/manifest.json` |
