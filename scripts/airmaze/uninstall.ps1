#requires -Version 5.1
<#
.SYNOPSIS
  Remove a per-user Dragon AI Agent install.

.DESCRIPTION
  Stops the product window, best-effort compose down (does not uninstall
  Docker Desktop), deletes the desktop shortcut, the Start Menu shortcut
  and folder, the LocalAppData app tree, and the HKCU Uninstall key so
  Settings > Apps no longer lists Dragon AI Agent.

.NOTES
  Called from Settings > Apps via the HKCU Uninstall UninstallString.
  ASCII punctuation only (Windows PowerShell 5.1).
#>

param(
    [switch]$Quiet,
    [switch]$SelfTest,
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]]$Remaining
)

$ErrorActionPreference = "Continue"
$ProductName = "Dragon AI Agent"
$InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Dragon AI Agent"
$UninstallRegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\DragonAIAgent"
$LogPath = Join-Path $env:TEMP "DragonAIAgent-uninstall.log"

function Write-UninstallLog {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    if (-not $Quiet) {
        Write-Host $line
    }
    try {
        Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {}
}

function Get-DesktopShortcutPath {
    return (Join-Path ([Environment]::GetFolderPath("Desktop")) "Dragon AI Agent.lnk")
}

function Get-StartMenuShortcutPath {
    return (Join-Path $StartMenuDir "Dragon AI Agent.lnk")
}

if ($SelfTest) {
    Write-Output "InstallRoot=$InstallRoot"
    Write-Output "DesktopLnk=$(Get-DesktopShortcutPath)"
    Write-Output "StartMenuLnk=$(Get-StartMenuShortcutPath)"
    Write-Output "StartMenuDir=$StartMenuDir"
    Write-Output "UninstallKey=$UninstallRegPath"
    Write-Output "Hive=HKCU"
    exit 0
}

Write-UninstallLog "=== $ProductName uninstall ==="
Write-UninstallLog "Install root: $InstallRoot"

foreach ($procName in @("DragonAIAgent")) {
    foreach ($p in Get-Process -Name $procName -ErrorAction SilentlyContinue) {
        try {
            Stop-Process -Id $p.Id -Force -ErrorAction Stop
            Write-UninstallLog "Stopped process $procName ($($p.Id))"
        } catch {
            Write-UninstallLog "Could not stop $procName ($($p.Id)): $($_.Exception.Message)"
        }
    }
}

$compose = Join-Path $InstallRoot "docker-compose.embedded.yml"
if (Test-Path -LiteralPath $compose) {
    try {
        $docker = Get-Command docker -ErrorAction SilentlyContinue
        if ($docker) {
            Push-Location $InstallRoot
            try {
                & docker compose -f docker-compose.embedded.yml down 2>&1 | ForEach-Object { Write-UninstallLog "compose: $_" }
            } finally {
                Pop-Location
            }
        }
    } catch {
        Write-UninstallLog "compose down skipped: $($_.Exception.Message)"
    }
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPaths = @(
    (Get-DesktopShortcutPath),
    (Get-StartMenuShortcutPath),
    (Join-Path $desktop "Dragon AI Agent Setup.lnk"),
    (Join-Path $desktop "Dragon AI Agent Bot Groups.lnk"),
    (Join-Path $desktop "Dragon AI Agent Dashboard.lnk"),
    (Join-Path $desktop "Dragon AI Agent Profiles.lnk"),
    (Join-Path $StartMenuDir "Dragon AI Agent Setup.lnk"),
    (Join-Path $StartMenuDir "Dragon AI Agent Bot Groups.lnk"),
    (Join-Path $StartMenuDir "Dragon AI Agent Dashboard.lnk"),
    (Join-Path $StartMenuDir "Dragon AI Agent Profiles.lnk")
)
foreach ($lnk in $shortcutPaths) {
    if (Test-Path -LiteralPath $lnk) {
        try {
            Remove-Item -LiteralPath $lnk -Force -ErrorAction Stop
            Write-UninstallLog "Removed shortcut: $lnk"
        } catch {
            Write-UninstallLog "Could not remove shortcut $lnk : $($_.Exception.Message)"
        }
    }
}

if (Test-Path -LiteralPath $StartMenuDir) {
    try {
        Remove-Item -LiteralPath $StartMenuDir -Recurse -Force -ErrorAction Stop
        Write-UninstallLog "Removed Start Menu folder: $StartMenuDir"
    } catch {
        Write-UninstallLog "Could not remove Start Menu folder: $($_.Exception.Message)"
    }
}

if (Test-Path -LiteralPath $UninstallRegPath) {
    try {
        Remove-Item -LiteralPath $UninstallRegPath -Recurse -Force -ErrorAction Stop
        Write-UninstallLog "Removed Apps uninstall key: $UninstallRegPath"
    } catch {
        Write-UninstallLog "Could not remove uninstall key: $($_.Exception.Message)"
    }
}

if (Test-Path -LiteralPath $InstallRoot) {
    $retries = 0
    while ((Test-Path -LiteralPath $InstallRoot) -and ($retries -lt 5)) {
        try {
            Remove-Item -LiteralPath $InstallRoot -Recurse -Force -ErrorAction Stop
            Write-UninstallLog "Removed app folder: $InstallRoot"
        } catch {
            $retries = $retries + 1
            Start-Sleep -Milliseconds 400
            if ($retries -ge 5) {
                Write-UninstallLog "Could not remove app folder: $($_.Exception.Message)"
            }
        }
    }
}

Write-UninstallLog "=== $ProductName uninstall finished. Log: $LogPath ==="
if (-not $Quiet) {
    Write-Host ""
    Write-Host "$ProductName was removed from this user account."
    Write-Host "  Apps entry, desktop shortcut, and Start Menu shortcut are gone."
    Write-Host ""
}
exit 0
