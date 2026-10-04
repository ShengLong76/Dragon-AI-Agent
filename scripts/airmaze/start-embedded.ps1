#requires -Version 5.1
<#
.SYNOPSIS
  Start Dragon AI Agent: embedded gateway plus a visible main UI (or an error dialog).

.DESCRIPTION
  This is the Desktop / Start Menu "Dragon AI Agent" entrypoint.
  It checks whether Docker is running and starts the engine invisibly when
  it is not (no dashboard, no onboarding, no tray icon). Then it brings the
  gateway up, wires Desktop Remote, and launches the packaged Dragon AI Agent
  desktop (DragonAIAgent.exe). It still
  waits until :8642 / :8650 are reachable and fail-closes if they are not.
  Failures (engine still down after a wait, compose errors, missing client)
  show a MessageBox / popup and exit non-zero. -StartDocker is kept as an alias.

  The installed Desktop / Start Menu shortcut runs Start-DragonAI.vbs (wscript)
  so no PowerShell console flashes. A normal start does not show the WinForms
  "Waiting for gateway..." Setup/Close status window - Dragon AI Agent is the
  loading UX. Status goes to launch.log. Use this .ps1 directly for debugging
  (-DebugConsole keeps the console). Use -GatewayOnly for CLI-only compose.
  Use -OpenDashboard to open :9119 (never opened on a normal start).
  Use -Smoke to validate the launch plan without touching Docker (no secrets).

.NOTES
  Fixes PATH for Docker Desktop CLI under common install locations.
  Does not open the Docker Desktop dashboard, onboarding, or tray icon.
#>

[CmdletBinding()]
param(
    [string]$InstallRoot = "",
    [switch]$Pull,
    [switch]$SkipPull,
    [switch]$GatewayOnly,
    [switch]$NoBrowser,
    [switch]$OpenDashboard,
    [switch]$StartDocker,
    [switch]$SilentHost,
    [switch]$DebugConsole,
    [switch]$NoWizard,
    [switch]$Smoke
)

$ErrorActionPreference = "Stop"
$ProductName = "Dragon AI Agent"
$DashboardUrl = "http://127.0.0.1:9119/"
$ApiHost = "127.0.0.1"
$ApiPort = 8642
$DashPort = 9119
# Desktop Remote token/WS - NOT the OpenAI API on 8642 (that surface has no /api/ws).
# GET / on :8650 is headless hermes serve ("web UI disabled"). The window must
# load the dashboard web UI on :8660 instead.
$DesktopServeUrl = "http://127.0.0.1:8650"
$DesktopServePort = 8650
$DesktopWebUIUrl = "http://127.0.0.1:8660/"
$DesktopWebUIPort = 8660
$DesktopSessionToken = "dragon-local"

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}

$script:LaunchLog = Join-Path $InstallRoot "launch.log"
$script:Windowless = $false
$script:WinFormsOk = $false
$script:LaunchForm = $null
$script:LaunchStatus = $null
$script:DashboardUrl = $DashboardUrl
# Current -desktop images refuse keys shorter than 16 chars. Honor an existing
# long API_SERVER_KEY (Cos/UltraDragon live) and only replace a missing/short one.
$script:ApiKey = "dragon-local-key"
if (-not [string]::IsNullOrWhiteSpace($env:API_SERVER_KEY) -and $env:API_SERVER_KEY.Length -ge 16) {
    $script:ApiKey = $env:API_SERVER_KEY
}
$script:DesktopServeUrl = $DesktopServeUrl
$script:DesktopWebUIUrl = $DesktopWebUIUrl
$script:DesktopWebUIPort = $DesktopWebUIPort
$script:DesktopSessionToken = $DesktopSessionToken
if ([string]::IsNullOrWhiteSpace($env:DRAGON_AI_UI_URL)) {
    $env:DRAGON_AI_UI_URL = $script:DesktopWebUIUrl
}

$finder = Join-Path $PSScriptRoot "Find-HermesDesktop.ps1"
if (-not (Test-Path -LiteralPath $finder)) {
    $finder = Join-Path $InstallRoot "scripts\airmaze\Find-HermesDesktop.ps1"
}
if (Test-Path -LiteralPath $finder) {
    . $finder
}

