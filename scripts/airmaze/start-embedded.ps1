#requires -Version 5.1
<#
.SYNOPSIS
  Start (or restart) the Dragon AI Agent embedded gateway container.

.NOTES
  Fixes PATH for Docker Desktop CLI under common install locations.
  Does not open the Docker Desktop dashboard.
#>

[CmdletBinding()]
param(
    [string]$InstallRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}

function Fix-DockerPath {
    $binDirs = @(
        (Join-Path $env:ProgramFiles "Docker\Docker\resources\bin"),
        (Join-Path $env:LOCALAPPDATA "Docker\resources\bin")
    )
    foreach ($d in $binDirs) {
        if ((Test-Path -LiteralPath $d) -and ($env:PATH -notlike "*$d*")) {
            $env:PATH = "$d;$env:PATH"
            Write-Host "[Dragon AI Agent] PATH += $d"
        }
    }
}

Fix-DockerPath

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "docker not found on PATH. Start Docker Desktop (tray) and retry."
}

$compose = Join-Path $InstallRoot "docker-compose.embedded.yml"
if (-not (Test-Path -LiteralPath $compose)) {
    throw "Missing $compose — run install.ps1 first."
}

$data = Join-Path $env:USERPROFILE ".hermes-airmaze-embedded"
if (-not (Test-Path $data)) { New-Item -ItemType Directory -Force -Path $data | Out-Null }
$env:HERMES_EMBEDDED_DATA = $data

Push-Location $InstallRoot
try {
    Write-Host "[Dragon AI Agent] docker compose pull..."
    docker compose -f docker-compose.embedded.yml pull
    Write-Host "[Dragon AI Agent] docker compose up -d..."
    docker compose -f docker-compose.embedded.yml up -d
    docker compose -f docker-compose.embedded.yml ps
    Write-Host "[Dragon AI Agent] Gateway: 127.0.0.1:8642  dashboard: http://127.0.0.1:9119"
} finally {
    Pop-Location
}
