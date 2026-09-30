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
    return $null
}

function Install-DragonAIDesktopFontPack {
    param([string[]]$Roots)
    $pack = Get-DragonAIDesktopFontPack
    if (-not $pack) { return @{ fontFamily = $null; copied = $false; htmlPatched = 0 } }
    $htmlPatched = 0
    $targets = 0
    $link = '<link rel="stylesheet" href="./dragon-ai-branding/dragon-ui.css" data-dragon-ai-branding="ui-face" />'
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
                Where-Object { $_.Extension -in @(".woff2", ".css", ".txt", ".md") } |
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
            $sheetPath = Join-Path $dest "dragon-ui.css"
            $cssMark = "/* dragon-ai-ui-face */"
            if (Test-Path -LiteralPath $sheetPath) {
                $sheet = [System.IO.File]::ReadAllText($sheetPath)
                $cssFiles = @(Get-ChildItem -LiteralPath $cand -Filter "*.css" -File -ErrorAction SilentlyContinue)
                $assetsDir = Join-Path $cand "assets"
                if (Test-Path -LiteralPath $assetsDir) {
                    $cssFiles += @(Get-ChildItem -LiteralPath $assetsDir -Filter "*.css" -File -ErrorAction SilentlyContinue)
                }
                foreach ($cssFile in $cssFiles) {
                    if ($cssFile.FullName -like "*dragon-ai-branding*") { continue }
                    $existing = [System.IO.File]::ReadAllText($cssFile.FullName)
                    if ($existing.Contains($cssMark)) { continue }
                    $cssDir = Split-Path -Parent $cssFile.FullName
                    $prefix = "./dragon-ai-branding"
                    if ([System.IO.Path]::GetFullPath($cssDir).TrimEnd('\') -ne [System.IO.Path]::GetFullPath($cand).TrimEnd('\')) {
                        $prefix = "../dragon-ai-branding"
                    }
                    $rewritten = $sheet.Replace('url("./', ('url("' + $prefix + '/'))
                    [System.IO.File]::WriteAllText($cssFile.FullName, ($existing.TrimEnd() + "`n" + $cssMark + "`n" + $rewritten + "`n"), $utf8)
                }
            }
            foreach ($html in $hasHtml) {
                $text = [System.IO.File]::ReadAllText($html.FullName)
                if ($text.Contains('data-dragon-ai-branding="ui-face"') -or $text.Contains('data-dragon-ai-branding="outfit"')) { continue }
                $out = $null
                $lower = $text.ToLowerInvariant()
                $idx = $lower.IndexOf("</head>")
                if ($idx -ge 0) {
                    $out = $text.Substring(0, $idx) + $link + "`n" + $text.Substring($idx)
                } else {
                    $out = $link + "`n" + $text
                }
                [System.IO.File]::WriteAllText($html.FullName, $out, $utf8)
                $htmlPatched++
            }
        }
    }
    return @{ fontFamily = "Syne"; copied = ($targets -gt 0); htmlPatched = $htmlPatched; targets = $targets }
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
                    $summary = $json | ConvertFrom-Json
                    if (-not $Quiet) {
                        Write-Host ("Dragon AI Agent UI overlay: {0} replacements in {1} files" -f $summary.replacementsApplied, $summary.filesChanged)
                    }
                    return $summary
                }
            } catch {}
        }
        $roots = Get-DragonAIDesktopBrandingRoots -ExePath $ExePath
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
            if ($hits -gt 0 -and $out -ne $text) {
                [System.IO.File]::WriteAllText($file.FullName, $out, $utf8)
                $filesChanged++
                $replacementsApplied += $hits
            }
        }
    }

    $font = Install-DragonAIDesktopFontPack -Roots $roots

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
