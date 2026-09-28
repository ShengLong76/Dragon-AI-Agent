#requires -Version 5.1
<#
.SYNOPSIS
  Apply the default Personal Assistant catalog profile (wrapper).
#>

[CmdletBinding()]
param(
    [string]$InstallRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}

$select = Join-Path $PSScriptRoot "Select-Profile.ps1"
if (-not (Test-Path $select)) {
    $select = Join-Path $InstallRoot "scripts\airmaze\Select-Profile.ps1"
}
& $select -InstallRoot $InstallRoot -PayloadRoot $InstallRoot -ProfileId "personal-assistant" -NonInteractive
Write-Host "[Dragon AI Agent] Default Personal Assistant profile applied."