function Write-LaunchLog {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host "[$ProductName] $Message"
    try {
        $dir = Split-Path -Parent $script:LaunchLog
        if ($dir -and -not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
        Add-Content -LiteralPath $script:LaunchLog -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {}
}

function Test-WinFormsAvailable {
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop | Out-Null
        Add-Type -AssemblyName System.Drawing -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Show-DragonDialog {
    <#
    .SYNOPSIS
      Always-visible error/info dialog. WinForms first, then WScript popup, then console pause.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [string]$Title = $ProductName,
        [ValidateSet("Error", "Info", "Warn")]
        [string]$Kind = "Error"
    )
    Write-LaunchLog $Message $Kind.ToUpperInvariant()
    if ($script:WinFormsOk) {
        $icon = switch ($Kind) {
            "Error" { [Windows.Forms.MessageBoxIcon]::Error }
            "Warn"  { [Windows.Forms.MessageBoxIcon]::Warning }
            default { [Windows.Forms.MessageBoxIcon]::Information }
        }
        [Windows.Forms.MessageBox]::Show(
            $Message,
            $Title,
            [Windows.Forms.MessageBoxButtons]::OK,
            $icon
        ) | Out-Null
        return
    }
    try {
        $sh = New-Object -ComObject WScript.Shell
        $iconCode = switch ($Kind) {
            "Error" { 16 }
            "Warn"  { 48 }
            default { 64 }
        }
        $sh.Popup($Message, 0, $Title, $iconCode) | Out-Null
        return
    } catch {}
    # Installed shortcut is windowless - never block on a hidden console.
    if ($script:Windowless) { return }
    Write-Host ""
    Write-Host $Message
    if ([Environment]::UserInteractive) {
        try { Read-Host "Press Enter to close" | Out-Null } catch {}
    }
}

function Update-LaunchStatus {
    param([string]$Text)
    Write-LaunchLog $Text
    if ($script:LaunchStatus -and $script:LaunchForm) {
        try {
            $script:LaunchStatus.Text = $Text
            $script:LaunchForm.Refresh()
            [Windows.Forms.Application]::DoEvents()
        } catch {}
    }
}

function New-LaunchStatusForm {
    if (-not $script:WinFormsOk) { return $false }
    try {
        $form = New-Object Windows.Forms.Form
        $form.Text = $ProductName
        $form.Size = New-Object Drawing.Size(560, 280)
        $form.StartPosition = "CenterScreen"
        $form.BackColor = [System.Drawing.Color]::FromArgb(28, 28, 32)
        $form.ForeColor = [System.Drawing.Color]::FromArgb(240, 240, 245)
        $form.FormBorderStyle = [Windows.Forms.FormBorderStyle]::FixedDialog
        $form.MaximizeBox = $false
        $form.MinimizeBox = $true
        $form.TopMost = $true

        $header = New-Object Windows.Forms.Panel
        $header.Location = New-Object Drawing.Point(0, 0)
        $header.Size = New-Object Drawing.Size(560, 56)
        $header.BackColor = [System.Drawing.Color]::FromArgb(37, 99, 235)  # #2563EB Marketplace / header lockup
        $form.Controls.Add($header)

        $logoPath = Join-Path $InstallRoot "branding\dragon-ai-agent-logo.png"
        if (-not (Test-Path -LiteralPath $logoPath)) { $logoPath = Join-Path $InstallRoot "dragon-ai-agent-logo.png" }
        $titleX = 16
        if (Test-Path -LiteralPath $logoPath) {
            try {
                $pic = New-Object Windows.Forms.PictureBox
                $pic.Image = [System.Drawing.Image]::FromFile($logoPath)
                $pic.SizeMode = [Windows.Forms.PictureBoxSizeMode]::Zoom
                $pic.Location = New-Object Drawing.Point(10, 6)
                $pic.Size = New-Object Drawing.Size(44, 44)
                $header.Controls.Add($pic)
                $titleX = 62
            } catch {}
        }

        $title = New-Object Windows.Forms.Label
        $title.Text = $ProductName
        $title.Location = New-Object Drawing.Point($titleX, 14)
        $title.Size = New-Object Drawing.Size(480, 28)
        $title.ForeColor = [System.Drawing.Color]::White
        $title.Font = New-Object Drawing.Font("Segoe UI", 14, [Drawing.FontStyle]::Bold)
        $header.Controls.Add($title)

        $status = New-Object Windows.Forms.Label
        $status.Text = "Starting..."
        $status.Location = New-Object Drawing.Point(16, 72)
        $status.Size = New-Object Drawing.Size(520, 80)
        $status.Font = New-Object Drawing.Font("Segoe UI", 10)
        $form.Controls.Add($status)

        $btnSetup = New-Object Windows.Forms.Button
        $btnSetup.Text = "Setup"
        $btnSetup.Location = New-Object Drawing.Point(16, 180)
        $btnSetup.Size = New-Object Drawing.Size(100, 36)
        $btnSetup.FlatStyle = [Windows.Forms.FlatStyle]::Flat
        $btnSetup.BackColor = [System.Drawing.Color]::FromArgb(40, 40, 48)
        $btnSetup.ForeColor = [System.Drawing.Color]::White
        $rootForUi = $InstallRoot
        $btnSetup.Add_Click({
            $wiz = Join-Path $rootForUi "scripts\airmaze\Onboard-Wizard.ps1"
            if (Test-Path -LiteralPath $wiz) {
                Start-HiddenPowerShell -ArgumentList @(
                    "-STA", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
                    "-File", $wiz, "-InstallRoot", $rootForUi
                )
            } else {
                Show-DragonDialog -Message "Onboard-Wizard.ps1 was not found. Re-run DragonAIAgentSetup." -Kind Warn
            }
        }.GetNewClosure())
        $form.Controls.Add($btnSetup)

        $btnClose = New-Object Windows.Forms.Button
        $btnClose.Text = "Close"
        $btnClose.Location = New-Object Drawing.Point(432, 180)
        $btnClose.Size = New-Object Drawing.Size(100, 36)
        $btnClose.FlatStyle = [Windows.Forms.FlatStyle]::Flat
        $btnClose.BackColor = [System.Drawing.Color]::FromArgb(40, 40, 48)
        $btnClose.ForeColor = [System.Drawing.Color]::White
        $btnClose.Add_Click({ $form.Close() }.GetNewClosure())
        $form.Controls.Add($btnClose)

        $script:LaunchForm = $form
        $script:LaunchStatus = $status
        $form.Add_Shown({ $form.Activate() }.GetNewClosure())
        $form.Show()
        $form.Refresh()
        [Windows.Forms.Application]::DoEvents()
        return $true
    } catch {
        Write-LaunchLog "Status form failed: $($_.Exception.Message)" "WARN"
        $script:LaunchForm = $null
        return $false
    }
}

function Test-LaunchedFromShortcut {
    try {
        $me = Get-CimInstance Win32_Process -Filter "ProcessId=$PID" -ErrorAction Stop
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($me.ParentProcessId)" -ErrorAction Stop
        $name = [IO.Path]::GetFileNameWithoutExtension([string]$parent.Name).ToLowerInvariant()
        return ($name -in @("explorer", "wscript", "cscript"))
    } catch {
        return $false
    }
}

function Hide-ConsoleWindow {
    try {
        if (-not ("DragonAINative" -as [type])) {
            Add-Type @"
using System;
using System.Runtime.InteropServices;
public class DragonAINative {
    [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
        }
        $hwnd = [DragonAINative]::GetConsoleWindow()
        if ($hwnd -ne [IntPtr]::Zero) {
            [DragonAINative]::ShowWindow($hwnd, 0) | Out-Null
        }
    } catch {}
}

function Start-HiddenPowerShell {
    param([string[]]$ArgumentList)
    $ps = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $quoted = foreach ($a in $ArgumentList) {
        if ($null -eq $a) { continue }
        $s = [string]$a
        if ($s -match '[\s"]') { '"' + ($s -replace '"', '\"') + '"' } else { $s }
    }
    $si = New-Object System.Diagnostics.ProcessStartInfo
    $si.FileName = $ps
    $si.Arguments = [string]::Join(' ', $quoted)
    $si.UseShellExecute = $false
    $si.CreateNoWindow = $true
    $si.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    [void][System.Diagnostics.Process]::Start($si)
}

function Remove-DeprecatedProductShortcuts {
    <#
      Start Menu / Desktop keep only the main Dragon AI Agent launcher.
      Delete leftover Bot Groups, Dashboard, Profiles, and Setup .lnk files.
    #>
    $desktop = [Environment]::GetFolderPath("Desktop")
    $startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Dragon AI Agent"
    $retired = @(
        "Dragon AI Agent Setup.lnk",
        "Dragon AI Agent Bot Groups.lnk",
        "Dragon AI Agent Dashboard.lnk",
        "Dragon AI Agent Profiles.lnk"
    )
    foreach ($dir in @($desktop, $startMenu)) {
        foreach ($name in $retired) {
            $p = Join-Path $dir $name
            if (Test-Path -LiteralPath $p) {
                try {
                    Remove-Item -LiteralPath $p -Force -ErrorAction Stop
                    Write-LaunchLog "Removed deprecated shortcut: $p"
                } catch {
                    Write-LaunchLog "Could not remove shortcut $p : $($_.Exception.Message)" "WARN"
                }
            }
        }
    }
}

function Repair-DragonAIProductShortcuts {
    <#
      Rewrite Desktop / Start Menu "Dragon AI Agent" to wscript + VBS if an older
      install still points at powershell.exe (that shortcut flashes a console).
      Also delete leftover Bot Groups / Dashboard / Profiles / Setup .lnk files.
    #>
    $vbs = Join-Path $InstallRoot "scripts\airmaze\Start-DragonAI.vbs"
    if (-not (Test-Path -LiteralPath $vbs)) {
        $vbs = Join-Path $PSScriptRoot "Start-DragonAI.vbs"
    }
    if (-not (Test-Path -LiteralPath $vbs)) { return }
    $wscript = Join-Path $env:SystemRoot "System32\wscript.exe"
    if (-not (Test-Path -LiteralPath $wscript)) { return }
    Remove-DeprecatedProductShortcuts
    $ico = Join-Path $InstallRoot "branding\dragon-ai-agent-logo.ico"
    if (-not (Test-Path -LiteralPath $ico)) { $ico = Join-Path $InstallRoot "dragon-ai-agent-logo.ico" }
    $startArgs = "//nologo `"$vbs`""
    $paths = @(
        (Join-Path ([Environment]::GetFolderPath("Desktop")) "Dragon AI Agent.lnk"),
        (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Dragon AI Agent\Dragon AI Agent.lnk")
    )
    try {
        $wsh = New-Object -ComObject WScript.Shell
        foreach ($p in $paths) {
            $dir = Split-Path -Parent $p
            if ($dir -and -not (Test-Path -LiteralPath $dir)) {
                New-Item -ItemType Directory -Force -Path $dir | Out-Null
            }
            $sc = $wsh.CreateShortcut($p)
            $alreadyHosted = $false
            if (Test-Path -LiteralPath $p) {
                $alreadyHosted = ($sc.TargetPath -like "*wscript.exe" -and $sc.Arguments -like "*Start-DragonAI.vbs*")
            }
            $sc.TargetPath = $wscript
            $sc.Arguments = $startArgs
            $sc.WorkingDirectory = $InstallRoot
            $sc.Description = "Dragon AI Agent - start the gateway and open the app"
            $sc.WindowStyle = 1
            if (Test-Path -LiteralPath $ico) { $sc.IconLocation = "$ico,0" }
            $sc.Save()
            if (-not $alreadyHosted) {
                Write-LaunchLog "Repaired product shortcut: $p"
            }
        }
    } catch {
        Write-LaunchLog "Shortcut repair skipped: $($_.Exception.Message)" "WARN"
    }
}

function Invoke-NativeDocker {
    <#
      UltraDragon: Docker CLI writes progress ("Container ... Running") to stderr.
      With $ErrorActionPreference=Stop, 2>&1 turns those ErrorRecords into a
      terminating error and a healthy launch exits 1. Same workaround as the
      machine-only patch: Continue around the native call, stringify stderr.
    #>
    param([Parameter(Mandatory = $true)][string[]]$DockerArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $prevNative = $null
    if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -Scope Global -ErrorAction SilentlyContinue) {
        $prevNative = $PSNativeCommandUseErrorActionPreference
        $PSNativeCommandUseErrorActionPreference = $false
    }
    try {
        $lines = & docker @DockerArgs 2>&1 | ForEach-Object { "$_" }
        $code = $LASTEXITCODE
        $output = if ($null -ne $lines) { ($lines -join "`n") } else { "" }
        return [pscustomobject]@{ ExitCode = $code; Output = $output }
    } finally {
        $ErrorActionPreference = $prev
        if ($null -ne $prevNative) {
            $PSNativeCommandUseErrorActionPreference = $prevNative
        }
    }
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
            Write-LaunchLog "PATH += $d"
        }
    }
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
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { return $false }
        $r = Invoke-NativeDocker -DockerArgs @("info")
        return ($r.ExitCode -eq 0)
    } catch {
        return $false
    }
}

