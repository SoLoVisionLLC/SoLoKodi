# Upload the built public/ tree to solokodi.sololink.cloud.
# Set $DeployTarget to your host sync command (rsync, scp, rclone, etc.).
#
# Example (adjust user@host and remote path):
#   $DeployTarget = "rsync -avz --delete ./public/ user@sololink:/var/www/solokodi/"
#
# After deploy, verify:
#   curl -s https://solokodi.sololink.cloud/solotv/repo/addons.xml | findstr repository.diggz
#   (should return nothing)
#   curl -I https://solokodi.sololink.cloud/solotv/repo/plugin.program.chef21/plugin.program.chef21-502.zip
#   (should be HTTP 200)

param(
    [string]$DeployTarget = $env:SOLOKODI_DEPLOY_CMD
)

$Root = Split-Path $PSScriptRoot -Parent
if (-not $DeployTarget) {
    Write-Host "Set SOLOKODI_DEPLOY_CMD or edit scripts/deploy_public.ps1 with your rsync/scp command."
    Write-Host "Local mirror is ready under: $Root\public\solotv\repo\"
    Write-Host "Run: python scripts/mirror_solotv_repo.py ; python scripts/build_repo.py"
    exit 1
}

Push-Location (Join-Path $Root "public")
Invoke-Expression $DeployTarget
Pop-Location
Write-Host "Deploy command finished. Verify solotv/repo/addons.xml on the CDN."
