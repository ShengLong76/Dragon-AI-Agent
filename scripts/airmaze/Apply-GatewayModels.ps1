#requires -Version 5.1
<#
.SYNOPSIS
  Write Dragon AI Agent default chat + image LLMs into Hermes gateway config.yaml
  and inherit that chat model onto every bot profile that has no override.
#>
[CmdletBinding()]
param(
    [string]$HermesHome = "",
    [string]$Chat = "grok-4.7",
    [string]$Image = "grok-imagine-image",
    [string]$CustomModel = "",
    [string]$BaseUrl = "",
    [string]$DesktopProfiles = "",
    [switch]$IfMissing,
    [switch]$RestartGateway
)

$ErrorActionPreference = "Continue"
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$engine = Join-Path $scriptDir "gateway_models.py"
if (-not (Test-Path -LiteralPath $engine)) {
    Write-Error "gateway_models.py not found beside Apply-GatewayModels.ps1"
    exit 1
}
if ([string]::IsNullOrWhiteSpace($HermesHome)) {
    $HermesHome = Join-Path $env:USERPROFILE ".hermes-airmaze-embedded"
}

$py = $null
foreach ($name in @("python3", "python", "py")) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { $py = $cmd.Source; break }
}
if (-not $py) {
    Write-Error "python3 is required to write gateway model defaults."
    exit 1
}

$pyArgs = @($engine, "apply", "--home", $HermesHome, "--chat", $Chat, "--image", $Image)
if ([string]::IsNullOrWhiteSpace($DesktopProfiles) -and $env:LOCALAPPDATA) {
    $DesktopProfiles = Join-Path $env:LOCALAPPDATA "hermes\profiles"
}
if (-not [string]::IsNullOrWhiteSpace($DesktopProfiles)) {
    $pyArgs += @("--profiles", $DesktopProfiles)
}
if (-not [string]::IsNullOrWhiteSpace($CustomModel)) { $pyArgs += @("--custom-model", $CustomModel) }
if (-not [string]::IsNullOrWhiteSpace($BaseUrl)) { $pyArgs += @("--base-url", $BaseUrl) }
if ($IfMissing) { $pyArgs += "--if-missing" }
& $py @pyArgs
$code = $LASTEXITCODE
if ($RestartGateway -and $code -eq 0) {
    try {
        $compose = Join-Path (Split-Path -Parent (Split-Path -Parent $scriptDir)) "docker-compose.embedded.yml"
        if (-not (Test-Path -LiteralPath $compose)) {
            $compose = Join-Path $env:LOCALAPPDATA "DragonAIAgent\docker-compose.embedded.yml"
        }
        if (Get-Command docker -ErrorAction SilentlyContinue) {
            docker compose -f $compose restart hermes-airmaze-gw hermes-airmaze-desktop 2>$null | Out-Null
        }
    } catch {}
}
exit $code
