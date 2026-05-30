# SoLoKodi Kids Build

SoLoKodi is a family of Kodi builds for different situations. **SoLoKodi Kids**
is the first profile — a fun, colorful setup that installs every official
kids source we could find from the Kodi repository.

## What the Kids Build Installs

| Source | Add-on | Content |
|--------|--------|---------|
| PBS Kids | `plugin.video.pbskids` | Arthur, Daniel Tiger, Wild Kratts |
| TVO Kids | `plugin.video.tvokids` | Canadian kids shows |
| YouTube | `plugin.video.youtube` | Kids channels and playlists |
| Pluto TV | `plugin.video.plutotv` | Free kids live channels |
| NASA | `plugin.video.nasa` | Space videos and live streams |
| ESA | `plugin.video.esa` | European Space Agency content |
| BBC iPlayer | `plugin.video.iplayerwww` | CBeebies & CBBC (UK) |
| WDR Maus | `plugin.video.wdrmaus` | Die Sendung mit der Maus |
| ZDF Tivi | `plugin.video.zdftivi` | German kids on-demand |

The setup wizard also applies the **Bello** skin with bright accent colors and
writes one-tap favourites for every source.

## What It Ships

- `repository.solokodi` — Kodi repository add-on pointing at the hosted feed.
- `plugin.program.solokodi.setup` — Kids build setup wizard.
- Static download site and Kodi repository feed under `/repo`.

## Build

```bash
python3 scripts/build_repo.py
python3 scripts/verify_repo.py
```

The build script also generates `public/builds/kids/manifest.json` for remote
update checks. See [docs/wizard-and-updates.md](docs/wizard-and-updates.md).

## Setup Wizard

Open **SoLoKodi Kids Setup** in Kodi:

1. **Run Setup Wizard** — guided install (sources, theme, shortcuts, RD, TMDb)
2. **Check for Updates** / **Update Build Now** — stay on the latest release
3. **Repair Build** — refresh add-ons and shortcuts without losing settings

## Local Preview

```bash
docker build -t solokodi-kids .
docker run --rm -p 8080:80 solokodi-kids
```

Open `http://localhost:8080`.

## Optional Real-Debrid

Parents can connect Real-Debrid via the device authorization flow. Tokens stay
local in the Kodi profile. The **SoLoKodi Kids Real-Debrid** add-on
(`plugin.video.solokodi.kidsrd`) uses those tokens to:

- Browse and play kids-filtered content from your RD library
- Discover G/PG kids movies and series via TMDb
- Stream cached titles through Real-Debrid when available

See [docs/kids-real-debrid.md](docs/kids-real-debrid.md) for setup details.

## More Builds

Sports, movies, and other SoLoKodi profiles are planned. Each build will have
its own sources, theme, and setup profile.
