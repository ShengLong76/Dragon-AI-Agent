#requires -Version 5.1
<#
.SYNOPSIS
  Import a Dragon AI Agent profile bundle from a zip, folder, or profile.json path.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath,
    [string]$InstallRoot = "",
    [string]$PayloadRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}

function Write-Dragon([string]$Message) {
    Write-Host "[Dragon AI Agent] $Message"
}

if (-not (Test-Path -LiteralPath $SourcePath)) {
    throw "Source not found: $SourcePath"
}

$stagingParent = Join-Path $InstallRoot "profiles\imported"
New-Item -ItemType Directory -Force -Path $stagingParent | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$staging = Join-Path $stagingParent "import-$stamp"
New-Item -ItemType Directory -Force -Path $staging | Out-Null

$src = (Resolve-Path -LiteralPath $SourcePath).Path
$item = Get-Item -LiteralPath $src

if ($item.PSIsContainer) {
    Copy-Item -Path (Join-Path $src "*") -Destination $staging -Recurse -Force
} elseif ($item.Extension -match '\.(zip)$') {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::ExtractToDirectory($src, $staging)
    # If zip contained a single top-level folder, dive in
    $kids = @(Get-ChildItem -LiteralPath $staging)
    if ($kids.Count -eq 1 -and $kids[0].PSIsContainer -and -not (Test-Path (Join-Path $staging "profile.json"))) {
        $staging = $kids[0].FullName
    }
} elseif ([IO.Path]::GetFileName($src) -ieq "profile.json") {
    $dir = Split-Path $src -Parent
    Copy-Item -Path (Join-Path $dir "*") -Destination $staging -Recurse -Force
} elseif ($item.Extension -match '\.(json)$') {
    # Single JSON manifest without bots — accept as thin import (bots optional external)
    Copy-Item -LiteralPath $src -Destination (Join-Path $staging "profile.json") -Force
} else {
    throw "Unsupported import type (use zip, profile folder, or profile.json): $src"
}

if (-not (Test-Path (Join-Path $staging "profile.json"))) {
    # search one level
    $found = Get-ChildItem -Path $staging -Filter profile.json -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $staging = Split-Path $found.FullName -Parent }
    else { throw "Imported bundle has no profile.json" }
}

$apply = Join-Path $PSScriptRoot "Apply-Profile.ps1"
if (-not (Test-Path $apply)) {
    $apply = Join-Path $InstallRoot "scripts\airmaze\Apply-Profile.ps1"
}
& $apply -ProfilePath $staging -InstallRoot $InstallRoot
Write-Dragon "Import complete from $src"
