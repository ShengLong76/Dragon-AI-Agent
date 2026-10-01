#requires -Version 5.1
<#
.SYNOPSIS
  Dragon AI Agent bot group dropdown — lists groups from this GitHub repo and deploys one.

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

function Show-BotGroupDropdown {
    $listed = Get-ListedGroups
    $groups = @($listed.groups)
    if ($groups.Count -eq 0) { throw "No bot groups listed." }

    $settingsRaw = Invoke-BotGroups -EngineArgs @("settings", "--install", $InstallRoot)
    $settings = $settingsRaw | ConvertFrom-Json
    $singularOn = [bool]$settings.allowSingularBotImportExport

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Dragon AI Agent — Teams"
    $form.Size = New-Object System.Drawing.Size(640, 420)
    $form.StartPosition = "CenterScreen"
    $form.BackColor = $script:BrandBack
    $form.ForeColor = $script:BrandText
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false

    $header = New-Object System.Windows.Forms.Panel
    $header.Size = New-Object System.Drawing.Size(640, 72)
    $header.Location = New-Object System.Drawing.Point(0, 0)
    $header.BackColor = $script:BrandRed
    $title = New-Object System.Windows.Forms.Label
    $title.Text = $ProductName
    $title.ForeColor = [System.Drawing.Color]::White
    $title.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
    $title.Location = New-Object System.Drawing.Point(20, 10)
    $title.AutoSize = $true
    $sub = New-Object System.Windows.Forms.Label
    $sub.Text = "Pick a team (Personal Assistant, Real Estate Lead Gen, Marketing Team, Trading Team). Import file still works."
    $sub.ForeColor = [System.Drawing.Color]::FromArgb(255, 220, 220)
    $sub.Location = New-Object System.Drawing.Point(20, 40)
    $sub.AutoSize = $true
    $header.Controls.Add($title)
    $header.Controls.Add($sub)
    $form.Controls.Add($header)

    $lbl = New-Object System.Windows.Forms.Label
    $lbl.Text = "Team"
    $lbl.ForeColor = $script:BrandMuted
    $lbl.Location = New-Object System.Drawing.Point(24, 92)
    $lbl.AutoSize = $true
    $form.Controls.Add($lbl)

    $combo = New-Object System.Windows.Forms.ComboBox
    $combo.DropDownStyle = "DropDownList"
    $combo.Location = New-Object System.Drawing.Point(24, 116)
    $combo.Size = New-Object System.Drawing.Size(580, 28)
    $combo.BackColor = [System.Drawing.Color]::FromArgb(50, 50, 58)
    $combo.ForeColor = $script:BrandText
    foreach ($g in $groups) {
        [void]$combo.Items.Add(("{0} — {1}" -f $g.name, $g.departmentJob))
    }
    if ($combo.Items.Count -gt 0) { $combo.SelectedIndex = 0 }
    $form.Controls.Add($combo)

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
    $status.Location = New-Object System.Drawing.Point(24, 156)
    $status.Size = New-Object System.Drawing.Size(580, 36)
    $form.Controls.Add($status)

    $chk = New-Object System.Windows.Forms.CheckBox
    $chk.Text = "Allow import or export of one bot"
    $chk.Checked = $singularOn
    $chk.ForeColor = $script:BrandText
    $chk.Location = New-Object System.Drawing.Point(24, 200)
    $chk.AutoSize = $true
    $chk.Add_CheckedChanged({
        $flag = if ($chk.Checked) { "on" } else { "off" }
        Invoke-BotGroups -EngineArgs @("settings", "--install", $InstallRoot, "--set-singular", $flag) | Out-Null
    })
    $form.Controls.Add($chk)

    $note = New-Object System.Windows.Forms.Label
    $note.Text = "Off by default. Not a create-a-bot path. Group deploy and group export stay available."
    $note.ForeColor = $script:BrandMuted
    $note.Location = New-Object System.Drawing.Point(44, 228)
    $note.Size = New-Object System.Drawing.Size(560, 36)
    $form.Controls.Add($note)

    $btnDeploy = New-Object System.Windows.Forms.Button
    $btnDeploy.Text = "Deploy"
    $btnDeploy.Location = New-Object System.Drawing.Point(24, 280)
    $btnDeploy.Size = New-Object System.Drawing.Size(120, 36)
    $btnDeploy.BackColor = $script:BrandRed
    $btnDeploy.ForeColor = [System.Drawing.Color]::White
    $btnDeploy.FlatStyle = "Flat"
    $btnDeploy.Add_Click({
        if ($combo.SelectedIndex -lt 0) { return }
        $id = $groups[$combo.SelectedIndex].id
        try {
            Deploy-ListedGroup -Id $id | Out-Null
            $status.Text = "Deployed $($groups[$combo.SelectedIndex].name). No manual file handling."
            [System.Windows.Forms.MessageBox]::Show("Deployed $($groups[$combo.SelectedIndex].name).", $ProductName) | Out-Null
        } catch {
            [System.Windows.Forms.MessageBox]::Show("$_", $ProductName) | Out-Null
        }
    })
    $form.Controls.Add($btnDeploy)

    $btnExport = New-Object System.Windows.Forms.Button
    $btnExport.Text = "Export"
    $btnExport.Location = New-Object System.Drawing.Point(156, 280)
    $btnExport.Size = New-Object System.Drawing.Size(120, 36)
    $btnExport.BackColor = $script:BrandPanel
    $btnExport.ForeColor = $script:BrandText
    $btnExport.FlatStyle = "Flat"
    $btnExport.Add_Click({
        if ($combo.SelectedIndex -lt 0) { return }
        $id = $groups[$combo.SelectedIndex].id
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = "Export bot group folder (same format as the GitHub repo)"
        if ($dialog.ShowDialog() -eq "OK") {
            $out = Join-Path $dialog.SelectedPath $id
            Invoke-BotGroups -EngineArgs @(
                "export", "--id", $id, "--out", $out,
                "--install", $InstallRoot, "--payload", $root
            ) | Out-Null
            $status.Text = "Exported $id (re-importable group file)."
        }
    })
    $form.Controls.Add($btnExport)

    $btnImport = New-Object System.Windows.Forms.Button
    $btnImport.Text = "Import file"
    $btnImport.Location = New-Object System.Drawing.Point(288, 280)
    $btnImport.Size = New-Object System.Drawing.Size(120, 36)
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
                $status.Text = "Imported $($ofd.FileName)"
            } catch {
                [System.Windows.Forms.MessageBox]::Show("$_", $ProductName) | Out-Null
            }
        }
    })
    $form.Controls.Add($btnImport)

    $btnClose = New-Object System.Windows.Forms.Button
    $btnClose.Text = "Close"
    $btnClose.Location = New-Object System.Drawing.Point(484, 280)
    $btnClose.Size = New-Object System.Drawing.Size(120, 36)
    $btnClose.BackColor = $script:BrandPanel
    $btnClose.ForeColor = $script:BrandText
    $btnClose.FlatStyle = "Flat"
    $btnClose.Add_Click({ $form.Close() })
    $form.Controls.Add($btnClose)

    [void]$form.ShowDialog()
}

if (Initialize-BotGroupWinForms) {
    Show-BotGroupDropdown
} else {
    $listed = Get-ListedGroups
    Write-Host ""
    Write-Host "========================================"
    Write-Host " Dragon AI Agent — choose a bot group"
    Write-Host "========================================"
    $i = 1
    foreach ($e in @($listed.groups)) {
        Write-Host ("  [{0}] {1}" -f $i, $e.name)
        Write-Host ("      {0}" -f $e.departmentJob)
        $i++
    }
    Write-Host "  [Enter] default = first listed group (Personal Assistant when present)"
    Write-Host ""
    $ans = Read-Host "Selection"
    $entries = @($listed.groups)
    if ([string]::IsNullOrWhiteSpace($ans)) {
        $chosen = $entries | Where-Object { $_.id -eq "personal-assistant" } | Select-Object -First 1
        if (-not $chosen) { $chosen = $entries[0] }
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
