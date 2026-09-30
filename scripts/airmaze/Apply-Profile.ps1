#requires -Version 5.1
<#
.SYNOPSIS
  Compatibility shim. Applies a folder that still has profile.json or bot-group.json.
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
$import = Join-Path $PSScriptRoot "Import-BotGroup.ps1"
if (-not (Test-Path -LiteralPath $import)) {
    $import = Join-Path $InstallRoot "scripts\airmaze\Import-BotGroup.ps1"
}
& $import -SourcePath $ProfilePath -InstallRoot $InstallRoot
