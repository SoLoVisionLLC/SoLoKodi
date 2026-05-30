# Setup Wizard & Update System

SoLoKodi uses a **guided setup wizard** and a **hosted build manifest** to
make installation easy and keep builds current.

## Setup Wizard

Open **SoLoKodi Kids Setup** in Kodi. The dashboard shows your progress and
offers these actions:

| Action | Purpose |
|--------|---------|
| **Run Setup Wizard** | Guided install from start to finish |
| **Build Status** | Checklist of required and optional steps |
| **Check for Updates** | Compare local install vs hosted manifest |
| **Update Build Now** | Install latest repo, add-ons, theme, shortcuts |
| **Repair Build** | Re-sync add-ons, theme, and favourites without changing RD/TMDb |

### Wizard steps (Kids build v1.1.0)

1. **Install kids sources** — official Kodi add-ons (PBS, TVO, YouTube, etc.)
2. **Install SoLoKodi add-ons** — Kids Real-Debrid from the SoLoKodi repo
3. **Apply fun theme** — Bello skin + bright accent colors
4. **Create home shortcuts** — favourites for every source
5. **Connect Real-Debrid** *(optional)* — device authorization flow
6. **Add TMDb API key** *(optional)* — for Kids Real-Debrid discovery

## Update System

### How it works

1. **Source of truth:** `src/builds/kids.json` defines the build profile
2. **Build step:** `python3 scripts/build_repo.py` generates:
   - `public/builds/kids/manifest.json` — hosted for remote checks
   - `resources/builds/kids.json` — embedded in the setup add-on (offline fallback)
3. **Kodi checks:** setup add-on fetches the remote manifest and compares:
   - Build version (`build.version`)
   - Repository version (`repository.version`)
   - SoLoKodi add-on versions (`solokodi_addons`, `setup_addon`)
4. **Apply:** **Update Build Now** updates the repo, add-ons, theme, and shortcuts

### Manifest URL

```
https://solokodi.sololink.cloud/builds/kids/manifest.json
```

### Auto-check on startup

The setup add-on runs a background service that checks for updates once per
day (after setup is complete) and shows a Kodi notification when updates are
available.

## Releasing a new build version

1. Edit `src/builds/kids.json` — bump `version`, add/remove sources, change theme
2. Bump add-on versions in `src/*/addon.xml` as needed
3. Run:
   ```bash
   python3 scripts/build_repo.py
   python3 scripts/verify_repo.py
   ```
4. Deploy the `public/` folder to `solokodi.sololink.cloud`
5. Users tap **Update Build Now** in Kodi (or get the daily notification)

### Version numbers

| Version | Meaning |
|---------|---------|
| `build.version` in `kids.json` | Profile version (sources, theme, wizard steps) |
| `repository.solokodi` version | Repo add-on zip |
| Individual add-on versions | Setup, Kids RD, etc. |

Bump `build.version` when the profile definition changes. Bump add-on versions
when their code changes.

## Adding a new build profile (future)

1. Create `src/builds/sports.json` (copy kids.json as template)
2. Re-run `build_repo.py` — manifests generate for every file in `src/builds/`
3. Add profile selection to the wizard when multiple profiles ship
