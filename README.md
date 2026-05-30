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

## Local Preview

```bash
docker build -t solokodi-kids .
docker run --rm -p 8080:80 solokodi-kids
```

Open `http://localhost:8080`.

## Optional Real-Debrid

Parents can connect Real-Debrid via the device authorization flow. Tokens stay
local in the Kodi profile. This is optional and not required for any kids
source in the build.

## More Builds

Sports, movies, and other SoLoKodi profiles are planned. Each build will have
its own sources, theme, and setup profile.
