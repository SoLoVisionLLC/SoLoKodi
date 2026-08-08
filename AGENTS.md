# AI Agent Guidelines for SoLoKodi

## Dual Local & Repository Updates
- **Mandatory Dual-Sync**: Whenever making changes or bug fixes to add-ons, scripts, or modules in the repository (`src/`), **always** apply the updates to both:
  1. The repository source files in `src/` (and commit them to git).
  2. The local Kodi installation directories in `%APPDATA%\Kodi\addons\` (e.g., `%APPDATA%\Kodi\addons\plugin.program.solokodi.setup\`, `%APPDATA%\Kodi\addons\script.module.acctmgr\`, etc.).
- When testing or applying fixes directly to the local Kodi `%APPDATA%` installation, ensure the changes are mirrored back into `src/` so they are packaged and published to GitHub.

## General Guidelines
- **UI Thread Safety**: Never block Kodi's main UI thread with synchronous network requests or heavy operations (such as multi-repo scans) during modal user interactions.
- **Repository Verification**: Run `python3 scripts/verify_repo.py` to ensure all secret checks, XML definitions, and package structures pass before committing or pushing changes.
