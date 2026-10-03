#requires -Version 5.1
<#
.SYNOPSIS
  Locate and launch the packaged Dragon AI Agent desktop.

.DESCRIPTION
  Dragon AI Agent is its own Windows app. The exe is DragonAIAgent.exe,
  shipped in the Dragon package and copied to
  %LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked.
  This script does not search for, copy, require, or mention a Hermes
  install. Hermes stays a separate product.
  Dot-source this file.
#>

function Get-DragonAIInstallRoot {
    param([string]$InstallRoot = "")
    if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
        $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
    }
    return $InstallRoot
}

function Get-DragonAIPrivateDesktopExe {
    param([string]$InstallRoot = "")
    return (Join-Path (Get-DragonAIInstallRoot -InstallRoot $InstallRoot) "desktop\win-unpacked\DragonAIAgent.exe")
}

function Get-DragonAIElectronUserDataDir {
    param([string]$InstallRoot = "")
    if ($env:DRAGON_AI_USER_DATA_DIR) {
        return $env:DRAGON_AI_USER_DATA_DIR
    }
    if ($env:HERMES_DESKTOP_USER_DATA_DIR) {
        return $env:HERMES_DESKTOP_USER_DATA_DIR
    }
    return (Join-Path (Get-DragonAIInstallRoot -InstallRoot $InstallRoot) "electron-userdata")
}

function Test-DragonAIPrivateDesktopPath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    $norm = $Path.Replace("/", "\")
    return ($norm -match '(?i)\\DragonAIAgent\\' -or $norm -match '(?i)\\DragonAIAgent$')
}

function Test-DragonAIHermesInstallPath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    if (Test-DragonAIPrivateDesktopPath -Path $Path) { return $false }
    $norm = $Path.Replace("/", "\").ToLowerInvariant()
    $leaf = [IO.Path]::GetFileName($norm)
    if ($leaf -eq "hermes.exe") { return $true }
    return ($norm -like "*\hermes\*" -or $norm -like "*\hermes")
}

function Assert-DragonAIPrivateDesktopPath {
    param(
        [string]$Path,
        [string]$Role = "branding"
    )
    if (-not (Test-DragonAIPrivateDesktopPath -Path $Path)) {
        throw "Refuse branding outside DragonAIAgent (standalone Hermes tree is not mutated; $Role): $Path"
    }
}

function Set-DragonAIDesktopUserDataEnv {
    param([string]$InstallRoot = "")
    $dir = Get-DragonAIElectronUserDataDir -InstallRoot $InstallRoot
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $env:HERMES_DESKTOP_USER_DATA_DIR = $dir
    $env:DRAGON_AI_USER_DATA_DIR = $dir
    $env:DRAGON_AI_INSTALL_ROOT = (Get-DragonAIInstallRoot -InstallRoot $InstallRoot)
    return $dir
}

function Get-DragonAIDesktopPointerPath {
    param([string]$InstallRoot = "")
    if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
        $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
    }
    return (Join-Path $InstallRoot "desktop-client.json")
}

function Get-DragonAIPackagedDesktopCandidates {
    param(
        [string]$InstallRoot = "",
        [string]$PayloadRoot = ""
    )
    $root = Get-DragonAIInstallRoot -InstallRoot $InstallRoot
    $list = @(
        (Join-Path $root "desktop\win-unpacked\DragonAIAgent.exe")
    )
    $payloads = @()
    if (-not [string]::IsNullOrWhiteSpace($PayloadRoot)) { $payloads += $PayloadRoot }
    if ($PSScriptRoot) {
        $payloads += (Join-Path $PSScriptRoot "..\..")
        $payloads += (Join-Path $PSScriptRoot "..")
        $payloads += $PSScriptRoot
    }
    foreach ($p in $payloads) {
        if (-not $p) { continue }
        $list += @(
            (Join-Path $p "desktop\win-unpacked\DragonAIAgent.exe"),
            (Join-Path $p "vendor\desktop\win-unpacked\DragonAIAgent.exe"),
            (Join-Path $p "vendor\desktop\DragonAIAgent.exe")
        )
    }
    return $list
}

