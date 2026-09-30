#requires -Version 5.1
<#
.SYNOPSIS
  Deploy the default Personal Assistant bot group (sidebar stays Personal Assistant).
#>
[CmdletBinding()]
param(
    [string]$InstallRoot = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}

$select = Join-Path $PSScriptRoot "Select-BotGroup.ps1"
if (-not (Test-Path $select)) {
    $select = Join-Path $InstallRoot "scripts\airmaze\Select-BotGroup.ps1"
}
& $select -InstallRoot $InstallRoot -PayloadRoot $InstallRoot -BotGroupId "personal-assistant" -NonInteractive
Write-Host "[Dragon AI Agent] Default Personal Assistant bot group applied."
