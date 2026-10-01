#requires -Version 5.1
<#
.SYNOPSIS
  Overlay Dragon AI Agent product chrome onto the on-disk Hermes Electron UI.

.DESCRIPTION
  This packaging repo launches upstream Hermes.exe and does not rebuild it.
  electron-builder unpacks dist/** to resources/app.asar.unpacked (asar
  integrity stays intact). This script rewrites user-visible product strings
  there: empty-state wordmark, composer placeholder, settings product name.

  Safe to run on every launch (idempotent). Does not touch Docker tags,
  tokens, ports, process names, or Bot Screen wiring.
#>
[CmdletBinding()]
param(
    [string]$ExePath = "",
    [string]$Root = "",
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

function Get-DragonAIDesktopBrandingTablePath {
    $here = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($here)) {
        $here = Split-Path -Parent $MyInvocation.MyCommand.Path
    }
    return (Join-Path $here "desktop_branding.json")
}

function Get-DragonAIDesktopBrandingTable {
    $path = Get-DragonAIDesktopBrandingTablePath
    if (-not (Test-Path -LiteralPath $path)) {
        throw "desktop_branding.json is missing next to Apply-DesktopBranding.ps1"
    }
    return (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Get-DragonAIDesktopBrandingRoots {
    param([Parameter(Mandatory = $true)][string]$ExePath)
    $exeDir = Split-Path -Parent $ExePath
    $roots = New-Object System.Collections.Generic.List[string]
    foreach ($rel in @("resources\app.asar.unpacked", "resources\app")) {
        $candidate = Join-Path $exeDir $rel
        if (Test-Path -LiteralPath $candidate) { $roots.Add($candidate) }
    }
    $desktopRoot = Split-Path -Parent (Split-Path -Parent $exeDir)
    $intro = Join-Path $desktopRoot "src\components\chat\intro.tsx"
    if (Test-Path -LiteralPath $intro) { $roots.Add((Join-Path $desktopRoot "src")) }
    $dist = Join-Path $desktopRoot "dist"
    if (Test-Path -LiteralPath $dist) { $roots.Add($dist) }
    return @($roots)
}

function Get-DragonAIDesktopFontPack {
    $here = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($here)) {
        $here = Split-Path -Parent $MyInvocation.MyCommand.Path
    }
    $candidates = @(
        (Join-Path (Split-Path -Parent (Split-Path -Parent $here)) "branding\fonts\syne"),
        (Join-Path (Split-Path -Parent (Split-Path -Parent $here)) "branding\fonts\league-spartan"),
        (Join-Path (Split-Path -Parent (Split-Path -Parent $here)) "branding\fonts\outfit"),
        (Join-Path $here "fonts\syne"),
        (Join-Path $here "fonts\league-spartan"),
        (Join-Path $here "fonts\outfit")
    )
    foreach ($c in $candidates) {
        if ((Test-Path -LiteralPath (Join-Path $c "dragon-ui.css")) -and (Get-ChildItem -LiteralPath $c -Filter "*.woff2" -File -ErrorAction SilentlyContinue)) {
            return $c
        }
    }
    throw "Apply-DesktopBranding: dragon-ui.css pack missing under branding/fonts/syne (Python is not required; PowerShell copies the prebuilt pack)"
}

function Get-DragonAIInstallUnpackedRoots {
    $hits = New-Object System.Collections.Generic.List[string]
    if (-not $env:LOCALAPPDATA) { return @() }
    $seed = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
    if (-not (Test-Path -LiteralPath $seed -PathType Container)) { return @() }
    Get-ChildItem -LiteralPath $seed -Recurse -Directory -Filter "app.asar.unpacked" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '\\node_modules\\' } |
        ForEach-Object { $hits.Add($_.FullName) }
    return @($hits)
}

function Get-DragonAIPackScript {
    param([Parameter(Mandatory = $true)][string]$Name)
    $pack = Get-DragonAIDesktopFontPack
    $path = Join-Path $pack $Name
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Apply-DesktopBranding: missing prebuilt inject script $Name in $pack"
    }
    return [System.IO.File]::ReadAllText($path).Trim()
}

function Remove-DragonAICrimsonLockupBorder {
    param([string]$Text)
    $re = New-Object System.Text.RegularExpressions.Regex 'border\s*:\s*1px\s+solid\s+rgba\(\s*196\s*,\s*30\s*,\s*58\s*,\s*[^)]+\)', 'IgnoreCase'
    return $re.Replace($Text, 'border:0')
}

function Add-DragonAIBeforeClose {
    param([string]$Html, [string]$Snippet)
    $lower = $Html.ToLowerInvariant()
    $idx = $lower.IndexOf("</head>")
    if ($idx -ge 0) {
        return @{ text = ($Html.Substring(0, $idx) + $Snippet + "`n" + $Html.Substring($idx)); changed = $true }
    }
    $idx = $lower.IndexOf("</body>")
    if ($idx -ge 0) {
        return @{ text = ($Html.Substring(0, $idx) + $Snippet + "`n" + $Html.Substring($idx)); changed = $true }
    }
    return @{ text = ($Html.TrimEnd() + "`n" + $Snippet + "`n"); changed = $true }
}

function Update-DragonAIMarkedSnippet {
    param([string]$Html, [string]$Mark, [string]$Snippet)
    $start = $Html.IndexOf("<script $Mark>")
    if ($start -lt 0) {
        $markAt = $Html.ToLowerInvariant().IndexOf($Mark.ToLowerInvariant())
        if ($markAt -lt 0) {
            return (Add-DragonAIBeforeClose -Html $Html -Snippet $Snippet)
        }
        $start = $Html.LastIndexOf("<script", $markAt)
        if ($start -lt 0) {
            return (Add-DragonAIBeforeClose -Html $Html -Snippet $Snippet)
        }
    }
    $end = $Html.IndexOf("</script>", $start)
    if ($end -lt 0) {
        return (Add-DragonAIBeforeClose -Html $Html -Snippet $Snippet)
    }
    $end += "</script>".Length
    $current = $Html.Substring($start, $end - $start)
    if ($current -eq $Snippet) {
        return @{ text = $Html; changed = $false }
    }
    return @{ text = ($Html.Substring(0, $start) + $Snippet + $Html.Substring($end)); changed = $true }
}

function Install-DragonAIDesktopFontPack {
    param([string[]]$Roots)
    $pack = Get-DragonAIDesktopFontPack
    $htmlPatched = 0
    $targets = 0
    $copiedCss = 0
    $link = '<link rel="stylesheet" href="./dragon-ai-branding/dragon-ui.css" data-dragon-ai-branding="ui-face" />'
    $sidebarMark = 'data-dragon-ai-branding="sidebar-header"'
    $teamsMark = 'data-dragon-ai-branding="teams-picker"'
    $sidebarSnippet = "<script $sidebarMark>`n" + (Get-DragonAIPackScript -Name "sidebar-header.js") + "`n</script>"
    $teamsSnippet = "<script $teamsMark>`n" + (Get-DragonAIPackScript -Name "teams-picker.js") + "`n</script>"
    if ($sidebarSnippet -notmatch 'data-dragon-ai-sidebar-fixed' -or $sidebarSnippet -notmatch 'findDragonSidebarHost' -or $sidebarSnippet -notmatch 'findColumnHost') {
        throw "Apply-DesktopBranding: sidebar-header.js is missing the body fixed-overlay fallback host"
    }
    if ($sidebarSnippet -notmatch 'findInFlowColumn' -or $sidebarSnippet -notmatch 'data-dragon-ai-sidebar-chrome') {
        throw "Apply-DesktopBranding: sidebar-header.js must prefer in-flow chrome above Sessions/Bots"
    }
    if ($sidebarSnippet -notmatch 'findBotsTab' -or $sidebarSnippet -notmatch 'data-dragon-ai-sidebar-clearance') {
        throw "Apply-DesktopBranding: sidebar-header.js must reserve clearance so the overlay does not cover BOTS"
    }
    if ($teamsSnippet -notmatch 'data-dragon-ai-sidebar-fixed' -or $teamsSnippet -notmatch 'findDragonSidebarHost' -or $teamsSnippet -notmatch 'Teams Marketplace') {
        throw "Apply-DesktopBranding: teams-picker.js is missing the fixed-overlay host or Teams Marketplace label"
    }
    if ($teamsSnippet -notmatch 'findInFlowColumn' -or $teamsSnippet -notmatch 'data-dragon-ai-sidebar-chrome') {
        throw "Apply-DesktopBranding: teams-picker.js must prefer in-flow chrome above Sessions/Bots"
    }
    if ($teamsSnippet -notmatch 'findBotsTab' -or $teamsSnippet -notmatch 'data-dragon-ai-sidebar-clearance') {
        throw "Apply-DesktopBranding: teams-picker.js must reserve clearance so the overlay does not cover BOTS"
    }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    foreach ($root in $Roots) {
        if (-not $root -or -not (Test-Path -LiteralPath $root -PathType Container)) { continue }
        $posix = $root.Replace("\", "/")
        if ($posix.EndsWith("/src") -or $posix.Contains("/src/")) { continue }
        foreach ($cand in @((Join-Path $root "dist"), $root)) {
            if (-not (Test-Path -LiteralPath $cand -PathType Container)) { continue }
            $hasHtml = @(Get-ChildItem -LiteralPath $cand -Filter "*.html" -File -ErrorAction SilentlyContinue)
            $hasJs = @(Get-ChildItem -LiteralPath $cand -Filter "*.js" -File -ErrorAction SilentlyContinue)
            $hasAssets = Test-Path -LiteralPath (Join-Path $cand "assets")
            if (-not ($hasHtml -or $hasJs -or $hasAssets)) { continue }
            $targets++
            $dest = Join-Path $cand "dragon-ai-branding"
            New-Item -ItemType Directory -Force -Path $dest | Out-Null
            Get-ChildItem -LiteralPath $pack -File -ErrorAction SilentlyContinue |
                Where-Object { $_.Extension -in @(".woff2", ".css", ".txt", ".md", ".js") } |
                ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $dest $_.Name) -Force }
            $scriptDir = $PSScriptRoot
            if ([string]::IsNullOrWhiteSpace($scriptDir)) {
                $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
            }
            $brandRoot = Join-Path (Split-Path -Parent (Split-Path -Parent $scriptDir)) "branding"
            foreach ($logoName in @("dragon-ai-agent-logo.svg", "dragon-ai-agent-logo.png")) {
                $logoSrc = Join-Path $brandRoot $logoName
                if (Test-Path -LiteralPath $logoSrc) {
                    Copy-Item -LiteralPath $logoSrc -Destination (Join-Path $dest $logoName) -Force
                }
            }
            $teamsSrc = Join-Path $brandRoot "teams"
            if (Test-Path -LiteralPath $teamsSrc) {
                $teamsDest = Join-Path $dest "teams"
                New-Item -ItemType Directory -Force -Path $teamsDest | Out-Null
                Get-ChildItem -LiteralPath $teamsSrc -Filter "*.svg" -File -ErrorAction SilentlyContinue |
                    ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $teamsDest $_.Name) -Force }
            }
            $sheetPath = Join-Path $dest "dragon-ui.css"
            if (-not (Test-Path -LiteralPath $sheetPath)) {
                throw "Apply-DesktopBranding: failed to copy dragon-ui.css into $dest"
            }
            $sheet = [System.IO.File]::ReadAllText($sheetPath)
            if ($sheet -notmatch "dragon-ai-lockup-wrap:1" -or $sheet -notmatch "dragon-ai-marketplace-label:1") {
                throw "Apply-DesktopBranding: copied dragon-ui.css is missing Teams label/wrap stamps ($sheetPath)"
            }
            if ($sheet -notmatch "dragon-ai-marketplace-blue:1" -or $sheet -notmatch "2563eb") {
                throw "Apply-DesktopBranding: copied dragon-ui.css is missing the blue Teams Marketplace button ($sheetPath)"
            }
            if ($sheet -notmatch "dragon-ai-logo-clearance:1" -or $sheet -notmatch "dragon-logo-clearance") {
                throw "Apply-DesktopBranding: copied dragon-ui.css is missing logo clearance ($sheetPath)"
            }
            if ($sheet -notmatch "dragon-ai-composer-chrome:1") {
                throw "Apply-DesktopBranding: copied dragon-ui.css is missing composer chrome stamp ($sheetPath)"
            }
            $copiedCss++
            $cssMark = "/* dragon-ai-ui-face */"
            $cssFiles = @(Get-ChildItem -LiteralPath $cand -Filter "*.css" -File -ErrorAction SilentlyContinue)
            $assetsDir = Join-Path $cand "assets"
            if (Test-Path -LiteralPath $assetsDir) {
                $cssFiles += @(Get-ChildItem -LiteralPath $assetsDir -Filter "*.css" -File -ErrorAction SilentlyContinue)
            }
            foreach ($cssFile in $cssFiles) {
                if ($cssFile.FullName -like "*dragon-ai-branding*") { continue }
                $existing = [System.IO.File]::ReadAllText($cssFile.FullName)
                $cssDir = Split-Path -Parent $cssFile.FullName
                $prefix = "./dragon-ai-branding"
                if ([System.IO.Path]::GetFullPath($cssDir).TrimEnd('\') -ne [System.IO.Path]::GetFullPath($cand).TrimEnd('\')) {
                    $prefix = "../dragon-ai-branding"
                }
                $rewritten = $sheet.Replace('url("./', ('url("' + $prefix + '/'))
                if ($existing.Contains($cssMark)) {
                    $idx = $existing.IndexOf($cssMark)
                    $outCss = $existing.Substring(0, $idx).TrimEnd() + "`n" + $cssMark + "`n" + $rewritten + "`n"
                } else {
                    $outCss = $existing.TrimEnd() + "`n" + $cssMark + "`n" + $rewritten + "`n"
                }
                if ($outCss -ne $existing) {
                    [System.IO.File]::WriteAllText($cssFile.FullName, $outCss, $utf8)
                }
            }
            foreach ($html in $hasHtml) {
                $text = [System.IO.File]::ReadAllText($html.FullName)
                $changed = $false
                if (-not $text.Contains('data-dragon-ai-branding="ui-face"') -and -not $text.Contains('data-dragon-ai-branding="outfit"')) {
                    $inserted = Add-DragonAIBeforeClose -Html $text -Snippet $link
                    $text = $inserted.text
                    $changed = $true
                }
                $sidebar = Update-DragonAIMarkedSnippet -Html $text -Mark $sidebarMark -Snippet $sidebarSnippet
                $text = $sidebar.text
                if ($sidebar.changed) { $changed = $true }
                $teams = Update-DragonAIMarkedSnippet -Html $text -Mark $teamsMark -Snippet $teamsSnippet
                $text = $teams.text
                if ($teams.changed) { $changed = $true }
                $stripped = Remove-DragonAICrimsonLockupBorder -Text $text
                if ($stripped -ne $text) {
                    $text = $stripped
                    $changed = $true
                }
                if ($changed) {
                    [System.IO.File]::WriteAllText($html.FullName, $text, $utf8)
                    $htmlPatched++
                }
            }
        }
    }
    if ($copiedCss -lt 1) {
        throw "Apply-DesktopBranding: dragon-ui.css / inject did not land in unpacked dist/dragon-ai-branding (no renderer target). Python is optional — this PowerShell copy must succeed."
    }
    return @{ fontFamily = "Syne"; copied = $true; htmlPatched = $htmlPatched; targets = $targets; cssCopied = $copiedCss }
}

