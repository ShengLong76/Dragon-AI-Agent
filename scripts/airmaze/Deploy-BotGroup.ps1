#requires -Version 5.1
<#
.SYNOPSIS
  Deploy one Dragon AI Agent bot group (GitHub / cache / bundled). No manual file handling.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BotGroupId,
    [string]$PayloadRoot = "",
    [string]$InstallRoot = "",
    [string]$DesktopProfilesRoot = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}

$select = Join-Path $PSScriptRoot "Select-BotGroup.ps1"
if (-not (Test-Path -LiteralPath $select)) {
    $select = Join-Path $InstallRoot "scripts\airmaze\Select-BotGroup.ps1"
}
$args = @{
    InstallRoot = $InstallRoot
    BotGroupId  = $BotGroupId
}
if ($PayloadRoot) { $args.PayloadRoot = $PayloadRoot }
& $select @args
