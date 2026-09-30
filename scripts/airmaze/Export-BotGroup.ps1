#requires -Version 5.1
<#
.SYNOPSIS
  Export a bot group in the same format the GitHub repo stores (re-importable).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BotGroupId,
    [Parameter(Mandatory = $true)]
    [string]$Destination,
    [string]$InstallRoot = "",
    [string]$PayloadRoot = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}
if ([string]::IsNullOrWhiteSpace($PayloadRoot)) { $PayloadRoot = $InstallRoot }

$engine = Join-Path $PSScriptRoot "bot_groups.py"
if (-not (Test-Path -LiteralPath $engine)) {
    $engine = Join-Path $InstallRoot "scripts\airmaze\bot_groups.py"
}
$py = (Get-Command python3 -ErrorAction SilentlyContinue)
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) { throw "Python is required to export a bot group." }
& $py.Source $engine export --id $BotGroupId --out $Destination --install $InstallRoot --payload $PayloadRoot
if ($LASTEXITCODE -ne 0) { throw "export failed" }
Write-Host "[Dragon AI Agent] Exported bot group $BotGroupId -> $Destination"