function Find-DragonAIPackagedDesktopExe {
    param(
        [string]$InstallRoot = "",
        [string]$PayloadRoot = ""
    )
    foreach ($c in Get-DragonAIPackagedDesktopCandidates -InstallRoot $InstallRoot -PayloadRoot $PayloadRoot) {
        if (-not $c) { continue }
        if (Test-DragonAIHermesInstallPath -Path $c) { continue }
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return $null
}

function Copy-DragonAIWinUnpackedTree {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDir,
        [Parameter(Mandatory = $true)][string]$DestDir
    )
    Assert-DragonAIPrivateDesktopPath -Path $DestDir -Role "copy-dest"
    if (Test-DragonAIHermesInstallPath -Path $SourceDir) {
        throw "Refuse copying from a Hermes install: $SourceDir"
    }
    if (Test-DragonAIPrivateDesktopPath -Path $SourceDir) {
        return
    }
    if (-not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
        throw "Packaged Dragon desktop folder missing: $SourceDir"
    }
    if (-not (Test-Path -LiteralPath $DestDir)) {
        New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
    }
    $robo = Get-Command robocopy -ErrorAction SilentlyContinue
    if ($robo) {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            & robocopy $SourceDir $DestDir /E /XO /NFL /NDL /NJH /NJS /NC /NS /NP | Out-Null
            if ($LASTEXITCODE -ge 8) {
                throw "robocopy failed with exit $LASTEXITCODE ($SourceDir -> $DestDir)"
            }
        } finally {
            $ErrorActionPreference = $prev
        }
        return
    }
    Copy-Item -Path (Join-Path $SourceDir "*") -Destination $DestDir -Recurse -Force
}

function Copy-DragonAIPrivateDesktopFromSource {
    param(
        [Parameter(Mandatory = $true)][string]$SourceExe,
        [string]$InstallRoot = ""
    )
    if (Test-DragonAIHermesInstallPath -Path $SourceExe) {
        throw "Refuse copying from a Hermes install: $SourceExe"
    }
    $destExe = Get-DragonAIPrivateDesktopExe -InstallRoot $InstallRoot
    $destDir = Split-Path -Parent $destExe
    if (Test-Path -LiteralPath $destExe) { return $destExe }
    if (-not (Test-Path -LiteralPath $SourceExe)) { return $null }
    if (Test-DragonAIPrivateDesktopPath -Path $SourceExe) { return $SourceExe }
    $leaf = [IO.Path]::GetFileName($SourceExe)
    if ($leaf -ne "DragonAIAgent.exe") { return $null }
    $srcDir = Split-Path -Parent $SourceExe
    $engine = Join-Path $PSScriptRoot "private_desktop.py"
    $py = Get-Command python3 -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
    if ($py -and (Test-Path -LiteralPath $engine)) {
        try {
            $null = & $py.Source $engine copy --source $SourceExe --dest-root (Get-DragonAIInstallRoot -InstallRoot $InstallRoot) 2>&1
            if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $destExe)) { return $destExe }
        } catch {}
    }
    Copy-DragonAIWinUnpackedTree -SourceDir $srcDir -DestDir $destDir
    if (-not (Test-Path -LiteralPath $destExe)) {
        if (-not (Test-Path -LiteralPath $destDir)) {
            New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        }
        Copy-Item -LiteralPath $SourceExe -Destination $destExe -Force
    }
    if (Test-Path -LiteralPath $destExe) { return $destExe }
    return $null
}

function Install-DragonAIPrivateDesktop {
    param(
        [string]$InstallRoot = "",
        [string]$PayloadRoot = ""
    )
    $dest = Get-DragonAIPrivateDesktopExe -InstallRoot $InstallRoot
    if (Test-Path -LiteralPath $dest) { return $dest }
    $src = Find-DragonAIPackagedDesktopExe -InstallRoot $InstallRoot -PayloadRoot $PayloadRoot
    if (-not $src) { return $null }
    if (Test-DragonAIPrivateDesktopPath -Path $src) { return $src }
    return (Copy-DragonAIPrivateDesktopFromSource -SourceExe $src -InstallRoot $InstallRoot)
}

function Find-DragonDesktopExe {
    param(
        [string]$InstallRoot = "",
        [string]$PayloadRoot = ""
    )
    $private = Get-DragonAIPrivateDesktopExe -InstallRoot $InstallRoot
    if (Test-Path -LiteralPath $private) { return $private }

    $pointer = Get-DragonAIDesktopPointerPath -InstallRoot $InstallRoot
    if (Test-Path -LiteralPath $pointer) {
        try {
            $saved = Get-Content -LiteralPath $pointer -Raw -Encoding UTF8 | ConvertFrom-Json
            $savedExe = [string]$saved.exe
            if ($savedExe -and (Test-Path -LiteralPath $savedExe)) {
                if (Test-DragonAIHermesInstallPath -Path $savedExe) { $savedExe = $null }
                elseif (Test-DragonAIPrivateDesktopPath -Path $savedExe) { return $savedExe }
                elseif ($savedExe) {
                    $copied = Copy-DragonAIPrivateDesktopFromSource -SourceExe $savedExe -InstallRoot $InstallRoot
                    if ($copied) { return $copied }
                }
            }
        } catch {}
    }

    return (Install-DragonAIPrivateDesktop -InstallRoot $InstallRoot -PayloadRoot $PayloadRoot)
}

