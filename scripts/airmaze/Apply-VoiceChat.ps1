#requires -Version 5.1
<#
.SYNOPSIS
  Select GPT or Grok voice for Dragon AI Agent (does not replace GPT).
#>
[CmdletBinding()]
param(
    [ValidateSet("gpt", "grok", "chained", "gpt-live", "grok-live")]
    [string]$Provider = "gpt",
    [string]$HermesHome = "",
    [switch]$RestartGateway
)

$ErrorActionPreference = "Continue"
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$engine = Join-Path $scriptDir "voice_chat.py"
if (-not (Test-Path -LiteralPath $engine)) {
    Write-Error "voice_chat.py not found beside Apply-VoiceChat.ps1"
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
    Write-Error "python3 is required to write voice provider selection."
    exit 1
}

& $py $engine apply --home $HermesHome --provider $Provider
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
