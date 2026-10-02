#requires -Version 5.1
<#
.SYNOPSIS
  Dragon AI Agent secure secret store (DPAPI) + onboarding progress / bot readiness.

.DESCRIPTION
  Dot-source this script. Secrets are ProtectedData (CurrentUser) binary files under
  %LOCALAPPDATA%\DragonAIAgent\onboarding\secrets\ — never written into JSON.

.NOTES
  Progress:  %LOCALAPPDATA%\DragonAIAgent\onboarding\progress.json
  Bots:      %LOCALAPPDATA%\DragonAIAgent\onboarding\bots-status.json
#>

$script:DragonAIOnboardingRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent\onboarding"
$script:DragonAISecretsDir     = Join-Path $script:DragonAIOnboardingRoot "secrets"
$script:DragonAIProgressPath   = Join-Path $script:DragonAIOnboardingRoot "progress.json"
$script:DragonAIBotsStatusPath = Join-Path $script:DragonAIOnboardingRoot "bots-status.json"

Add-Type -AssemblyName System.Security -ErrorAction SilentlyContinue | Out-Null

function Ensure-DragonAIOnboardingDirs {
    foreach ($d in @($script:DragonAIOnboardingRoot, $script:DragonAISecretsDir)) {
        if (-not (Test-Path -LiteralPath $d)) {
            New-Item -ItemType Directory -Force -Path $d | Out-Null
        }
    }
}

function Get-DragonAISecretPath {
    param([Parameter(Mandatory = $true)][string]$Name)
    $safe = ($Name -replace '[^A-Za-z0-9_\-\.]', '_')
    return (Join-Path $script:DragonAISecretsDir "$safe.bin")
}

function Save-DragonAISecret {
    <#
    .SYNOPSIS
      Encrypt plaintext with DPAPI (CurrentUser) and store as a binary file.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$PlainText
    )
    Ensure-DragonAIOnboardingDirs
    if ([string]::IsNullOrEmpty($PlainText)) {
        throw "Save-DragonAISecret: PlainText is empty for name '$Name'"
    }
    $bytes = [Text.Encoding]::UTF8.GetBytes($PlainText)
    $protected = [Security.Cryptography.ProtectedData]::Protect(
        $bytes,
        $null,
        [Security.Cryptography.DataProtectionScope]::CurrentUser
    )
    $path = Get-DragonAISecretPath -Name $Name
    [IO.File]::WriteAllBytes($path, $protected)
}

function Get-DragonAISecret {
    <#
    .SYNOPSIS
      Decrypt a DPAPI secret file; returns $null if missing.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Name
    )
    $path = Get-DragonAISecretPath -Name $Name
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try {
        $protected = [IO.File]::ReadAllBytes($path)
        $bytes = [Security.Cryptography.ProtectedData]::Unprotect(
            $protected,
            $null,
            [Security.Cryptography.DataProtectionScope]::CurrentUser
        )
        return [Text.Encoding]::UTF8.GetString($bytes)
    } catch {
        Write-Warning "Get-DragonAISecret failed for '$Name': $($_.Exception.Message)"
        return $null
    }
}

function Remove-DragonAISecret {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Name
    )
    $path = Get-DragonAISecretPath -Name $Name
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    }
}

function Test-DragonAISecret {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Name
    )
    $path = Get-DragonAISecretPath -Name $Name
    return (Test-Path -LiteralPath $path)
}

function Get-DragonAIOnboardingProgress {
    Ensure-DragonAIOnboardingDirs
    if (-not (Test-Path -LiteralPath $script:DragonAIProgressPath)) {
        return [pscustomobject]@{
            profileId = ""
            skipped   = $false
            updatedAt = $null
            steps     = [ordered]@{
                welcome       = "pending"
                email         = "pending"
                crm           = "pending"
                telephony     = "pending"
                property_data = "pending"
                dialer        = "pending"
                review        = "pending"
            }
            nonSecret = [ordered]@{}
        }
    }
    try {
        $raw = Get-Content -LiteralPath $script:DragonAIProgressPath -Raw -Encoding UTF8
        return ($raw | ConvertFrom-Json)
    } catch {
        Write-Warning "Could not read progress.json: $($_.Exception.Message)"
        return [pscustomobject]@{
            profileId = ""
            skipped   = $false
            updatedAt = $null
            steps     = [ordered]@{
                welcome = "pending"; email = "pending"; crm = "pending"
                telephony = "pending"; property_data = "pending"
                dialer = "pending"; review = "pending"
            }
            nonSecret = [ordered]@{}
        }
    }
}

function Save-DragonAIOnboardingProgress {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]$Progress
    )
    Ensure-DragonAIOnboardingDirs
    if ($Progress.PSObject.Properties.Name -contains "updatedAt") {
        $Progress.updatedAt = (Get-Date).ToString("o")
    } else {
        $Progress | Add-Member -MemberType NoteProperty -Name updatedAt -Value ((Get-Date).ToString("o")) -Force
    }
    $json = $Progress | ConvertTo-Json -Depth 10
    Set-Content -LiteralPath $script:DragonAIProgressPath -Value $json -Encoding UTF8
}

function Get-DragonAIBotStatus {
    Ensure-DragonAIOnboardingDirs
    if (-not (Test-Path -LiteralPath $script:DragonAIBotsStatusPath)) {
        return [pscustomobject]@{
            profileId = ""
            updatedAt = $null
            bots      = [ordered]@{}
        }
    }
    try {
        $raw = Get-Content -LiteralPath $script:DragonAIBotsStatusPath -Raw -Encoding UTF8
        return ($raw | ConvertFrom-Json)
    } catch {
        return [pscustomobject]@{ profileId = ""; updatedAt = $null; bots = [ordered]@{} }
    }
}