function Find-HermesDesktopExe {
    param([string]$InstallRoot = "")
    return (Find-DragonDesktopExe -InstallRoot $InstallRoot)
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
    Assert-DragonAIPrivateDesktopPath -Path $ExePath -Role "launch"
    $wd = Split-Path -Parent $ExePath
    $obj = [ordered]@{
        exe              = $ExePath
        workingDirectory = $wd
        userDataDir      = (Get-DragonAIElectronUserDataDir -InstallRoot $InstallRoot)
        updatedAt        = (Get-Date).ToString("o")
        notes            = "Dragon AI Agent desktop shipped with the Dragon package."
    }
    $pointer = Get-DragonAIDesktopPointerPath -InstallRoot $InstallRoot
    ($obj | ConvertTo-Json) | Set-Content -LiteralPath $pointer -Encoding UTF8
    return $pointer
}

function Exclude-DragonAIHermesBots {
    $engine = Join-Path $PSScriptRoot "exclude_hermes_bot.py"
    if (-not (Test-Path -LiteralPath $engine)) { return $false }
    $desktop = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "hermes\profiles" } else { "" }
    $embedded = if ($env:USERPROFILE) { Join-Path $env:USERPROFILE ".hermes-airmaze-embedded\profiles" } else { "" }
    $py = Get-Command python3 -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
    if (-not $py) { return $false }
    try {
        & $py.Source $engine purge --desktop $desktop --embedded $embedded | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Set-DragonAIMainWindowTitle {
    # Window rename only for processes under DragonAIAgent.
    param(
        [string]$Title = "Dragon AI Agent",
        [int]$TimeoutSec = 40
    )
    try {
        if (-not ("DragonAIWinTitle" -as [type])) {
            Add-Type @"
using System;
using System.Runtime.InteropServices;
public class DragonAIWinTitle {
    public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern bool SetWindowText(IntPtr hWnd, string lpString);
    public static int SetTitleForPids(int[] pids, string title) {
        int n = 0;
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            if (!IsWindowVisible(hWnd)) return true;
            for (int i = 0; i < pids.Length; i++) {
                if (pids[i] == (int)pid) {
                    SetWindowText(hWnd, title);
                    n++;
                }
            }
            return true;
        }, IntPtr.Zero);
        return n;
    }
}
"@
        }
    } catch {
        return $false
    }
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $procs = @()
        $procs += @(Get-Process -Name "DragonAIAgent" -ErrorAction SilentlyContinue)
        $procs += @(Get-Process -Name "msedge" -ErrorAction SilentlyContinue)
        $procs = @($procs | Where-Object {
            $_.Path -and (Test-DragonAIPrivateDesktopPath -Path ([string]$_.Path))
        })
        $pids = @($procs | ForEach-Object { [int]$_.Id } | Select-Object -Unique)
        if ($pids.Count -gt 0) {
            try {
                $n = [DragonAIWinTitle]::SetTitleForPids([int[]]$pids, $Title)
                if ($n -gt 0) { return $true }
            } catch {}
            foreach ($p in $procs) {
                if ($p.MainWindowHandle -ne [IntPtr]::Zero) {
                    try {
                        [DragonAIWinTitle]::SetWindowText($p.MainWindowHandle, $Title) | Out-Null
                        return $true
                    } catch {}
                }
            }
        }
        Start-Sleep -Milliseconds 400
    }
    return $false
}

function Apply-DragonAIDesktopUiBranding {
    param(
        [Parameter(Mandatory = $true)][string]$ExePath
    )
    Assert-DragonAIPrivateDesktopPath -Path $ExePath -Role "branding"
    $apply = Join-Path $PSScriptRoot "Apply-DesktopBranding.ps1"
    if (-not (Test-Path -LiteralPath $apply)) {
        return $false
    }
    $unpacked = Join-Path (Split-Path -Parent $ExePath) "resources\app.asar.unpacked"
    if (-not (Test-Path -LiteralPath $unpacked)) {
        return $true
    }
    try {
        . $apply
        if (Get-Command Invoke-DragonAIDesktopBrandingOverlay -ErrorAction SilentlyContinue) {
            Invoke-DragonAIDesktopBrandingOverlay -ExePath $ExePath -Quiet | Out-Null
            return $true
        }
    } catch {
        if ($_.Exception.Message -like "Refuse *outside DragonAIAgent*") { throw }
        Write-Warning "Dragon AI Agent UI overlay skipped: $($_.Exception.Message)"
    }
    return $false
}

