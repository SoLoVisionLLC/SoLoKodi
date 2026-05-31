# SoLoTV Build

SoLoTV is a **SoLo-branded Kodi build** based on the [Diggz repository](https://diggz1.me/diggzrepo) and **Chef Omega Wizard** (`plugin.program.chef21`). It delivers the Xenon 4K experience (movies, TV, live TV, sports, Debrid) with SoLoKodi setup, updates, and shortcuts.

## What SoLoTV includes

| Piece | Source |
|-------|--------|
| Diggz repository | [diggz1.me/diggzrepo](https://diggz1.me/diggzrepo) — `Diggz_Repo.zip` |
| Build wizard | Chef Omega Wizard from `repository.diggz` |
| Interface | Xenon 4K (Debrid or Free) — installed inside Chef wizard |
| SoLo layer | `plugin.program.solokodi.setup` with profile `solotv` |

Real-Debrid and streaming addons are configured **inside the Chef / Xenon wizard**, not by SoLoKodi directly.

## Install (new Kodi profile)

1. Install **repository.solokodi** from [solokodi.sololink.cloud](https://solokodi.sololink.cloud).
2. Install **SoLoKodi Setup** from the SoLoKodi repository.
3. Open **SoLoKodi Setup → Switch to SoLoTV** (or run with `?action=init_solotv`).
4. Complete the **SoLoTV Setup Wizard**:
   - Install Diggz repository
   - Install Chef Omega Wizard
   - Create SoLoTV favourites
   - (Optional) Connect Real-Debrid
   - Open Chef wizard and install **Xenon 4K**
5. Restart Kodi when Xenon finishes.

## Branding

- Accent color: `#1565C0` (SoLoTV blue)
- Favourites: **SoLoTV Setup**, **Chef Omega Wizard**
- Setup wizard title: **SoLoTV Setup**

## Manifest

- Source: `src/builds/solotv.json`
- Hosted: `/builds/solotv/manifest.json`

## Legal note

Diggz Xenon, its addons, and third-party repositories are maintained by their respective authors. SoLoTV only automates installing the official Diggz repo URL and applying SoLo branding on top.
