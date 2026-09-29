#requires -Version 5.1
<#
.SYNOPSIS
  Locate the Hermes/Electron desktop client on Windows and remember a stable path.

.DESCRIPTION
  UltraDragon ships the client as an unpacked Electron build, e.g.
  %LOCALAPPDATA%\hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe
  — not "Hermes Desktop.exe" under Programs. Dot-source this file.
#>

function Get-HermesDesktopExactCandidates {
    $la = $env:LOCALAPPDATA
    $pf = $env:ProgramFiles
    $pf86 = ${env:ProgramFiles(x86)}
    return @(
        (Join-Path $la "hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe"),
        (Join-Path $la "hermes\hermes-agent\apps\desktop\dist\win-unpacked\Hermes.exe"),
        (Join-Path $la "hermes\hermes-agent\apps\desktop\out\win-unpacked\Hermes.exe"),
        (Join-Path $la "hermes\Hermes Desktop.exe"),
        (Join-Path $la "hermes\HermesDesktop.exe"),
        (Join-Path $la "hermes\Hermes.exe"),
        (Join-Path $la "Programs\hermes\Hermes Desktop.exe"),
        (Join-Path $la "Programs\hermes\Hermes.exe"),
        (Join-Path $la "Programs\Hermes\Hermes.exe"),
        (Join-Path $la "Programs\Hermes\Hermes Desktop.exe"),
        (Join-Path $pf "Hermes\Hermes Desktop.exe"),
        (Join-Path $pf "Hermes\Hermes.exe"),
        (Join-Path $pf86 "Hermes\Hermes Desktop.exe")
    )
}

function Get-HermesDesktopSearchRoots {
    return @(
        (Join-Path $env:LOCALAPPDATA "hermes"),
        (Join-Path $env:LOCALAPPDATA "Programs\hermes"),
        (Join-Path $env:LOCALAPPDATA "Programs\Hermes"),
        (Join-Path $env:ProgramFiles "Hermes"),
        (Join-Path ${env:ProgramFiles(x86)} "Hermes")
    )
}

function Get-DragonAIDesktopPointerPath {
    param([string]$InstallRoot = "")
    if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
        $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
    }
    return (Join-Path $InstallRoot "desktop-client.json")
}

function Find-HermesDesktopExe {
    param([string]$InstallRoot = "")

    $pointer = Get-DragonAIDesktopPointerPath -InstallRoot $InstallRoot
    if (Test-Path -LiteralPath $pointer) {
        try {
            $saved = Get-Content -LiteralPath $pointer -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($saved.exe -and (Test-Path -LiteralPath ([string]$saved.exe))) {
                return [string]$saved.exe
            }
        } catch {}
    }

    foreach ($c in Get-HermesDesktopExactCandidates) {
        if ($c -and (Test-Path -LiteralPath $c)) { return $c }
    }

    foreach ($root in Get-HermesDesktopSearchRoots) {
        if (-not $root -or -not (Test-Path -LiteralPath $root)) { continue }
        try {
            $hit = Get-ChildItem -LiteralPath $root -Filter "Hermes.exe" -Recurse -File -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.Name -eq "Hermes.exe" -and (
                        $_.DirectoryName -like "*win-unpacked*" -or
                        $_.DirectoryName -like "*release*" -or
                        $_.FullName -like "*\Hermes\Hermes.exe"
                    )
                } |
                Select-Object -First 1
            if ($hit) { return $hit.FullName }
        } catch {}
    }

    return $null
}

function Save-DragonAIDesktopPointer {
    param(
        [Parameter(Mandatory = $true)][string]$ExePath,
        [string]$InstallRoot = ""
    )
    if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
        $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
    }
    if (-not (Test-Path -LiteralPath $InstallRoot)) {
        New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
    }
    $wd = Split-Path -Parent $ExePath
    $obj = [ordered]@{
        exe              = $ExePath
        workingDirectory = $wd
        updatedAt        = (Get-Date).ToString("o")
        notes            = "On-disk filename stays Hermes.exe (Electron resources). Display name is Dragon AI Agent."
    }
    $pointer = Get-DragonAIDesktopPointerPath -InstallRoot $InstallRoot
    ($obj | ConvertTo-Json) | Set-Content -LiteralPath $pointer -Encoding UTF8

    try {
        $wsh = New-Object -ComObject WScript.Shell
        $lnkPath = Join-Path $InstallRoot "Dragon AI Agent Client.lnk"
        $sc = $wsh.CreateShortcut($lnkPath)
        $sc.TargetPath = $ExePath
        $sc.WorkingDirectory = $wd
        $sc.Description = "Dragon AI Agent desktop"
        $sc.WindowStyle = 1
        $ico = Join-Path $InstallRoot "branding\dragon-ai-agent-logo.ico"
        if (-not (Test-Path -LiteralPath $ico)) { $ico = Join-Path $InstallRoot "dragon-ai-agent-logo.ico" }
        if (Test-Path -LiteralPath $ico) { $sc.IconLocation = "$ico,0" }
        $sc.Save()
    } catch {}

    return $pointer
}

function Set-DragonAIMainWindowTitle {
    <#
    .SYNOPSIS
      Rename the unpacked Electron window to Dragon AI Agent (packaging wrap).
      Taskbar AppUserModelID / About / tray still need a rebuilt client binary.
    #>
    param(
        [string]$Title = "Dragon AI Agent",
        [int]$TimeoutSec = 25
    )
    try {
        if (-not ("DragonAIWinTitle" -as [type])) {
            Add-Type @"
using System;
using System.Runtime.InteropServices;
public class DragonAIWinTitle {
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern bool SetWindowText(IntPtr hWnd, string lpString);
}
"@
        }
    } catch {
        return $false
    }
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $procs = @(Get-Process -Name "Hermes" -ErrorAction SilentlyContinue)
        foreach ($p in $procs) {
            if ($p.MainWindowHandle -ne [IntPtr]::Zero) {
                try {
                    [DragonAIWinTitle]::SetWindowText($p.MainWindowHandle, $Title) | Out-Null
                    return $true
                } catch {}
            }
        }
        Start-Sleep -Milliseconds 400
    }
    return $false
}

function Start-HermesDesktopClient {
    param(
        [Parameter(Mandatory = $true)][string]$ExePath
    )
    $wd = Split-Path -Parent $ExePath
    Start-Process -FilePath $ExePath -WorkingDirectory $wd -ErrorAction Stop
    Set-DragonAIMainWindowTitle -Title "Dragon AI Agent" | Out-Null
    return $true
}
