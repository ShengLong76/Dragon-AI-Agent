#requires -Version 5.1
<#
.SYNOPSIS
  Interactive or non-interactive selection from the built-in Dragon AI Agent profile catalog.
#>
[CmdletBinding()]
param(
    [string]$PayloadRoot = "",
    [string]$InstallRoot = "",
    [string]$ProfileId = "",
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}

function Write-Dragon([string]$Message) {
    Write-Host "[Dragon AI Agent] $Message"
}

function Resolve-Payload {
    param([string]$Hint)
    if ($Hint -and (Test-Path -LiteralPath $Hint)) {
        return (Resolve-Path -LiteralPath $Hint).Path
    }
    if ($PSScriptRoot) {
        foreach ($c in @(
            (Join-Path $PSScriptRoot "..\.."),
            (Join-Path $PSScriptRoot ".."),
            $PSScriptRoot
        )) {
            $cat = Join-Path $c "profiles\catalog.json"
            if (Test-Path -LiteralPath $cat) { return (Resolve-Path $c).Path }
        }
    }
    $ir = Join-Path $InstallRoot "profiles"
    if (Test-Path (Join-Path $ir "catalog.json")) { return $InstallRoot }
    throw "Cannot find profiles/catalog.json. Pass -PayloadRoot."
}

$root = Resolve-Payload -Hint $PayloadRoot
$catalogPath = Join-Path $root "profiles\catalog.json"
if (-not (Test-Path $catalogPath)) {
    # payload may nest under install copy
    $alt = Join-Path $InstallRoot "profiles\catalog.json"
    if (Test-Path $alt) { $catalogPath = $alt; $root = $InstallRoot }
    else { throw "Missing catalog at $catalogPath" }
}

$catalog = Get-Content -LiteralPath $catalogPath -Raw -Encoding UTF8 | ConvertFrom-Json
$entries = @($catalog.profiles)
if ($entries.Count -eq 0) { throw "Catalog is empty" }

$chosen = $null
if (-not [string]::IsNullOrWhiteSpace($ProfileId)) {
    $chosen = $entries | Where-Object { $_.id -eq $ProfileId } | Select-Object -First 1
    if (-not $chosen) { throw "ProfileId '$ProfileId' not in catalog" }
} elseif ($NonInteractive) {
    $chosen = $entries | Where-Object { $_.id -eq "personal-assistant" } | Select-Object -First 1
    if (-not $chosen) { $chosen = $entries[0] }
} else {
    Write-Host ""
    Write-Host "========================================"
    Write-Host " Dragon AI Agent — choose a profile"
    Write-Host "========================================"
    $i = 1
    foreach ($e in $entries) {
        Write-Host ("  [{0}] {1}" -f $i, $e.displayName)
        Write-Host ("      {0}" -f $e.description)
        $i++
    }
    Write-Host ("  [{0}] Import from file (zip or profile folder/JSON)" -f $i)
    Write-Host "  [Enter] default = Personal Assistant (or first catalog entry)"
    Write-Host ""
    $ans = Read-Host "Selection"
    if ([string]::IsNullOrWhiteSpace($ans)) {
        $chosen = $entries | Where-Object { $_.id -eq "personal-assistant" } | Select-Object -First 1
        if (-not $chosen) { $chosen = $entries[0] }
    } elseif ($ans -match '^\d+$') {
        $n = [int]$ans
        if ($n -ge 1 -and $n -le $entries.Count) {
            $chosen = $entries[$n - 1]
        } elseif ($n -eq ($entries.Count + 1)) {
            $importPath = Read-Host "Path to profile zip, folder, or profile.json"
            $importScript = Join-Path $PSScriptRoot "Import-Profile.ps1"
            if (-not (Test-Path $importScript)) {
                $importScript = Join-Path $InstallRoot "scripts\airmaze\Import-Profile.ps1"
            }
            & $importScript -SourcePath $importPath -InstallRoot $InstallRoot -PayloadRoot $root
            return
        } else {
            throw "Invalid selection: $ans"
        }
    } else {
        # treat as profile id
        $chosen = $entries | Where-Object { $_.id -eq $ans } | Select-Object -First 1
        if (-not $chosen) { throw "Unknown selection: $ans" }
    }
}

$rel = [string]$chosen.path
if (-not $rel) { $rel = [string]$chosen.id }
$profileDir = Join-Path $root ("profiles\" + ($rel -replace '/', '\'))
if (-not (Test-Path (Join-Path $profileDir "profile.json"))) {
    throw "Catalog profile folder missing profile.json: $profileDir"
}

$apply = Join-Path $PSScriptRoot "Apply-Profile.ps1"
if (-not (Test-Path $apply)) {
    $apply = Join-Path $InstallRoot "scripts\airmaze\Apply-Profile.ps1"
}
& $apply -ProfilePath $profileDir -InstallRoot $InstallRoot
Write-Dragon "Selected catalog profile: $($chosen.displayName)"
