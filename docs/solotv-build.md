# SoLoTV Build

SoLoTV is a **SoLo-branded Kodi streaming build** based on the same add-on catalog as the popular Xenon stack. It does **not** install `repository.diggz` or show Diggz branding during setup.

## Full catalog mirror

| Layer | SoLoTV approach |
|-------|-----------------|
| **Repository add-on** | `repository.solotv` — points at `https://solokodi.sololink.cloud/solotv/repo/` |
| **Catalog list** | SoLo-branded `addons.xml` (Diggz repository add-ons **removed**) |
| **Add-on packages** | All ~58 packages downloaded, metadata patched, hosted on your CDN |
| **Build wizard** | `plugin.program.chef21` ZIP patched → **SoLoTV Build Wizard** |
| **Skins** | Display names rebranded (e.g. Diggz Xenon → SoLoTV Xenon); add-on ids unchanged for compatibility |

Generate / refresh the mirror:

```bash
python scripts/mirror_solotv_repo.py          # full download + patch
python scripts/mirror_solotv_repo.py --force  # re-download everything
python scripts/mirror_solotv_repo.py --xml-only  # catalog XML only
```

Mirrored ZIPs are gitignored (large). They are **not** pushed to GitHub; they are created during the Docker image build (see below).

## Our own SoLoTV build (Diggz foundation, rebranded)

Instead of pointing the Build Wizard at Diggz's build list, SoLoTV ships **our
own build**, seeded from the Diggz AIO foundation and rebranded by SoLoVision.
We maintain it going forward.

| Piece | Where |
|-------|-------|
| **Build config** | `src/solotv_build/build.json` — name, version, foundation source URL(s), wizard source URLs |
| **Branding overrides** | `src/solotv_build/overrides/` — drop-in file replacements (images/binaries) keyed by in-build path |
| **Pipeline** | `scripts/build_solotv_build.py` |
| **Build list** | `public/solotv/builds.xml` (generated) — our `<build>` entries point at our zips |
| **Build zip** | `public/solotv/builds/solotv-<version>-<kodi>.zip` (generated, gitignored, large) |
| **Wizard text** | `public/solotv/notify.txt`, `videos.txt`, `changelog.txt` |

What the pipeline does:

1. Downloads the foundation build zip (cached in `work/`, with archive.org fallback).
2. Rebrands all text files (Diggz → SoLoTV / SoLoVision) and applies any file
   overrides from `src/solotv_build/overrides/`.
3. Repoints the **bundled** `plugin.program.chef21/uservar.py` to our hosted
   `builds.xml`/`notify`/`videos`/`changelog` (and drops its stale `.pyc`) so the
   restored build never falls back to Diggz endpoints.
4. Repackages to `public/solotv/builds/` and writes our `builds.xml`.

The installed SoLoKodi Setup add-on **also** repoints the live wizard
(`solotv_repo.repoint_wizard_sources`, driven by `streaming_repo` URLs in
`src/builds/solotv.json`) immediately after install/launch.

```bash
python scripts/build_solotv_build.py --inspect K21   # list branded paths/images to rebrand
python scripts/build_solotv_build.py K21             # build the K21 target
python scripts/build_solotv_build.py                 # build every target in build.json
python scripts/build_solotv_build.py --xml-only      # only (re)write builds.xml + wizard text
```

**Rebranding images:** run `--inspect` to find branded assets (e.g.
`addons/resource.images.skinbackgrounds.xenon/resources/Diggz/diggz.png`), then
drop replacements at the same relative path under `src/solotv_build/overrides/`.

## Deploy (Coolify)

This site is served from the repo **Dockerfile** (`nginx` + `public/`). Coolify redeploys when you push to the connected branch (typically `main`).

On each build, Docker runs:

1. `python scripts/mirror_solotv_repo.py` — download and rebrand ~58 catalog ZIPs (invoked by `build_repo.py`)
2. `python scripts/build_repo.py` — SoLoKodi repo ZIPs, manifests, `repository.solotv` zip
3. `python scripts/verify_repo.py`
4. `python scripts/build_solotv_build.py ${SOLOTV_TARGETS}` — rebranded SoLoTV build(s) + `builds.xml` (defaults to `K21`; downloads ~166MB each)

The first deploy after a catalog change can take a few minutes while ZIPs download. You do **not** need to rsync `public/` by hand unless you bypass Coolify.

**Push to deploy:** commit source changes → `git push` → wait for Coolify build → verify:

```bash
curl -s https://solokodi.sololink.cloud/solotv/repo/addons.xml | grep repository.diggz
# (no output = good)

curl -I https://solokodi.sololink.cloud/solotv/repo/plugin.program.chef21/plugin.program.chef21-502.zip
# HTTP 200
```

Local dev without Coolify: `docker build -t solokodi .` then `docker run --rm -p 8080:80 solokodi`.

## Install

1. Install **repository.solokodi** from [solokodi.sololink.cloud](https://solokodi.sololink.cloud).
2. Install **SoLoKodi Setup**.
3. In the **build chooser**, pick **SoLoTV**, then run the setup wizard.
4. Wizard steps (all SoLo-branded in UI):
   - Install **SoLoTV repository** (not Diggz)
   - Install **SoLoTV Build Wizard**
   - Create shortcuts
   - Optional Real-Debrid
   - Open wizard → pick **SoLoTV 4K** (our own build)

## Build locally (optional)

```bash
python scripts/mirror_solotv_repo.py   # SoLoTV addons.xml + ZIPs
python scripts/build_repo.py         # ZIPs + manifests
python scripts/verify_repo.py
```

Production: push to GitHub and let Coolify run the same steps inside Docker.

## File source for manual install

- URL: `https://solokodi.sololink.cloud/solotv/`
- ZIP: `repository.solotv-1.0.1.zip`

## Legal

Upstream add-ons remain the work of their authors. SoLoTV provides branded repository metadata, setup automation, and post-install wizard renaming. Review licenses before hosting a full package mirror on your CDN.
