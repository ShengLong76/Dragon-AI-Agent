#requires -Version 5.1
<#
.SYNOPSIS
  Dragon AI Agent v0.1.0 Windows bootstrap installer.

.DESCRIPTION
  Provisions WSL2 and Docker Desktop (Setup-owned: packaged installer, then
  Setup-owned download, quiet install, half-install repair; fully invisible:
  no dashboard, no onboarding, no tray icon, no docker.com page), then the
  embedded gateway, bot group dropdown, and desktop.

.NOTES
  Log: %LOCALAPPDATA%\DragonAIAgent\install.log
  Package files: %LOCALAPPDATA%\DragonAIAgent\
  Data: %USERPROFILE%\.hermes-airmaze-embedded  (internal gateway data dir)
#>

[CmdletBinding()]
param(
    [string]$PayloadRoot = "",
    [string]$BotGroupId = "",
    [string]$ProfileId = "",
    [string]$ImportBotGroup = "",
    [string]$ImportProfile = "",
    [switch]$SkipBotGroupPrompt,
    [switch]$SkipProfilePrompt
)

$ErrorActionPreference = "Continue"
$ProductName = "Dragon AI Agent"
$ProductVersion = "0.1.0"
$InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
$LogPath = Join-Path $InstallRoot "install.log"
$DataDir = Join-Path $env:USERPROFILE ".hermes-airmaze-embedded"
$DockerSettingsDir = Join-Path $env:APPDATA "Docker"
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Dragon AI Agent"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO", [switch]$FileOnly)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    if (-not $FileOnly) {
        Write-Host $line
    }
    try {
        if (-not (Test-Path -LiteralPath $InstallRoot)) {
            New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
        }
        Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {}
}

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-ElevatedIfNeeded {
    param([string]$Reason)
    if (Test-IsAdmin) { return $true }
    Write-Log "Elevation may be required: $Reason" "WARN"
    return $false
}

function Resolve-PayloadRoot {
    if (-not [string]::IsNullOrWhiteSpace($PayloadRoot) -and (Test-Path -LiteralPath $PayloadRoot)) {
        return (Resolve-Path -LiteralPath $PayloadRoot).Path
    }
    if ($PSScriptRoot) {
        $candidate = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
        if (Test-Path (Join-Path $candidate "docker-compose.embedded.yml")) { return $candidate }
        $candidate2 = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
        if (Test-Path (Join-Path $candidate2 "docker-compose.embedded.yml")) { return $candidate2 }
        if (Test-Path (Join-Path $PSScriptRoot "docker-compose.embedded.yml")) { return $PSScriptRoot }
    }
    $here = (Get-Location).Path
    if (Test-Path (Join-Path $here "docker-compose.embedded.yml")) { return $here }
    throw "Cannot locate payload root (docker-compose.embedded.yml). Pass -PayloadRoot."
}

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

# --- Docker Desktop: invisible engine (no window / tray / onboarding) ------

function Set-DockerHeadlessSettings {
    Write-Log "Configuring Docker Desktop for invisible engine start (no dashboard, no onboarding, no tray)." -FileOnly
    Ensure-Dir $DockerSettingsDir

    # PowerShell hashtables are case-insensitive. camelCase only in this $patch.
    # settings-store.json gets a separate PascalCase table below.
    $legacy = @{
        openUIOnStartupDisabled = $true
        openAtLogin             = $true
        autoStart               = $true
        startMinimized          = $true
        minimizeToTray          = $true
        displayedOnboarding     = $true
        displayedTutorial       = $true
        analyticsEnabled        = $false
        disableTips             = $true
        licenseTermsVersion     = 2
        disableTrayIcon         = $true
        enableDockerAI          = $false
    }
    $store = @{
        OpenUIOnStartupDisabled = $true
        AutoStart               = $true
        DisplayedOnboarding     = $true
        DisplayedTutorial       = $true
        AnalyticsEnabled        = $false
        DisableTips             = $true
        LicenseTermsVersion     = 2
        DisableTrayIcon         = $true
        EnableDockerAI          = $false
    }

    $targets = @(
        @{ File = (Join-Path $DockerSettingsDir "settings.json"); Patch = $legacy },
        @{ File = (Join-Path $DockerSettingsDir "settings-store.json"); Patch = $store }
    )

    foreach ($target in $targets) {
        $file = $target.File
        $patch = $target.Patch
        try {
            $obj = $null
            if (Test-Path -LiteralPath $file) {
                $raw = Get-Content -LiteralPath $file -Raw -ErrorAction Stop
                if (-not [string]::IsNullOrWhiteSpace($raw)) {
                    $obj = $raw | ConvertFrom-Json -ErrorAction Stop
                }
            }
            if ($null -eq $obj) {
                $obj = [pscustomobject]@{}
            }
            foreach ($k in $patch.Keys) {
                $obj | Add-Member -MemberType NoteProperty -Name $k -Value $patch[$k] -Force
            }
            $json = $obj | ConvertTo-Json -Depth 20
            Set-Content -LiteralPath $file -Value $json -Encoding UTF8
            Write-Log "Patched Docker settings: $file" -FileOnly
        } catch {
            Write-Log "Could not patch $file : $($_.Exception.Message)" "WARN" -FileOnly
        }
    }
}

function Set-DockerTrayOnlySettings {
    Set-DockerHeadlessSettings
}