function Test-DragonAISkipBrandingFile {
    param([string]$Name)
    if ($Name -eq ".dragon-ai-ui-branding.json") { return $true }
    foreach ($prefix in @("LICENSE", "NOTICE", "THIRD_PARTY", "COPYING")) {
        if ($Name.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) { return $true }
    }
    $ext = [System.IO.Path]::GetExtension($Name).ToLowerInvariant()
    $ok = @(".js", ".mjs", ".cjs", ".html", ".htm", ".css", ".json", ".map", ".ts", ".tsx", ".jsx")
    return -not ($ok -contains $ext)
}

function Invoke-DragonAIDesktopBrandingOverlay {
    param(
        [string]$ExePath = "",
        [string]$Root = "",
        [switch]$Quiet
    )
    $table = Get-DragonAIDesktopBrandingTable
    $rows = @($table.replacements | Sort-Object { $_.from.Length } -Descending)
    $roots = @()
    $pySummary = $null
    if ($Root) {
        $roots = @($Root)
    } elseif ($ExePath) {
        $py = $null
        foreach ($cmd in @("python3", "python", "py")) {
            $hit = Get-Command $cmd -ErrorAction SilentlyContinue
            if ($hit) { $py = $hit.Source; break }
        }
        $engine = Join-Path $PSScriptRoot "desktop_branding.py"
        if ($py -and (Test-Path -LiteralPath $engine)) {
            $pyArgs = @($engine, "--exe", $ExePath, "--json")
            if ($py -like "*\py.exe" -or $py -like "*/py") { $pyArgs = @("-3") + $pyArgs }
            try {
                $json = & $py @pyArgs 2>&1 | Out-String
                if ($LASTEXITCODE -eq 0 -and $json) {
                    try { $pySummary = $json | ConvertFrom-Json } catch { $pySummary = $null }
                }
            } catch {}
        }
        $roots = @(Get-DragonAIDesktopBrandingRoots -ExePath $ExePath) + @(Get-DragonAIInstallUnpackedRoots)
    } else {
        throw "Apply-DesktopBranding requires -ExePath or -Root"
    }

    $filesChanged = 0
    $replacementsApplied = 0
    $utf8 = New-Object System.Text.UTF8Encoding $false
    foreach ($dir in $roots) {
        if (-not (Test-Path -LiteralPath $dir)) { continue }
        $files = @()
        if (Test-Path -LiteralPath $dir -PathType Leaf) {
            $files = @(Get-Item -LiteralPath $dir)
        } else {
            $files = @(Get-ChildItem -LiteralPath $dir -Recurse -File -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.FullName -notmatch '\\node_modules\\|\\\.git\\|\\prebuilds\\' -and
                    -not (Test-DragonAISkipBrandingFile -Name $_.Name) -and
                    $_.Length -lt 40MB
                })
        }
        foreach ($file in $files) {
            $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
            if ($bytes -contains 0) { continue }
            $text = $utf8.GetString($bytes)
            if ($text.Length -gt 0 -and $text[0] -eq [char]0xFEFF) {
                $text = $text.Substring(1)
            }
            $out = $text
            $hits = 0
            foreach ($row in $rows) {
                if ($out.Contains($row.from)) {
                    $n = ([regex]::Matches($out, [regex]::Escape($row.from))).Count
                    $out = $out.Replace($row.from, $row.to)
                    $hits += $n
                }
            }
            $posix = $file.FullName.Replace("\", "/")
            foreach ($row in @($table.source_only)) {
                if (-not $row) { continue }
                $suffix = [string]$row.path_suffix
                if ($suffix -and $posix.EndsWith($suffix.Replace("\", "/")) -and $out.Contains($row.from)) {
                    $n = ([regex]::Matches($out, [regex]::Escape($row.from))).Count
                    $out = $out.Replace($row.from, $row.to)
                    $hits += $n
                }
            }
            $stripped = Remove-DragonAICrimsonLockupBorder -Text $out
            if ($stripped -ne $out) {
                $out = $stripped
                $hits++
            }
            if ($hits -gt 0 -and $out -ne $text) {
                [System.IO.File]::WriteAllText($file.FullName, $out, $utf8)
                $filesChanged++
                $replacementsApplied += $hits
            }
        }
    }

    $font = Install-DragonAIDesktopFontPack -Roots $roots
    if (-not $font.copied) {
        throw "Apply-DesktopBranding: dragon-ui.css / inject did not land in unpacked dist/dragon-ai-branding"
    }

    if ($ExePath) {
        $scriptDir = $PSScriptRoot
        if ([string]::IsNullOrWhiteSpace($scriptDir)) {
            $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
        }
        $icoCandidates = @(
            (Join-Path (Split-Path -Parent (Split-Path -Parent $scriptDir)) "installer\winres\icon.ico"),
            (Join-Path (Split-Path -Parent (Split-Path -Parent $scriptDir)) "branding\dragon-ai-agent-logo.ico")
        )
        foreach ($ico in $icoCandidates) {
            if (Test-Path -LiteralPath $ico) {
                $resourcesDir = Join-Path (Split-Path -Parent $ExePath) "resources"
                New-Item -ItemType Directory -Force -Path $resourcesDir | Out-Null
                Copy-Item -LiteralPath $ico -Destination (Join-Path $resourcesDir "icon.ico") -Force
                Copy-Item -LiteralPath $ico -Destination (Join-Path (Split-Path -Parent $ExePath) "icon.ico") -Force
                break
            }
        }
    }

    if ($ExePath) {
        $resources = Join-Path (Split-Path -Parent $ExePath) "resources"
        if (Test-Path -LiteralPath $resources) {
            $stamp = [ordered]@{
                version              = $table.version
                product              = $table.product
                fontFamily           = "Syne"
                filesChanged         = $filesChanged
                replacementsApplied  = $replacementsApplied
            }
            ($stamp | ConvertTo-Json) | Set-Content -LiteralPath (Join-Path $resources ".dragon-ai-ui-branding.json") -Encoding UTF8
        }
    }

    if (-not $Quiet) {
        Write-Host ("Dragon AI Agent UI overlay: {0} replacements in {1} files (font={2})" -f $replacementsApplied, $filesChanged, $font.fontFamily)
        if ($replacementsApplied -eq 0) {
            Write-Host "No unpacked renderer strings matched. If the empty state still says HERMES AGENT, the UI is inside integrity-protected app.asar and needs an upstream Electron rebuild."
        }
    }
    return [pscustomobject]@{
        filesChanged         = $filesChanged
        replacementsApplied  = $replacementsApplied
        roots                = $roots
        font                 = $font
    }
}

if ($MyInvocation.InvocationName -ne '.' -and $MyInvocation.Line -notmatch '^\s*\.') {
    if ($ExePath -or $Root) {
        Invoke-DragonAIDesktopBrandingOverlay -ExePath $ExePath -Root $Root -Quiet:$Quiet | Out-Null
    }
}
