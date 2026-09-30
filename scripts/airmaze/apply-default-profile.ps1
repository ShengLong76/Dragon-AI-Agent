#requires -Version 5.1
<#
.SYNOPSIS
  Compatibility shim. Default Personal Assistant bot group.
#>
[CmdletBinding()]
param(
    [string]$InstallRoot = ""
)

$next = Join-Path $PSScriptRoot "apply-default-bot-group.ps1"
if (-not (Test-Path -LiteralPath $next)) {
    $next = Join-Path $InstallRoot "scripts\airmaze\apply-default-bot-group.ps1"
}
& $next -InstallRoot $InstallRoot
