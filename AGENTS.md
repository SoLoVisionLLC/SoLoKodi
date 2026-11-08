# AI Agent Guidelines for SoLoKodi

## Dual Local & Repository Updates
- **Mandatory Dual-Sync**: Whenever making changes or bug fixes to add-ons, scripts, or modules in the repository (`src/`), **always** apply the updates to both:
  1. The repository source files in `src/` (and commit them to git).
  2. The local Kodi installation directories in `%APPDATA%\Kodi\addons\` (e.g., `%APPDATA%\Kodi\addons\plugin.program.solokodi.setup\`, `%APPDATA%\Kodi\addons\script.module.acctmgr\`, etc.).
- When testing or applying fixes directly to the local Kodi `%APPDATA%` installation, ensure the changes are mirrored back into `src/` so they are packaged and published to GitHub.

## General Guidelines
- **UI Thread Safety**: Never block Kodi's main UI thread with synchronous network requests or heavy operations (such as multi-repo scans) during modal user interactions.
- **Repository Verification**: Run `python3 scripts/verify_repo.py` to ensure all secret checks, XML definitions, and package structures pass before committing or pushing changes.

<!-- solo-skills:credentials:start -->
## Missing credentials: check SoLoVault
- For a missing key, token or password needed by an already authorized task, check existing environment variables, the local credentials folder and the OS secret store first. If it is still missing, check SoLoVault before stopping or asking the owner for the value.
- Read the `solovault-credentials` skill before using the vault. In a project clone, including Codex, read `.claude/skills/solovault-credentials/SKILL.md`; if absent, use the installed shared skill or its canonical source at `SoLoVisionLLC/solo-skills/claude-plugins/solo-skills/skills/solovault-credentials/SKILL.md`.
- Use the skill's `scripts/solovault-run.sh` helper to pass a value directly into the authorized command. Never print secrets, commit them, put them in command arguments or expose plaintext through `solovault-agent get` or MCP `read_entry`.
- If the existing agent key or entry cannot be found, or the vault returns `BAD_KEY` or `DENIED`, stop that operation and report the missing credential by name only. Do not create credentials, expand access or bypass a denial to unblock it.
- This is lookup guidance only. It does not authorize credential creation or rotation, permission changes, external transmission, production deployment or any otherwise unapproved action. Repository-specific restrictions always win: preserve read-only tasks and synthetic-only development; when real credentials or real vault data are forbidden, do not access them.
<!-- solo-skills:credentials:end -->