function Test-TcpOpen {
    param([string]$TargetHost, [int]$Port, [int]$TimeoutMs = 800)
    $client = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($TargetHost, $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if (-not $ok) { return $false }
        $client.EndConnect($iar)
        return $true
    } catch {
        return $false
    } finally {
        if ($client) { try { $client.Close() } catch {} }
    }
}

function Set-DockerHeadlessSettings {
    $dir = Join-Path $env:APPDATA "Docker"
    try {
        if (-not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
    } catch {
        Write-LaunchLog "Could not create Docker settings dir: $($_.Exception.Message)" "WARN"
        return
    }
    # PowerShell hashtables are case-insensitive. camelCase only here.
    $legacy = @{
        openUIOnStartupDisabled = $true
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
        DisplayedOnboarding     = $true
        DisplayedTutorial       = $true
        AnalyticsEnabled        = $false
        DisableTips             = $true
        LicenseTermsVersion     = 2
        DisableTrayIcon         = $true
        EnableDockerAI          = $false
    }
    $targets = @(
        @{ Name = "settings.json"; Patch = $legacy },
        @{ Name = "settings-store.json"; Patch = $store }
    )
    foreach ($target in $targets) {
        $file = Join-Path $dir $target.Name
        $patch = $target.Patch
        try {
            $obj = $null
            if (Test-Path -LiteralPath $file) {
                $raw = Get-Content -LiteralPath $file -Raw -ErrorAction Stop
                if (-not [string]::IsNullOrWhiteSpace($raw)) {
                    $obj = $raw | ConvertFrom-Json -ErrorAction Stop
                }
            }
            if ($null -eq $obj) { $obj = [pscustomobject]@{} }
            foreach ($k in $patch.Keys) {
                $obj | Add-Member -MemberType NoteProperty -Name $k -Value $patch[$k] -Force
            }
            Set-Content -LiteralPath $file -Value ($obj | ConvertTo-Json -Depth 20) -Encoding UTF8
            Write-LaunchLog "Patched Docker headless settings: $file"
        } catch {
            Write-LaunchLog "Could not patch $file : $($_.Exception.Message)" "WARN"
        }
    }
}

function Set-DockerTrayOnlySettings {
    Set-DockerHeadlessSettings
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
        try {
            Start-Process -FilePath $FilePath -WindowStyle Minimized -ErrorAction Stop
        } catch {
            Start-Process -FilePath $FilePath -ErrorAction SilentlyContinue
        }
    }
}

