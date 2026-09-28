#requires -Version 5.1
<#
.SYNOPSIS
  Dragon AI Agent v0.1.0 Windows bootstrap installer.

.DESCRIPTION
  Best-effort provision of WSL2, Docker Desktop (tray-minimized, no dashboard popup),
  embedded gateway, profile catalog selection / import, and agent desktop launch attempt.

.NOTES
  Log: %LOCALAPPDATA%\DragonAIAgent\install.log
  Package files: %LOCALAPPDATA%\DragonAIAgent\
  Data: %USERPROFILE%\.hermes-airmaze-embedded  (internal gateway data dir)
#>

[CmdletBinding()]
param(
    [string]$PayloadRoot = "",
    [string]$ProfileId = "",
    [string]$ImportProfile = "",
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
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
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

# --- Docker Desktop: tray-only / no dashboard on startup --------------------

function Set-DockerTrayOnlySettings {
    Write-Log "Configuring Docker Desktop for tray-only startup (no dashboard window)..."
    Ensure-Dir $DockerSettingsDir

    $patch = @{
        openUIOnStartupDisabled = $true
        OpenUIOnStartupDisabled = $true
        openAtLogin             = $true
        autoStart               = $true
        startMinimized          = $true
        minimizeToTray          = $true
        displayedOnboarding     = $true
        analyticsEnabled        = $false
    }

    $files = @(
        (Join-Path $DockerSettingsDir "settings.json"),
        (Join-Path $DockerSettingsDir "settings-store.json")
    )

    foreach ($file in $files) {
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
            Write-Log "Patched Docker settings: $file"
        } catch {
            Write-Log "Could not patch $file : $($_.Exception.Message)" "WARN"
        }
    }
}

function Get-DockerDesktopExe {
    $candidates = @(
        (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Docker\Docker\Docker Desktop.exe"),
        (Join-Path $env:LOCALAPPDATA "Docker\Docker Desktop.exe")
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path -LiteralPath $c)) { return $c }
    }
    return $null
}

