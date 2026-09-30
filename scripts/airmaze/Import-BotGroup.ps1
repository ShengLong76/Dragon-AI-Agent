#requires -Version 5.1
<#
.SYNOPSIS
  Import a re-exported bot group (zip/folder/JSON). One-bot files require the singular toggle.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath,
    [string]$InstallRoot = "",
    [string]$PayloadRoot = "",
    [string]$DesktopProfilesRoot = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}
if ([string]::IsNullOrWhiteSpace($PayloadRoot)) { $PayloadRoot = $InstallRoot }
if ([string]::IsNullOrWhiteSpace($DesktopProfilesRoot)) {
    if ($env:LOCALAPPDATA) { $DesktopProfilesRoot = Join-Path $env:LOCALAPPDATA "hermes\profiles" }
    else { $DesktopProfilesRoot = Join-Path $InstallRoot "hermes-profiles" }
}

$engine = Join-Path $PSScriptRoot "bot_groups.py"
if (-not (Test-Path -LiteralPath $engine)) {
    $engine = Join-Path $InstallRoot "scripts\airmaze\bot_groups.py"
}
$py = (Get-Command python3 -ErrorAction SilentlyContinue)
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) { throw "Python is required to import a bot group." }
& $py.Source $engine import --source $SourcePath --install $InstallRoot --desktop $DesktopProfilesRoot --payload $PayloadRoot
if ($LASTEXITCODE -ne 0) { throw "import failed" }
Write-Host "[Dragon AI Agent] Import complete from $SourcePath"
