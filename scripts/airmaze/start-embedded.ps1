#requires -Version 5.1
<#
.SYNOPSIS
  Start Dragon AI Agent: embedded gateway plus a visible main UI (or an error dialog).

.DESCRIPTION
  This is the Desktop / Start Menu "Dragon AI Agent" entrypoint.
  It checks whether Docker is running and starts Docker Desktop in the
  system tray when it is not (no Containers dashboard). Then it brings the
  gateway up, waits until the API is reachable on the Windows host, then
  launches the Dragon AI Agent desktop (on-disk Hermes.exe). Failures
  (engine still down after a wait, compose errors, missing client) show a
  MessageBox / popup and exit non-zero. -StartDocker is kept as an alias.

  The installed Desktop / Start Menu shortcut runs Start-DragonAI.vbs (wscript)
  so no PowerShell console flashes. Use this .ps1 directly for debugging
  (-DebugConsole keeps the console). Use -GatewayOnly for CLI-only compose.
  Use -OpenDashboard to open :9119 (never opened on a normal start).
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
# Desktop Remote token/WS — NOT the OpenAI API on 8642 (that surface has no /api/ws).
$DesktopServeUrl = "http://127.0.0.1:8650"
$DesktopServePort = 8650
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
$script:ApiKey = "dragon-local"
$script:DesktopServeUrl = $DesktopServeUrl
$script:DesktopSessionToken = $DesktopSessionToken

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
    # Installed shortcut is windowless — never block on a hidden console.
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
        $header.BackColor = [System.Drawing.Color]::FromArgb(196, 30, 58)
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

function Repair-DragonAIProductShortcuts {
    <#
      Rewrite Desktop / Start Menu "Dragon AI Agent" to wscript + VBS if an older
      install still points at powershell.exe (that shortcut flashes a console).
    #>
    $vbs = Join-Path $InstallRoot "scripts\airmaze\Start-DragonAI.vbs"
    if (-not (Test-Path -LiteralPath $vbs)) {
        $vbs = Join-Path $PSScriptRoot "Start-DragonAI.vbs"
    }
    if (-not (Test-Path -LiteralPath $vbs)) { return }
    $wscript = Join-Path $env:SystemRoot "System32\wscript.exe"
    if (-not (Test-Path -LiteralPath $wscript)) { return }
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
            $existing = $null
            if (Test-Path -LiteralPath $p) {
                $existing = $wsh.CreateShortcut($p)
                if ($existing.TargetPath -like "*wscript.exe" -and $existing.Arguments -like "*Start-DragonAI.vbs*") {
                    continue
                }
            }
            $dir = Split-Path -Parent $p
            if ($dir -and -not (Test-Path -LiteralPath $dir)) {
                New-Item -ItemType Directory -Force -Path $dir | Out-Null
            }
            $sc = $wsh.CreateShortcut($p)
            $sc.TargetPath = $wscript
            $sc.Arguments = $startArgs
            $sc.WorkingDirectory = $InstallRoot
            $sc.Description = "Dragon AI Agent — start the gateway and open the app"
            $sc.WindowStyle = 1
            if (Test-Path -LiteralPath $ico) { $sc.IconLocation = "$ico,0" }
            $sc.Save()
            Write-LaunchLog "Repaired product shortcut: $p"
        }
    } catch {
        Write-LaunchLog "Shortcut repair skipped: $($_.Exception.Message)" "WARN"
    }
}