function Hide-DockerDesktopUi {
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
}

function Start-DockerIfNeeded {
    Fix-DockerPath
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        if (Test-DockerEngine) {
            Hide-DockerDesktopUi
            Stop-DockerDesktopTrayIfEngineUp
            return $true
        }
    }
    $exe = Get-DockerDesktopExe
    if (-not $exe) {
        return $false
    }
    Set-DockerHeadlessSettings
    $env:DOCKER_DESKTOP_DISABLE_LOGIN = "1"
    Write-LaunchLog "Starting background engine (invisible; no dashboard, no tray, no onboarding)."
    $svc = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -ne "Running") {
        try {
            Start-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
        } catch {
            Start-Process -FilePath "net" -ArgumentList "start","com.docker.service" -Verb RunAs -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue
        }
    }
    $backend = Get-DockerBackendExe
    if ($backend) {
        Start-HiddenNativeProcess -FilePath $backend
    }
    if (-not (Test-DockerEngine)) {
        Start-HiddenNativeProcess -FilePath $exe
    }
    $deadline = (Get-Date).AddMinutes(3)
    while ((Get-Date) -lt $deadline) {
        Hide-DockerDesktopUi
        Fix-DockerPath
        if ((Get-Command docker -ErrorAction SilentlyContinue) -and (Test-DockerEngine)) {
            Hide-DockerDesktopUi
            Stop-DockerDesktopTrayIfEngineUp
            return $true
        }
        Start-Sleep -Seconds 4
        if ($script:LaunchForm) { [Windows.Forms.Application]::DoEvents() }
    }
    Hide-DockerDesktopUi
    return ((Get-Command docker -ErrorAction SilentlyContinue) -and (Test-DockerEngine))
}

function Test-DockerCliFailureText {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    return ($Text -match 'error during connect|The system cannot find the file|open //\./pipe/docker|Cannot connect to the Docker daemon|dockerDesktopLinuxEngine|failed to connect')
}

function Invoke-DockerCompose {
    param([string[]]$ComposeArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $r = Invoke-NativeDocker -DockerArgs (@("compose", "-f", "docker-compose.embedded.yml") + $ComposeArgs)
        if ($r.Output) { Write-LaunchLog ($r.Output.Trim()) }
        if ($r.ExitCode -ne 0) {
            throw "docker compose $($ComposeArgs -join ' ') failed (exit $($r.ExitCode)). $($r.Output)"
        }
        if (Test-DockerCliFailureText $r.Output) {
            throw "Dragon AI Agent could not reach its background engine (compose printed a connect/pipe error but did not fail closed). Open the app again in a minute. $($r.Output)"
        }
        return $r.Output
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Start-GatewayContainer {
    param([string]$ComposePath)
    $data = Join-Path $env:USERPROFILE ".hermes-airmaze-embedded"
    if (-not (Test-Path $data)) { New-Item -ItemType Directory -Force -Path $data | Out-Null }
    $env:HERMES_EMBEDDED_DATA = $data
    $applyModels = Join-Path $PSScriptRoot "Apply-GatewayModels.ps1"
    if (Test-Path -LiteralPath $applyModels) {
        try {
            & $applyModels -HermesHome $data -IfMissing | Out-Null
            Write-LaunchLog "Applied default chat/image LLMs if gateway config was missing them"
        } catch {
            Write-LaunchLog "Gateway model defaults skipped: $($_.Exception.Message)" "WARN"
        }
    }

    if (-not (Test-DockerEngine)) {
        throw "Dragon AI Agent could not start its background engine. Open the app again in a minute."
    }

    Push-Location $InstallRoot
    try {
        $doPull = [bool]$Pull
        if ($SkipPull) { $doPull = $false }
        if ($doPull) {
            Update-LaunchStatus "Updating gateway image (docker compose pull)..."
            Invoke-DockerCompose -ComposeArgs @("pull") | Out-Null
        }
        Update-LaunchStatus "Starting embedded gateway..."
        Invoke-DockerCompose -ComposeArgs @("up", "-d") | Out-Null
        Invoke-DockerCompose -ComposeArgs @("ps") | Out-Null
    } finally {
        Pop-Location
    }

    $running = $false
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $insp = Invoke-NativeDocker -DockerArgs @("inspect", "-f", "{{.State.Running}}", "hermes-airmaze-gw")
        $running = ($insp.ExitCode -eq 0 -and $insp.Output.Trim() -eq "true")
    } catch {
        $running = $false
    } finally {
        $ErrorActionPreference = $prev
    }
    if (-not $running) {
        throw "Container hermes-airmaze-gw is not running. Docker compose did not bring the gateway up. See launch.log and: docker logs hermes-airmaze-gw"
    }
}

function Test-HttpReachable {
    param(
        [string]$Url,
        [int]$TimeoutSec = 3,
        [hashtable]$Headers = $null
    )
    try {
        if ($null -eq $Headers) {
            $Headers = @{ Authorization = "Bearer $($script:ApiKey)" }
        }
        $null = Invoke-WebRequest -Uri $Url -Headers $Headers -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
        return $true
    } catch {
        $resp = $_.Exception.Response
        if ($resp) { return $true }
        $msg = [string]$_.Exception.Message
        if ($msg -match '401|403|404|400') { return $true }
        return $false
    }
}

function Test-DesktopServeReady {
    param([int]$TimeoutSec = 3)
    $headers = @{ "X-Hermes-Session-Token" = $script:DesktopSessionToken }
    if (Test-HttpReachable -Url "$($script:DesktopServeUrl)/api/health" -TimeoutSec $TimeoutSec -Headers $headers) {
        return $true
    }
    return (Test-HttpReachable -Url "$($script:DesktopServeUrl)/api/status" -TimeoutSec $TimeoutSec -Headers $headers)
}

function Test-DesktopWebUIReady {
    param([int]$TimeoutSec = 3)
    $url = $script:DesktopWebUIUrl
    try {
        $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
        $body = [string]$resp.Content
        if ($body -match 'web UI disabled' -or $body -match 'Headless backend \(hermes serve\)') {
            Write-LaunchLog "Desktop web UI at $url returned the headless hermes serve page (web UI disabled)" "WARN"
            return $false
        }
        if ($body -match '<html' -or $body -match '<!DOCTYPE') {
            return $true
        }
        Write-LaunchLog "Desktop web UI at $url is reachable but is not an HTML page" "WARN"
        return $false
    } catch {
        return $false
    }
}

function Sync-EmbeddedGatewayProfiles {
    <#
      Remote Desktop serve lists bots from the Linux HERMES_HOME volume,
      not %LOCALAPPDATA%\hermes\profiles. Mirror applied bots into that volume.
    #>
    $embedded = Join-Path $env:USERPROFILE ".hermes-airmaze-embedded"
    $srcRoot = Join-Path $env:LOCALAPPDATA "hermes\profiles"
    if (-not (Test-Path -LiteralPath $srcRoot)) { return 0 }
    $destRoot = Join-Path $embedded "profiles"
    New-Item -ItemType Directory -Force -Path $destRoot | Out-Null
    $n = 0
    Get-ChildItem -LiteralPath $srcRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Name -in @("default", "hermes")) { return }
        $dest = Join-Path $destRoot $_.Name
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        foreach ($name in @("SOUL.md", "bot.yaml", "profile.yaml", "config.yaml", "bot.meta.json")) {
            $src = Join-Path $_.FullName $name
            if (Test-Path -LiteralPath $src) {
                Copy-Item -LiteralPath $src -Destination (Join-Path $dest $name) -Force
            }
        }
        $bot = Join-Path $_.FullName "bot.yaml"
        if ((Test-Path -LiteralPath $bot) -and -not (Test-Path -LiteralPath (Join-Path $dest "config.yaml"))) {
            Copy-Item -LiteralPath $bot -Destination (Join-Path $dest "config.yaml") -Force
        }
        $n++
    }
    Write-LaunchLog "Synced $n profile(s) into embedded gateway $destRoot"
    return $n
}

