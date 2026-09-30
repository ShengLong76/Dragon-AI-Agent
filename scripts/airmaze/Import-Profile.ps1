#requires -Version 5.1
<#
.SYNOPSIS
  Compatibility shim. Import a leftover profile bundle as a bot group.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath,
    [string]$InstallRoot = "",
    [string]$PayloadRoot = ""
)

$import = Join-Path $PSScriptRoot "Import-BotGroup.ps1"
if (-not (Test-Path -LiteralPath $import)) {
    $import = Join-Path $InstallRoot "scripts\airmaze\Import-BotGroup.ps1"
}
& $import -SourcePath $SourcePath -InstallRoot $InstallRoot -PayloadRoot $PayloadRoot
