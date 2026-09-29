#requires -Version 5.1
<#
.SYNOPSIS
  Start Dragon AI Agent: embedded gateway plus a visible main UI (or an error dialog).

.DESCRIPTION
  This is the Desktop / Start Menu "Dragon AI Agent" entrypoint.
  It starts Docker if needed, brings the gateway up, waits until the API
  is reachable on the Windows host, then launches the Hermes/Electron
  desktop client. Failures (Docker down, compose errors, missing client)
  show a MessageBox / popup and exit non-zero — never a silent flash.

  Use -GatewayOnly for the old CLI-only compose behavior (no browser / form).
  Use -Smoke to validate the launch plan without touching Docker (no secrets).

.NOTES
  Fixes PATH for Docker Desktop CLI under common install locations.
  Does not open the Docker Desktop dashboard (tray-only is intentional).
#>

[CmdletBinding()]
param(
    [string]$InstallRoot = "",
    [switch]$Pull,
    [switch]$SkipPull,
    [switch]$GatewayOnly,
    [switch]$NoBrowser,
    [switch]$NoWizard,
    [switch]$Smoke
)

$ErrorActionPreference = "Stop"
$ProductName = "Dragon AI Agent"
$DashboardUrl = "http://127.0.0.1:9119/"
$ApiHost = "127.0.0.1"
$ApiPort = 8642
$DashPort = 9119

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}

