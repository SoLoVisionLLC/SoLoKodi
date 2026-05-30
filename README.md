# SoLoKodi Family Build

SoLoKodi is a kid-focused Kodi repository and setup add-on served as a static
site. It provides a locked-down setup workflow, official kid-safe add-on
shortcuts, and parent-managed Real-Debrid device authorization for lawful
personal media workflows.

## What It Ships

- `repository.solokodi`: Kodi repository add-on that points Kodi at the hosted
  repository feed.
- `plugin.program.solokodi.setup`: Kodi program add-on for family setup,
  official PBS Kids/YouTube installation, Real-Debrid device authorization, and
  parent lock guidance.
- Static download site and Kodi repository feed under `/repo`.

## Build

```bash
python3 scripts/build_repo.py
python3 scripts/verify_repo.py
```

## Local Preview

```bash
docker build -t solokodi-family .
docker run --rm -p 8080:80 solokodi-family
```

Open `http://localhost:8080`.

## Real-Debrid Boundary

The add-on uses Real-Debrid's official OAuth device flow and stores tokens only
inside the local Kodi profile after the parent authorizes the device. It does
not include third-party piracy add-ons, provider scrapers, torrent search, or a
shared API token.
