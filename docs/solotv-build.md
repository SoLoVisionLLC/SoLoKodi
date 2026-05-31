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

Mirrored ZIPs are gitignored (large). Deploy the entire `public/solotv/repo/` folder to your web host.

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

## Build / deploy

```bash
python scripts/mirror_solotv_repo.py   # SoLoTV addons.xml on public/solotv/repo/
python scripts/build_repo.py         # ZIPs + manifests
python scripts/verify_repo.py
```

Deploy `public/` including `public/solotv/` and `public/solotv/repo/addons.xml`.

## File source for manual install

- URL: `https://solokodi.sololink.cloud/solotv/`
- ZIP: `repository.solotv-1.0.1.zip`

## Legal

Upstream add-ons remain the work of their authors. SoLoTV provides branded repository metadata, setup automation, and post-install wizard renaming. Review licenses before hosting a full package mirror on your CDN.