function Set-EmbeddedDesktopRemoteConnection {
    $setter = Join-Path $PSScriptRoot "Set-EmbeddedDesktopConnection.ps1"
    if (-not (Test-Path -LiteralPath $setter)) {
        $setter = Join-Path $InstallRoot "scripts\airmaze\Set-EmbeddedDesktopConnection.ps1"
    }
    if (-not (Test-Path -LiteralPath $setter)) {
        Write-LaunchLog "Set-EmbeddedDesktopConnection.ps1 missing; Desktop Remote was not auto-wired" "WARN"
        return $false
    }
    try {
        if (Get-Command Set-DragonAIDesktopUserDataEnv -ErrorAction SilentlyContinue) {
            Set-DragonAIDesktopUserDataEnv -InstallRoot $InstallRoot | Out-Null
        } elseif (-not $env:HERMES_DESKTOP_USER_DATA_DIR) {
            $env:HERMES_DESKTOP_USER_DATA_DIR = Join-Path $InstallRoot "electron-userdata"
        }
        $conn = Join-Path $env:HERMES_DESKTOP_USER_DATA_DIR "connections.json"
        & $setter -Url $script:DesktopServeUrl -Token $script:DesktopSessionToken -ConnectionsPath $conn
        Write-LaunchLog "Desktop Remote Embedded Linux wired to $($script:DesktopServeUrl) ($conn; standalone Hermes primary stays local)"
        return $true
    } catch {
        Write-LaunchLog "Desktop Remote wire skipped: $($_.Exception.Message)" "WARN"
        return $false
    }
}

function Wait-GatewayReady {
    param([int]$TimeoutSec = 90, [switch]$RequireDesktopServe, [switch]$RequireDesktopWebUI)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $last = @{ Ok = $false; Dashboard = $false; Api = $false; DesktopServe = $false; DesktopWebUI = $false }
    while ((Get-Date) -lt $deadline) {
        $apiTcp = Test-TcpOpen -TargetHost $ApiHost -Port $ApiPort
        $apiHttp = $false
        if ($apiTcp) {
            $apiHttp = Test-HttpReachable -Url "http://${ApiHost}:${ApiPort}/v1/models"
            if (-not $apiHttp) {
                $apiHttp = Test-HttpReachable -Url "http://${ApiHost}:${ApiPort}/"
            }
        }
        $dash = Test-TcpOpen -TargetHost $ApiHost -Port $DashPort
        $desktopTcp = Test-TcpOpen -TargetHost $ApiHost -Port $DesktopServePort
        $desktopHttp = $false
        if ($desktopTcp) {
            $desktopHttp = Test-DesktopServeReady
        }
        $webUI = Test-DesktopWebUIReady
        $last = @{
            Ok            = ($apiTcp -and $apiHttp)
            Dashboard     = $dash
            Api           = ($apiTcp -and $apiHttp)
            DesktopServe  = ($desktopTcp -and $desktopHttp)
            DesktopWebUI  = $webUI
        }
        # Host TCP/HTTP on 8642 is required. 9119 alone is not enough (docker-proxy
        # can listen while the dashboard process crash-loops). Bot Screen also
        # needs the Desktop serve proxy on 8650 (/api/health + /api/ws). The
        # product window needs the dashboard web UI on 8660 (not the headless
        # "web UI disabled" body on 8650 GET /).
        $serveOk = ((-not $RequireDesktopServe) -or $last.DesktopServe)
        $uiOk = ((-not $RequireDesktopWebUI) -or $last.DesktopWebUI)
        if ($last.Ok -and $serveOk -and $uiOk) {
            return $last
        }
        Start-Sleep -Seconds 2
        if ($script:LaunchForm) { [Windows.Forms.Application]::DoEvents() }
    }
    return $last
}

