#requires -Version 5.1
<#
.SYNOPSIS
  Point Dragon AI Agent Desktop at the embedded Linux Desktop serve proxy.

.DESCRIPTION
  Upserts %APPDATA%\Hermes\connections.json with Remote "Embedded Linux" →
  http://127.0.0.1:8650 and the compose placeholder session token (dragon-local).
  Rewrites a prior Remote that targeted the OpenAI API on :8642.

  Prefer the Python helper when python3/py is on PATH (same merge rules).
#>
[CmdletBinding()]
param(
    [string]$Url = "http://127.0.0.1:8650",
    [string]$Token = "dragon-local",
    [string]$ConnectionsPath = "",
    [switch]$NoPrimary,
    [switch]$Smoke
)

$ErrorActionPreference = "Stop"
$helper = Join-Path $PSScriptRoot "embedded_desktop_connection.py"
if (-not (Test-Path -LiteralPath $helper)) {
    $helper = Join-Path (Split-Path -Parent $PSScriptRoot) "airmaze\embedded_desktop_connection.py"
}

function Get-PythonExe {
    foreach ($name in @("python3", "py", "python")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    return $null
}

function Get-DefaultConnectionsPath {
    $appdata = $env:APPDATA
    if ([string]::IsNullOrWhiteSpace($appdata)) {
        $appdata = Join-Path $env:USERPROFILE "AppData\Roaming"
    }
    return (Join-Path $appdata "Hermes\connections.json")
}

if ($Smoke) {
    if (-not (Test-Path -LiteralPath $helper)) {
        throw "Smoke: missing embedded_desktop_connection.py"
    }
    $py = Get-PythonExe
    if (-not $py) {
        Write-Host "SMOKE OK: Set-EmbeddedDesktopConnection helper is present (python not on PATH)."
        exit 0
    }
    $tmp = Join-Path ([IO.Path]::GetTempPath()) ("dragon-conn-smoke-" + [guid]::NewGuid().ToString("n") + ".json")
    try {
        & $py $helper --path $tmp --url $Url --token $Token | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "python helper exited $LASTEXITCODE" }
        $doc = Get-Content -LiteralPath $tmp -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($doc.primary -ne "embedded-linux") { throw "Smoke: primary was $($doc.primary)" }
        $hit = @($doc.connections) | Where-Object { $_.id -eq "embedded-linux" } | Select-Object -First 1
        if (-not $hit -or [string]$hit.url -notlike "*8650*") { throw "Smoke: missing 8650 remote" }
        Write-Host "SMOKE OK: connections.json helper wrote Embedded Linux → 8650"
        exit 0
    } finally {
        Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue
    }
}

$dest = $ConnectionsPath
if ([string]::IsNullOrWhiteSpace($dest)) {
    $dest = Get-DefaultConnectionsPath
}

$py = Get-PythonExe
if ($py -and (Test-Path -LiteralPath $helper)) {
    $args = @($helper, "--path", $dest, "--url", $Url, "--token", $Token)
    if ($NoPrimary) { $args += "--no-primary" }
    $out = & $py @args
    if ($LASTEXITCODE -ne 0) {
        throw "embedded_desktop_connection.py failed: $out"
    }
    Write-Host $out
    return
}

# PowerShell fallback (no Python). Same shape as the Python helper.
$dir = Split-Path -Parent $dest
if ($dir -and -not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$doc = $null
if (Test-Path -LiteralPath $dest) {
    try {
        $doc = Get-Content -LiteralPath $dest -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $doc = $null
    }
}
if ($null -eq $doc) {
    $doc = [pscustomobject]@{
        version     = 2
        primary     = "local"
        launchMode  = "primary"
        lastUsed    = "local"
        connections = @()
    }
}

$rows = @()
if ($doc.connections) { $rows = @($doc.connections) }
if (-not ($rows | Where-Object { $_.id -eq "local" })) {
    $rows = @([pscustomobject]@{ id = "local"; kind = "local"; label = "This device" }) + $rows
}

$remote = [pscustomobject]@{
    id       = "embedded-linux"
    kind     = "remote"
    label    = "Embedded Linux"
    url      = $Url
    authMode = "token"
    token    = [pscustomobject]@{ encoding = "plain"; value = $Token }
}

$legacy = @("http://127.0.0.1:8642", "http://localhost:8642")
$out = @()
$replaced = $false
foreach ($row in $rows) {
    $rid = [string]$row.id
    $rurl = ([string]$row.url).TrimEnd("/")
    if ($rid -eq "embedded-linux" -or ($row.kind -eq "remote" -and $legacy -contains $rurl)) {
        $out += $remote
        $replaced = $true
    } else {
        $out += $row
    }
}
if (-not $replaced) { $out += $remote }

$doc | Add-Member -MemberType NoteProperty -Name connections -Value $out -Force
$primary = [string]$doc.primary
if (-not $NoPrimary) {
    $primaryIsLegacy = $false
    foreach ($row in $out) {
        if ([string]$row.id -eq $primary -and $legacy -contains ([string]$row.url).TrimEnd("/")) {
            $primaryIsLegacy = $true
        }
    }
    if ([string]::IsNullOrWhiteSpace($primary) -or $primary -eq "local" -or $primary -eq "embedded-linux" -or $primaryIsLegacy) {
        $doc | Add-Member -MemberType NoteProperty -Name primary -Value "embedded-linux" -Force
        $doc | Add-Member -MemberType NoteProperty -Name lastUsed -Value "embedded-linux" -Force
        if (-not $doc.launchMode) {
            $doc | Add-Member -MemberType NoteProperty -Name launchMode -Value "primary" -Force
        }
    }
}

($doc | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $dest -Encoding UTF8
Write-Host "Wrote Embedded Linux Remote → $Url ($dest)"
