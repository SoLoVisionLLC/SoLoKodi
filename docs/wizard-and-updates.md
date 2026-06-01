# Setup Wizard & Update System

SoLoKodi uses a **guided setup wizard** and a **hosted build manifest** to
make installation easy and keep builds current.

## Build Chooser (first launch)

Open **SoLoKodi Setup** in Kodi. On first launch — before any build is
installed — a **visual build chooser** appears (no build is selected by
default). Each build is shown as a card with art, version, and a tagline:

| Build | Tagline | Needs Real-Debrid |
|-------|---------|-------------------|
| **SoLoKodi Kids** | Safe, colorful, kid-first Kodi. | No |
| **SoLoTV** | Stream everything. SoLo simple. | Recommended |

Pick a build to launch its guided setup wizard. You can re-open the chooser
anytime from the dashboard via **Change Build**.

## Setup Wizard

After a build is chosen, the dashboard shows your progress and offers these
actions:

| Action | Purpose |
|--------|---------|
| **Run Setup Wizard** | Guided install from start to finish |
| **Change Build** | Re-open the build chooser to switch builds |
| **Build Status** | Checklist of required and optional steps |
| **Check for Updates** | Compare local install vs hosted manifest |
| **Update Build Now** | Install latest repo, add-ons, theme, shortcuts |
| **Change Kids Skin** *(Kids)* | Switch between Bello and Nimbus |
| **Open SoLoTV Build Wizard** *(SoLoTV)* | Install/update the Xenon interface |
| **Repair Build** | Re-sync add-ons, theme, and favourites without changing RD/TMDb |
| **Connect Real-Debrid** | Device-code authorization for Real-Debrid |
| **Authorize Trakt** | Device-code authorization for Trakt |
| **Set TMDb API Key** | Save the TMDb key used for metadata lookup |
| **Maintenance** | Clear cache/packages/thumbnails, reset build, force close |

### Maintenance tools

The **Maintenance** menu provides Diggz-style upkeep without touching your
credentials:

| Tool | What it does |
|------|--------------|
| **Clear Cache** | Deletes temporary cache files |
| **Clear Packages** | Removes downloaded add-on `.zip` install files |
| **Clear Thumbnails** | Clears cached artwork (rebuilds automatically) |
| **Reset SoLoKodi Build** | Clears build selection + setup progress (keeps Real-Debrid/Trakt/TMDb) |
| **Force Close Kodi** | Closes Kodi to apply skin/build changes cleanly |

### Wizard steps (Kids build v1.3.0)

1. **Install kids sources** — official Kodi add-ons (PBS, TVO, YouTube, etc.)
2. **Install SoLoKodi add-ons** — Kids Real-Debrid from the SoLoKodi repo
3. **Choose kids theme** — Bello or Nimbus skin + bright accent colors
4. **Create shortcuts and home menu** — favourites plus Bello or Nimbus menu items for every kids source
5. **Connect Real-Debrid** *(optional)* — device authorization flow
6. **Add TMDb API key** *(optional)* — for Kids Real-Debrid discovery

### Wizard steps (SoLoTV build v1.0.5)

1. **Install SoLoTV repository** - adds the streaming repository
2. **Install SoLoTV Build Wizard** - installs and patches the wizard
3. **Create SoLoTV shortcuts** - favourites for setup and the build wizard
4. **Connect Real-Debrid** *(optional)* - device authorization flow
5. **Authorize Trakt** *(optional)* - device authorization flow
6. **Add TMDb API key** *(optional)* - metadata support
7. **Install SoLoTV interface** - opens the SoLoTV Build Wizard

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
4. Push to GitHub — Coolify rebuilds the Docker image (mirrors SoLoTV catalog + serves `public/`)
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
