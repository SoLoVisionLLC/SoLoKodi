# SoLoTV Build

SoLoTV is a **SoLo-branded Kodi streaming build** based on the same add-on catalog as the popular Xenon stack. It does **not** install `repository.diggz` or show Diggz branding during setup.

## What is cloned vs what is mirrored

| Layer | SoLoTV approach |
|-------|-----------------|
| **Repository add-on** | `repository.solotv` — SoLoVision branding |
| **Catalog list** | SoLo-branded `addons.xml` hosted at `/solotv/repo/` |
| **Add-on packages** | Downloaded from the upstream Omega mirror (same versions Xenon expects) |
| **Build wizard** | Same engine (`plugin.program.chef21`), metadata patched after install to read **SoLoTV Build Wizard** |
| **Interface (Xenon skin)** | Installed through the wizard; skin may still use Xenon artwork internally until we ship a forked skin ZIP |

We are **not** redistributing a renamed copy of every ZIP in git yet. The catalog is mirrored and rebranded at the metadata layer; packages are fetched from the upstream CDN at install time. A full offline mirror of all 60+ add-ons can be added to `scripts/mirror_solotv_repo.py` later if you want zero upstream dependency.

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
- ZIP: `repository.solotv-1.0.0.zip`

## Legal

Upstream add-ons remain the work of their authors. SoLoTV provides branded repository metadata, setup automation, and post-install wizard renaming. Review licenses before hosting a full package mirror on your CDN.