function Test-DockerEngine {
    try {
        $null = & docker info 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Start-DockerHeadless {
    Write-Log "Starting Docker engine (headless / tray-friendly)..."
    Set-DockerTrayOnlySettings

    $svc = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
    if ($svc) {
        if ($svc.Status -ne "Running") {
            try {
                if (Test-IsAdmin) {
                    Start-Service -Name "com.docker.service" -ErrorAction Stop
                    Write-Log "Started com.docker.service"
                } else {
                    Write-Log "com.docker.service present but not running; admin rights needed to start service" "WARN"
                    Start-Process -FilePath "net" -ArgumentList "start","com.docker.service" -Verb RunAs -Wait -ErrorAction SilentlyContinue
                }
            } catch {
                Write-Log "Service start failed: $($_.Exception.Message)" "WARN"
            }
        } else {
            Write-Log "com.docker.service already running"
        }
    }

    if (-not (Test-DockerEngine)) {
        $exe = Get-DockerDesktopExe
        if ($exe) {
            Write-Log "Launching Docker Desktop (tray / no UI force): $exe"
            try {
                Start-Process -FilePath $exe -WindowStyle Minimized -ErrorAction Stop
            } catch {
                Start-Process -FilePath $exe -ErrorAction SilentlyContinue
            }
        } else {
            Write-Log "Docker Desktop.exe not found on disk yet" "WARN"
        }
    }

    $deadline = (Get-Date).AddMinutes(3)
    while ((Get-Date) -lt $deadline) {
        if (Test-DockerEngine) {
            Write-Log "Docker engine is ready"
            return $true
        }
        Start-Sleep -Seconds 5
    }
    Write-Log "Docker engine not ready within timeout" "WARN"
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

# --- Docker Desktop install -------------------------------------------------

function Ensure-DockerDesktop {
    Write-Log "Checking Docker Desktop..."
    if (Get-DockerDesktopExe) {
        Write-Log "Docker Desktop found"
        Set-DockerTrayOnlySettings
        return $true
    }

    Write-Log "Docker Desktop not found; attempting quiet download/install..."
    $installer = Join-Path $env:TEMP "DockerDesktopInstaller-DragonAIAgent.exe"
    $url = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Write-Log "Downloading Docker Desktop installer..."
        Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing -ErrorAction Stop
        Write-Log "Running quiet install (may still need UAC / reboot)..."
        $args = "install --quiet --accept-license"
        $p = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru -ErrorAction Stop
        Write-Log "Docker installer exit code: $($p.ExitCode)"
        Set-DockerTrayOnlySettings
        if (Get-DockerDesktopExe) { return $true }
    } catch {
        Write-Log "Quiet install failed: $($_.Exception.Message)" "WARN"
    }

    Write-Log "Opening Docker Desktop download page for manual install..." "WARN"
    try {
        Start-Process "https://www.docker.com/products/docker-desktop/"
    } catch {}
    Write-Host ""
    Write-Host "ACTION REQUIRED: Install Docker Desktop, then re-run Dragon AI Agent Setup."
    Write-Host "After install, Docker will be configured to stay in the system tray (no dashboard popup)."
    Write-Host ""
    return $false
}

function Fix-DockerPath {
    $binDirs = @(
        (Join-Path $env:ProgramFiles "Docker\Docker\resources\bin"),
        (Join-Path $env:LOCALAPPDATA "Docker\resources\bin")
    )
    foreach ($d in $binDirs) {
        if ((Test-Path -LiteralPath $d) -and ($env:PATH -notlike "*$d*")) {
            $env:PATH = "$d;$env:PATH"
            Write-Log "Prepended Docker bin to PATH: $d"
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
    Ensure-Dir (Join-Path $InstallRoot "profiles")
    Ensure-Dir (Join-Path $InstallRoot "branding")

    $composeSrc = Join-Path $Root "docker-compose.embedded.yml"
    if (Test-Path $composeSrc) {
        Copy-Item -LiteralPath $composeSrc -Destination (Join-Path $InstallRoot "docker-compose.embedded.yml") -Force
    }

    # Copy profiles catalog tree
    $profilesSrc = Join-Path $Root "profiles"
    if (Test-Path $profilesSrc) {
        Copy-Item -Path $profilesSrc -Destination (Join-Path $InstallRoot "profiles") -Recurse -Force
        Write-Log "Copied profiles catalog"
    }

    # Branding / logo
    foreach ($logoName in @("dragon-ai-agent-logo.png", "dragon-ai-agent-logo.ico", "dragon-ai-agent-logo.svg")) {
        $logoSrc = Join-Path $Root $logoName
        if (-not (Test-Path $logoSrc)) { $logoSrc = Join-Path $Root "branding\$logoName" }
        if (Test-Path $logoSrc) {
            Copy-Item -LiteralPath $logoSrc -Destination (Join-Path $InstallRoot "branding\$logoName") -Force
            Copy-Item -LiteralPath $logoSrc -Destination (Join-Path $InstallRoot $logoName) -Force
            Write-Log "Copied logo $logoName"
        }
    }

    foreach ($rel in @(
        "scripts\airmaze\start-embedded.ps1",
        "scripts\airmaze\apply-default-profile.ps1",
        "scripts\airmaze\install.ps1",
        "scripts\airmaze\Apply-Profile.ps1",
        "scripts\airmaze\Select-Profile.ps1",
        "scripts\airmaze\Import-Profile.ps1",
        "scripts\airmaze\Onboard-Wizard.ps1",
        "scripts\airmaze\DragonAI-SecureStore.ps1",
        "templates\profiles\personal-assistant\SOUL.md",
        "templates\profiles\personal-assistant\profile.yaml",
        "docs\airmaze\SETUP_GUIDE.md",
        "docs\airmaze\ARCHITECTURE.md",
        "docs\airmaze\EMBEDDED_GATEWAY.md",
        "docs\airmaze\UPSTREAM_NOTES.md",
        "docs\airmaze\STATUS.md",
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

function Install-Shortcuts {
    Write-Log "Creating desktop and Start Menu shortcuts..."
    $ico = Join-Path $InstallRoot "branding\dragon-ai-agent-logo.ico"
    if (-not (Test-Path $ico)) { $ico = Join-Path $InstallRoot "dragon-ai-agent-logo.ico" }
    $png = Join-Path $InstallRoot "branding\dragon-ai-agent-logo.png"
    $iconLocation = $ico
    if (-not (Test-Path $iconLocation)) { $iconLocation = $png }

    $startScript = Join-Path $InstallRoot "scripts\airmaze\start-embedded.ps1"
    $selectScript = Join-Path $InstallRoot "scripts\airmaze\Select-Profile.ps1"
    $targetPs = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

    Ensure-Dir $StartMenuDir
    $desktop = [Environment]::GetFolderPath("Desktop")

    try {
        $wsh = New-Object -ComObject WScript.Shell

        $sc1Path = Join-Path $desktop "Dragon AI Agent.lnk"
        $sc1 = $wsh.CreateShortcut($sc1Path)
        $sc1.TargetPath = $targetPs
        $sc1.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`""
        $sc1.WorkingDirectory = $InstallRoot
        $sc1.Description = "Dragon AI Agent — start embedded gateway"
        $sc1.WindowStyle = 1
        if ($iconLocation -and (Test-Path $iconLocation)) { $sc1.IconLocation = "$iconLocation,0" }
        $sc1.Save()
        Write-Log "Desktop shortcut: $sc1Path"

        $sc2Path = Join-Path $StartMenuDir "Dragon AI Agent.lnk"
        $sc2 = $wsh.CreateShortcut($sc2Path)
        $sc2.TargetPath = $targetPs
        $sc2.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`""
        $sc2.WorkingDirectory = $InstallRoot
        $sc2.Description = "Dragon AI Agent — start embedded gateway"
        if ($iconLocation -and (Test-Path $iconLocation)) { $sc2.IconLocation = "$iconLocation,0" }
        $sc2.Save()

        $sc3Path = Join-Path $StartMenuDir "Dragon AI Agent Profiles.lnk"
        $sc3 = $wsh.CreateShortcut($sc3Path)
        $sc3.TargetPath = $targetPs
        $sc3.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$selectScript`" -InstallRoot `"$InstallRoot`" -PayloadRoot `"$InstallRoot`""
        $sc3.WorkingDirectory = $InstallRoot
        $sc3.Description = "Dragon AI Agent — select or import a profile"
        if ($iconLocation -and (Test-Path $iconLocation)) { $sc3.IconLocation = "$iconLocation,0" }
        $sc3.Save()

        $onboardScript = Join-Path $InstallRoot "scripts\airmaze\Onboard-Wizard.ps1"
        if (Test-Path -LiteralPath $onboardScript) {
            $sc4Path = Join-Path $StartMenuDir "Dragon AI Agent Setup.lnk"
            $sc4 = $wsh.CreateShortcut($sc4Path)
            $sc4.TargetPath = $targetPs
            $sc4.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$onboardScript`" -InstallRoot `"$InstallRoot`" -PayloadRoot `"$InstallRoot`""
            $sc4.WorkingDirectory = $InstallRoot
            $sc4.Description = "Dragon AI Agent — first-run onboarding wizard"
            if ($iconLocation -and (Test-Path $iconLocation)) { $sc4.IconLocation = "$iconLocation,0" }
            $sc4.Save()

            $sc5Path = Join-Path $desktop "Dragon AI Agent Setup.lnk"
            $sc5 = $wsh.CreateShortcut($sc5Path)
            $sc5.TargetPath = $targetPs
            $sc5.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$onboardScript`" -InstallRoot `"$InstallRoot`" -PayloadRoot `"$InstallRoot`""
            $sc5.WorkingDirectory = $InstallRoot
            $sc5.Description = "Dragon AI Agent — first-run onboarding wizard"
            if ($iconLocation -and (Test-Path $iconLocation)) { $sc5.IconLocation = "$iconLocation,0" }
            $sc5.Save()
            Write-Log "Setup shortcuts: $sc4Path ; $sc5Path"
        }

        Write-Log "Start Menu shortcuts under: $StartMenuDir"
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
        & docker compose -f docker-compose.embedded.yml pull 2>&1 | ForEach-Object { Write-Log "compose pull: $_" }
        & docker compose -f docker-compose.embedded.yml up -d 2>&1 | ForEach-Object { Write-Log "compose up: $_" }
        if ($LASTEXITCODE -ne 0) {
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

function Invoke-ProfileSetup([string]$Root) {
    $select = Join-Path $InstallRoot "scripts\airmaze\Select-Profile.ps1"
    if (-not (Test-Path $select)) {
        $select = Join-Path $Root "scripts\airmaze\Select-Profile.ps1"
    }
    $import = Join-Path $InstallRoot "scripts\airmaze\Import-Profile.ps1"
    if (-not (Test-Path $import)) {
        $import = Join-Path $Root "scripts\airmaze\Import-Profile.ps1"
    }

    if (-not [string]::IsNullOrWhiteSpace($ImportProfile)) {
        Write-Log "Importing profile from $ImportProfile"
        & $import -SourcePath $ImportProfile -InstallRoot $InstallRoot -PayloadRoot $Root
        return
    }

    if (-not [string]::IsNullOrWhiteSpace($ProfileId)) {
        Write-Log "Selecting catalog profile id=$ProfileId"
        & $select -PayloadRoot $Root -InstallRoot $InstallRoot -ProfileId $ProfileId -NonInteractive
        return
    }

    if ($SkipProfilePrompt) {
        Write-Log "SkipProfilePrompt: defaulting to personal-assistant"
        & $select -PayloadRoot $Root -InstallRoot $InstallRoot -ProfileId "personal-assistant" -NonInteractive
        return
    }

    # Interactive menu (also offers import)
    try {
        & $select -PayloadRoot $Root -InstallRoot $InstallRoot
    } catch {
        Write-Log "Profile selection failed ($($_.Exception.Message)); applying Personal Assistant" "WARN"
        & $select -PayloadRoot $Root -InstallRoot $InstallRoot -ProfileId "personal-assistant" -NonInteractive
    }
}

function Start-AgentDesktop {
    Write-Log "Looking for agent desktop client..."
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "hermes\Hermes Desktop.exe"),
        (Join-Path $env:LOCALAPPDATA "hermes\HermesDesktop.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\hermes\Hermes Desktop.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Hermes\Hermes.exe"),
        (Join-Path $env:ProgramFiles "Hermes\Hermes Desktop.exe"),
        (Join-Path $env:ProgramFiles "Hermes\Hermes.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Hermes\Hermes Desktop.exe")
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path -LiteralPath $c)) {
            Write-Log "Launching agent desktop client: $c"
            Start-Process -FilePath $c -ErrorAction SilentlyContinue
            Write-Log "Point Remote gateway at http://127.0.0.1:9119 (API 127.0.0.1:8642). Open Profiles / Bot Screen and pick an installed bot."
            return $true
        }
    }
    Write-Host ""
    Write-Host "Agent desktop client was not found."
    Write-Host "Next steps:"
    Write-Host "  1. Install a compatible open-source agent desktop client (separate installer)."
    Write-Host "  2. Add Remote gateway: host 127.0.0.1, API port 8642 / dashboard http://127.0.0.1:9119"
    Write-Host "     Local dashboard credentials are in THIRD_PARTY_NOTICES.md / EMBEDDED_GATEWAY.md"
    Write-Host "  3. Open Profiles, select a bot from your applied Dragon AI Agent profile, then open Bot Screen."
    Write-Host ""
    Write-Log "Agent desktop client not found; printed next steps" "WARN"
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

$dockerOk = Ensure-DockerDesktop
if ($dockerOk) {
    Set-DockerTrayOnlySettings
    Start-DockerHeadless | Out-Null
} else {
    Write-Log "Docker not ready; package files will still be copied. Re-run after installing Docker." "WARN"
}

Install-PackageFiles -Root $root

if ($dockerOk -and (Test-DockerEngine)) {
    Start-EmbeddedGateway | Out-Null
} elseif ($dockerOk) {
    Write-Log "Skipping compose up until Docker engine is running. Re-run installer or: scripts\airmaze\start-embedded.ps1" "WARN"
}

Invoke-ProfileSetup -Root $root

# First-run onboarding wizard (do not fail entire install if wizard errors)
try {
    $wizard = Join-Path $InstallRoot "scripts\airmaze\Onboard-Wizard.ps1"
    if (-not (Test-Path -LiteralPath $wizard)) {
        $wizard = Join-Path $root "scripts\airmaze\Onboard-Wizard.ps1"
    }
    if (Test-Path -LiteralPath $wizard) {
        $wizProfile = $ProfileId
        $activePath = Join-Path $InstallRoot "active-profile.json"
        if ([string]::IsNullOrWhiteSpace($wizProfile) -and (Test-Path -LiteralPath $activePath)) {
            try {
                $active = Get-Content -LiteralPath $activePath -Raw -Encoding UTF8 | ConvertFrom-Json
                $wizProfile = [string]$active.profileId
            } catch {}
        }
        Write-Log "Launching onboarding wizard (profile=$wizProfile)..."
        $wizArgs = @{
            InstallRoot = $InstallRoot
            PayloadRoot = $InstallRoot
        }
        if (-not [string]::IsNullOrWhiteSpace($wizProfile)) {
            $wizArgs["ProfileId"] = $wizProfile
        }
        & $wizard @wizArgs
        Write-Log "Onboarding wizard finished (exit $LASTEXITCODE)"
    } else {
        Write-Log "Onboard-Wizard.ps1 not found; skipping wizard" "WARN"
    }
} catch {
    Write-Log "Onboarding wizard failed (install continues): $($_.Exception.Message)" "WARN"
}

Install-Shortcuts
Start-AgentDesktop | Out-Null

$setupGuide = Join-Path $InstallRoot "docs\airmaze\SETUP_GUIDE.md"
Write-Log "=== Install finished. Log: $LogPath ==="
Write-Host ""
Write-Host "$ProductName v$ProductVersion setup complete (best-effort)."
Write-Host "  Install root: $InstallRoot"
Write-Host "  Log:          $LogPath"
Write-Host "  Gateway:      127.0.0.1:8642  dashboard: http://127.0.0.1:9119"
Write-Host "  Docker UI:    tray-only (dashboard suppressed on startup)"
Write-Host "  Profiles:     Start Menu > Dragon AI Agent > Dragon AI Agent Profiles"
Write-Host "  Setup wizard: Start Menu / Desktop > Dragon AI Agent Setup"
Write-Host "  Setup guide:  $setupGuide"
Write-Host ""