function Invoke-NativeDocker {
    <#
      UltraDragon: Docker CLI writes progress ("Container … Running") to stderr.
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

function Set-DockerTrayOnlySettings {
    $dir = Join-Path $env:APPDATA "Docker"
    try {
        if (-not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
    } catch {
        Write-LaunchLog "Could not create Docker settings dir: $($_.Exception.Message)" "WARN"
        return
    }
    $patch = @{
        openUIOnStartupDisabled = $true
        OpenUIOnStartupDisabled = $true
        startMinimized          = $true
        minimizeToTray          = $true
        displayedOnboarding     = $true
    }
    foreach ($name in @("settings.json", "settings-store.json")) {
        $file = Join-Path $dir $name
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
            Write-LaunchLog "Patched Docker tray-only settings: $file"
        } catch {
            Write-LaunchLog "Could not patch $file : $($_.Exception.Message)" "WARN"
        }
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
    Set-DockerTrayOnlySettings
    Update-LaunchStatus "Starting Docker Desktop (system tray). This can take a minute..."
    try {
        Start-Process -FilePath $exe -WindowStyle Hidden -ErrorAction Stop
    } catch {
        try {
            Start-Process -FilePath $exe -WindowStyle Minimized -ErrorAction Stop
        } catch {
            Start-Process -FilePath $exe -ErrorAction SilentlyContinue
        }
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
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $r = Invoke-NativeDocker -DockerArgs (@("compose", "-f", "docker-compose.embedded.yml") + $ComposeArgs)
        if ($r.Output) { Write-LaunchLog ($r.Output.Trim()) }
        if ($r.ExitCode -ne 0) {
            throw "docker compose $($ComposeArgs -join ' ') failed (exit $($r.ExitCode)). $($r.Output)"
        }
        if (Test-DockerCliFailureText $r.Output) {
            throw "Docker engine is not running (compose printed a connect/pipe error but did not fail closed). Start Docker Desktop from the tray and try again. $($r.Output)"
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
            & $applyModels -Home $data -IfMissing | Out-Null
            Write-LaunchLog "Applied default chat/image LLMs if gateway config was missing them"
        } catch {
            Write-LaunchLog "Gateway model defaults skipped: $($_.Exception.Message)" "WARN"
        }
    }

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
        & $setter -Url $script:DesktopServeUrl -Token $script:DesktopSessionToken
        Write-LaunchLog "Desktop Remote Embedded Linux wired to $($script:DesktopServeUrl) (session token placeholder, not echoed)"
        return $true
    } catch {
        Write-LaunchLog "Desktop Remote wire skipped: $($_.Exception.Message)" "WARN"
        return $false
    }
}

function Wait-GatewayReady {
    param([int]$TimeoutSec = 90, [switch]$RequireDesktopServe)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $last = @{ Ok = $false; Dashboard = $false; Api = $false; DesktopServe = $false }
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
        $last = @{
            Ok            = ($apiTcp -and $apiHttp)
            Dashboard     = $dash
            Api           = ($apiTcp -and $apiHttp)
            DesktopServe  = ($desktopTcp -and $desktopHttp)
        }
        # Host TCP/HTTP on 8642 is required. 9119 alone is not enough (docker-proxy
        # can listen while the dashboard process crash-loops). Bot Screen also
        # needs the Desktop serve proxy on 8650 (/api/health + /api/ws).
        if ($last.Ok -and ((-not $RequireDesktopServe) -or $last.DesktopServe)) {
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
    if (-not (Get-Command Find-HermesDesktopExe -ErrorAction SilentlyContinue)) {
        throw "Find-HermesDesktop.ps1 was not loaded. Re-run DragonAIAgentSetup so scripts\airmaze\Find-HermesDesktop.ps1 is installed."
    }
    $exe = Find-HermesDesktopExe -InstallRoot $InstallRoot
    if (-not $exe) {
        $hint = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe"
        throw @"
Dragon AI Agent desktop was not found, so there is no app window to show.

Expected on-disk client (internal filename Hermes.exe):
  $hint

Install the desktop client, then open Dragon AI Agent again.
A branded shortcut is written to %LOCALAPPDATA%\DragonAIAgent\Dragon AI Agent Client.lnk once it is found.
"@
    }
    Write-LaunchLog "Launching Dragon AI Agent desktop: $exe"
    Save-DragonAIDesktopPointer -ExePath $exe -InstallRoot $InstallRoot | Out-Null
    # Belt-and-suspenders: some Desktop builds honor these on first boot.
    $env:HERMES_DESKTOP_REMOTE_URL = $script:DesktopServeUrl
    $env:HERMES_DESKTOP_REMOTE_TOKEN = $script:DesktopSessionToken
    # Start-HermesDesktopClient runs Apply-DragonAIDesktopUiBranding on unpacked
    # renderer files (empty state / composer / settings) before Hermes.exe opens.
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

function Start-OnboardingIfNeeded {
    if ($NoWizard) { return }
    if (-not (Test-OnboardingNeedsUi)) { return }
    $wiz = Join-Path $InstallRoot "scripts\airmaze\Onboard-Wizard.ps1"
    if (-not (Test-Path -LiteralPath $wiz)) { return }
    Update-LaunchStatus "Opening first-run setup wizard..."
    Start-HiddenPowerShell -ArgumentList @(
        "-STA", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
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
        desktopServe  = "${ApiHost}:${DesktopServePort}"
        log           = $script:LaunchLog
        ui            = @(
            "windowless host: Start-DragonAI.vbs / wscript.exe (no console)",
            "blocking error dialog on failure (never a raw console)",
            "require desktop client (win-unpacked Hermes.exe on disk)",
            "overlay unpacked Electron UI chrome to Dragon AI Agent before launch",
            "launch Dragon AI Agent desktop only (not $DashboardUrl)",
            "start Docker Desktop in the tray when docker info fails (already running is a no-op)",
            "first-run Onboard-Wizard if welcome is still pending",
            "docker CLI stderr progress is not a terminating error",
            "Desktop Remote → $($script:DesktopServeUrl) (token mode; not :8642)",
            "wait for /api/health on the Desktop serve proxy with X-Hermes-Session-Token"
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
        "openUIOnStartupDisabled",
        "DebugConsole",
        "New-LaunchStatusForm",
        "Invoke-NativeDocker",
        "Repair-DragonAIProductShortcuts",
        "CreateNoWindow",
        "hermes-airmaze-gw is not running",
        "Set-EmbeddedDesktopRemoteConnection",
        "X-Hermes-Session-Token",
        "8650",
        "Apply-DragonAIDesktopUiBranding",
        "Exclude-DragonAIHermesBots",
        "teams_picker",
        "8653"
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
        New-LaunchStatusForm | Out-Null
        if ($script:Windowless) { Hide-ConsoleWindow }
    }

    $compose = Join-Path $InstallRoot "docker-compose.embedded.yml"
    if (-not (Test-Path -LiteralPath $compose)) {
        throw "Dragon AI Agent is not installed (missing $compose). Unzip the package and run DragonAIAgentSetup.exe first."
    }

    Update-LaunchStatus "Checking Docker..."
    Fix-DockerPath
    if ($StartDocker) {
        Write-LaunchLog "StartDocker is the default launch path; starting Docker in the tray if needed"
    }
    if (-not (Start-DockerIfNeeded)) {
        throw "Docker Desktop did not become ready. Start it from the system tray, wait until it is ready, then open Dragon AI Agent again."
    }

    Start-GatewayContainer -ComposePath $compose
    Exclude-DragonAIHermesBots
    Start-DragonAITeamsPicker
    try { Sync-EmbeddedGatewayProfiles | Out-Null } catch {
        Write-LaunchLog "Profile sync skipped: $($_.Exception.Message)" "WARN"
    }
    Update-LaunchStatus "Waiting for gateway API on ${ApiHost}:${ApiPort} and Desktop serve on ${ApiHost}:${DesktopServePort}..."
    $ready = Wait-GatewayReady -TimeoutSec 120 -RequireDesktopServe
    if (-not $ready.Ok) {
        throw "The embedded gateway API is not reachable from Windows at http://${ApiHost}:${ApiPort}/ (container may be loopback-bound or crash-looping). Check Docker tray, docker logs hermes-airmaze-gw, and %LOCALAPPDATA%\DragonAIAgent\launch.log."
    }
    if (-not $ready.DesktopServe) {
        throw "The Desktop Bot Screen backend is not reachable at $($script:DesktopServeUrl)/api/health (expected X-Hermes-Session-Token + /api/ws). Check: docker logs hermes-airmaze-desktop && docker logs hermes-airmaze-desktop-proxy. Do not point Remote at :8642 (OpenAI API only)."
    }
    Set-EmbeddedDesktopRemoteConnection | Out-Null

    if ($showUi) {
        Start-OnboardingIfNeeded
        $exe = Start-AgentDesktopOrThrow
        if ($OpenDashboard) {
            try { Open-Dashboard } catch { Write-LaunchLog "Dashboard open skipped: $($_.Exception.Message)" "WARN" }
        }
        $msg = "Dragon AI Agent launched.`nDesktop Screen: $($script:DesktopServeUrl)`nGateway API: http://${ApiHost}:${ApiPort}/"
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
