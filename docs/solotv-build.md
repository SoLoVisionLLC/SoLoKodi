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

## Deploy (Coolify)

This site is served from the repo **Dockerfile** (`nginx` + `public/`). Coolify redeploys when you push to the connected branch (typically `main`).

On each build, Docker runs:

1. `python scripts/mirror_solotv_repo.py` — download and rebrand ~58 catalog ZIPs
2. `python scripts/build_repo.py` — SoLoKodi repo ZIPs, manifests, `repository.solotv` zip
3. `python scripts/verify_repo.py`

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
3. **Switch to SoLoTV** and run the setup wizard.
4. Wizard steps (all SoLo-branded in UI):
   - Install **SoLoTV repository** (not Diggz)
   - Install **SoLoTV Build Wizard**
   - Create shortcuts
   - Optional Real-Debrid
   - Open wizard → pick Xenon 4K (Debrid or Free)

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
