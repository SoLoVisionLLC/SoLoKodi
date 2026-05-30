# SoLoKodi Kids Build

The Kids build is the first profile in the SoLoKodi family. It prioritizes
**maximum kid content** from official Kodi sources with a fun, colorful theme.

## Sources

All add-ons install from the **official Kodi repository** — no third-party
repos required.

| Favourite shortcut | Add-on ID | Notes |
|--------------------|-----------|-------|
| PBS Kids | `plugin.video.pbskids` | US public broadcasting |
| TVO Kids | `plugin.video.tvokids` | Canada |
| YouTube | `plugin.video.youtube` | General; curate via subscriptions |
| Pluto TV | `plugin.video.plutotv` | Free live channels incl. kids |
| NASA Space | `plugin.video.nasa` | Educational space content |
| ESA Space | `plugin.video.esa` | European Space Agency |
| CBeebies and CBBC | `plugin.video.iplayerwww` | UK only |
| Die Maus | `plugin.video.wdrmaus` | German classic |
| ZDF Tivi | `plugin.video.zdftivi` | German kids VOD |

## Theme

Setup applies:

- **Skin:** `skin.bello.10` (colorful tile-based UI from official repo)
- **Accent colors:** bright blue (`FF42A5F5`) and orange (`FFFF7043`)

Restart Kodi after setup to see the full theme.

## Setup Flow

1. Install `repository.solokodi` from the hosted ZIP (`repository.solokodi-0.4.0.zip`).
2. Install `plugin.program.solokodi.setup` from the SoLoKodi repo.
3. Open **SoLoKodi Kids Setup** and run **Setup Wizard**.
4. Restart Kodi.
5. Use **Check for Updates** or **Update Build Now** to stay current.

See [wizard-and-updates.md](wizard-and-updates.md) for the full wizard and update system.

## Guardrails Removed

Previous versions included mandatory parent-lock checklists and anti-piracy
warnings that blocked the kids-first experience. v0.2.0 removes those:

- Setup dialog is welcoming, not restrictive
- Parent tips are optional, not auto-shown after setup
- Landing page focuses on what's included, not legal boundaries
- No source filtering — all official kids add-ons are installed

Optional Real-Debrid remains available via **Kids Real-Debrid**
(`plugin.video.solokodi.kidsrd`). See [kids-real-debrid.md](kids-real-debrid.md).

## Adding More Sources

Edit `KIDS_ADDONS` in
`src/plugin.program.solokodi.setup/resources/lib/setup.py` and rebuild:

```bash
python3 scripts/build_repo.py
python3 scripts/verify_repo.py
```

Each entry is a tuple of `(addon_id, install_label, favourite_name)`.