function Open-Dashboard {
    if (-not $OpenDashboard -or $NoBrowser) { return }
    Update-LaunchStatus "Opening dashboard $DashboardUrl"
    try {
        Start-Process $DashboardUrl
    } catch {
        try { Start-Process "cmd.exe" -ArgumentList "/c", "start", $DashboardUrl } catch {
            throw "Could not open a browser for $DashboardUrl : $($_.Exception.Message)"
        }
    }
}

function Start-AgentDesktopOrThrow {
    if (-not (Get-Command Find-HermesDesktopExe -ErrorAction SilentlyContinue) -and -not (Get-Command Find-DragonDesktopExe -ErrorAction SilentlyContinue)) {
        throw "Find-HermesDesktop.ps1 was not loaded. Re-run DragonAIAgentSetup so scripts\airmaze\Find-HermesDesktop.ps1 is installed."
    }
    if (Get-Command Set-DragonAIDesktopUserDataEnv -ErrorAction SilentlyContinue) {
        Set-DragonAIDesktopUserDataEnv -InstallRoot $InstallRoot | Out-Null
    }
    $exe = $null
    if (Get-Command Install-DragonAIPrivateDesktop -ErrorAction SilentlyContinue) {
        $exe = Install-DragonAIPrivateDesktop -InstallRoot $InstallRoot
    }
    if (-not $exe -and (Get-Command Find-DragonDesktopExe -ErrorAction SilentlyContinue)) {
        $exe = Find-DragonDesktopExe -InstallRoot $InstallRoot
    }
    if (-not $exe -and (Get-Command Find-HermesDesktopExe -ErrorAction SilentlyContinue)) {
        $exe = Find-HermesDesktopExe -InstallRoot $InstallRoot
    }
    $hint = Join-Path $InstallRoot "desktop\win-unpacked\DragonAIAgent.exe"
    if ($exe -and (Get-Command Test-DragonAIHermesInstallPath -ErrorAction SilentlyContinue)) {
        if (Test-DragonAIHermesInstallPath -Path $exe) { $exe = $null }
    }
    if (-not $exe -or -not (Test-Path -LiteralPath $exe)) {
        throw @"
Dragon AI Agent desktop was not found in this package, so there is no app window to show.

Expected:
  $hint

Re-download DragonAIAgentSetup.exe and run that one installer.
"@
    }
    if (Get-Command Test-DragonAIPrivateDesktopPath -ErrorAction SilentlyContinue) {
        if (-not (Test-DragonAIPrivateDesktopPath -Path $exe)) {
            throw "Refuse launch outside DragonAIAgent: $exe"
        }
    }
    Write-LaunchLog "Launching Dragon AI Agent desktop: $exe"
    Save-DragonAIDesktopPointer -ExePath $exe -InstallRoot $InstallRoot | Out-Null
    # Bot Screen / Remote stays on headless serve :8650. The window loads :8660.
    $env:HERMES_DESKTOP_REMOTE_URL = $script:DesktopServeUrl
    $env:HERMES_DESKTOP_REMOTE_TOKEN = $script:DesktopSessionToken
    $env:DRAGON_AI_UI_URL = $script:DesktopWebUIUrl
    Write-LaunchLog "Desktop Screen is $($script:DesktopWebUIUrl) (dashboard web UI). Gateway API is http://${ApiHost}:${ApiPort}/. Desktop serve API is $($script:DesktopServeUrl) (not the window)."
    if (Get-Command Start-DragonAIDesktopClient -ErrorAction SilentlyContinue) {
        Start-DragonAIDesktopClient -ExePath $exe -InstallRoot $InstallRoot
    } else {
        Start-HermesDesktopClient -ExePath $exe -InstallRoot $InstallRoot
    }
    return $exe
}

function Test-OnboardingNeedsUi {
    $progressPath = Join-Path $env:LOCALAPPDATA "DragonAIAgent\onboarding\progress.json"
    if (-not (Test-Path -LiteralPath $progressPath)) { return $true }
    try {
        $p = Get-Content -LiteralPath $progressPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($p.skipped) { return $false }
        $welcome = $null
        if ($p.steps) {
            if ($p.steps.PSObject.Properties.Name -contains "welcome") {
                $welcome = [string]$p.steps.welcome
            }
        }
        if ([string]::IsNullOrWhiteSpace($welcome) -or $welcome -eq "pending") { return $true }
        return $false
    } catch {
        return $false
    }
}

function Exclude-DragonAIHermesBots {
    $engine = Join-Path $PSScriptRoot "exclude_hermes_bot.py"
    if (-not (Test-Path -LiteralPath $engine)) {
        $engine = Join-Path $InstallRoot "scripts\airmaze\exclude_hermes_bot.py"
    }
    if (-not (Test-Path -LiteralPath $engine)) { return }
    $desktop = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "hermes\profiles" } else { "" }
    $embedded = if ($env:USERPROFILE) { Join-Path $env:USERPROFILE ".hermes-airmaze-embedded\profiles" } else { "" }
    $py = Get-Command python3 -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
    if (-not $py) { return }
    try {
        & $py.Source $engine purge --desktop $desktop --embedded $embedded | Out-Null
        Write-LaunchLog "Excluded leftover Hermes bot profiles (default/hermes)"
    } catch {
        Write-LaunchLog "Hermes exclude skipped: $($_.Exception.Message)" "WARN"
    }
}

