# SoLoKodi is deployed via Coolify from this Git repo (Dockerfile).
# Push to the branch Coolify watches (usually main); the image build runs:
#   mirror_solotv_repo.py -> build_repo.py -> verify_repo.py
#
# Manual override only if you host outside Coolify:
#   $env:SOLOKODI_DEPLOY_CMD = 'rsync -avz --delete ./ user@host:/var/www/solokodi/public/'
#   .\scripts\deploy_public.ps1

param(
    [string]$DeployTarget = $env:SOLOKODI_DEPLOY_CMD
)

$Root = Split-Path $PSScriptRoot -Parent

if (-not $DeployTarget) {
    Write-Host "Coolify deploy: commit and push to GitHub; Coolify rebuilds from Dockerfile."
    Write-Host "Local test: docker build -t solokodi `"$Root`" ; docker run --rm -p 8080:80 solokodi"
    Write-Host "Local mirror only: python scripts/build_repo.py"
    exit 0
}

Push-Location (Join-Path $Root "public")
Invoke-Expression $DeployTarget
Pop-Location
Write-Host "Manual deploy finished."
