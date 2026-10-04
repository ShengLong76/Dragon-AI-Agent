#requires -Version 5.1
<#
.SYNOPSIS
  Remove Dragon AI Agent from this user account.

.DESCRIPTION
  Deletes Dragon AI Agent files, shortcuts, and the Windows Apps uninstall
  entry. Does not uninstall Docker Desktop. Does not reboot Windows.
#>

[CmdletBinding()]
param(
    [switch]$Quiet
)

$ErrorActionPreference = "Continue"
$ProductName = "Dragon AI Agent"
$InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Dragon AI Agent"
$UninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\DragonAIAgent"
$LogPath = Join-Path $env:TEMP "DragonAIAgent-uninstall.log"

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    if (-not $Quiet) { Write-Host $line }
    try { Add-Content -LiteralPath $LogPath -Value $line -Encoding ASCII -ErrorAction SilentlyContinue } catch {}
}

function Stop-DragonAIProcesses {
    foreach ($name in @("DragonAIAgent", "DragonAIAgentSetup")) {
        Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.Path -and ($_.Path -like "*DragonAIAgent*")) {
                Write-Log "Stopping $($_.Name) pid=$($_.Id)"
                Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Remove-DragonAIShortcuts {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $names = @(
        "Dragon AI Agent.lnk",
        "Dragon AI Agent Setup.lnk",
        "Dragon AI Agent Bot Groups.lnk",
        "Dragon AI Agent Dashboard.lnk",
        "Dragon AI Agent Profiles.lnk"
    )
    foreach ($dir in @($desktop, $StartMenuDir)) {
        foreach ($name in $names) {
            $p = Join-Path $dir $name
            if (Test-Path -LiteralPath $p) {
                Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
                Write-Log "Removed shortcut $p"
            }
        }
    }
    if (Test-Path -LiteralPath $StartMenuDir) {
        try {
            if (-not (Get-ChildItem -LiteralPath $StartMenuDir -Force -ErrorAction SilentlyContinue)) {
                Remove-Item -LiteralPath $StartMenuDir -Force -ErrorAction SilentlyContinue
            }
        } catch {}
    }
}

Write-Log "=== $ProductName uninstall (does not remove Docker Desktop, does not reboot) ==="
Stop-DragonAIProcesses
Remove-DragonAIShortcuts

if (Test-Path -LiteralPath $UninstallKey) {
    Remove-Item -LiteralPath $UninstallKey -Recurse -Force -ErrorAction SilentlyContinue
    Write-Log "Removed Apps uninstall entry"
}

# Never touch Docker Desktop, WSL, or Program Files\Docker.
# Do not reboot Windows.

if (Test-Path -LiteralPath $InstallRoot) {
    try {
        Remove-Item -LiteralPath $InstallRoot -Recurse -Force -ErrorAction Stop
        Write-Log "Removed $InstallRoot"
    } catch {
        Write-Log "Could not remove all of $InstallRoot : $($_.Exception.Message)"
    }
}

Write-Log "=== $ProductName uninstall finished. Docker Desktop was left installed. No reboot. ==="
if (-not $Quiet) {
    Write-Host ""
    Write-Host "$ProductName was removed from this user account."
    Write-Host "Docker Desktop was not uninstalled."
    Write-Host "Windows was not rebooted."
}
exit 0
