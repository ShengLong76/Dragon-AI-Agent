#requires -Version 5.1
<#
.SYNOPSIS
  Locate a *source* Hermes.exe, then launch the private Dragon AI copy.

.DESCRIPTION
  Hermes and Dragon AI are separate programs. Standalone UltraDragon Hermes
  stays at e.g.
  %LOCALAPPDATA%\hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe
  Dragon AI copies that win-unpacked tree to
  %LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked
  and sets HERMES_DESKTOP_USER_DATA_DIR to
  %LOCALAPPDATA%\DragonAIAgent\electron-userdata.
  Branding / window rename never touch the standalone tree.
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
    return (Join-Path (Get-DragonAIInstallRoot -InstallRoot $InstallRoot) "desktop\win-unpacked\Hermes.exe")
}

function Get-DragonAIElectronUserDataDir {
    param([string]$InstallRoot = "")
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
    return $dir
}

function Get-HermesDesktopExactCandidates {
    # Source-only standalone Hermes locations. Do not brand these.
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

function Find-HermesDesktopSourceExe {
    param([string]$InstallRoot = "")

    foreach ($c in Get-HermesDesktopExactCandidates) {
        if ($c -and (Test-Path -LiteralPath $c) -and -not (Test-DragonAIPrivateDesktopPath -Path $c)) {
            return $c
        }
    }

    foreach ($root in Get-HermesDesktopSearchRoots) {
        if (-not $root -or -not (Test-Path -LiteralPath $root)) { continue }
        try {
            $hit = Get-ChildItem -LiteralPath $root -Filter "Hermes.exe" -Recurse -File -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.Name -eq "Hermes.exe" -and -not (Test-DragonAIPrivateDesktopPath -Path $_.FullName) -and (
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

function Copy-DragonAIWinUnpackedTree {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDir,
        [Parameter(Mandatory = $true)][string]$DestDir
    )
    Assert-DragonAIPrivateDesktopPath -Path $DestDir -Role "copy-dest"
    if (Test-DragonAIPrivateDesktopPath -Path $SourceDir) {
        return
    }
    if (-not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
        throw "Source win-unpacked folder missing: $SourceDir"
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
    $destExe = Get-DragonAIPrivateDesktopExe -InstallRoot $InstallRoot
    $destDir = Split-Path -Parent $destExe
    if (Test-Path -LiteralPath $destExe) { return $destExe }
    if (-not (Test-Path -LiteralPath $SourceExe)) { return $null }
    if (Test-DragonAIPrivateDesktopPath -Path $SourceExe) { return $SourceExe }
    $srcDir = Split-Path -Parent $SourceExe
    $engine = Join-Path $PSScriptRoot "private_desktop.py"
    $py = Get-Command python3 -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
    if ($py -and (Test-Path -LiteralPath $engine)) {
        try {
            $json = & $py.Source $engine copy --source $SourceExe --dest-root (Get-DragonAIInstallRoot -InstallRoot $InstallRoot) 2>&1 | Out-String
            if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $destExe)) { return $destExe }
        } catch {}
    }
    Copy-DragonAIWinUnpackedTree -SourceDir $srcDir -DestDir $destDir
    if (Test-Path -LiteralPath $destExe) { return $destExe }
    return $null
}

function Install-DragonAIPrivateDesktop {
    param([string]$InstallRoot = "")
    $dest = Get-DragonAIPrivateDesktopExe -InstallRoot $InstallRoot
    if (Test-Path -LiteralPath $dest) { return $dest }
    $src = Find-HermesDesktopSourceExe -InstallRoot $InstallRoot
    if (-not $src) { return $null }
    return (Copy-DragonAIPrivateDesktopFromSource -SourceExe $src -InstallRoot $InstallRoot)
}

function Find-HermesDesktopExe {
    param([string]$InstallRoot = "")

    $private = Get-DragonAIPrivateDesktopExe -InstallRoot $InstallRoot
    if (Test-Path -LiteralPath $private) { return $private }

    $pointer = Get-DragonAIDesktopPointerPath -InstallRoot $InstallRoot
    if (Test-Path -LiteralPath $pointer) {
        try {
            $saved = Get-Content -LiteralPath $pointer -Raw -Encoding UTF8 | ConvertFrom-Json
            $savedExe = [string]$saved.exe
            if ($savedExe -and (Test-Path -LiteralPath $savedExe)) {
                if (Test-DragonAIPrivateDesktopPath -Path $savedExe) { return $savedExe }
                $copied = Copy-DragonAIPrivateDesktopFromSource -SourceExe $savedExe -InstallRoot $InstallRoot
                if ($copied) { return $copied }
            }
        } catch {}
    }

    return (Install-DragonAIPrivateDesktop -InstallRoot $InstallRoot)
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
        notes            = "Private Dragon AI copy. On-disk filename stays Hermes.exe. Standalone Hermes tree is not mutated."
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
        # Taskbar grouping: match upstream Hermes.exe AppUserModelID so the
        # Dragon ICO on this .lnk can represent the running process.
        Set-DragonAIShortcutAppUserModelId -LnkPath $lnkPath -AppUserModelId "com.nousresearch.hermes"
    } catch {}

    return $pointer
}

function Set-DragonAIShortcutAppUserModelId {
    param(
        [Parameter(Mandatory = $true)][string]$LnkPath,
        [string]$AppUserModelId = "com.nousresearch.hermes"
    )
    if (-not (Test-Path -LiteralPath $LnkPath)) { return $false }
    try {
        if (-not ("DragonAIShortcutAumid" -as [type])) {
            Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

[ComImport, Guid("00021401-0000-0000-C000-000000000046")]
public class DragonAIShellLinkCoClass {}

[ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("000214F9-0000-0000-C000-000000000046")]
public interface IDragonAIShellLinkW {
    void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszFile, int cchMaxPath, IntPtr pfd, uint fFlags);
    void GetIDList(out IntPtr ppidl);
    void SetIDList(IntPtr pidl);
    void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszName, int cchMaxName);
    void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string pszName);
    void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszDir, int cchMaxPath);
    void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string pszDir);
    void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszArgs, int cchMaxPath);
    void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string pszArgs);
    void GetHotkey(out short pwHotkey);
    void SetHotkey(short wHotkey);
    void GetShowCmd(out int piShowCmd);
    void SetShowCmd(int iShowCmd);
    void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszIconPath, int cchIconPath, out int piIcon);
    void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string pszIconPath, int iIcon);
    void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string pszPathRel, uint dwReserved);
    void Resolve(IntPtr hwnd, uint fFlags);
    void SetPath([MarshalAs(UnmanagedType.LPWStr)] string pszFile);
}