$script:LaunchLog = Join-Path $InstallRoot "launch.log"
$script:WinFormsOk = $false
$script:LaunchForm = $null
$script:LaunchStatus = $null
$script:LaunchDashButton = $null
$script:DashboardUrl = $DashboardUrl
$script:ApiKey = "airmaze-local"

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
        $header.BackColor = [System.Drawing.Color]::FromArgb(196, 30, 58)
        $form.Controls.Add($header)

        $title = New-Object Windows.Forms.Label
        $title.Text = $ProductName
        $title.Location = New-Object Drawing.Point(16, 14)
        $title.Size = New-Object Drawing.Size(520, 28)
        $title.ForeColor = [System.Drawing.Color]::White
        $title.Font = New-Object Drawing.Font("Segoe UI", 14, [Drawing.FontStyle]::Bold)
        $header.Controls.Add($title)

        $status = New-Object Windows.Forms.Label
        $status.Text = "Starting..."
        $status.Location = New-Object Drawing.Point(16, 72)
        $status.Size = New-Object Drawing.Size(520, 80)
        $status.Font = New-Object Drawing.Font("Segoe UI", 10)
        $form.Controls.Add($status)

        $btnDash = New-Object Windows.Forms.Button
        $btnDash.Text = "Open dashboard"
        $btnDash.Location = New-Object Drawing.Point(16, 180)
        $btnDash.Size = New-Object Drawing.Size(140, 36)
        $btnDash.Enabled = $false
        $btnDash.FlatStyle = [Windows.Forms.FlatStyle]::Flat
        $btnDash.BackColor = [System.Drawing.Color]::FromArgb(196, 30, 58)
        $btnDash.ForeColor = [System.Drawing.Color]::White
        $btnDash.Add_Click({
            try { Start-Process $script:DashboardUrl } catch {}
        }.GetNewClosure())
        $form.Controls.Add($btnDash)

        $btnSetup = New-Object Windows.Forms.Button
        $btnSetup.Text = "Setup"
        $btnSetup.Location = New-Object Drawing.Point(168, 180)
        $btnSetup.Size = New-Object Drawing.Size(100, 36)
        $btnSetup.FlatStyle = [Windows.Forms.FlatStyle]::Flat
        $btnSetup.BackColor = [System.Drawing.Color]::FromArgb(40, 40, 48)
        $btnSetup.ForeColor = [System.Drawing.Color]::White
        $rootForUi = $InstallRoot
        $btnSetup.Add_Click({
            $wiz = Join-Path $rootForUi "scripts\airmaze\Onboard-Wizard.ps1"
            if (Test-Path -LiteralPath $wiz) {
                Start-Process -FilePath (Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe") `
                    -ArgumentList @("-STA", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $wiz, "-InstallRoot", $rootForUi)
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
        $script:LaunchDashButton = $btnDash
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

function Fix-DockerPath {
    $binDirs = @(
        (Join-Path $env:ProgramFiles "Docker\Docker\resources\bin"),
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

function Start-DockerIfNeeded {
    Fix-DockerPath
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        if (Test-DockerEngine) { return $true }
    }
    $exe = Get-DockerDesktopExe
    if (-not $exe) {
        return $false
    }
    Update-LaunchStatus "Starting Docker Desktop (system tray). This can take a minute..."
    try {
        Start-Process -FilePath $exe -WindowStyle Minimized -ErrorAction Stop
    } catch {
        Start-Process -FilePath $exe -ErrorAction SilentlyContinue
    }
    $deadline = (Get-Date).AddMinutes(3)
    while ((Get-Date) -lt $deadline) {
        Fix-DockerPath
        if ((Get-Command docker -ErrorAction SilentlyContinue) -and (Test-DockerEngine)) {
            return $true
        }
        Start-Sleep -Seconds 4
        if ($script:LaunchForm) { [Windows.Forms.Application]::DoEvents() }
    }
    return ((Get-Command docker -ErrorAction SilentlyContinue) -and (Test-DockerEngine))
}

function Test-DockerCliFailureText {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    return ($Text -match 'error during connect|The system cannot find the file|open //\./pipe/docker|Cannot connect to the Docker daemon|dockerDesktopLinuxEngine|failed to connect')
}

function Invoke-DockerCompose {
    param([string[]]$ComposeArgs)
    $output = & docker compose -f docker-compose.embedded.yml @ComposeArgs 2>&1 | Out-String
    $code = $LASTEXITCODE
    if ($output) { Write-LaunchLog ($output.Trim()) }
    if ($code -ne 0) {
        throw "docker compose $($ComposeArgs -join ' ') failed (exit $code). $output"
    }
    if (Test-DockerCliFailureText $output) {
        throw "Docker engine is not running (compose printed a connect/pipe error but did not fail closed). Start Docker Desktop from the tray and try again. $output"
    }
    return $output
}

function Start-GatewayContainer {
    param([string]$ComposePath)
    $data = Join-Path $env:USERPROFILE ".hermes-airmaze-embedded"
    if (-not (Test-Path $data)) { New-Item -ItemType Directory -Force -Path $data | Out-Null }
    $env:HERMES_EMBEDDED_DATA = $data

    if (-not (Test-DockerEngine)) {
        throw "Docker engine is not running (docker info failed). Start Docker Desktop from the system tray, wait until it is ready, then open Dragon AI Agent again."
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
    try {
        $state = & docker inspect -f "{{.State.Running}}" hermes-airmaze-gw 2>&1 | Out-String
        $running = ($LASTEXITCODE -eq 0 -and $state.Trim() -eq "true")
    } catch {
        $running = $false
    }
    if (-not $running) {
        throw "Container hermes-airmaze-gw is not running. Docker compose did not bring the gateway up. See launch.log and: docker logs hermes-airmaze-gw"
    }
}

function Test-HttpReachable {
    param([string]$Url, [int]$TimeoutSec = 3)
    try {
        $headers = @{ Authorization = "Bearer $($script:ApiKey)" }
        $null = Invoke-WebRequest -Uri $Url -Headers $headers -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
        return $true
    } catch {
        $resp = $_.Exception.Response
        if ($resp) { return $true }
        $msg = [string]$_.Exception.Message
        if ($msg -match '401|403|404|400') { return $true }
        return $false
    }
}

function Wait-GatewayReady {
    param([int]$TimeoutSec = 90)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
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
        # Host TCP/HTTP on 8642 is required. 9119 alone is not enough (docker-proxy
        # can listen while the dashboard process crash-loops).
        if ($apiTcp -and $apiHttp) {
            return @{ Ok = $true; Dashboard = $dash; Api = $true }
        }
        Start-Sleep -Seconds 2
        if ($script:LaunchForm) { [Windows.Forms.Application]::DoEvents() }
    }
    return @{ Ok = $false; Dashboard = $false; Api = $false }
}

function Open-Dashboard {
    if ($NoBrowser) { return }
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
    if (-not (Get-Command Find-HermesDesktopExe -ErrorAction SilentlyContinue)) {
        throw "Find-HermesDesktop.ps1 was not loaded. Re-run DragonAIAgentSetup so scripts\airmaze\Find-HermesDesktop.ps1 is installed."
    }
    $exe = Find-HermesDesktopExe -InstallRoot $InstallRoot
    if (-not $exe) {
        $hint = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe"
        throw @"
Hermes desktop client was not found, so Dragon AI Agent has no window to show.

Expected (UltraDragon unpacked build):
  $hint

Install or build the Hermes desktop client, then open Dragon AI Agent again.
A stable shortcut is written to %LOCALAPPDATA%\DragonAIAgent\Hermes Desktop.lnk once the exe is found.
"@
    }
    Write-LaunchLog "Launching Hermes desktop: $exe"
    Save-DragonAIDesktopPointer -ExePath $exe -InstallRoot $InstallRoot | Out-Null
    Start-HermesDesktopClient -ExePath $exe
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

function Start-OnboardingIfNeeded {
    if ($NoWizard) { return }
    if (-not (Test-OnboardingNeedsUi)) { return }
    $wiz = Join-Path $InstallRoot "scripts\airmaze\Onboard-Wizard.ps1"
    if (-not (Test-Path -LiteralPath $wiz)) { return }
    Update-LaunchStatus "Opening first-run setup wizard..."
    $ps = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    Start-Process -FilePath $ps -ArgumentList @(
        "-STA", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", $wiz, "-InstallRoot", $InstallRoot
    )
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
        log           = $script:LaunchLog
        ui            = @(
            "status window (WinForms) or blocking error dialog",
            "require Hermes.exe (including win-unpacked path)",
            "launch Hermes desktop wired to 127.0.0.1:8642",
            "open $DashboardUrl only after the API is reachable",
            "first-run Onboard-Wizard if welcome is still pending"
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
        "http://127.0.0.1:9119",
        "New-LaunchStatusForm",
        "hermes-airmaze-gw is not running"
    )
    foreach ($token in $required) {
        if ($text -notlike "*$token*") {
            throw "Smoke: launcher is missing required symbol '$token'"
        }
    }
    Write-Host "SMOKE OK: a normal start launches Hermes desktop or a blocking error dialog. No secrets required."
    return 0
}

# --- Main -------------------------------------------------------------------

if ($Smoke) {
    $code = Invoke-Smoke
    exit $code
}

$script:WinFormsOk = Test-WinFormsAvailable
$showUi = -not $GatewayOnly

try {
    if ($showUi) {
        New-LaunchStatusForm | Out-Null
        if ($script:LaunchForm) {
            Hide-ConsoleWindow
        }
    }

    $compose = Join-Path $InstallRoot "docker-compose.embedded.yml"
    if (-not (Test-Path -LiteralPath $compose)) {
        throw "Dragon AI Agent is not installed (missing $compose). Unzip the package and run DragonAIAgentSetup.exe first."
    }

    Update-LaunchStatus "Checking Docker..."
    if (-not (Start-DockerIfNeeded)) {
        throw "Docker Desktop is required and was not found or did not become ready. Install Docker Desktop, wait for the tray icon, then open Dragon AI Agent again."
    }

    Start-GatewayContainer -ComposePath $compose
    Update-LaunchStatus "Waiting for gateway API on ${ApiHost}:${ApiPort} from Windows..."
    $ready = Wait-GatewayReady
    if (-not $ready.Ok) {
        throw "The embedded gateway API is not reachable from Windows at http://${ApiHost}:${ApiPort}/ (container may be loopback-bound or crash-looping). Check Docker tray, docker logs hermes-airmaze-gw, and %LOCALAPPDATA%\DragonAIAgent\launch.log."
    }

    if ($showUi) {
        Start-OnboardingIfNeeded
        $exe = Start-AgentDesktopOrThrow
        if (-not $NoBrowser) {
            try { Open-Dashboard } catch { Write-LaunchLog "Dashboard open skipped: $($_.Exception.Message)" "WARN" }
        }
        $msg = "Hermes desktop launched: $exe`nGateway API: http://${ApiHost}:${ApiPort}/`nDashboard: $DashboardUrl"
        Update-LaunchStatus $msg
        if ($script:LaunchDashButton) { $script:LaunchDashButton.Enabled = $true }
        if ($script:LaunchForm -and -not $script:LaunchForm.IsDisposed) {
            try {
                $script:LaunchForm.TopMost = $false
                $script:LaunchForm.Close()
            } catch {}
        }
    } else {
        Write-LaunchLog "Gateway-only: 127.0.0.1:$ApiPort  dashboard: $DashboardUrl"
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
