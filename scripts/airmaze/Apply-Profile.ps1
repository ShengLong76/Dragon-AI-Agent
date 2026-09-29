#requires -Version 5.1
<#
.SYNOPSIS
  Apply a Dragon AI Agent profile bundle (folder with profile.json) into local config.

.DESCRIPTION
  - Copies each bot to %LOCALAPPDATA%\hermes\profiles\<bot-id>\ (agent desktop profile picker path)
  - Copies connector templates to %LOCALAPPDATA%\DragonAIAgent\connectors\<profile-id>\
  - Records the active profile id under DragonAIAgent\active-profile.json

.PARAMETER ProfilePath
  Path to a profile folder containing profile.json (or the profile.json file itself).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProfilePath,
    [string]$InstallRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}

function Write-Dragon([string]$Message) {
    Write-Host "[Dragon AI Agent] $Message"
}

# Resolve profile directory
$p = $ProfilePath
if (Test-Path -LiteralPath $p -PathType Leaf) {
    if ([IO.Path]::GetFileName($p) -ieq "profile.json") {
        $profileDir = Split-Path $p -Parent
    } else {
        throw "Expected a profile folder or profile.json, got: $p"
    }
} else {
    $profileDir = (Resolve-Path -LiteralPath $p).Path
}

$manifestPath = Join-Path $profileDir "profile.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Missing profile.json in $profileDir"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$profileId = [string]$manifest.id
if ([string]::IsNullOrWhiteSpace($profileId)) { throw "profile.json missing id" }

Write-Dragon "Applying profile '$($manifest.displayName)' ($profileId)..."

# Desktop profile root (technical path used by the open-source agent desktop stack)
$desktopProfilesRoot = Join-Path $env:LOCALAPPDATA "hermes\profiles"
New-Item -ItemType Directory -Force -Path $desktopProfilesRoot | Out-Null

$bots = @($manifest.bots)
if ($bots.Count -eq 0) {
    Write-Dragon "WARNING: profile has no bots[] entries"
}

foreach ($bot in $bots) {
    $botId = [string]$bot.id
    if ([string]::IsNullOrWhiteSpace($botId)) { continue }
    $dest = Join-Path $desktopProfilesRoot $botId
    New-Item -ItemType Directory -Force -Path $dest | Out-Null

    $soulRel = [string]$bot.soul
    $cfgRel = [string]$bot.config
    if ($soulRel) {
        $soulSrc = Join-Path $profileDir ($soulRel -replace '/', '\')
        if (Test-Path -LiteralPath $soulSrc) {
            Copy-Item -LiteralPath $soulSrc -Destination (Join-Path $dest "SOUL.md") -Force
        } else {
            Write-Dragon "WARNING: missing SOUL at $soulSrc"
        }
    }
    if ($cfgRel) {
        $cfgSrc = Join-Path $profileDir ($cfgRel -replace '/', '\')
        if (Test-Path -LiteralPath $cfgSrc) {
            # Desktop historically reads profile.yaml; also keep bot.yaml
            Copy-Item -LiteralPath $cfgSrc -Destination (Join-Path $dest "bot.yaml") -Force
            Copy-Item -LiteralPath $cfgSrc -Destination (Join-Path $dest "profile.yaml") -Force
        }
    }
    # Mirror display metadata
    $meta = [ordered]@{
        id           = $botId
        display_name = [string]$bot.displayName
        description  = [string]$bot.description
        profile_id   = $profileId
    }
    ($meta | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath (Join-Path $dest "bot.meta.json") -Encoding UTF8
    Write-Dragon "Bot installed for picker: $botId -> $dest"
}

# Connectors -> DragonAIAgent
$connRoot = Join-Path $InstallRoot "connectors\$profileId"
New-Item -ItemType Directory -Force -Path $connRoot | Out-Null
$connDir = Join-Path $profileDir "connectors"
if (Test-Path -LiteralPath $connDir) {
    Copy-Item -Path (Join-Path $connDir "*") -Destination $connRoot -Force -Recurse
    Write-Dragon "Connector templates -> $connRoot"
}

foreach ($c in @($manifest.connectors)) {
    $tpl = [string]$c.configTemplate
    if (-not $tpl) { continue }
    $src = Join-Path $profileDir ($tpl -replace '/', '\')
    if (Test-Path -LiteralPath $src) {
        Copy-Item -LiteralPath $src -Destination (Join-Path $connRoot ([IO.Path]::GetFileName($src))) -Force
    }
}

# Keep a copy of the applied profile bundle under install root
$applied = Join-Path $InstallRoot "profiles\applied\$profileId"
New-Item -ItemType Directory -Force -Path $applied | Out-Null
Copy-Item -Path (Join-Path $profileDir "*") -Destination $applied -Force -Recurse

$active = [ordered]@{
    profileId    = $profileId
    displayName  = [string]$manifest.displayName
    appliedAt    = (Get-Date).ToString("o")
    bots         = @($bots | ForEach-Object { $_.id })
    desktopRoot  = $desktopProfilesRoot
}
($active | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath (Join-Path $InstallRoot "active-profile.json") -Encoding UTF8

Write-Dragon "Active profile recorded. In Dragon AI Agent, open Profiles and pick a bot (ids: $(($bots | ForEach-Object { $_.id }) -join ', '))."
Write-Dragon "Remote gateway (if prompted): http://127.0.0.1:9119  API 127.0.0.1:8642"

# Initialize bot readiness (real-estate-* -> needs_setup until onboarding completes)
try {
    $secureStore = Join-Path $PSScriptRoot "DragonAI-SecureStore.ps1"
    if (-not (Test-Path -LiteralPath $secureStore)) {
        $secureStore = Join-Path $InstallRoot "scripts\airmaze\DragonAI-SecureStore.ps1"
    }
    if (Test-Path -LiteralPath $secureStore) {
        . $secureStore
        $botIdList = @($bots | ForEach-Object { [string]$_.id } | Where-Object { $_ })
        if ($profileId -like "real-estate*") {
            Initialize-DragonAIBotsNeedsSetup -ProfileId $profileId -BotIds $botIdList | Out-Null
            Write-Dragon "Bot status initialized to needs_setup (run Dragon AI Agent Setup wizard)."
        } elseif ($profileId -like "personal-assistant*") {
            Initialize-DragonAIBotsNeedsSetup -ProfileId $profileId -BotIds $botIdList | Out-Null
            Write-Dragon "Bot status initialized (personal-assistant ready)."
        }
    }
} catch {
    Write-Dragon "WARNING: could not initialize bots-status: $($_.Exception.Message)"
}