function Start-DragonAIDesktopClient {
    param(
        [Parameter(Mandatory = $true)][string]$ExePath,
        [string]$InstallRoot = ""
    )
    Assert-DragonAIPrivateDesktopPath -Path $ExePath -Role "launch"
    if (Test-DragonAIHermesInstallPath -Path $ExePath) {
        throw "Refuse launch of a Hermes install: $ExePath"
    }
    Set-DragonAIDesktopUserDataEnv -InstallRoot $InstallRoot | Out-Null
    $wd = Split-Path -Parent $ExePath
    Exclude-DragonAIHermesBots | Out-Null
    try {
        Apply-DragonAIDesktopUiBranding -ExePath $ExePath | Out-Null
    } catch {
        if ($_.Exception.Message -like "Refuse *outside DragonAIAgent*") { throw }
    }
    try {
        $picker = Join-Path $PSScriptRoot "teams_picker.py"
        $py = Get-Command python3 -ErrorAction SilentlyContinue
        if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
        $install = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
        $desktop = Join-Path $env:LOCALAPPDATA "hermes\profiles"
        $embedded = Join-Path $env:USERPROFILE ".hermes-airmaze-embedded\profiles"
        if ($py -and (Test-Path -LiteralPath $picker)) {
            Start-Process -FilePath $py.Source -ArgumentList @(
                $picker, "serve", "--payload", $install, "--install", $install,
                "--desktop", $desktop, "--embedded", $embedded,
                "--host", "127.0.0.1", "--port", "8653"
            ) -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
        }
        $voice = Join-Path $PSScriptRoot "voice_chat.py"
        $voiceHome = Join-Path $env:USERPROFILE ".hermes-airmaze-embedded"
        if ($py -and (Test-Path -LiteralPath $voice)) {
            Start-Process -FilePath $py.Source -ArgumentList @(
                $voice, "serve", "--home", $voiceHome,
                "--host", "127.0.0.1", "--port", "8654"
            ) -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
        }
    } catch {}
    $proc = $null
    try {
        $proc = Start-Process -FilePath $ExePath -WorkingDirectory $wd -PassThru -ErrorAction Stop
    } catch {
        $msg = "Dragon AI Agent did not start. $($_.Exception.Message)"
        Write-LaunchResult -Ok $false -ErrorMessage $msg -InstallRoot $InstallRoot
        throw $msg
    }
    Start-Sleep -Milliseconds 1200
    if ($proc -and $proc.HasExited) {
        $msg = "Dragon AI Agent exited immediately (code $($proc.ExitCode)). No window was shown."
        Write-LaunchResult -Ok $false -ErrorMessage $msg -InstallRoot $InstallRoot -PidValue $proc.Id
        throw $msg
    }
    Write-LaunchResult -Ok $true -Message "Dragon AI Agent process is running." -InstallRoot $InstallRoot -PidValue $(if ($proc) { $proc.Id } else { 0 })
    Set-DragonAIMainWindowTitle -Title "Dragon AI Agent" | Out-Null
    return $true
}

function Write-LaunchResult {
    param(
        [bool]$Ok,
        [string]$Message = "",
        [string]$ErrorMessage = "",
        [string]$InstallRoot = "",
        [int]$PidValue = 0
    )
    $root = Get-DragonAIInstallRoot -InstallRoot $InstallRoot
    $obj = [ordered]@{
        ok      = [bool]$Ok
        action  = "start-desktop"
        message = $Message
        error   = $ErrorMessage
        pid     = $PidValue
        exe     = "desktop\win-unpacked\DragonAIAgent.exe"
    }
    try {
        if (-not (Test-Path -LiteralPath $root)) {
            New-Item -ItemType Directory -Force -Path $root | Out-Null
        }
        ($obj | ConvertTo-Json) | Set-Content -LiteralPath (Join-Path $root "launch-result.json") -Encoding UTF8
    } catch {}
    if (-not $Ok) {
        if (Get-Command Show-DragonDialog -ErrorAction SilentlyContinue) {
            Show-DragonDialog -Message $ErrorMessage -Kind Error
        } else {
            try {
                Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
                [System.Windows.Forms.MessageBox]::Show($ErrorMessage, "Dragon AI Agent") | Out-Null
            } catch {}
        }
    }
}

function Start-HermesDesktopClient {
    param(
        [Parameter(Mandatory = $true)][string]$ExePath,
        [string]$InstallRoot = ""
    )
    return (Start-DragonAIDesktopClient -ExePath $ExePath -InstallRoot $InstallRoot)
}