[StructLayout(LayoutKind.Sequential, Pack = 4)]
public struct DragonAIPROPERTYKEY { public Guid fmtid; public uint pid; }

[StructLayout(LayoutKind.Sequential)]
public struct DragonAIPROPVARIANT {
    public ushort vt;
    public ushort wReserved1, wReserved2, wReserved3;
    public IntPtr pszVal;
}

[ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")]
public interface IDragonAIPropertyStore {
    uint GetCount(out uint cProps);
    uint GetAt(uint iProp, out DragonAIPROPERTYKEY pkey);
    uint GetValue(ref DragonAIPROPERTYKEY key, out DragonAIPROPVARIANT pv);
    uint SetValue(ref DragonAIPROPERTYKEY key, ref DragonAIPROPVARIANT pv);
    uint Commit();
}

public static class DragonAIShortcutAumid {
    public static void Set(string lnkPath, string appId) {
        var link = (IDragonAIShellLinkW)new DragonAIShellLinkCoClass();
        var persist = (IPersistFile)link;
        persist.Load(lnkPath, 0);
        var store = (IDragonAIPropertyStore)link;
        var key = new DragonAIPROPERTYKEY {
            fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"),
            pid = 5
        };
        var pv = new DragonAIPROPVARIANT { vt = 31, pszVal = Marshal.StringToCoTaskMemUni(appId) };
        store.SetValue(ref key, ref pv);
        store.Commit();
        persist.Save(lnkPath, true);
        Marshal.FreeCoTaskMem(pv.pszVal);
    }
}
"@
        }
        [DragonAIShortcutAumid]::Set($LnkPath, $AppUserModelId)
        return $true
    } catch {
        return $false
    }
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
    <#
    .SYNOPSIS
      Rename the unpacked Electron window to Dragon AI Agent (packaging wrap).
      Only processes whose path is under DragonAIAgent (private desktop).
      Taskbar AppUserModelID / About / tray still need a rebuilt client binary.
    #>
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
        $procs += @(Get-Process -Name "Hermes" -ErrorAction SilentlyContinue)
        $procs += @(Get-Process -Name "hermes-agent" -ErrorAction SilentlyContinue)
        # Window rename only for the private Dragon path - never standalone Hermes.
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
    <#
    .SYNOPSIS
      Rewrite unpacked Electron renderer product chrome to Dragon AI Agent.
      Private DragonAIAgent copy only. Does not rebuild Hermes.exe and does
      not touch app.asar integrity or the standalone Hermes tree.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$ExePath
    )
    Assert-DragonAIPrivateDesktopPath -Path $ExePath -Role "branding"
    $apply = Join-Path $PSScriptRoot "Apply-DesktopBranding.ps1"
    if (-not (Test-Path -LiteralPath $apply)) {
        return $false
    }
    try {
        . $apply
        if (Get-Command Invoke-DragonAIDesktopBrandingOverlay -ErrorAction SilentlyContinue) {
            Invoke-DragonAIDesktopBrandingOverlay -ExePath $ExePath -Quiet | Out-Null
            return $true
        }
    } catch {
        Write-Warning "Dragon AI Agent UI overlay failed: $($_.Exception.Message)"
        throw
    }
    return $false
}

function Start-HermesDesktopClient {
    param(
        [Parameter(Mandatory = $true)][string]$ExePath,
        [string]$InstallRoot = ""
    )
    Assert-DragonAIPrivateDesktopPath -Path $ExePath -Role "launch"
    Set-DragonAIDesktopUserDataEnv -InstallRoot $InstallRoot | Out-Null
    $wd = Split-Path -Parent $ExePath
    # Overlay empty-state / composer / settings copy before the window opens.
    # PowerShell copies dragon-ui.css + inject even when python3 is not on PATH.
    # Branding is refused outside DragonAIAgent.
    Exclude-DragonAIHermesBots | Out-Null
    try {
        Apply-DragonAIDesktopUiBranding -ExePath $ExePath | Out-Null
    } catch {
        if ($_.Exception.Message -like "Refuse *outside DragonAIAgent*") { throw }
        Write-Warning "Dragon AI Agent UI overlay did not update unpacked dist: $($_.Exception.Message)"
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
    Start-Process -FilePath $ExePath -WorkingDirectory $wd -ErrorAction Stop
    Set-DragonAIMainWindowTitle -Title "Dragon AI Agent" | Out-Null
    return $true
}
