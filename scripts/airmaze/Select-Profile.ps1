#requires -Version 5.1
<#
.SYNOPSIS
  Compatibility shim. Profiles are bot groups. Opens the bot group dropdown.
#>
[CmdletBinding()]
param(
    [string]$PayloadRoot = "",
    [string]$InstallRoot = "",
    [string]$ProfileId = "",
    [string]$BotGroupId = "",
    [switch]$NonInteractive
)

$next = Join-Path $PSScriptRoot "Select-BotGroup.ps1"
if (-not (Test-Path -LiteralPath $next)) {
    $next = Join-Path $InstallRoot "scripts\airmaze\Select-BotGroup.ps1"
}
if ([string]::IsNullOrWhiteSpace($BotGroupId)) { $BotGroupId = $ProfileId }
$splat = @{
    PayloadRoot     = $PayloadRoot
    InstallRoot     = $InstallRoot
    BotGroupId      = $BotGroupId
    NonInteractive  = $NonInteractive
}
& $next @splat
