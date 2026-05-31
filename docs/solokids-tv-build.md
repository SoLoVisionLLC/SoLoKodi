# SoLoKids TV Build

SoLoKids TV is a kid-friendly clone of the SoLoTV streaming build. It uses the
same full streaming foundation and Real-Debrid-ready add-ons, but the build
list, setup copy, artwork, and home shortcuts are branded for kids.

## What Is Different From SoLoKodi Kids

SoLoKodi Kids is the official-source profile: PBS Kids, TVO Kids, Pluto TV,
NASA, and other kid add-ons from the Kodi repository.

SoLoKids TV is a streaming build: it restores a rebranded SoLoTV-style
interface and expects Real-Debrid for playback. It does not add family Trakt
playlist menus.

## Build Assets

| Piece | Where |
|-------|-------|
| Build profile | `src/builds/solokids-tv.json` |
| Build package config | `src/solokids_tv_build/build.json` |
| Kid-friendly card art | `src/plugin.program.solokodi.setup/resources/media/cards/solokids-tv.png` |
| In-build image overrides | `src/solokids_tv_build/overrides/` |
| Hosted build list | `public/solokids-tv/builds.xml` |

## Local Build

```bash
python scripts/build_repo.py
python scripts/build_solotv_build.py --profile solokids-tv --xml-only
python scripts/build_solotv_build.py --profile solokids-tv K21
python scripts/verify_repo.py
```

Docker builds SoLoTV and SoLoKids TV during deploy. Use `SOLOKIDS_TV_TARGETS`
to limit Kodi targets when needed.