function Start-DragonAITeamsPicker {
    $engine = Join-Path $PSScriptRoot "teams_picker.py"
    if (-not (Test-Path -LiteralPath $engine)) {
        $engine = Join-Path $InstallRoot "scripts\airmaze\teams_picker.py"
    }
    if (-not (Test-Path -LiteralPath $engine)) { return }
    $py = Get-Command python3 -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
    if (-not $py) { return }
    $desktop = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "hermes\profiles" } else { Join-Path $InstallRoot "hermes-profiles" }
    $embedded = if ($env:USERPROFILE) { Join-Path $env:USERPROFILE ".hermes-airmaze-embedded\profiles" } else { "" }
    $payload = $InstallRoot
    $scriptTree = Join-Path $PSScriptRoot "..\.."
    $cosMark = "bot-groups\marketing-team\bots\content-strategist\SOUL.md"
    if (Test-Path -LiteralPath (Join-Path $scriptTree $cosMark)) {
        $payload = (Resolve-Path -LiteralPath $scriptTree).Path
    } elseif (-not (Test-Path -LiteralPath (Join-Path $payload $cosMark))) {
        if (Test-Path -LiteralPath (Join-Path $payload "bot-groups\catalog.json")) {
            # keep InstallRoot
        } elseif (Test-Path -LiteralPath (Join-Path $scriptTree "bot-groups\catalog.json")) {
            $payload = (Resolve-Path -LiteralPath $scriptTree).Path
        }
    }
    try {
        Start-Process -FilePath $py.Source -ArgumentList @(
            $engine, "serve",
            "--payload", $payload,
            "--install", $InstallRoot,
            "--desktop", $desktop,
            "--embedded", $embedded,
            "--host", "127.0.0.1",
            "--port", "8653"
        ) -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
        Write-LaunchLog "Teams picker helper on http://127.0.0.1:8653/api/teams"
    } catch {
        Write-LaunchLog "Teams picker helper skipped: $($_.Exception.Message)" "WARN"
    }
}

function Start-DragonAIVoiceChat {
    $engine = Join-Path $PSScriptRoot "voice_chat.py"
    if (-not (Test-Path -LiteralPath $engine)) {
        $engine = Join-Path $InstallRoot "scripts\airmaze\voice_chat.py"
    }
    if (-not (Test-Path -LiteralPath $engine)) { return }
    $py = Get-Command python3 -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
    if (-not $py) { return }
    $embeddedHome = if ($env:USERPROFILE) { Join-Path $env:USERPROFILE ".hermes-airmaze-embedded" } else { Join-Path $InstallRoot "hermes-home" }
    try {
        Start-Process -FilePath $py.Source -ArgumentList @(
            $engine, "serve",
            "--home", $embeddedHome,
            "--host", "127.0.0.1",
            "--port", "8654"
        ) -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
        Write-LaunchLog "Voice helper on http://127.0.0.1:8654/api/voice (GPT + Grok duplex)"
    } catch {
        Write-LaunchLog "Voice helper skipped: $($_.Exception.Message)" "WARN"
    }
}

function Start-OnboardingIfNeeded {
    # WinForms Onboard-Wizard is deprecated as a first-run surface.
    # Model defaults are applied by Apply-GatewayModels (-IfMissing) before compose up.
    # Operators pick models in the in-app Models UI.
    if ($NoWizard) { return }
    Write-LaunchLog "First-run setup uses in-app Models UI (WinForms Onboard-Wizard shortcut retired)"
}

function Get-LaunchPlan {
    $compose = Join-Path $InstallRoot "docker-compose.embedded.yml"
    return [ordered]@{
        product       = $ProductName
        installRoot   = $InstallRoot
        compose       = $compose
        composeExists = (Test-Path -LiteralPath $compose)
        dashboardUrl  = $DashboardUrl
        api           = "${ApiHost}:${ApiPort}"
        desktopServe  = "${ApiHost}:${DesktopServePort}"
        desktopWebUI  = $script:DesktopWebUIUrl
        log           = $script:LaunchLog
        ui            = @(
            "windowless host: Start-DragonAI.vbs / wscript.exe (no console)",
            "blocking error dialog on failure (never a raw console)",
            "require packaged Dragon AI Agent desktop (%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked\DragonAIAgent.exe)",
            "set HERMES_DESKTOP_USER_DATA_DIR to %LOCALAPPDATA%\DragonAIAgent\electron-userdata",
            "overlay unpacked Electron UI chrome on the private Dragon copy only (refuse branding outside DragonAIAgent)",
            "standalone Hermes connections.json primary stays local",
            "launch Dragon AI Agent desktop only (not $DashboardUrl)",
            "start the background engine invisibly when docker info fails (already running is a no-op; no dashboard, no onboarding, no tray icon)",
            "first-run uses in-app Models UI (WinForms Onboard-Wizard not launched)",
            "do not show Waiting for gateway Setup/Close status window (Dragon AI Agent is the loading UX)",
            "docker CLI stderr progress is not a terminating error",
            "Desktop Remote -> $($script:DesktopServeUrl) (token mode; not :8642)",
            "wait for /api/health on the Desktop serve proxy with X-Hermes-Session-Token",
            "window loads $($script:DesktopWebUIUrl) (hermes dashboard web UI), not :8650 GET /",
            "fail launch if the desktop URL returns the headless web UI disabled page"
        )
    }
}

function Invoke-Smoke {
    $plan = Get-LaunchPlan
    Write-Host "SMOKE: $ProductName launch plan"
    Write-Host ("  InstallRoot: {0}" -f $plan.installRoot)
    Write-Host ("  Compose:     {0} (exists={1})" -f $plan.compose, $plan.composeExists)
    Write-Host ("  Dashboard:   {0}" -f $plan.dashboardUrl)
    Write-Host ("  API:         {0}" -f $plan.api)
    Write-Host ("  Desktop:     {0}" -f $plan.desktopServe)
    Write-Host ("  Web UI:      {0}" -f $plan.desktopWebUI)
    Write-Host ("  Log:         {0}" -f $plan.log)
    foreach ($step in $plan.ui) {
        Write-Host ("  UI:          {0}" -f $step)
    }
    $self = $PSCommandPath
    if (-not $self) { $self = $MyInvocation.MyCommand.Path }
    $text = Get-Content -LiteralPath $self -Raw -ErrorAction Stop
    $required = @(
        "Show-DragonDialog",
        "Find-HermesDesktopExe",
        "Start-AgentDesktopOrThrow",
        "win-unpacked",
        "Start-DragonAI.vbs",
        "SilentHost",
        "OpenDashboard",
        "StartDocker",
        "Start-DockerIfNeeded",
        "Set-DockerTrayOnlySettings",
        "Set-DockerHeadlessSettings",
        "Hide-DockerDesktopUi",
        "disableTrayIcon",
        "openUIOnStartupDisabled",
        "DebugConsole",
        "New-LaunchStatusForm",
        "do not show Waiting for gateway Setup/Close status window",
        "Invoke-NativeDocker",
        "Repair-DragonAIProductShortcuts",
        "Remove-DeprecatedProductShortcuts",
        "CreateNoWindow",
        "hermes-airmaze-gw is not running",
        "Set-EmbeddedDesktopRemoteConnection",
        "X-Hermes-Session-Token",
        "8650",
        "Apply-DragonAIDesktopUiBranding",
        "Install-DragonAIPrivateDesktop",
        "DragonAIAgent.exe",
        "Find-DragonDesktopExe",
        "HERMES_DESKTOP_USER_DATA_DIR",
        "electron-userdata",
        "Exclude-DragonAIHermesBots",
        "teams_picker",
        "8653",
        "voice_chat",
        "8654",
        "8660",
        "Test-DesktopWebUIReady",
        "web UI disabled"
    )
    foreach ($token in $required) {
        if ($text -notlike "*$token*") {
            throw "Smoke: launcher is missing required symbol '$token'"
        }
    }
    Write-Host "SMOKE OK: a normal start launches Dragon AI Agent or a blocking error dialog. No secrets required."
    return 0
}