function Set-DragonAIBotStatus {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]$Status
    )
    Ensure-DragonAIOnboardingDirs
    if ($Status.PSObject.Properties.Name -contains "updatedAt") {
        $Status.updatedAt = (Get-Date).ToString("o")
    } else {
        $Status | Add-Member -MemberType NoteProperty -Name updatedAt -Value ((Get-Date).ToString("o")) -Force
    }
    $json = $Status | ConvertTo-Json -Depth 10
    Set-Content -LiteralPath $script:DragonAIBotsStatusPath -Value $json -Encoding UTF8
}

function Get-DragonAIRealEstateBotIds {
    return @(
        "lead-sourcer",
        "email-warmer",
        "cold-call-script-writer",
        "follow-up-sequencer"
    )
}

function Test-DragonAIRequiredStepsComplete {
    param($Progress, [string]$ProfileId)

    if ($ProfileId -like "personal-assistant*") {
        return $true
    }

    if ($Progress.skipped) { return $false }

    $steps = $Progress.steps
    $required = @("email", "crm", "telephony")
    foreach ($r in $required) {
        $val = $null
        if ($steps -is [hashtable] -or $steps -is [System.Collections.IDictionary]) {
            $val = $steps[$r]
        } elseif ($steps.PSObject.Properties.Name -contains $r) {
            $val = $steps.$r
        }
        if ($val -ne "success") { return $false }
    }
    return $true
}

function Update-DragonAIBotsFromProgress {
    <#
    .SYNOPSIS
      Set all bot-group bots to ready or needs_setup based on required onboarding steps.
      Real-estate required: email + crm + telephony (welcome optional; property-data/dialer optional).
      Personal-assistant: mark ready (no critical connectors).
    #>
    [CmdletBinding()]
    param(
        [string]$ProfileId = "",
        $Progress = $null,
        [string[]]$BotIds = @()
    )

    if ($null -eq $Progress) {
        $Progress = Get-DragonAIOnboardingProgress
    }
    if ([string]::IsNullOrWhiteSpace($ProfileId)) {
        $ProfileId = [string]$Progress.profileId
    }
    if ([string]::IsNullOrWhiteSpace($ProfileId)) {
        $activeGroup = Join-Path $env:LOCALAPPDATA "DragonAIAgent\active-bot-group.json"
        if ([string]::IsNullOrWhiteSpace($ProfileId) -and (Test-Path -LiteralPath $activeGroup)) {
            try {
                $active = Get-Content -LiteralPath $activeGroup -Raw -Encoding UTF8 | ConvertFrom-Json
                $ProfileId = [string]$active.botGroupId
            } catch {}
        }
        $activePath = Join-Path $env:LOCALAPPDATA "DragonAIAgent\active-profile.json"
        if (Test-Path -LiteralPath $activePath) {
            try {
                $active = Get-Content -LiteralPath $activePath -Raw -Encoding UTF8 | ConvertFrom-Json
                $ProfileId = [string]$active.profileId
            } catch {}
        }
    }

    if ($BotIds.Count -eq 0) {
        if ($ProfileId -like "real-estate*") {
            $BotIds = Get-DragonAIRealEstateBotIds
        } elseif ($ProfileId -like "personal-assistant*") {
            $BotIds = @("personal-assistant")
        } else {
            $existing = Get-DragonAIBotStatus
            if ($existing.bots) {
                $BotIds = @($existing.bots.PSObject.Properties.Name)
            }
        }
    }

    $ready = Test-DragonAIRequiredStepsComplete -Progress $Progress -ProfileId $ProfileId
    $state = if ($ready) { "ready" } else { "needs_setup" }

    $botsMap = [ordered]@{}
    foreach ($id in $BotIds) {
        if ([string]::IsNullOrWhiteSpace($id)) { continue }
        $botsMap[$id] = $state
    }

    $status = [pscustomobject]@{
        profileId = $ProfileId
        updatedAt = (Get-Date).ToString("o")
        bots      = $botsMap
        reason    = if ($ready) {
            "Required onboarding steps complete (or personal-assistant bot group)."
        } else {
            "Required steps incomplete (email + crm + telephony) or wizard skipped; bots stay needs_setup."
        }
    }
    Set-DragonAIBotStatus -Status $status
    return $status
}

function Initialize-DragonAIBotsNeedsSetup {
    <#
    .SYNOPSIS
      Initialize bots-status.json to needs_setup for a bot group (used by Deploy-BotGroup).
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$ProfileId,
        [string[]]$BotIds = @()
    )
    if ($BotIds.Count -eq 0) {
        if ($ProfileId -like "real-estate*") {
            $BotIds = Get-DragonAIRealEstateBotIds
        } elseif ($ProfileId -like "personal-assistant*") {
            $BotIds = @("personal-assistant")
        }
    }
    $botsMap = [ordered]@{}
    $state = if ($ProfileId -like "personal-assistant*") { "ready" } else { "needs_setup" }
    foreach ($id in $BotIds) {
        if ([string]::IsNullOrWhiteSpace($id)) { continue }
        $botsMap[$id] = $state
    }
    $status = [pscustomobject]@{
        profileId = $ProfileId
        updatedAt = (Get-Date).ToString("o")
        bots      = $botsMap
        reason    = if ($state -eq "ready") {
            "Personal Assistant bot group — no critical connectors required."
        } else {
            "Bot group applied; finish required connectors in the app (in-app Models UI). WinForms Setup shortcut retired."
        }
    }
    Set-DragonAIBotStatus -Status $status
    return $status
}
