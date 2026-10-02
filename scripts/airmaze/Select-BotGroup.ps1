#requires -Version 5.1
<#
.SYNOPSIS
  Dragon AI Agent Teams popup — lists groups from this GitHub repo and launches checked teams.

.DESCRIPTION
  Front end of https://github.com/ShengLong76/airmaze-agent bot-groups/.
  Do not hard-code the list. Do not add a leftover sidebar bot. Do not restyle (crimson #C41E3A).
  Singular import/export stays off unless the user turns allowSingularBotImportExport on.
#>
[CmdletBinding()]
param(
    [string]$PayloadRoot = "",
    [string]$InstallRoot = "",
    [string]$BotGroupId = "",
    [string]$ProfileId = "",
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"
$ProductName = "Dragon AI Agent"

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}
if ([string]::IsNullOrWhiteSpace($BotGroupId) -and -not [string]::IsNullOrWhiteSpace($ProfileId)) {
    $BotGroupId = $ProfileId
}

function Write-Dragon([string]$Message) {
    Write-Host "[Dragon AI Agent] $Message"
}

function Resolve-Payload {
    param([string]$Hint)
    if ($Hint -and (Test-Path -LiteralPath $Hint)) {
        return (Resolve-Path -LiteralPath $Hint).Path
    }
    if ($PSScriptRoot) {
        foreach ($c in @(
            (Join-Path $PSScriptRoot "..\.."),
            (Join-Path $PSScriptRoot ".."),
            $PSScriptRoot
        )) {
            $cat = Join-Path $c "bot-groups\catalog.json"
            if (Test-Path -LiteralPath $cat) { return (Resolve-Path $c).Path }
        }
    }
    if (Test-Path (Join-Path $InstallRoot "bot-groups\catalog.json")) { return $InstallRoot }
    throw "Cannot find bot-groups/catalog.json. Pass -PayloadRoot."
}

function Get-Python {
    foreach ($name in @("python3", "python", "py")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    throw "Python is required to list bot groups from GitHub (bot_groups.py)."
}

function Get-Engine {
    $engine = Join-Path $PSScriptRoot "bot_groups.py"
    if (-not (Test-Path -LiteralPath $engine)) {
        $engine = Join-Path $InstallRoot "scripts\airmaze\bot_groups.py"
    }
    if (-not (Test-Path -LiteralPath $engine)) { throw "missing bot_groups.py" }
    return $engine
}

function Get-DesktopProfilesRoot {
    if ($env:LOCALAPPDATA) { return (Join-Path $env:LOCALAPPDATA "hermes\profiles") }
    return (Join-Path $InstallRoot "hermes-profiles")
}

function Invoke-BotGroups {
    param([string[]]$EngineArgs)
    $py = Get-Python
    $engine = Get-Engine
    $out = & $py $engine @EngineArgs 2>&1
    $code = $LASTEXITCODE
    $text = ($out | Out-String)
    if ($code -ne 0) { throw "bot_groups.py failed ($code): $text" }
    return $text
}

$root = Resolve-Payload -Hint $PayloadRoot
$desktopRoot = Get-DesktopProfilesRoot

function Get-ListedGroups {
    $raw = Invoke-BotGroups -EngineArgs @("list", "--payload", $root, "--install", $InstallRoot)
    return $raw | ConvertFrom-Json
}

function Deploy-ListedGroup {
    param([string]$Id)
    $raw = Invoke-BotGroups -EngineArgs @(
        "deploy", "--id", $Id,
        "--payload", $root,
        "--install", $InstallRoot,
        "--desktop", $desktopRoot
    )
    Write-Dragon "Deployed bot group: $Id"
    return $raw | ConvertFrom-Json
}

if (-not [string]::IsNullOrWhiteSpace($BotGroupId)) {
    Deploy-ListedGroup -Id $BotGroupId | Out-Null
    return
}

if ($NonInteractive) {
    $listed = Get-ListedGroups
    $pick = $listed.groups | Where-Object { $_.id -eq "personal-assistant" } | Select-Object -First 1
    if (-not $pick) { $pick = $listed.groups | Select-Object -First 1 }
    if (-not $pick) { throw "No bot groups listed (GitHub, cache, and bundle were empty)." }
    Deploy-ListedGroup -Id $pick.id | Out-Null
    return
}

function Initialize-BotGroupWinForms {
    if ($script:BotGroupFormsReady) { return $true }
    try {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        [System.Windows.Forms.Application]::EnableVisualStyles()
        $script:BrandBack = [System.Drawing.Color]::FromArgb(28, 28, 32)
        $script:BrandPanel = [System.Drawing.Color]::FromArgb(40, 40, 48)
        $script:BrandRed = [System.Drawing.Color]::FromArgb(196, 30, 58)
        $script:BrandText = [System.Drawing.Color]::FromArgb(240, 240, 245)
        $script:BrandMuted = [System.Drawing.Color]::FromArgb(160, 160, 170)
        $script:BotGroupFormsReady = $true
        return $true
    } catch {
        return $false
    }
}

function Show-TeamsPopup {
    $listed = Get-ListedGroups
    $groups = @($listed.groups | Where-Object { $_.id -ne "personal-assistant" })
    if ($groups.Count -eq 0) { throw "No bot teams listed." }
    $script:TeamsGroups = $groups

    $settingsRaw = Invoke-BotGroups -EngineArgs @("settings", "--install", $InstallRoot)
    $settings = $settingsRaw | ConvertFrom-Json
    $singularOn = [bool]$settings.allowSingularBotImportExport

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Dragon AI Agent — Teams Marketplace"
    $form.Size = New-Object System.Drawing.Size(720, 560)
    $form.MinimumSize = New-Object System.Drawing.Size(640, 480)
    $form.StartPosition = "CenterScreen"
    $form.BackColor = $script:BrandBack
    $form.ForeColor = $script:BrandText
    $form.FormBorderStyle = "Sizable"
    $form.MaximizeBox = $true

    $header = New-Object System.Windows.Forms.Panel
    $header.Size = New-Object System.Drawing.Size(720, 80)
    $header.Dock = "Top"
    $header.BackColor = $script:BrandRed
    $title = New-Object System.Windows.Forms.Label
    $title.Text = $ProductName
    $title.ForeColor = [System.Drawing.Color]::White
    $title.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
    $title.Location = New-Object System.Drawing.Point(20, 10)
    $title.AutoSize = $true
    $sub = New-Object System.Windows.Forms.Label
    $sub.Text = "Marketplace catalog. Check teams to Launch. Personal Assistant is already installed. Export strips secrets. Import stays on this popup."
    $sub.ForeColor = [System.Drawing.Color]::FromArgb(255, 220, 220)
    $sub.Location = New-Object System.Drawing.Point(20, 40)
    $sub.Size = New-Object System.Drawing.Size(670, 32)
    $header.Controls.Add($title)
    $header.Controls.Add($sub)
    $form.Controls.Add($header)

    $lbl = New-Object System.Windows.Forms.Label
    $lbl.Text = "Teams Marketplace"
    $lbl.ForeColor = $script:BrandMuted
    $lbl.Location = New-Object System.Drawing.Point(24, 96)
    $lbl.AutoSize = $true
    $form.Controls.Add($lbl)

    $list = New-Object System.Windows.Forms.CheckedListBox
    $list.CheckOnClick = $true
    $list.Location = New-Object System.Drawing.Point(24, 120)
    $list.Size = New-Object System.Drawing.Size(656, 220)
    $list.Anchor = "Top,Left,Right,Bottom"
    $list.BackColor = [System.Drawing.Color]::FromArgb(50, 50, 58)
    $list.ForeColor = $script:BrandText
    $list.BorderStyle = "FixedSingle"
    foreach ($g in $groups) {
        $label = if ($g.displayName) { [string]$g.displayName } else { [string]$g.name }
        $blurb = if ($g.blurb) { [string]$g.blurb } else { [string]$g.departmentJob }
        $bits = @()
        if ($g.seats) { $bits += ("{0} seats" -f $g.seats) }
        if ($g.author) { $bits += [string]$g.author }
        $suffix = if ($bits.Count) { " ({0})" -f ($bits -join " · ") } else { "" }
        [void]$list.Items.Add(("{0} — {1}{2}" -f $label, $blurb, $suffix))
    }
    $form.Controls.Add($list)
    $script:TeamsList = $list

    $status = New-Object System.Windows.Forms.Label
    $src = [string]$listed.source
    if ($src -eq "github") {
        $status.Text = "Listed from github.com/ShengLong76/airmaze-agent (bot-groups/)"
    } elseif ($src -eq "cache") {
        $status.Text = "GitHub unreachable — using cached catalog"
    } else {
        $status.Text = "GitHub unreachable — using bundled catalog"
    }
    $status.ForeColor = $script:BrandMuted
    $status.Location = New-Object System.Drawing.Point(24, 350)
    $status.Size = New-Object System.Drawing.Size(656, 36)
    $status.Anchor = "Left,Right,Bottom"
    $form.Controls.Add($status)
    $script:TeamsStatus = $status

    $chk = New-Object System.Windows.Forms.CheckBox
    $chk.Text = "Allow import or export of one bot"
    $chk.Checked = $singularOn
    $chk.ForeColor = $script:BrandText
    $chk.Location = New-Object System.Drawing.Point(24, 392)
    $chk.AutoSize = $true
    $chk.Anchor = "Left,Bottom"
    $chk.Add_CheckedChanged({
        $flag = if ($chk.Checked) { "on" } else { "off" }
        Invoke-BotGroups -EngineArgs @("settings", "--install", $InstallRoot, "--set-singular", $flag) | Out-Null
    })
    $form.Controls.Add($chk)

    $note = New-Object System.Windows.Forms.Label
    $note.Text = "Off by default. Not a create-a-bot path. Group launch and group export stay available."
    $note.ForeColor = $script:BrandMuted
    $note.Location = New-Object System.Drawing.Point(44, 416)
    $note.Size = New-Object System.Drawing.Size(636, 28)
    $note.Anchor = "Left,Right,Bottom"
    $form.Controls.Add($note)

    $btnLaunch = New-Object System.Windows.Forms.Button
    $btnLaunch.Text = "Launch"
    $btnLaunch.Location = New-Object System.Drawing.Point(24, 456)
    $btnLaunch.Size = New-Object System.Drawing.Size(120, 36)
    $btnLaunch.Anchor = "Left,Bottom"
    $btnLaunch.BackColor = $script:BrandRed
    $btnLaunch.ForeColor = [System.Drawing.Color]::White
    $btnLaunch.FlatStyle = "Flat"
    $btnLaunch.Add_Click({
        $picked = @($script:TeamsList.CheckedIndices)
        if ($picked.Count -lt 1) {
            $script:TeamsStatus.Text = "Check one or more teams to launch."
            return
        }
        try {
            $names = @()
            foreach ($idx in $picked) {
                $g = $script:TeamsGroups[$idx]
                Deploy-ListedGroup -Id $g.id | Out-Null
                $names += $(if ($g.displayName) { $g.displayName } else { $g.name })
            }
            $script:TeamsStatus.Text = "Launched $($names -join ', '). Each team files under its own name."
            [System.Windows.Forms.MessageBox]::Show("Launched $($names -join ', ').", $ProductName) | Out-Null
        } catch {
            [System.Windows.Forms.MessageBox]::Show("$_", $ProductName) | Out-Null
        }
    })
    $form.Controls.Add($btnLaunch)

    $btnExport = New-Object System.Windows.Forms.Button
    $btnExport.Text = "Export"
    $btnExport.Location = New-Object System.Drawing.Point(156, 456)
    $btnExport.Size = New-Object System.Drawing.Size(120, 36)
    $btnExport.Anchor = "Left,Bottom"
    $btnExport.BackColor = $script:BrandPanel
    $btnExport.ForeColor = $script:BrandText
    $btnExport.FlatStyle = "Flat"
    $btnExport.Add_Click({
        $picked = @($script:TeamsList.CheckedIndices)
        if ($picked.Count -lt 1) {
            $script:TeamsStatus.Text = "Check one or more teams to export."
            return
        }
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = "Export team group folder (same format as the GitHub repo)"
        if ($dialog.ShowDialog() -eq "OK") {
            foreach ($idx in $picked) {
                $id = $script:TeamsGroups[$idx].id
                $out = Join-Path $dialog.SelectedPath $id
                Invoke-BotGroups -EngineArgs @(
                    "export", "--id", $id, "--out", $out,
                    "--install", $InstallRoot, "--payload", $root
                ) | Out-Null
            }
            $script:TeamsStatus.Text = "Exported checked teams (re-importable group files)."
        }
    })
    $form.Controls.Add($btnExport)

    $btnImport = New-Object System.Windows.Forms.Button
    $btnImport.Text = "Import file"
    $btnImport.Location = New-Object System.Drawing.Point(288, 456)
    $btnImport.Size = New-Object System.Drawing.Size(120, 36)
    $btnImport.Anchor = "Left,Bottom"
    $btnImport.BackColor = $script:BrandPanel
    $btnImport.ForeColor = $script:BrandText
    $btnImport.FlatStyle = "Flat"
    $btnImport.Add_Click({
        $ofd = New-Object System.Windows.Forms.OpenFileDialog
        $ofd.Filter = "Bot group (*.json;*.zip)|*.json;*.zip|All files (*.*)|*.*"
        if ($ofd.ShowDialog() -eq "OK") {
            try {
                Invoke-BotGroups -EngineArgs @(
                    "import", "--source", $ofd.FileName,
                    "--install", $InstallRoot, "--desktop", $desktopRoot, "--payload", $root
                ) | Out-Null
                $script:TeamsStatus.Text = "Imported $($ofd.FileName)"
            } catch {
                [System.Windows.Forms.MessageBox]::Show("$_", $ProductName) | Out-Null
            }
        }
    })
    $form.Controls.Add($btnImport)

    $btnClose = New-Object System.Windows.Forms.Button
    $btnClose.Text = "Close"
    $btnClose.Location = New-Object System.Drawing.Point(560, 456)
    $btnClose.Size = New-Object System.Drawing.Size(120, 36)
    $btnClose.Anchor = "Right,Bottom"
    $btnClose.BackColor = $script:BrandPanel
    $btnClose.ForeColor = $script:BrandText
    $btnClose.FlatStyle = "Flat"
    $btnClose.Add_Click({ $form.Close() })
    $form.Controls.Add($btnClose)

    [void]$form.ShowDialog()
}

if (Initialize-BotGroupWinForms) {
    Show-TeamsPopup
} else {
    $listed = Get-ListedGroups
    Write-Host ""
    Write-Host "========================================"
    Write-Host " Dragon AI Agent — Teams Marketplace"
    Write-Host "========================================"
    $entries = @($listed.groups | Where-Object { $_.id -ne "personal-assistant" })
    $i = 1
    foreach ($e in $entries) {
        Write-Host ("  [{0}] {1}" -f $i, $e.name)
        Write-Host ("      {0}" -f $e.departmentJob)
        $i++
    }
    Write-Host "  [Enter] cancel — Personal Assistant is already installed"
    Write-Host ""
    $ans = Read-Host "Selection"
    if ([string]::IsNullOrWhiteSpace($ans)) {
        Write-Dragon "No team selected. Personal Assistant stays."
        return
    } elseif ($ans -match '^\d+$') {
        $n = [int]$ans
        if ($n -ge 1 -and $n -le $entries.Count) { $chosen = $entries[$n - 1] }
        else { throw "Invalid selection: $ans" }
    } else {
        $chosen = $entries | Where-Object { $_.id -eq $ans } | Select-Object -First 1
        if (-not $chosen) { throw "Unknown selection: $ans" }
    }
    Deploy-ListedGroup -Id $chosen.id | Out-Null
}