# --- Main -------------------------------------------------------------------

if ($Smoke) {
    $code = Invoke-Smoke
    exit $code
}

$script:WinFormsOk = Test-WinFormsAvailable
$script:Windowless = $false
$showUi = -not $GatewayOnly
# Primary success is the desktop client. :9119 stays closed unless -OpenDashboard.
if (-not $OpenDashboard) {
    $NoBrowser = $true
}
if ($SilentHost) {
    $NoBrowser = $true
}
# Hide the console for the installed shortcut (wscript / old explorer .lnk).
# Keep it when a human launched this .ps1 from a terminal, or passed -DebugConsole.
if ($DebugConsole) {
    $script:Windowless = $false
} elseif ($SilentHost -or (Test-LaunchedFromShortcut)) {
    $script:Windowless = $true
    Hide-ConsoleWindow
}

try {
    Repair-DragonAIProductShortcuts
    if ($showUi) {
        # James: do not pop the Waiting for gateway / Setup / Close monitor.
        # Dragon AI Agent desktop is the default loading experience. New-LaunchStatusForm
        # stays in-tree for branding tests / optional debug, but is not shown
        # on a normal Desktop / Start Menu launch. Progress is launch.log only.
        if ($script:Windowless) { Hide-ConsoleWindow }
    }

    $compose = Join-Path $InstallRoot "docker-compose.embedded.yml"
    if (-not (Test-Path -LiteralPath $compose)) {
        throw "Dragon AI Agent is not installed (missing $compose). Run DragonAIAgentSetup.exe first."
    }

    Update-LaunchStatus "Starting background engine..."
    Fix-DockerPath
    if ($StartDocker) {
        Write-LaunchLog "StartDocker is the default launch path; starting the background engine invisibly if needed"
    }
    if (-not (Start-DockerIfNeeded)) {
        throw "Dragon AI Agent could not start its background engine. Open the app again in a minute."
    }

    Start-GatewayContainer -ComposePath $compose
    Exclude-DragonAIHermesBots
    Start-DragonAITeamsPicker
    Start-DragonAIVoiceChat
    try { Sync-EmbeddedGatewayProfiles | Out-Null } catch {
        Write-LaunchLog "Profile sync skipped: $($_.Exception.Message)" "WARN"
    }
    Set-EmbeddedDesktopRemoteConnection | Out-Null

    if ($showUi) {
        Start-OnboardingIfNeeded
        # Open Dragon AI Agent first so its window is the loading UX
        # while :8642 / :8650 become reachable. Do not insert a Dragon status form.
        $exe = Start-AgentDesktopOrThrow
    }

    Update-LaunchStatus "Waiting for gateway API on ${ApiHost}:${ApiPort} and Desktop serve on ${ApiHost}:${DesktopServePort}..."
    $ready = Wait-GatewayReady -TimeoutSec 120 -RequireDesktopServe -RequireDesktopWebUI
    if (-not $ready.Ok) {
        throw "The embedded gateway API is not reachable from Windows at http://${ApiHost}:${ApiPort}/ (container may be loopback-bound or crash-looping). See %LOCALAPPDATA%\DragonAIAgent\launch.log and docker logs hermes-airmaze-gw."
    }
    if (-not $ready.DesktopServe) {
        throw "The Desktop Bot Screen backend is not reachable at $($script:DesktopServeUrl)/api/health (expected X-Hermes-Session-Token + /api/ws). Check: docker logs hermes-airmaze-desktop && docker logs hermes-airmaze-desktop-proxy. Do not point Remote at :8642 (OpenAI API only)."
    }
    if (-not $ready.DesktopWebUI) {
        throw "The desktop chat screen is not reachable at $($script:DesktopWebUIUrl) (or it returned the headless web UI disabled page). Check: docker logs hermes-airmaze-desktop-ui && docker logs hermes-airmaze-desktop-ui-proxy. Do not open :8650 in the window; that is hermes serve, not the chat UI."
    }

    if ($showUi) {
        if ($OpenDashboard) {
            try { Open-Dashboard } catch { Write-LaunchLog "Dashboard open skipped: $($_.Exception.Message)" "WARN" }
        }
        $msg = "Dragon AI Agent launched.`nDesktop Screen: $($script:DesktopWebUIUrl)`nGateway API: http://${ApiHost}:${ApiPort}/`nDesktop serve API: $($script:DesktopServeUrl)"
        Update-LaunchStatus $msg
        if ($script:LaunchForm -and -not $script:LaunchForm.IsDisposed) {
            try {
                $script:LaunchForm.TopMost = $false
                $script:LaunchForm.Close()
            } catch {}
        }
    } else {
        Write-LaunchLog "Gateway-only: 127.0.0.1:$ApiPort  desktop serve: $($script:DesktopServeUrl)  dashboard: $DashboardUrl"
    }
    exit 0
} catch {
    $err = $_.Exception.Message
    if ($script:LaunchForm) {
        try { $script:LaunchForm.Hide() } catch {}
    }
    if ($showUi) {
        Show-DragonDialog -Message $err -Kind Error
    } else {
        Write-LaunchLog $err "ERROR"
    }
    exit 1
}