function Get-DockerDesktopExe {
    $candidates = @(
        (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Docker\Docker\Docker Desktop.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe"),
        (Join-Path $env:LOCALAPPDATA "Docker\Docker Desktop.exe")
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path -LiteralPath $c)) { return $c }
    }
    return $null
}

function Test-DockerEngine {
    try {
        Fix-DockerPath
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { return $false }
        $null = & docker info 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Get-DockerBackendExe {
    $dirs = @()
    $desktop = Get-DockerDesktopExe
    if ($desktop) {
        $dirs += (Join-Path (Split-Path -Parent $desktop) "resources")
    }
    $dirs += @(
        (Join-Path $env:ProgramFiles "Docker\Docker\resources"),
        (Join-Path ${env:ProgramFiles(x86)} "Docker\Docker\resources"),
        (Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources"),
        (Join-Path $env:LOCALAPPDATA "Docker\resources")
    )
    foreach ($d in $dirs) {
        if (-not $d) { continue }
        $p = Join-Path $d "com.docker.backend.exe"
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $null
}

function Start-HiddenNativeProcess {
    param([string]$FilePath, [string]$Arguments = "")
    if (-not $FilePath -or -not (Test-Path -LiteralPath $FilePath)) { return }
    try {
        $si = New-Object System.Diagnostics.ProcessStartInfo
        $si.FileName = $FilePath
        if (-not [string]::IsNullOrWhiteSpace($Arguments)) { $si.Arguments = $Arguments }
        $si.UseShellExecute = $false
        $si.CreateNoWindow = $true
        $si.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
        [void][System.Diagnostics.Process]::Start($si)
        return
    } catch {}
    try {
        Start-Process -FilePath $FilePath -WindowStyle Hidden -ErrorAction Stop
    } catch {
        Start-Process -FilePath $FilePath -ErrorAction SilentlyContinue
    }
}

function Hide-DockerDesktopUi {
    <#
      Hide Docker Desktop windows. After the engine is up, stop Docker Desktop.exe
      so the whale tray icon is not shown. com.docker.service / backend stay.
    #>
    try {
        if (-not ("DragonAIDockerUi" -as [type])) {
            Add-Type @"
using System;
using System.Runtime.InteropServices;
public class DragonAIDockerUi {
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
        }
    } catch {}
    $uiNames = @("Docker Desktop", "DockerDesktop")
    foreach ($p in Get-Process -ErrorAction SilentlyContinue) {
        if ($uiNames -notcontains $p.ProcessName) { continue }
        try {
            if ($p.MainWindowHandle -ne [IntPtr]::Zero) {
                [DragonAIDockerUi]::ShowWindow($p.MainWindowHandle, 0) | Out-Null
            }
        } catch {}
    }
}

function Stop-DockerDesktopTrayIfEngineUp {
    if (-not (Test-DockerEngine)) { return }
    $svc = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
    if (-not $svc -or $svc.Status -ne "Running") { return }
    foreach ($p in Get-Process -Name "Docker Desktop","DockerDesktop" -ErrorAction SilentlyContinue) {
        try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
    Start-Sleep -Milliseconds 400
    if (-not (Test-DockerEngine)) {
        Write-Log "Engine dropped after hiding Docker Desktop UI; backend will be restarted if needed." "WARN" -FileOnly
    }
}

function Start-DockerHeadless {
    Write-Log "Starting background engine (invisible; no dashboard, no tray, no onboarding)." -FileOnly
    Fix-DockerPath
    Set-DockerHeadlessSettings
    $env:DOCKER_DESKTOP_DISABLE_LOGIN = "1"

    if (Test-DockerEngine) {
        Hide-DockerDesktopUi
        Stop-DockerDesktopTrayIfEngineUp
        return $true
    }

    $svc = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
    if ($svc) {
        if ($svc.Status -ne "Running") {
            try {
                if (Test-IsAdmin) {
                    Start-Service -Name "com.docker.service" -ErrorAction Stop
                    Write-Log "Started com.docker.service" -FileOnly
                } else {
                    Write-Log "com.docker.service present but not running; elevating service start" "WARN" -FileOnly
                    Start-Process -FilePath "net" -ArgumentList "start","com.docker.service" -Verb RunAs -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue
                }
            } catch {
                Write-Log "Service start failed: $($_.Exception.Message)" "WARN" -FileOnly
            }
        } else {
            Write-Log "com.docker.service already running" -FileOnly
        }
    }

    $backend = Get-DockerBackendExe
    if ($backend -and -not (Test-DockerEngine)) {
        Write-Log "Starting com.docker.backend.exe hidden: $backend" -FileOnly
        Start-HiddenNativeProcess -FilePath $backend
    }

    if (-not (Test-DockerEngine)) {
        $exe = Get-DockerDesktopExe
        if ($exe) {
            Write-Log "Starting Docker Desktop.exe hidden (last resort, UI will be hidden): $exe" -FileOnly
            Start-HiddenNativeProcess -FilePath $exe
        } else {
            Write-Log "Docker Desktop.exe not found on disk yet" "WARN" -FileOnly
        }
    }

    $deadline = (Get-Date).AddMinutes(3)
    while ((Get-Date) -lt $deadline) {
        Hide-DockerDesktopUi
        if (Test-DockerEngine) {
            Hide-DockerDesktopUi
            Stop-DockerDesktopTrayIfEngineUp
            Write-Log "Docker engine is ready" -FileOnly
            return $true
        }
        Start-Sleep -Seconds 5
    }
    Hide-DockerDesktopUi
    Write-Log "Docker engine not ready within timeout" "WARN" -FileOnly
    return $false
}

# --- WSL2 -------------------------------------------------------------------

function Ensure-WSL2 {
    Write-Log "Checking WSL2..."
    $wsl = Get-Command wsl -ErrorAction SilentlyContinue
    if ($wsl) {
        try {
            $status = & wsl --status 2>&1 | Out-String
            Write-Log "WSL present. Status snippet: $($status.Substring(0, [Math]::Min(200, $status.Length)))"
            return $true
        } catch {
            Write-Log "wsl exists but status failed: $($_.Exception.Message)" "WARN"
        }
    }

    Write-Log "WSL missing or incomplete; attempting wsl --install (reboot may be required)..."
    Invoke-ElevatedIfNeeded "Enable WSL2 / VirtualMachinePlatform"
    try {
        if (Test-IsAdmin) {
            dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart 2>&1 | Out-Null
            dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart 2>&1 | Out-Null
        }
        & wsl --install --no-distribution 2>&1 | ForEach-Object { Write-Log "wsl: $_" }
        if ($LASTEXITCODE -ne 0) {
            & wsl --install 2>&1 | ForEach-Object { Write-Log "wsl: $_" }
        }
        Write-Log "WSL install invoked. A REBOOT may be required before Docker Desktop works." "WARN"
    } catch {
        Write-Log "WSL install attempt failed: $($_.Exception.Message). Install WSL2 manually, then re-run." "ERROR"
        return $false
    }
    return $true
}

# --- Docker Desktop install (Setup owns this; not a user prerequisite) ------

function Test-DockerCliPresent {
    Fix-DockerPath
    return [bool](Get-Command docker -ErrorAction SilentlyContinue)
}

function Test-DockerDesktopComplete {
    # Exe + CLI. Engine-up is Start-DockerHeadless, not "installed".
    return ([bool](Get-DockerDesktopExe) -and (Test-DockerCliPresent))
}

function Find-BundledDockerInstaller {
    param([string]$PayloadRoot = "")
    $names = @(
        "Docker Desktop Installer.exe",
        "DockerDesktopInstaller.exe",
        "DockerDesktopInstaller-DragonAIAgent.exe"
    )
    $dirs = @()
    if (-not [string]::IsNullOrWhiteSpace($PayloadRoot)) {
        $dirs += (Join-Path $PayloadRoot "vendor\docker")
        $dirs += (Join-Path $PayloadRoot "installer\vendor\docker")
    }
    if ($PSScriptRoot) {
        $dirs += (Join-Path $PSScriptRoot "vendor\docker")
        $dirs += (Join-Path $PSScriptRoot "..\vendor\docker")
        $dirs += (Join-Path $PSScriptRoot "..\..\vendor\docker")
        $dirs += (Join-Path $PSScriptRoot "installer\vendor\docker")
    }
    $dirs += (Join-Path $InstallRoot "vendor\docker")
    foreach ($dir in $dirs) {
        if (-not $dir) { continue }
        foreach ($name in $names) {
            $p = Join-Path $dir $name
            if (Test-Path -LiteralPath $p) { return $p }
        }
    }
    return $null
}

function Get-DockerInstallerCachePath {
    $dir = Join-Path $InstallRoot "vendor\docker"
    Ensure-Dir $dir
    return (Join-Path $dir "Docker Desktop Installer.exe")
}

function Save-DockerInstallerFromUrl {
    param([string]$Dest)
    $url = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    $destDir = Split-Path $Dest -Parent
    Ensure-Dir $destDir
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Write-Log "Downloading Docker Desktop installer (Setup-owned, not a separate manual install)..." -FileOnly
    Invoke-WebRequest -Uri $url -OutFile $Dest -UseBasicParsing -ErrorAction Stop
    if (-not (Test-Path -LiteralPath $Dest)) { throw "Download produced no file: $Dest" }
    return $Dest
}

function Resolve-DockerInstaller {
    param([string]$PayloadRoot)
    $bundled = Find-BundledDockerInstaller -PayloadRoot $PayloadRoot
    if ($bundled) {
        Write-Log "Using packaged Docker Desktop installer: $bundled" -FileOnly
        return $bundled
    }
    $cache = Get-DockerInstallerCachePath
    if (Test-Path -LiteralPath $cache) {
        Write-Log "Using cached Docker Desktop installer: $cache" -FileOnly
        return $cache
    }
    Write-Log "Package has no vendor/docker installer; Setup will download it." -FileOnly
    return (Save-DockerInstallerFromUrl -Dest $cache)
}

function Invoke-DockerDesktopQuietInstall {
    param([string]$InstallerPath)
    Write-Log "Running quiet Docker Desktop install (may need UAC / reboot): $InstallerPath" -FileOnly
    $argList = @("install", "--quiet", "--accept-license", "--always-run-service")
    $start = @{
        FilePath     = $InstallerPath
        ArgumentList = $argList
        Wait         = $true
        PassThru     = $true
        WindowStyle  = "Hidden"
        ErrorAction  = "Stop"
    }
    if (-not (Test-IsAdmin)) {
        $start["Verb"] = "RunAs"
    }
    $p = Start-Process @start
    Write-Log "Docker installer exit code: $($p.ExitCode)" -FileOnly
    # 0 = ok; 3010 = success, reboot required (MSI)
    return ($p.ExitCode -eq 0 -or $p.ExitCode -eq 3010)
}

function Ensure-DockerDesktop {
    param([string]$PayloadRoot = "")
    Write-Log "Checking Docker Desktop (Setup owns this step)..." -FileOnly
    Fix-DockerPath
    if (Test-DockerDesktopComplete) {
        Write-Log "Docker Desktop is already installed" -FileOnly
        Set-DockerHeadlessSettings
        return $true
    }

    if ((Get-DockerDesktopExe) -and -not (Test-DockerCliPresent)) {
        Write-Log "Docker Desktop.exe is present but the CLI is missing (half-installed); Setup will repair via quiet install." "WARN" -FileOnly
    } elseif (-not (Get-DockerDesktopExe)) {
        Write-Log "Docker Desktop is not installed; Setup will install it from the package or a Setup-owned download." -FileOnly
    }

    try {
        $installer = Resolve-DockerInstaller -PayloadRoot $PayloadRoot
        $ok = Invoke-DockerDesktopQuietInstall -InstallerPath $installer
        Fix-DockerPath
        Set-DockerHeadlessSettings
        if (Get-DockerDesktopExe) {
            if (-not (Test-DockerCliPresent)) {
                Write-Log "Docker Desktop.exe landed but CLI is not on PATH yet; PATH will be patched for this session." "WARN" -FileOnly
            }
            return $true
        }
        if (-not $ok) {
            Write-Log "Quiet Docker install did not produce Docker Desktop.exe (exit indicated failure)." "ERROR" -FileOnly
        }
    } catch {
        Write-Log "Setup-owned Docker install failed: $($_.Exception.Message)" "ERROR" -FileOnly
    }

    Write-Log "Background engine is not installed yet. Package files will still be copied. Re-run Dragon AI Agent Setup after a reboot if Windows asked for one." "WARN" -FileOnly
    return $false
}

function Fix-DockerPath {
    $binDirs = @(
        (Join-Path $env:ProgramFiles "Docker\Docker\resources\bin"),
        (Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin"),
        (Join-Path $env:LOCALAPPDATA "Docker\resources\bin")
    )
    foreach ($d in $binDirs) {
        if ((Test-Path -LiteralPath $d) -and ($env:PATH -notlike "*$d*")) {
            $env:PATH = "$d;$env:PATH"
            Write-Log "Prepended Docker bin to PATH: $d" -FileOnly
        }
    }
}

# --- Package files + gateway ------------------------------------------------

function Install-PackageFiles([string]$Root) {
    Write-Log "Writing package files to $InstallRoot"
    Ensure-Dir $InstallRoot
    Ensure-Dir (Join-Path $InstallRoot "scripts\airmaze")
    Ensure-Dir (Join-Path $InstallRoot "templates\profiles\personal-assistant")
    Ensure-Dir (Join-Path $InstallRoot "docs\airmaze")
    Ensure-Dir (Join-Path $InstallRoot "bot-groups")
    Ensure-Dir (Join-Path $InstallRoot "branding")

    $composeSrc = Join-Path $Root "docker-compose.embedded.yml"
    if (Test-Path $composeSrc) {
        Copy-Item -LiteralPath $composeSrc -Destination (Join-Path $InstallRoot "docker-compose.embedded.yml") -Force
    }

    # Copy bot-groups catalog tree (GitHub overlay; survives an upstream desktop-agent sync)
    $groupsSrc = Join-Path $Root "bot-groups"
    if (Test-Path $groupsSrc) {
        Copy-Item -Path $groupsSrc -Destination (Join-Path $InstallRoot "bot-groups") -Recurse -Force
        Write-Log "Copied bot-groups catalog"
    }

    $deskSrc = Join-Path $Root "desktop\win-unpacked"
    if (-not (Test-Path -LiteralPath (Join-Path $deskSrc "DragonAIAgent.exe"))) {
        $deskSrc = Join-Path $Root "vendor\desktop\win-unpacked"
    }
    if (Test-Path -LiteralPath (Join-Path $deskSrc "DragonAIAgent.exe")) {
        $deskDst = Join-Path $InstallRoot "desktop\win-unpacked"
        Ensure-Dir $deskDst
        Copy-Item -Path (Join-Path $deskSrc "*") -Destination $deskDst -Recurse -Force
        Write-Log "Copied packaged Dragon AI Agent desktop"
    }

    # Branding / logo
    foreach ($logoName in @("dragon-ai-agent-logo.png", "dragon-ai-agent-logo.ico", "dragon-ai-agent-logo.svg")) {
        $logoSrc = Join-Path $Root $logoName
        if (-not (Test-Path $logoSrc)) { $logoSrc = Join-Path $Root "branding\$logoName" }
        if (-not (Test-Path $logoSrc)) {
            throw "Install refused: missing required Dragon logo $logoName (branding\$logoName)"
        }
        Copy-Item -LiteralPath $logoSrc -Destination (Join-Path $InstallRoot "branding\$logoName") -Force
        Copy-Item -LiteralPath $logoSrc -Destination (Join-Path $InstallRoot $logoName) -Force
        Write-Log "Copied logo $logoName"
    }

    $winresSrc = Join-Path $Root "installer\winres\icon.ico"
    if (Test-Path -LiteralPath $winresSrc) {
        $winresDstDir = Join-Path $InstallRoot "installer\winres"
        Ensure-Dir $winresDstDir
        Copy-Item -LiteralPath $winresSrc -Destination (Join-Path $winresDstDir "icon.ico") -Force
        Write-Log "Copied installer/winres/icon.ico (taskbar/tray ICO)"
    }

    $fontsSrc = Join-Path $Root "branding\fonts"
    if (-not (Test-Path -LiteralPath $fontsSrc)) {
        $fontsSrc = Join-Path $PSScriptRoot "..\..\branding\fonts"
    }
    if (Test-Path -LiteralPath $fontsSrc) {
        $fontsDstParent = Join-Path $InstallRoot "branding"
        Ensure-Dir $fontsDstParent
        Copy-Item -Path $fontsSrc -Destination $fontsDstParent -Recurse -Force
        Write-Log "Copied branding/fonts (Syne wordmark face)"
    }

    $teamsSrc = Join-Path $Root "branding\teams"
    if (-not (Test-Path -LiteralPath $teamsSrc)) {
        $teamsSrc = Join-Path $PSScriptRoot "..\..\branding\teams"
    }
    if (Test-Path -LiteralPath $teamsSrc) {
        $brandingDst = Join-Path $InstallRoot "branding"
        Ensure-Dir $brandingDst
        Copy-Item -Path $teamsSrc -Destination $brandingDst -Recurse -Force
        Write-Log "Copied branding/teams seat icons"
    }

    $voiceSrc = Join-Path $Root "branding\voice"
    if (-not (Test-Path -LiteralPath $voiceSrc)) {
        $voiceSrc = Join-Path $PSScriptRoot "..\..\branding\voice"
    }
    if (Test-Path -LiteralPath $voiceSrc) {
        $voiceDstParent = Join-Path $InstallRoot "branding"
        Ensure-Dir $voiceDstParent
        Copy-Item -Path $voiceSrc -Destination $voiceDstParent -Recurse -Force
        Write-Log "Copied branding/voice (Grok duplex overlay)"
    }

    foreach ($rel in @(
        "scripts\airmaze\start-embedded.ps1",
        "scripts\airmaze\apply-default-bot-group.ps1",
        "scripts\airmaze\apply-default-profile.ps1",
        "scripts\airmaze\install.ps1",
        "scripts\airmaze\bot_groups.py",
        "scripts\airmaze\Test-BotGroups.py",
        "scripts\airmaze\Select-BotGroup.ps1",
        "scripts\airmaze\Deploy-BotGroup.ps1",
        "scripts\airmaze\Export-BotGroup.ps1",
        "scripts\airmaze\Import-BotGroup.ps1",
        "scripts\airmaze\Apply-Profile.ps1",
        "scripts\airmaze\Select-Profile.ps1",
        "scripts\airmaze\Import-Profile.ps1",
        "docs\airmaze\BOT_GROUPS.md",
        "scripts\airmaze\Onboard-Wizard.ps1",
        "scripts\airmaze\gateway_models.py",
        "scripts\airmaze\Apply-GatewayModels.ps1",
        "scripts\airmaze\Test-GatewayModels.py",
        "docs\airmaze\FIRST_RUN_MODELS.md",
        "scripts\airmaze\voice_chat.py",
        "scripts\airmaze\Apply-VoiceChat.ps1",
        "scripts\airmaze\patch_grok_voice_mode.py",
        "scripts\airmaze\Test-VoiceChat.py",
        "docs\airmaze\VOICE.md",
        "docs\airmaze\DOCKER_LAUNCH.md",
        "docs\airmaze\DOCKER_INSTALL.md",
        "scripts\airmaze\Test-DockerInstall.py",
        "vendor\docker\README.md",
        "installer\stage-docker-desktop.py",
        "docs\airmaze\WINDOWS_LAUNCH_PARSE.md",
        "scripts\airmaze\Test-WindowsLaunchParse.py",
        "scripts\airmaze\DragonAI-SecureStore.ps1",
        "scripts\airmaze\Find-HermesDesktop.ps1",
        "scripts\airmaze\private_desktop.py",
        "scripts\airmaze\Test-PrivateDesktop.py",
        "scripts\airmaze\Test-DragonDesktop.py",
        "vendor\desktop\README.md",
        "desktop\README.md",
        "scripts\airmaze\Apply-DesktopBranding.ps1",
        "scripts\airmaze\desktop_branding.py",
        "scripts\airmaze\desktop_branding.json",
        "scripts\airmaze\Test-DesktopBranding.py",
        "docs\airmaze\PRIVATE_DESKTOP.md",
        "scripts\airmaze\exclude_hermes_bot.py",
        "scripts\airmaze\Test-ExcludeHermesBot.py",
        "scripts\airmaze\teams_picker.py",
        "scripts\airmaze\Test-TeamsPicker.py",
        "scripts\airmaze\team_marketplace.py",
        "scripts\airmaze\Test-TeamsMarketplace.py",
        "docs\airmaze\TEAMS_POPUP.md",
        "docs\airmaze\TEAMS_MARKETPLACE.md",
        "docs\airmaze\PRODUCT_BRANDING.md",
        "scripts\airmaze\Start-DragonAI.vbs",
        "scripts\airmaze\desktop-loopback-proxy.py",
        "scripts\airmaze\start-desktop-serve.sh",
        "scripts\airmaze\start-desktop-proxy.sh",
        "scripts\airmaze\start-gateway.sh",
        "scripts\airmaze\embedded_desktop_connection.py",
        "scripts\airmaze\Set-EmbeddedDesktopConnection.ps1",
        "scripts\airmaze\Test-DesktopServeAdapter.py",
        "templates\profiles\personal-assistant\SOUL.md",
        "templates\profiles\personal-assistant\profile.yaml",
        "docs\airmaze\SETUP_GUIDE.md",
        "docs\airmaze\ARCHITECTURE.md",
        "docs\airmaze\EMBEDDED_GATEWAY.md",
        "docs\airmaze\UPSTREAM_NOTES.md",
        "docs\airmaze\STATUS.md",
        "docs\airmaze\BRANDING.md",
        "README.md",
        "CHANGELOG.md",
        "PACKAGING.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md"
    )) {
        $src = Join-Path $Root $rel
        if (-not (Test-Path $src)) {
            $alt = Join-Path $Root ($rel -replace '^scripts\\airmaze\\','scripts\')
            if (Test-Path $alt) { $src = $alt }
            $alt2 = Join-Path $Root (Split-Path $rel -Leaf)
            if ((-not (Test-Path $src)) -and (Test-Path $alt2)) { $src = $alt2 }
        }
        if (Test-Path $src) {
            $dest = Join-Path $InstallRoot $rel
            $destDir = Split-Path $dest -Parent
            Ensure-Dir $destDir
            Copy-Item -LiteralPath $src -Destination $dest -Force
            Write-Log "Copied $rel"
        } else {
            Write-Log "Missing optional source: $rel" "WARN"
        }
    }

    # Copy all docs/airmaze/*.md (best-effort)
    $docsSrc = Join-Path $Root "docs\airmaze"
    $docsDst = Join-Path $InstallRoot "docs\airmaze"
    if (Test-Path -LiteralPath $docsSrc) {
        Ensure-Dir $docsDst
        Get-ChildItem -LiteralPath $docsSrc -Filter "*.md" -File -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $docsDst $_.Name) -Force
            Write-Log "Copied docs/airmaze/$($_.Name)"
        }
    }

    $thisScript = $MyInvocation.PSCommandPath
    if (-not $thisScript) { $thisScript = $PSCommandPath }
    if ($thisScript -and (Test-Path $thisScript)) {
        Copy-Item -LiteralPath $thisScript -Destination (Join-Path $InstallRoot "install.ps1") -Force
    }

    Ensure-Dir $DataDir
    Write-Log "Data directory: $DataDir"
}

function Remove-DeprecatedProductShortcuts {
    <#
      Start Menu / Desktop keep only the main Dragon AI Agent launcher.
      Delete leftover Bot Groups, Dashboard, Profiles, and Setup .lnk files.
    #>
    $desktop = [Environment]::GetFolderPath("Desktop")
    $retired = @(
        "Dragon AI Agent Setup.lnk",
        "Dragon AI Agent Bot Groups.lnk",
        "Dragon AI Agent Dashboard.lnk",
        "Dragon AI Agent Profiles.lnk"
    )
    foreach ($dir in @($desktop, $StartMenuDir)) {
        foreach ($name in $retired) {
            $p = Join-Path $dir $name
            if (Test-Path -LiteralPath $p) {
                try {
                    Remove-Item -LiteralPath $p -Force -ErrorAction Stop
                    Write-Log "Removed deprecated shortcut: $p"
                } catch {
                    Write-Log "Could not remove shortcut $p : $($_.Exception.Message)" "WARN"
                }
            }
        }
    }
}

function Install-Shortcuts {
    Write-Log "Creating desktop and Start Menu shortcuts..."
    $ico = Join-Path $InstallRoot "branding\dragon-ai-agent-logo.ico"
    if (-not (Test-Path $ico)) { $ico = Join-Path $InstallRoot "dragon-ai-agent-logo.ico" }
    $png = Join-Path $InstallRoot "branding\dragon-ai-agent-logo.png"
    $iconLocation = $ico
    if (-not (Test-Path $iconLocation)) { $iconLocation = $png }

    $startVbs = Join-Path $InstallRoot "scripts\airmaze\Start-DragonAI.vbs"
    $targetWscript = Join-Path $env:SystemRoot "System32\wscript.exe"

    Ensure-Dir $StartMenuDir
    $desktop = [Environment]::GetFolderPath("Desktop")
    Remove-DeprecatedProductShortcuts

    try {
        $wsh = New-Object -ComObject WScript.Shell

        # Product shortcut: wscript host - no PowerShell console flash.
        $startArgs = "//nologo `"$startVbs`""

        $sc1Path = Join-Path $desktop "Dragon AI Agent.lnk"
        $sc1 = $wsh.CreateShortcut($sc1Path)
        $sc1.TargetPath = $targetWscript
        $sc1.Arguments = $startArgs
        $sc1.WorkingDirectory = $InstallRoot
        $sc1.Description = "Dragon AI Agent - start the gateway and open the app"
        $sc1.WindowStyle = 1
        if ($iconLocation -and (Test-Path $iconLocation)) { $sc1.IconLocation = "$iconLocation,0" }
        $sc1.Save()
        Write-Log "Desktop shortcut: $sc1Path"

        $sc2Path = Join-Path $StartMenuDir "Dragon AI Agent.lnk"
        $sc2 = $wsh.CreateShortcut($sc2Path)
        $sc2.TargetPath = $targetWscript
        $sc2.Arguments = $startArgs
        $sc2.WorkingDirectory = $InstallRoot
        $sc2.Description = "Dragon AI Agent - start the gateway and open the app"
        $sc2.WindowStyle = 1
        if ($iconLocation -and (Test-Path $iconLocation)) { $sc2.IconLocation = "$iconLocation,0" }
        $sc2.Save()

        Write-Log "Start Menu shortcut: $sc2Path"
    } catch {
        Write-Log "Shortcut creation failed: $($_.Exception.Message)" "WARN"
    }
}

function Start-EmbeddedGateway {
    Write-Log "Pulling and starting embedded gateway..."
    Fix-DockerPath
    $compose = Join-Path $InstallRoot "docker-compose.embedded.yml"
    if (-not (Test-Path $compose)) {
        Write-Log "Compose file missing at $compose" "ERROR"
        return $false
    }
    $env:HERMES_EMBEDDED_DATA = $DataDir
    Push-Location $InstallRoot
    try {
        $pullOut = & docker compose -f docker-compose.embedded.yml pull 2>&1 | Out-String
        if ($pullOut) { Write-Log "compose pull: $($pullOut.Trim())" }
        $upOut = & docker compose -f docker-compose.embedded.yml up -d 2>&1 | Out-String
        if ($upOut) { Write-Log "compose up: $($upOut.Trim())" }
        if ($LASTEXITCODE -ne 0 -or $upOut -match 'error during connect|open //\./pipe/docker|Cannot connect to the Docker daemon') {
            Write-Log "docker compose up failed (exit $LASTEXITCODE)" "ERROR"
            return $false
        }
        Write-Log "Gateway container requested up"
        & docker compose -f docker-compose.embedded.yml ps 2>&1 | ForEach-Object { Write-Log "ps: $_" }
        return $true
    } finally {
        Pop-Location
    }
}

function Invoke-BotGroupSetup([string]$Root) {
    $select = Join-Path $InstallRoot "scripts\airmaze\Select-BotGroup.ps1"
    if (-not (Test-Path $select)) {
        $select = Join-Path $Root "scripts\airmaze\Select-BotGroup.ps1"
    }
    $import = Join-Path $InstallRoot "scripts\airmaze\Import-BotGroup.ps1"
    if (-not (Test-Path $import)) {
        $import = Join-Path $Root "scripts\airmaze\Import-BotGroup.ps1"
    }

    $importPath = if ($ImportBotGroup) { $ImportBotGroup } else { $ImportProfile }
    $groupId = if ($BotGroupId) { $BotGroupId } else { $ProfileId }
    $skipPrompt = $SkipBotGroupPrompt -or $SkipProfilePrompt

    if (-not [string]::IsNullOrWhiteSpace($importPath)) {
        Write-Log "Importing bot group from $importPath"
        & $import -SourcePath $importPath -InstallRoot $InstallRoot -PayloadRoot $Root
        return
    }

    if (-not [string]::IsNullOrWhiteSpace($groupId)) {
        Write-Log "Deploying catalog bot group id=$groupId"
        & $select -PayloadRoot $Root -InstallRoot $InstallRoot -BotGroupId $groupId -NonInteractive
        return
    }

    if ($skipPrompt) {
        Write-Log "SkipBotGroupPrompt: defaulting to personal-assistant"
        & $select -PayloadRoot $Root -InstallRoot $InstallRoot -BotGroupId "personal-assistant" -NonInteractive
        return
    }

    try {
        & $select -PayloadRoot $Root -InstallRoot $InstallRoot
    } catch {
        Write-Log "Bot group selection failed ($($_.Exception.Message)); applying Personal Assistant" "WARN"
        & $select -PayloadRoot $Root -InstallRoot $InstallRoot -BotGroupId "personal-assistant" -NonInteractive
    }
}

function Start-AgentDesktop {
    Write-Log "Looking for packaged Dragon AI Agent desktop..."
    $finder = Join-Path $InstallRoot "scripts\airmaze\Find-HermesDesktop.ps1"
    if (-not (Test-Path -LiteralPath $finder)) {
        $finder = Join-Path $PSScriptRoot "Find-HermesDesktop.ps1"
    }
    if (Test-Path -LiteralPath $finder) { . $finder }
    $exe = $null
    if (Get-Command Set-DragonAIDesktopUserDataEnv -ErrorAction SilentlyContinue) {
        Set-DragonAIDesktopUserDataEnv -InstallRoot $InstallRoot | Out-Null
    } else {
        $env:HERMES_DESKTOP_USER_DATA_DIR = Join-Path $InstallRoot "electron-userdata"
    }
    if (Get-Command Install-DragonAIPrivateDesktop -ErrorAction SilentlyContinue) {
        $exe = Install-DragonAIPrivateDesktop -InstallRoot $InstallRoot -PayloadRoot $root
    } elseif (Get-Command Find-DragonDesktopExe -ErrorAction SilentlyContinue) {
        $exe = Find-DragonDesktopExe -InstallRoot $InstallRoot -PayloadRoot $root
    } elseif (Get-Command Find-HermesDesktopExe -ErrorAction SilentlyContinue) {
        $exe = Find-HermesDesktopExe -InstallRoot $InstallRoot
    }
    if ($exe -and (Get-Command Test-DragonAIHermesInstallPath -ErrorAction SilentlyContinue)) {
        if (Test-DragonAIHermesInstallPath -Path $exe) { $exe = $null }
    }
    if ($exe -and (Get-Command Test-DragonAIPrivateDesktopPath -ErrorAction SilentlyContinue)) {
        if (-not (Test-DragonAIPrivateDesktopPath -Path $exe)) { $exe = $null }
    }
    if ($exe) {
        Write-Log "Launching Dragon AI Agent desktop: $exe"
        try {
            Save-DragonAIDesktopPointer -ExePath $exe -InstallRoot $InstallRoot | Out-Null
            if (Get-Command Start-DragonAIDesktopClient -ErrorAction SilentlyContinue) {
                Start-DragonAIDesktopClient -ExePath $exe -InstallRoot $InstallRoot
            } else {
                Start-HermesDesktopClient -ExePath $exe -InstallRoot $InstallRoot
            }
        } catch {
            if ($_.Exception.Message -like "Refuse *outside DragonAIAgent*") { throw }
            if ($_.Exception.Message -like "Refuse *Hermes install*") { throw }
            if (Get-Command Test-DragonAIPrivateDesktopPath -ErrorAction SilentlyContinue) {
                if (-not (Test-DragonAIPrivateDesktopPath -Path $exe)) { throw }
            }
            Start-Process -FilePath $exe -WorkingDirectory (Split-Path -Parent $exe) -ErrorAction SilentlyContinue
        }
        return $true
    }
    $hint = Join-Path $InstallRoot "desktop\win-unpacked\DragonAIAgent.exe"
    Write-Host ""
    Write-Host "Dragon AI Agent desktop was not found in this package."
    Write-Host "  Expected: $hint"
    Write-Host "Re-download Dragon-AI-Agent-v0.1.0-windows.zip and run DragonAIAgentSetup.exe."
    Write-Host ""
    Write-Log "Packaged Dragon AI Agent desktop missing at $hint" "WARN"
    return $false
}

# --- Main -------------------------------------------------------------------

Write-Host ""
Write-Host "========================================"
Write-Host " $ProductName Setup v$ProductVersion"
Write-Host "========================================"
Write-Host ""
Write-Log "=== $ProductName installer v$ProductVersion ==="
try {
    $root = Resolve-PayloadRoot
    Write-Log "Payload root: $root"
} catch {
    Write-Log $_.Exception.Message "ERROR"
    exit 1
}

Ensure-Dir $InstallRoot
Ensure-WSL2 | Out-Null

Write-Host "Preparing runtime..."
$dockerOk = Ensure-DockerDesktop -PayloadRoot $root
if ($dockerOk) {
    Set-DockerHeadlessSettings
    Fix-DockerPath
    Start-DockerHeadless | Out-Null
} else {
    Write-Log "Background engine not ready after Setup-owned install; package files will still be copied. Re-run Setup after a reboot if Windows asked for one." "WARN" -FileOnly
}

Install-PackageFiles -Root $root

function Exclude-DragonAIHermesBots {
    $engine = Join-Path $InstallRoot "scripts\airmaze\exclude_hermes_bot.py"
    if (-not (Test-Path -LiteralPath $engine)) {
        $engine = Join-Path $PSScriptRoot "exclude_hermes_bot.py"
    }
    if (-not (Test-Path -LiteralPath $engine)) { return }
    $desktop = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "hermes\profiles" } else { "" }
    $embedded = if ($env:USERPROFILE) { Join-Path $env:USERPROFILE ".hermes-airmaze-embedded\profiles" } else { "" }
    $py = Get-Command python3 -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
    if (-not $py) { return }
    try {
        & $py.Source $engine purge --desktop $desktop --embedded $embedded | Out-Null
        Write-Log "Excluded leftover Hermes bot profiles (default/hermes)"
    } catch {
        Write-Log "Hermes exclude skipped: $($_.Exception.Message)" "WARN"
    }
}
Exclude-DragonAIHermesBots

Fix-DockerPath
if ($dockerOk -and (Test-DockerEngine)) {
    Start-EmbeddedGateway | Out-Null
} elseif ($dockerOk) {
    Write-Log "Skipping compose up until the background engine is running (often after a first-install reboot). Open Dragon AI Agent or re-run Setup." "WARN" -FileOnly
} else {
    Write-Log "Skipping compose up because the background engine is not installed yet. Re-run Dragon AI Agent Setup." "WARN" -FileOnly
}

Invoke-BotGroupSetup -Root $root

# First-run models live in-app (Apply-GatewayModels + desktop Models UI).
# Do not launch WinForms Onboard-Wizard.ps1.

Install-Shortcuts
Start-AgentDesktop | Out-Null

$setupGuide = Join-Path $InstallRoot "docs\airmaze\SETUP_GUIDE.md"
Write-Log "=== Install finished. Log: $LogPath ==="
Write-Host ""
Write-Host "$ProductName v$ProductVersion setup complete (best-effort)."
Write-Host "  Install root: $InstallRoot"
Write-Host "  Log:          $LogPath"
Write-Host "  Desktop Screen: http://127.0.0.1:8650  (Remote token dragon-local)"
Write-Host "  Gateway API:    127.0.0.1:8642  dashboard: http://127.0.0.1:9119"
Write-Host "  Bot groups:   in-app Teams Marketplace"
Write-Host "  First-run:    in-app Models UI (Dragon AI Agent launcher)"
Write-Host "  Setup guide:  $setupGuide"
Write-Host ""
