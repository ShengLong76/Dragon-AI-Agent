#requires -Version 5.1
<#
.SYNOPSIS
  Dragon AI Agent first-run onboarding wizard (WinForms or console fallback).

.DESCRIPTION
  Steps: Welcome -> Models (chat + image LLM) -> Email -> CRM -> Telephony -> Optional integrations -> Review.
  Secrets via DragonAI-SecureStore.ps1 (DPAPI). Progress resumes at first incomplete step.
#>
[CmdletBinding()]
param(
    [string]$InstallRoot = "",
    [string]$PayloadRoot = "",
    [string]$BotGroupId = "",
    [string]$ProfileId = "",
    [switch]$SkipWelcome,
    [switch]$Force,
    [switch]$SelfTest
)

$ErrorActionPreference = "Continue"
$ProductName = "Dragon AI Agent"

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent"
}
if ([string]::IsNullOrWhiteSpace($PayloadRoot)) {
    $PayloadRoot = $InstallRoot
}

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$secureStore = Join-Path $scriptDir "DragonAI-SecureStore.ps1"
if (-not (Test-Path -LiteralPath $secureStore)) {
    $secureStore = Join-Path $InstallRoot "scripts\airmaze\DragonAI-SecureStore.ps1"
}
if (-not (Test-Path -LiteralPath $secureStore)) {
    Write-Error "DragonAI-SecureStore.ps1 not found beside wizard or under InstallRoot."
    exit 1
}
. $secureStore

$LogPath = Join-Path $env:LOCALAPPDATA "DragonAIAgent\onboarding\wizard.log"
Ensure-DragonAIOnboardingDirs

function Write-WizardLog {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    try { Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue } catch {}
}

function Resolve-WizardProfileId {
    if (-not [string]::IsNullOrWhiteSpace($BotGroupId)) { return $BotGroupId }
    if (-not [string]::IsNullOrWhiteSpace($ProfileId)) { return $ProfileId }
    $activeGroup = Join-Path $InstallRoot "active-bot-group.json"
    if (Test-Path -LiteralPath $activeGroup) {
        try {
            $a = Get-Content -LiteralPath $activeGroup -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($a.botGroupId) { return [string]$a.botGroupId }
        } catch {}
    }
    $activePath = Join-Path $InstallRoot "active-profile.json"
    if (Test-Path -LiteralPath $activePath) {
        try {
            $a = Get-Content -LiteralPath $activePath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($a.botGroupId) { return [string]$a.botGroupId }
            if ($a.profileId) { return [string]$a.profileId }
        } catch {}
    }
    $p = Get-DragonAIOnboardingProgress
    if ($p.profileId) { return [string]$p.profileId }
    return "personal-assistant"
}

function Test-DictHasKey {
    param($Map, [string]$Name)
    if ($null -eq $Map) { return $false }
    # [ordered] is OrderedDictionary: IDictionary.Contains, not ContainsKey.
    if ($Map -is [hashtable]) { return $Map.ContainsKey($Name) }
    if ($Map -is [System.Collections.IDictionary]) { return $Map.Contains($Name) }
    return ($Map.PSObject.Properties.Name -contains $Name)
}

function Get-MapValue {
    param($Map, [string]$Name, [string]$Default = "")
    if (-not (Test-DictHasKey -Map $Map -Name $Name)) { return $Default }
    if ($Map -is [hashtable] -or $Map -is [System.Collections.IDictionary]) {
        return [string]$Map[$Name]
    }
    return [string]$Map.$Name
}

function Get-StepValue {
    param($Progress, [string]$Name)
    $steps = $Progress.steps
    if ($null -eq $steps) { return "pending" }
    $v = Get-MapValue -Map $steps -Name $Name -Default "pending"
    if ([string]::IsNullOrWhiteSpace($v)) { return "pending" }
    return $v
}

function Format-WizardStepWord {
    param([string]$Status)
    switch -Regex ([string]$Status) {
        '^success$' { return "OK" }
        '^failed$'  { return "failed" }
        '^skipped$' { return "skipped" }
        '^in_app$'  { return "in-app" }
        default     { return "pending" }
    }
}

function Test-WizardStepComplete {
    param([string]$Status)
    return ([string]$Status -in @("success", "skipped", "in_app"))
}

function Format-WizardStatusLine {
    <#
    .SYNOPSIS
      Short Welcome + Models status only. Never concatenates every PENDING step.
    #>
    param($Progress)
    $welcome = Format-WizardStepWord (Get-StepValue -Progress $Progress -Name "welcome")
    $models = Format-WizardStepWord (Get-StepValue -Progress $Progress -Name "models")
    return "Welcome: $welcome / Models: $models"
}

function Test-WizardCanSetText {
    <#
    .SYNOPSIS
      True only when Target has a settable Text property (WinForms/WPF control or similar).
      $null, hashtables, and PSCustomObjects without Text are refused - assigning .Text
      to those throws: The property 'Text' cannot be found on this object.
    #>
    param($Target)
    if ($null -eq $Target) { return $false }
    if ($Target -is [hashtable] -or $Target -is [System.Collections.IDictionary]) {
        return $false
    }
    $prop = $Target.PSObject.Properties["Text"]
    if ($null -eq $prop) { return $false }
    return [bool]$prop.IsSettable
}

function Set-WizardControlText {
    param($Target, [string]$Value)
    if (-not (Test-WizardCanSetText -Target $Target)) { return $false }
    try {
        $Target.Text = $Value
        return $true
    } catch {
        return $false
    }
}

function Set-WizardMessage {
    param([string]$Value)
    Set-WizardControlText -Target $script:WizMsgLabel -Value $Value | Out-Null
}

function Set-StepValue {
    param($Progress, [string]$Name, [string]$Value)
    if ($null -eq $Progress.steps) {
        $Progress | Add-Member -MemberType NoteProperty -Name steps -Value ([pscustomobject]@{}) -Force
    }
    $steps = $Progress.steps
    if ($steps -is [hashtable] -or $steps -is [System.Collections.IDictionary]) {
        $steps[$Name] = $Value
    } else {
        $steps | Add-Member -MemberType NoteProperty -Name $Name -Value $Value -Force
    }
}

function Set-NonSecret {
    param($Progress, [string]$Key, $Value)
    if ($null -eq $Progress.nonSecret) {
        $Progress | Add-Member -MemberType NoteProperty -Name nonSecret -Value ([pscustomobject]@{}) -Force
    }
    $ns = $Progress.nonSecret
    if ($ns -is [hashtable] -or $ns -is [System.Collections.IDictionary]) {
        $ns[$Key] = $Value
    } else {
        $ns | Add-Member -MemberType NoteProperty -Name $Key -Value $Value -Force
    }
}

function Get-EmbeddedHermesHome {
    if ($env:HERMES_EMBEDDED_DATA) { return [string]$env:HERMES_EMBEDDED_DATA }
    return (Join-Path $env:USERPROFILE ".hermes-airmaze-embedded")
}

function Get-WizardChatCatalog {
    @(
        @{ id = "grok-4.7"; label = "Grok (xAI) - grok-4.7" },
        @{ id = "grok-4.6"; label = "Grok (xAI) - grok-4.6" },
        @{ id = "grok-4.5"; label = "Grok (xAI) - grok-4.5" },
        @{ id = "grok-4.3"; label = "Grok (xAI) - grok-4.3" },
        @{ id = "gpt-4o"; label = "OpenAI - gpt-4o" },
        @{ id = "claude-sonnet-4-6"; label = "Anthropic - claude-sonnet-4-6" },
        @{ id = "gemini-2.5-pro"; label = "Google Gemini - gemini-2.5-pro" },
        @{ id = "openrouter-gpt-4o"; label = "OpenRouter - openai/gpt-4o" },
        @{ id = "self-hosted"; label = "Self-hosted / custom endpoint" }
    )
}

function Get-WizardImageCatalog {
    @(
        @{ id = "grok-imagine-image"; label = "Grok Imagine - grok-imagine-image" },
        @{ id = "grok-imagine-image-quality"; label = "Grok Imagine (Quality) - grok-imagine-image-quality" },
        @{ id = "grok-imagine-image-2.0"; label = "Grok Imagine 2.0 - grok-imagine-image-2.0" }
    )
}

function Invoke-ApplyGatewayModels {
    param(
        [string]$Chat = "grok-4.7",
        [string]$Image = "grok-imagine-image",
        [string]$CustomModel = "",
        [string]$BaseUrl = "",
        [switch]$IfMissing
    )
    $apply = Join-Path $scriptDir "Apply-GatewayModels.ps1"
    if (-not (Test-Path -LiteralPath $apply)) {
        $apply = Join-Path $InstallRoot "scripts\airmaze\Apply-GatewayModels.ps1"
    }
    if (-not (Test-Path -LiteralPath $apply)) {
        Write-WizardLog "Apply-GatewayModels.ps1 missing; model defaults not written" "WARN"
        return $false
    }
    $embeddedHome = Get-EmbeddedHermesHome
    $applyArgs = @("-HermesHome", $embeddedHome, "-Chat", $Chat, "-Image", $Image)
    if (-not [string]::IsNullOrWhiteSpace($CustomModel)) { $applyArgs += @("-CustomModel", $CustomModel) }
    if (-not [string]::IsNullOrWhiteSpace($BaseUrl)) { $applyArgs += @("-BaseUrl", $BaseUrl) }
    if ($IfMissing) { $applyArgs += "-IfMissing" } else { $applyArgs += "-RestartGateway" }
    try {
        & $apply @applyArgs | Out-Null
        Write-WizardLog "Applied gateway models chat=$Chat image=$Image custom=$CustomModel baseUrl=$BaseUrl ifMissing=$IfMissing home=$embeddedHome"
        return ($LASTEXITCODE -eq 0)
    } catch {
        Write-WizardLog "Apply-GatewayModels failed: $($_.Exception.Message)" "WARN"
        return $false
    }
}

function Get-FirstIncompleteStep {
    param($Progress)
    if ($Force) { return "welcome" }
    if ($Progress.skipped) { return "done" }
    $order = @("welcome", "models", "email", "crm", "telephony", "property_data", "dialer", "review")
    foreach ($s in $order) {
        $v = Get-StepValue -Progress $Progress -Name $s
        if (-not (Test-WizardStepComplete -Status $v)) { return $s }
    }
    return "done"
}

function Write-ConnectorPlaceholders {
    param($Progress, [string]$ProfId)
    $connRoot = Join-Path $env:LOCALAPPDATA "DragonAIAgent\connectors\$ProfId"
    if (-not (Test-Path -LiteralPath $connRoot)) {
        New-Item -ItemType Directory -Force -Path $connRoot | Out-Null
    }
    $ns = $Progress.nonSecret
    function NS([string]$k) {
        return (Get-MapValue -Map $ns -Name $k -Default "")
    }

    $emailObj = [ordered]@{
        id = "email"; type = "smtp"; displayName = "Email sending"; status = (Get-StepValue $Progress "email")
        from_address = (NS "email_from_address"); from_name = (NS "email_display_name")
        smtp_host = (NS "email_smtp_host"); smtp_port = (NS "email_smtp_port"); smtp_ssl = (NS "email_smtp_ssl")
        provider = (NS "email_provider"); username = (NS "email_username")
        notes = "Secrets stored via DPAPI under onboarding\secrets. No passwords in this file."
    }
    ($emailObj | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath (Join-Path $connRoot "email.onboarded.json") -Encoding UTF8

    $crmObj = [ordered]@{
        id = "crm"; type = "vtiger"; displayName = "CRM"; status = (Get-StepValue $Progress "crm")
        base_url = (NS "crm_url"); username = (NS "crm_username")
        notes = "Access key stored via DPAPI. No secrets in this file."
    }
    ($crmObj | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath (Join-Path $connRoot "crm.onboarded.json") -Encoding UTF8

    $telObj = [ordered]@{
        id = "telephony"; type = "twilio"; displayName = "Telephony"; status = (Get-StepValue $Progress "telephony")
        twilio_account_sid = (NS "twilio_account_sid"); from_phone = (NS "twilio_from_phone")
        voice_provider = (NS "voice_provider"); seller_name = ""
        notes = "Auth tokens / API keys stored via DPAPI. No secrets in this file."
    }
    ($telObj | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath (Join-Path $connRoot "telephony.onboarded.json") -Encoding UTF8

    $pdObj = [ordered]@{
        id = "property-data"; type = "api_key"; displayName = "Property data"; status = (Get-StepValue $Progress "property_data")
        base_url = (NS "property_data_base_url")
        notes = "API key stored via DPAPI if provided."
    }
    ($pdObj | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath (Join-Path $connRoot "property-data.onboarded.json") -Encoding UTF8

    $dialObj = [ordered]@{
        id = "dialer"; type = "api_key"; displayName = "Dialer"; status = (Get-StepValue $Progress "dialer")
        base_url = (NS "dialer_base_url"); from_number = (NS "dialer_from_number")
        notes = "API key stored via DPAPI if provided."
    }
    ($dialObj | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath (Join-Path $connRoot "dialer.onboarded.json") -Encoding UTF8

    Write-WizardLog "Wrote connector placeholders (non-secret) under $connRoot"
}

# --- Verification helpers ---------------------------------------------------

function Test-SmtpSend {
    param(
        [string]$HostName, [int]$Port, [bool]$EnableSsl,
        [string]$Username, [string]$Password,
        [string]$FromAddress, [string]$DisplayName
    )
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $client = New-Object System.Net.Mail.SmtpClient($HostName, $Port)
        $client.EnableSsl = $EnableSsl
        $client.Timeout = 30000
        if (-not [string]::IsNullOrWhiteSpace($Username)) {
            $client.Credentials = New-Object System.Net.NetworkCredential($Username, $Password)
        }
        $msg = New-Object System.Net.Mail.MailMessage
        $msg.From = New-Object System.Net.Mail.MailAddress($FromAddress, $DisplayName)
        $msg.To.Add($FromAddress)
        $msg.Subject = "Dragon AI Agent - email connection test"
        $msg.Body = "This is a test message from Dragon AI Agent Setup. Your SMTP settings work."
        $client.Send($msg)
        $msg.Dispose()
        $client.Dispose()
        return @{ Ok = $true; Message = "Test email sent to $FromAddress." }
    } catch {
        $err = $_.Exception.Message
        if ($_.Exception.InnerException) { $err = $_.Exception.InnerException.Message }
        return @{ Ok = $false; Message = "Could not send test email: $err. Check host, port, SSL, and password (Gmail needs an App Password)." }
    }
}

function Test-VtigerLogin {
    param([string]$BaseUrl, [string]$Username, [string]$AccessKey)
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $base = $BaseUrl.TrimEnd('/')
        $ws = "$base/webservice.php"
        # Challenge
        $chalUri = "$ws`?operation=getchallenge&username=$([uri]::EscapeDataString($Username))"
        $chalResp = Invoke-RestMethod -Uri $chalUri -Method Get -TimeoutSec 20 -ErrorAction Stop
        if (-not $chalResp.success) {
            # Fallback: simple GET to base URL
            $null = Invoke-WebRequest -Uri $base -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
            return @{ Ok = $true; Message = "CRM URL reachable (webservice challenge failed; URL check OK)."; Partial = $true }
        }
        $token = [string]$chalResp.result.token
        $sum = $token + $AccessKey
        $md5 = [Security.Cryptography.MD5]::Create()
        $hashBytes = $md5.ComputeHash([Text.Encoding]::UTF8.GetBytes($sum))
        $accessHash = ([BitConverter]::ToString($hashBytes) -replace '-', '').ToLowerInvariant()
        $body = @{
            operation = "login"
            username  = $Username
            accessKey = $accessHash
        }
        $login = Invoke-RestMethod -Uri $ws -Method Post -Body $body -TimeoutSec 20 -ErrorAction Stop
        if (-not $login.success) {
            return @{ Ok = $false; Message = "Vtiger login failed. Check username and access key." }
        }
        $session = [string]$login.result.sessionName
        try {
            $lt = Invoke-RestMethod -Uri "$ws`?operation=listtypes&sessionName=$([uri]::EscapeDataString($session))" -Method Get -TimeoutSec 20
            $types = @()
            if ($lt.success -and $lt.result -and $lt.result.types) {
                $types = @($lt.result.types)
            }
            $hasLeads = ($types -contains "Leads") -or ($types -contains "Contacts")
            $extra = if ($hasLeads) { " Leads/Contacts modules visible." } else { " Logged in (module list partial)." }
            return @{ Ok = $true; Message = "Vtiger webservice login OK.$extra" }
        } catch {
            return @{ Ok = $true; Message = "Vtiger login OK (listtypes skipped)." }
        }
    } catch {
        try {
            $null = Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
            return @{ Ok = $true; Message = "CRM URL reachable (full webservice login failed: $($_.Exception.Message))."; Partial = $true }
        } catch {
            return @{ Ok = $false; Message = "Could not reach CRM: $($_.Exception.Message)" }
        }
    }
}

function Test-TwilioAccount {
    param([string]$AccountSid, [string]$AuthToken)
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $uri = "https://api.twilio.com/2010-04-01/Accounts/$AccountSid.json"
        $pair = "${AccountSid}:${AuthToken}"
        $b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
        $headers = @{ Authorization = "Basic $b64" }
        $resp = Invoke-RestMethod -Uri $uri -Headers $headers -Method Get -TimeoutSec 20 -ErrorAction Stop
        $friendly = [string]$resp.friendly_name
        $status = [string]$resp.status
        return @{ Ok = $true; Message = "Twilio account OK ($friendly, status=$status)." }
    } catch {
        return @{ Ok = $false; Message = "Twilio check failed: $($_.Exception.Message). Verify Account SID and Auth Token." }
    }
}

function Invoke-TwilioTestCall {
    param([string]$AccountSid, [string]$AuthToken, [string]$FromPhone, [string]$ToPhone)
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $uri = "https://api.twilio.com/2010-04-01/Accounts/$AccountSid/Calls.json"
        $pair = "${AccountSid}:${AuthToken}"
        $b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
        $headers = @{ Authorization = "Basic $b64" }
        $body = @{
            To   = $ToPhone
            From = $FromPhone
            Twiml = '<Response><Say>This is a Dragon AI Agent telephony test call. Goodbye.</Say></Response>'
        }
        $null = Invoke-RestMethod -Uri $uri -Headers $headers -Method Post -Body $body -TimeoutSec 30 -ErrorAction Stop
        return @{ Ok = $true; Message = "Test call placed to $ToPhone." }
    } catch {
        return @{ Ok = $false; Message = "Test call failed: $($_.Exception.Message)" }
    }
}

# --- Branding colors (must load System.Drawing before [System.Drawing.Color]) -

$script:WinFormsReady = $false
$script:BrandBack = $null
$script:BrandPanel = $null
$script:BrandRed = $null
$script:BrandBlue = $null
$script:BrandText = $null
$script:BrandMuted = $null
$script:BrandOk = $null
$script:BrandFail = $null
$script:BrandPend = $null
$script:WizMsgLabel = $null
$script:WizProgress = $null
$script:WizForm = $null
$script:WizChatBox = $null
$script:WizImageBox = $null
$script:WizChatCatalog = @()
$script:WizImageCatalog = @()
$script:WizCustomPanel = $null
$script:WizBaseUrlBox = $null
$script:WizCustomModelBox = $null
$script:WizCustomKeyBox = $null

function Initialize-WizardWinForms {
    if ($script:WinFormsReady) { return $true }
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop | Out-Null
        Add-Type -AssemblyName System.Drawing -ErrorAction Stop | Out-Null
        # Tokens from design-system/dragon-ai-agent/pages/desktop-client.md
        # Header lockup is Marketplace blue; primary buttons stay crimson.
        $script:BrandBack = [System.Drawing.Color]::FromArgb(28, 28, 32)      # #1C1C20
        $script:BrandPanel = [System.Drawing.Color]::FromArgb(40, 40, 48)     # #282830
        $script:BrandRed = [System.Drawing.Color]::FromArgb(196, 30, 58)      # #C41E3A (buttons / accent)
        $script:BrandBlue = [System.Drawing.Color]::FromArgb(37, 99, 235)     # #2563EB (header lockup; Marketplace)
        $script:BrandText = [System.Drawing.Color]::FromArgb(240, 240, 245)    # #F0F0F5
        $script:BrandMuted = [System.Drawing.Color]::FromArgb(160, 160, 170)   # #A0A0AA
        $script:BrandOk = [System.Drawing.Color]::FromArgb(60, 180, 90)       # #3CB45A
        $script:BrandFail = [System.Drawing.Color]::FromArgb(220, 70, 70)     # #DC4646
        $script:BrandPend = [System.Drawing.Color]::FromArgb(200, 160, 40)    # #C8A028
        $script:WinFormsReady = $true
        return $true
    } catch {
        $script:WinFormsReady = $false
        return $false
    }
}

function Test-WinFormsAvailable {
    return (Initialize-WizardWinForms)
}

# ============================================================================
# CONSOLE FALLBACK
# ============================================================================

function Show-ConsoleStatus([string]$Label, [string]$Status) {
    $tag = switch ($Status) {
        "success" { "[OK]" }
        "failed"  { "[FAIL]" }
        "skipped" { "[SKIP]" }
        default   { "[PEND]" }
    }
    Write-Host ("  {0,-12} {1}" -f $tag, $Label)
}

function Invoke-ConsoleWizard {
    param($Progress, [string]$ProfId)

    Write-Host ""
    Write-Host "========================================"
    Write-Host " $ProductName Setup"
    Write-Host "========================================"
    Write-Host " Bot group: $ProfId"
    Write-Host " Secrets: DPAPI under %LOCALAPPDATA%\DragonAIAgent\onboarding\secrets\"
    Write-Host ""

    $start = Get-FirstIncompleteStep -Progress $Progress
    if ($SkipWelcome -and $start -eq "welcome") { $start = "models" }

    # WELCOME
    if ($start -eq "welcome" -or $Force) {
        Write-Host "--- Welcome ---"
        Write-Host "$ProductName helps you run business bots (Real Estate: Lead Sourcer -> Email Warmer -> consent gate -> calling)."
        Write-Host "This is setup software, not legal advice."
        $ans = Read-Host "Continue [C], Skip wizard [S]"
        if ($ans -match '^[Ss]') {
            $Progress.skipped = $true
            $Progress.profileId = $ProfId
            Set-StepValue $Progress "welcome" "skipped"
            Save-DragonAIOnboardingProgress $Progress
            Invoke-ApplyGatewayModels -IfMissing | Out-Null
            Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
            Write-WizardLog "Wizard skipped by user"
            Write-Host "Wizard skipped. Bots remain needs_setup until you complete required steps."
            return 0
        }
        Set-StepValue $Progress "welcome" "success"
        $Progress.profileId = $ProfId
        $Progress.skipped = $false
        Save-DragonAIOnboardingProgress $Progress
        $start = "models"
    }

    # MODELS (default chat + image LLM)
    if ($start -eq "models" -or $Force) {
        if ((Get-StepValue $Progress "models") -ne "success" -or $Force) {
            Write-Host ""
            Write-Host "--- Default chat LLM and default image LLM ---"
            Write-Host "Suggested default is Grok (xAI). Cloud picks reuse keys already on this PC (XAI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY / GEMINI_API_KEY, OPENROUTER_API_KEY)."
            Write-Host "Every bot inherits this chat model (Personal Assistant and later team seats) unless you override that bot."
            $chatRows = @(Get-WizardChatCatalog)
            $n = 1
            foreach ($row in $chatRows) {
                $mark = if ($n -eq 1) { " (suggested)" } else { "" }
                Write-Host ("  [{0}] {1}{2}" -f $n, $row.label, $mark)
                $n++
            }
            Write-Host "  [S] Skip (write Grok defaults if missing)"
            $chatChoice = Read-Host "Default chat LLM"
            Write-Host "Image: [1] Grok Imagine grok-imagine-image  [2] grok-imagine-image-quality  [3] grok-imagine-image-2.0  [S] Skip"
            $imgChoice = Read-Host "Default image LLM"
            if ($chatChoice -match '^[Ss]' -and $imgChoice -match '^[Ss]') {
                Invoke-ApplyGatewayModels -IfMissing | Out-Null
                Set-StepValue $Progress "models" "skipped"
            } else {
                $chatIdx = 0
                [void][int]::TryParse($chatChoice, [ref]$chatIdx)
                if ($chatIdx -lt 1 -or $chatIdx -gt $chatRows.Count) { $chatIdx = 1 }
                $chat = [string]$chatRows[$chatIdx - 1].id
                $image = switch ($imgChoice) {
                    "2" { "grok-imagine-image-quality" }
                    "3" { "grok-imagine-image-2.0" }
                    default { "grok-imagine-image" }
                }
                $customModel = ""
                $baseUrl = ""
                if ($chat -eq "self-hosted") {
                    $baseUrl = Read-Host "Self-hosted base URL (OpenAI-compatible, e.g. http://127.0.0.1:11434/v1)"
                    $customModel = Read-Host "Self-hosted model id"
                    $customKey = Read-Host "API key (optional; blank for local)"
                    if ([string]::IsNullOrWhiteSpace($baseUrl)) { $baseUrl = "http://127.0.0.1:11434/v1" }
                    if ([string]::IsNullOrWhiteSpace($customModel)) { $customModel = "local-model" }
                    if (-not [string]::IsNullOrWhiteSpace($customKey)) {
                        Save-DragonAISecret -Name "chat_api_key" -PlainText $customKey
                    }
                    Set-NonSecret $Progress "chat_base_url" $baseUrl
                    Set-NonSecret $Progress "chat_provider" "custom"
                }
                Invoke-ApplyGatewayModels -Chat $chat -Image $image -CustomModel $customModel -BaseUrl $baseUrl | Out-Null
                Set-NonSecret $Progress "chat_model" $(if ($customModel) { $customModel } else { $chat })
                Set-NonSecret $Progress "image_model" $image
                Set-StepValue $Progress "models" "success"
            }
            Save-DragonAIOnboardingProgress $Progress
        }
        $start = "email"
    }

    # EMAIL
    if ($start -eq "email" -or ($Force -and $start -ne "done")) {
        if ((Get-StepValue $Progress "email") -ne "success" -or $Force) {
            Write-Host ""
            Write-Host "--- Connect email ---"
            Write-Host "  [1] Gmail (App Password)  [2] Outlook/Microsoft 365  [3] Generic SMTP  [S] Skip for now"
            $choice = Read-Host "Provider"
            if ($choice -match '^[Ss]') {
                Set-StepValue $Progress "email" "skipped"
                Save-DragonAIOnboardingProgress $Progress
                Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
            } else {
                $provider = switch ($choice) {
                    "1" { "gmail" }
                    "2" { "outlook" }
                    default { "smtp" }
                }
                if ($provider -eq "gmail") {
                    Write-Host "Gmail: create an App Password at https://myaccount.google.com/apppasswords"
                    try { Start-Process "https://myaccount.google.com/apppasswords" } catch {}
                    $smtpHost = "smtp.gmail.com"; $smtpPort = 587; $ssl = $true
                } elseif ($provider -eq "outlook") {
                    Write-Host "Outlook: app password or SMTP auth for smtp.office365.com"
                    $smtpHost = "smtp.office365.com"; $smtpPort = 587; $ssl = $true
                } else {
                    $smtpHost = Read-Host "SMTP host"
                    $smtpPort = [int](Read-Host "SMTP port (e.g. 587)")
                    $sslAns = Read-Host "Enable SSL/TLS? [Y/n]"
                    $ssl = -not ($sslAns -match '^[Nn]')
                }
                $from = Read-Host "From address"
                $disp = Read-Host "Display name"
                $user = Read-Host "Username (often same as from)"
                $pass = Read-Host "Password / App Password"
                Write-Host "Verifying SMTP..."
                $r = Test-SmtpSend -HostName $smtpHost -Port $smtpPort -EnableSsl $ssl -Username $user -Password $pass -FromAddress $from -DisplayName $disp
                Write-Host $r.Message
                if ($r.Ok) {
                    Save-DragonAISecret -Name "email_password" -PlainText $pass
                    Set-NonSecret $Progress "email_from_address" $from
                    Set-NonSecret $Progress "email_display_name" $disp
                    Set-NonSecret $Progress "email_username" $user
                    Set-NonSecret $Progress "email_smtp_host" $smtpHost
                    Set-NonSecret $Progress "email_smtp_port" $smtpPort
                    Set-NonSecret $Progress "email_smtp_ssl" $ssl
                    Set-NonSecret $Progress "email_provider" $provider
                    Set-StepValue $Progress "email" "success"
                } else {
                    Set-StepValue $Progress "email" "failed"
                }
                Save-DragonAIOnboardingProgress $Progress
                Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
            }
        }
        $start = "crm"
    }

    # CRM
    if ($start -eq "crm" -or $Force) {
        if ((Get-StepValue $Progress "crm") -ne "success" -or $Force) {
            Write-Host ""
            Write-Host "--- Connect CRM (Vtiger) ---"
            $skip = Read-Host "Skip for now? [y/N]"
            if ($skip -match '^[Yy]') {
                Set-StepValue $Progress "crm" "skipped"
            } else {
                $url = Read-Host "Vtiger URL (e.g. https://crm.example.com)"
                $user = Read-Host "Username"
                $key = Read-Host "Access key (or password)"
                Write-Host "Verifying CRM..."
                $r = Test-VtigerLogin -BaseUrl $url -Username $user -AccessKey $key
                Write-Host $r.Message
                if ($r.Ok) {
                    Save-DragonAISecret -Name "crm_access_key" -PlainText $key
                    Set-NonSecret $Progress "crm_url" $url
                    Set-NonSecret $Progress "crm_username" $user
                    Set-StepValue $Progress "crm" "success"
                } else {
                    Set-StepValue $Progress "crm" "failed"
                }
            }
            Save-DragonAIOnboardingProgress $Progress
            Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
        }
        $start = "telephony"
    }

    # TELEPHONY
    if ($start -eq "telephony" -or $Force) {
        if ((Get-StepValue $Progress "telephony") -ne "success" -or $Force) {
            Write-Host ""
            Write-Host "--- Connect telephony ---"
            $skip = Read-Host "Skip for now? [y/N]"
            if ($skip -match '^[Yy]') {
                Set-StepValue $Progress "telephony" "skipped"
            } else {
                $sid = Read-Host "Twilio Account SID"
                $tok = Read-Host "Twilio Auth Token"
                $from = Read-Host "Twilio From phone (E.164)"
                Write-Host "Voice provider (at least one):"
                $bland = Read-Host "Bland API key (or Enter to skip)"
                $vapi = Read-Host "Vapi API key (or Enter to skip)"
                if ([string]::IsNullOrWhiteSpace($bland) -and [string]::IsNullOrWhiteSpace($vapi)) {
                    Write-Host "WARNING: No Bland/Vapi key - storing Twilio only; voice AI may need setup later." "WARN"
                }
                Write-Host "Verifying Twilio..."
                $r = Test-TwilioAccount -AccountSid $sid -AuthToken $tok
                Write-Host $r.Message
                if ($r.Ok) {
                    Save-DragonAISecret -Name "twilio_auth_token" -PlainText $tok
                    if ($bland) { Save-DragonAISecret -Name "bland_api_key" -PlainText $bland }
                    if ($vapi) { Save-DragonAISecret -Name "vapi_api_key" -PlainText $vapi }
                    Set-NonSecret $Progress "twilio_account_sid" $sid
                    Set-NonSecret $Progress "twilio_from_phone" $from
                    $vp = if ($bland) { "bland" } elseif ($vapi) { "vapi" } else { "twilio-only" }
                    Set-NonSecret $Progress "voice_provider" $vp
                    $doCall = Read-Host "Place a test call? Enter destination number or leave blank to skip"
                    if (-not [string]::IsNullOrWhiteSpace($doCall)) {
                        $cr = Invoke-TwilioTestCall -AccountSid $sid -AuthToken $tok -FromPhone $from -ToPhone $doCall
                        Write-Host $cr.Message
                    } else {
                        Write-Host "Test call skipped (Twilio account still validated)."
                    }
                    Set-StepValue $Progress "telephony" "success"
                } else {
                    Set-StepValue $Progress "telephony" "failed"
                }
            }
            Save-DragonAIOnboardingProgress $Progress
            Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
        }
        $start = "property_data"
    }

    # OPTIONAL property-data
    if ($start -eq "property_data" -or $Force) {
        if ((Get-StepValue $Progress "property_data") -ne "success" -and (Get-StepValue $Progress "property_data") -ne "skipped") {
            Write-Host ""
            Write-Host "--- Optional: property data ---"
            $skip = Read-Host "Skip for now? [Y/n]"
            if (-not ($skip -match '^[Nn]')) {
                Set-StepValue $Progress "property_data" "skipped"
            } else {
                $base = Read-Host "Property data API base URL"
                $key = Read-Host "API key"
                if ($key) { Save-DragonAISecret -Name "property_data_api_key" -PlainText $key }
                Set-NonSecret $Progress "property_data_base_url" $base
                Set-StepValue $Progress "property_data" "success"
            }
            Save-DragonAIOnboardingProgress $Progress
        }
        $start = "dialer"
    }

    # OPTIONAL dialer
    if ($start -eq "dialer" -or $Force) {
        if ((Get-StepValue $Progress "dialer") -ne "success" -and (Get-StepValue $Progress "dialer") -ne "skipped") {
            Write-Host ""
            Write-Host "--- Optional: dialer API ---"
            $skip = Read-Host "Skip for now? [Y/n]"
            if (-not ($skip -match '^[Nn]')) {
                Set-StepValue $Progress "dialer" "skipped"
            } else {
                $base = Read-Host "Dialer API base URL"
                $key = Read-Host "API key"
                $fn = Read-Host "From number (optional)"
                if ($key) { Save-DragonAISecret -Name "dialer_api_key" -PlainText $key }
                Set-NonSecret $Progress "dialer_base_url" $base
                Set-NonSecret $Progress "dialer_from_number" $fn
                Set-StepValue $Progress "dialer" "success"
            }
            Save-DragonAIOnboardingProgress $Progress
        }
        $start = "review"
    }

    # REVIEW
    Write-Host ""
    Write-Host "--- Review (no secrets shown) ---"
    Show-ConsoleStatus "Welcome" (Get-StepValue $Progress "welcome")
    Show-ConsoleStatus "Models" (Get-StepValue $Progress "models")
    $reviewChat = Get-MapValue -Map $Progress.nonSecret -Name "chat_model" -Default ""
    if ($reviewChat) {
        Write-Host "  Default chat LLM (all bots inherit): $reviewChat"
    }
    Show-ConsoleStatus "Email" (Get-StepValue $Progress "email")
    Show-ConsoleStatus "CRM" (Get-StepValue $Progress "crm")
    Show-ConsoleStatus "Telephony" (Get-StepValue $Progress "telephony")
    Show-ConsoleStatus "Property data" (Get-StepValue $Progress "property_data")
    Show-ConsoleStatus "Dialer" (Get-StepValue $Progress "dialer")
    Set-StepValue $Progress "review" "success"
    $Progress.profileId = $ProfId
    Save-DragonAIOnboardingProgress $Progress
    Write-ConnectorPlaceholders -Progress $Progress -ProfId $ProfId
    $botStatus = Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress
    Write-Host ""
    Write-Host "Bot readiness: $($botStatus.reason)"
    Write-Host "Setup guide: $(Join-Path $InstallRoot 'docs\airmaze\SETUP_GUIDE.md')"
    Write-WizardLog "Console wizard finished"
    return 0
}

# ============================================================================
# WINFORMS UI
# ============================================================================

function New-BrandButton {
    param([string]$Text, [Drawing.Point]$Location, [Drawing.Size]$Size, [switch]$Primary)
    $b = New-Object Windows.Forms.Button
    $b.Text = $Text
    $b.Location = $Location
    $b.Size = $Size
    $b.FlatStyle = [Windows.Forms.FlatStyle]::Flat
    $b.ForeColor = $script:BrandText
    if ($Primary) {
        $b.BackColor = $script:BrandRed
        $b.FlatAppearance.BorderColor = $script:BrandRed
    } else {
        $b.BackColor = $script:BrandPanel
        $b.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(80, 80, 90)
    }
    $b.Font = New-Object Drawing.Font("Segoe UI", 10)
    return $b
}

function New-BrandLabel {
    param([string]$Text, [Drawing.Point]$Location, [int]$Width = 520, [int]$Height = 24, [switch]$Muted, [switch]$Title)
    $l = New-Object Windows.Forms.Label
    $l.Text = $Text
    $l.Location = $Location
    $l.Size = New-Object Drawing.Size($Width, $Height)
    $l.ForeColor = if ($Muted) { $script:BrandMuted } else { $script:BrandText }
    $l.BackColor = [System.Drawing.Color]::Transparent
    if ($Title) {
        $l.Font = New-Object Drawing.Font("Segoe UI", 14, [Drawing.FontStyle]::Bold)
    } else {
        $l.Font = New-Object Drawing.Font("Segoe UI", 9)
    }
    return $l
}

function New-BrandTextBox {
    param([Drawing.Point]$Location, [int]$Width = 360, [switch]$Password)
    $t = New-Object Windows.Forms.TextBox
    $t.Location = $Location
    $t.Width = $Width
    $t.BackColor = [System.Drawing.Color]::FromArgb(50, 50, 58)
    $t.ForeColor = $script:BrandText
    $t.BorderStyle = [Windows.Forms.BorderStyle]::FixedSingle
    if ($Password) { $t.UseSystemPasswordChar = $true }
    return $t
}

function Update-StatusStrip {
    param($Panel, $Progress)
    if ($null -eq $Panel) { return }
    $Panel.Controls.Clear()
    $lbl = New-Object Windows.Forms.Label
    Set-WizardControlText -Target $lbl -Value (Format-WizardStatusLine -Progress $Progress) | Out-Null
    $lbl.Location = New-Object Drawing.Point(12, 4)
    $lbl.AutoSize = $true
    $lbl.ForeColor = if ($script:BrandText) { $script:BrandText } else { [System.Drawing.Color]::FromArgb(240, 240, 245) }
    $lbl.Font = New-Object Drawing.Font("Segoe UI", 9)
    [void]$Panel.Controls.Add($lbl)
}

function Invoke-WinFormsWizard {
    param($Progress, [string]$ProfId)

    if (-not (Initialize-WizardWinForms)) {
        throw "WinForms/System.Drawing is not available."
    }
    if ($null -eq $script:BrandBack) {
        throw "Brand colors were not initialized (System.Drawing.Color missing)."
    }

    $script:WizResult = 0
    $script:CurrentStep = Get-FirstIncompleteStep -Progress $Progress
    if ($SkipWelcome -and $script:CurrentStep -eq "welcome") { $script:CurrentStep = "models" }
    if ($Force) { $script:CurrentStep = "welcome" }

    $form = New-Object Windows.Forms.Form
    $form.Text = "Dragon AI Agent Setup"
    $form.Size = New-Object Drawing.Size(720, 560)
    $form.StartPosition = "CenterScreen"
    $form.BackColor = $script:BrandBack
    $form.ForeColor = $script:BrandText
    $form.FormBorderStyle = [Windows.Forms.FormBorderStyle]::FixedDialog
    $form.MaximizeBox = $false
    $form.MinimizeBox = $true

    $header = New-Object Windows.Forms.Panel
    $header.Location = New-Object Drawing.Point(0, 0)
    $header.Size = New-Object Drawing.Size(720, 72)
    $header.BackColor = $script:BrandBlue
    $form.Controls.Add($header)

    $logoPath = Join-Path $InstallRoot "branding\dragon-ai-agent-logo.png"
    if (-not (Test-Path $logoPath)) { $logoPath = Join-Path $InstallRoot "dragon-ai-agent-logo.png" }
    if (Test-Path -LiteralPath $logoPath) {
        try {
            $pic = New-Object Windows.Forms.PictureBox
            $pic.Image = [Drawing.Image]::FromFile($logoPath)
            $pic.SizeMode = [Windows.Forms.PictureBoxSizeMode]::Zoom
            $pic.Location = New-Object Drawing.Point(12, 8)
            $pic.Size = New-Object Drawing.Size(56, 56)
            $header.Controls.Add($pic)
        } catch {}
    }

    $hdrTitle = New-BrandLabel -Text $ProductName -Location (New-Object Drawing.Point(80, 12)) -Width 500 -Height 28 -Title
    $hdrTitle.ForeColor = [System.Drawing.Color]::White
    $header.Controls.Add($hdrTitle)
    $hdrSub = New-BrandLabel -Text "Dragon AI Agent first-run setup - bot group: $ProfId" -Location (New-Object Drawing.Point(80, 40)) -Width 500 -Height 22
    $hdrSub.ForeColor = $script:BrandText
    $header.Controls.Add($hdrSub)

    $statusStrip = New-Object Windows.Forms.Panel
    $statusStrip.Location = New-Object Drawing.Point(0, 72)
    $statusStrip.Size = New-Object Drawing.Size(720, 28)
    $statusStrip.BackColor = $script:BrandPanel
    $form.Controls.Add($statusStrip)

    $content = New-Object Windows.Forms.Panel
    $content.Location = New-Object Drawing.Point(0, 100)
    $content.Size = New-Object Drawing.Size(720, 360)
    $content.BackColor = $script:BrandBack
    $form.Controls.Add($content)

    $footer = New-Object Windows.Forms.Panel
    $footer.Location = New-Object Drawing.Point(0, 460)
    $footer.Size = New-Object Drawing.Size(720, 60)
    $footer.BackColor = $script:BrandPanel
    $form.Controls.Add($footer)

    $msgLabel = New-BrandLabel -Text "" -Location (New-Object Drawing.Point(12, 18)) -Width 400 -Height 28
    $footer.Controls.Add($msgLabel)
    $script:WizMsgLabel = $msgLabel
    $script:WizProgress = $Progress
    $script:WizForm = $form
    $script:WizProfId = $ProfId

    function Clear-Content { $content.Controls.Clear() }

    function Show-StepWelcome {
        Clear-Content
        Update-StatusStrip $statusStrip $Progress
        $content.Controls.Add((New-BrandLabel -Text "Welcome to Dragon AI Agent" -Location (New-Object Drawing.Point(40, 24)) -Width 600 -Height 32 -Title))
        $pitch = @"
Dragon AI Agent runs business-ready bots on this Windows PC with an embedded gateway.

Real Estate flow: Lead Sourcer -> Email Warmer -> consent gate -> calling.
Secrets stay on this machine (Windows DPAPI). This software is not legal advice.
"@
        $content.Controls.Add((New-BrandLabel -Text $pitch -Location (New-Object Drawing.Point(40, 70)) -Width 620 -Height 80 -Muted))
        $content.Controls.Add((New-BrandLabel -Text "Open Teams Marketplace anytime from the Dragon AI sidebar (or Bot Groups). Applied bots file under that team name, not Unassigned." -Location (New-Object Drawing.Point(40, 150)) -Width 620 -Height 36 -Muted))

        $btnContinue = New-BrandButton -Text "Continue" -Location (New-Object Drawing.Point(40, 200)) -Size (New-Object Drawing.Size(140, 36)) -Primary
        $btnSkip = New-BrandButton -Text "Skip wizard" -Location (New-Object Drawing.Point(200, 200)) -Size (New-Object Drawing.Size(140, 36))
        $btnTeams = New-BrandButton -Text "Teams Marketplace" -Location (New-Object Drawing.Point(360, 200)) -Size (New-Object Drawing.Size(200, 36))
        $content.Controls.Add($btnTeams)
        $btnTeams.Add_Click({
            $select = Join-Path $InstallRoot "scripts\airmaze\Select-BotGroup.ps1"
            if (-not (Test-Path -LiteralPath $select)) { $select = Join-Path $scriptDir "Select-BotGroup.ps1" }
            if (Test-Path -LiteralPath $select) {
                Start-Process -FilePath (Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe") -ArgumentList @("-STA", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $select, "-InstallRoot", $InstallRoot, "-PayloadRoot", $PayloadRoot) -WindowStyle Normal | Out-Null
            }
        })
        $content.Controls.Add($btnContinue)
        $content.Controls.Add($btnSkip)

        $btnContinue.Add_Click({
            Set-StepValue $Progress "welcome" "success"
            $Progress.profileId = $ProfId
            $Progress.skipped = $false
            Save-DragonAIOnboardingProgress $Progress
            Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
            $script:CurrentStep = "models"
            Show-CurrentStep
        })
        $btnSkip.Add_Click({
            $Progress.skipped = $true
            $Progress.profileId = $ProfId
            Set-StepValue $Progress "welcome" "skipped"
            Save-DragonAIOnboardingProgress $Progress
            Invoke-ApplyGatewayModels -IfMissing | Out-Null
            Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
            Write-WizardLog "Wizard skipped (WinForms)"
            $script:WizResult = 0
            if ($script:WizForm) { $script:WizForm.Close() } else { $form.Close() }
        })
    }

    function Show-StepModels {
        Clear-Content
        Update-StatusStrip $statusStrip $Progress
        $content.Controls.Add((New-BrandLabel -Text "Default chat LLM and image LLM" -Location (New-Object Drawing.Point(40, 8)) -Width 620 -Height 26 -Title))
        $content.Controls.Add((New-BrandLabel -Text "Suggested default is Grok (xAI). Cloud picks reuse keys already on this PC (XAI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY). Self-hosted asks for a base URL and model id." -Location (New-Object Drawing.Point(40, 36)) -Width 620 -Height 36 -Muted))

        $chatRows = @(Get-WizardChatCatalog)
        $imageRows = @(Get-WizardImageCatalog)
        $script:WizChatCatalog = $chatRows
        $script:WizImageCatalog = $imageRows

        $content.Controls.Add((New-BrandLabel -Text "Default chat LLM" -Location (New-Object Drawing.Point(40, 76)) -Width 240 -Height 18 -Muted))
        $cbChat = New-Object Windows.Forms.ComboBox
        $cbChat.DropDownStyle = [Windows.Forms.ComboBoxStyle]::DropDownList
        $cbChat.Location = New-Object Drawing.Point(40, 94)
        $cbChat.Size = New-Object Drawing.Size(440, 26)
        $cbChat.BackColor = [System.Drawing.Color]::FromArgb(50, 50, 58)
        $cbChat.ForeColor = $script:BrandText
        foreach ($row in $chatRows) { [void]$cbChat.Items.Add($row.label) }
        $cbChat.SelectedIndex = 0
        $content.Controls.Add($cbChat)

        $content.Controls.Add((New-BrandLabel -Text "Default image LLM" -Location (New-Object Drawing.Point(40, 124)) -Width 240 -Height 18 -Muted))
        $cbImage = New-Object Windows.Forms.ComboBox
        $cbImage.DropDownStyle = [Windows.Forms.ComboBoxStyle]::DropDownList
        $cbImage.Location = New-Object Drawing.Point(40, 142)
        $cbImage.Size = New-Object Drawing.Size(440, 26)
        $cbImage.BackColor = [System.Drawing.Color]::FromArgb(50, 50, 58)
        $cbImage.ForeColor = $script:BrandText
        foreach ($row in $imageRows) { [void]$cbImage.Items.Add($row.label) }
        $cbImage.SelectedIndex = 0
        $content.Controls.Add($cbImage)

        $customPanel = New-Object Windows.Forms.Panel
        $customPanel.Location = New-Object Drawing.Point(40, 174)
        $customPanel.Size = New-Object Drawing.Size(620, 88)
        $customPanel.BackColor = $script:BrandBack
        $customPanel.Visible = $false
        $customPanel.Controls.Add((New-BrandLabel -Text "Base URL" -Location (New-Object Drawing.Point(0, 4)) -Width 120 -Height 18 -Muted))
        $tbBase = New-BrandTextBox -Location (New-Object Drawing.Point(130, 2)) -Width 460
        $tbBase.Text = "http://127.0.0.1:11434/v1"
        $customPanel.Controls.Add($tbBase)
        $customPanel.Controls.Add((New-BrandLabel -Text "Model id" -Location (New-Object Drawing.Point(0, 32)) -Width 120 -Height 18 -Muted))
        $tbCustomModel = New-BrandTextBox -Location (New-Object Drawing.Point(130, 30)) -Width 460
        $tbCustomModel.Text = "local-model"
        $customPanel.Controls.Add($tbCustomModel)
        $customPanel.Controls.Add((New-BrandLabel -Text "API key" -Location (New-Object Drawing.Point(0, 60)) -Width 120 -Height 18 -Muted))
        $tbCustomKey = New-BrandTextBox -Location (New-Object Drawing.Point(130, 58)) -Width 460 -Password
        $customPanel.Controls.Add($tbCustomKey)
        $content.Controls.Add($customPanel)

        $content.Controls.Add((New-BrandLabel -Text "Writes into the embedded gateway so chat and Generate work. All bots inherit this chat model unless you override a bot. API keys stay on this PC (env or DPAPI), never in config.yaml." -Location (New-Object Drawing.Point(40, 266)) -Width 620 -Height 40 -Muted))

        $btnContinue = New-BrandButton -Text "Continue" -Location (New-Object Drawing.Point(40, 308)) -Size (New-Object Drawing.Size(140, 36)) -Primary
        $btnSkip = New-BrandButton -Text "Skip for now" -Location (New-Object Drawing.Point(200, 308)) -Size (New-Object Drawing.Size(140, 36))
        $content.Controls.Add($btnContinue)
        $content.Controls.Add($btnSkip)

        $script:WizChatBox = $cbChat
        $script:WizImageBox = $cbImage
        $script:WizCustomPanel = $customPanel
        $script:WizBaseUrlBox = $tbBase
        $script:WizCustomModelBox = $tbCustomModel
        $script:WizCustomKeyBox = $tbCustomKey

        $cbChat.Add_SelectedIndexChanged({
            $show = $false
            if ($script:WizChatBox -and $script:WizChatCatalog -and $script:WizChatBox.SelectedIndex -ge 0 -and $script:WizChatBox.SelectedIndex -lt $script:WizChatCatalog.Count) {
                $show = ([string]$script:WizChatCatalog[$script:WizChatBox.SelectedIndex].id -eq "self-hosted")
            }
            if ($script:WizCustomPanel) { $script:WizCustomPanel.Visible = $show }
        })

        $btnContinue.Add_Click({
            $chatIdx = 0
            $imgIdx = 0
            if ($script:WizChatBox) { $chatIdx = [int]$script:WizChatBox.SelectedIndex }
            if ($script:WizImageBox) { $imgIdx = [int]$script:WizImageBox.SelectedIndex }
            $chat = "grok-4.7"
            if ($script:WizChatCatalog -and $chatIdx -ge 0 -and $chatIdx -lt $script:WizChatCatalog.Count) {
                $chat = [string]$script:WizChatCatalog[$chatIdx].id
            }
            $image = "grok-imagine-image"
            if ($script:WizImageCatalog -and $imgIdx -ge 0 -and $imgIdx -lt $script:WizImageCatalog.Count) {
                $image = [string]$script:WizImageCatalog[$imgIdx].id
            }
            $customModel = ""
            $baseUrl = ""
            if ($chat -eq "self-hosted") {
                if ($script:WizBaseUrlBox) { $baseUrl = [string]$script:WizBaseUrlBox.Text }
                if ($script:WizCustomModelBox) { $customModel = [string]$script:WizCustomModelBox.Text }
                if ([string]::IsNullOrWhiteSpace($baseUrl) -or [string]::IsNullOrWhiteSpace($customModel)) {
                    Set-WizardMessage "Self-hosted needs a base URL and a model id."
                    return
                }
                $key = ""
                if ($script:WizCustomKeyBox) { $key = [string]$script:WizCustomKeyBox.Text }
                if (-not [string]::IsNullOrWhiteSpace($key)) {
                    Save-DragonAISecret -Name "chat_api_key" -PlainText $key
                }
                Set-NonSecret $script:WizProgress "chat_base_url" $baseUrl
                Set-NonSecret $script:WizProgress "chat_provider" "custom"
            }
            Set-WizardMessage "Writing Dragon AI Agent model defaults..."
            Invoke-ApplyGatewayModels -Chat $chat -Image $image -CustomModel $customModel -BaseUrl $baseUrl | Out-Null
            Set-NonSecret $script:WizProgress "chat_model" $(if ($customModel) { $customModel } else { $chat })
            Set-NonSecret $script:WizProgress "image_model" $image
            Set-StepValue $script:WizProgress "models" "success"
            Save-DragonAIOnboardingProgress $script:WizProgress
            $script:CurrentStep = "email"
            Show-CurrentStep
        })
        $btnSkip.Add_Click({
            Invoke-ApplyGatewayModels -IfMissing | Out-Null
            Set-StepValue $script:WizProgress "models" "skipped"
            Save-DragonAIOnboardingProgress $script:WizProgress
            $script:CurrentStep = "email"
            Show-CurrentStep
        })
    }

    function Show-StepEmail {
        Clear-Content
        Update-StatusStrip $statusStrip $Progress
        $content.Controls.Add((New-BrandLabel -Text "Connect email" -Location (New-Object Drawing.Point(40, 8)) -Width 600 -Height 28 -Title))

        $rbGmail = New-Object Windows.Forms.RadioButton
        $rbGmail.Text = "Gmail (App Password / OAuth instructions)"
        $rbGmail.Location = New-Object Drawing.Point(40, 44)
        $rbGmail.Size = New-Object Drawing.Size(400, 22)
        $rbGmail.ForeColor = $script:BrandText
        $rbGmail.Checked = $true
        $rbOutlook = New-Object Windows.Forms.RadioButton
        $rbOutlook.Text = "Outlook / Microsoft 365"
        $rbOutlook.Location = New-Object Drawing.Point(40, 68)
        $rbOutlook.Size = New-Object Drawing.Size(400, 22)
        $rbOutlook.ForeColor = $script:BrandText
        $rbSmtp = New-Object Windows.Forms.RadioButton
        $rbSmtp.Text = "Generic SMTP"
        $rbSmtp.Location = New-Object Drawing.Point(40, 92)
        $rbSmtp.Size = New-Object Drawing.Size(400, 22)
        $rbSmtp.ForeColor = $script:BrandText
        $content.Controls.Add($rbGmail); $content.Controls.Add($rbOutlook); $content.Controls.Add($rbSmtp)

        $y = 120
        $content.Controls.Add((New-BrandLabel -Text "From address" -Location (New-Object Drawing.Point(40, $y)) -Width 140 -Height 20 -Muted))
        $tbFrom = New-BrandTextBox -Location (New-Object Drawing.Point(190, ($y - 2))) -Width 300
        $content.Controls.Add($tbFrom); $y += 28
        $content.Controls.Add((New-BrandLabel -Text "Display name" -Location (New-Object Drawing.Point(40, $y)) -Width 140 -Height 20 -Muted))
        $tbDisp = New-BrandTextBox -Location (New-Object Drawing.Point(190, ($y - 2))) -Width 300
        $content.Controls.Add($tbDisp); $y += 28
        $content.Controls.Add((New-BrandLabel -Text "Username" -Location (New-Object Drawing.Point(40, $y)) -Width 140 -Height 20 -Muted))
        $tbUser = New-BrandTextBox -Location (New-Object Drawing.Point(190, ($y - 2))) -Width 300
        $content.Controls.Add($tbUser); $y += 28
        $content.Controls.Add((New-BrandLabel -Text "Password" -Location (New-Object Drawing.Point(40, $y)) -Width 140 -Height 20 -Muted))
        $tbPass = New-BrandTextBox -Location (New-Object Drawing.Point(190, ($y - 2))) -Width 300 -Password
        $content.Controls.Add($tbPass); $y += 28
        $content.Controls.Add((New-BrandLabel -Text "SMTP host" -Location (New-Object Drawing.Point(40, $y)) -Width 140 -Height 20 -Muted))
        $tbHost = New-BrandTextBox -Location (New-Object Drawing.Point(190, ($y - 2))) -Width 200
        $tbHost.Text = "smtp.gmail.com"
        $content.Controls.Add($tbHost)
        $content.Controls.Add((New-BrandLabel -Text "Port" -Location (New-Object Drawing.Point(410, $y)) -Width 40 -Height 20 -Muted))
        $tbPort = New-BrandTextBox -Location (New-Object Drawing.Point(450, ($y - 2))) -Width 60
        $tbPort.Text = "587"
        $content.Controls.Add($tbPort); $y += 28
        $cbSsl = New-Object Windows.Forms.CheckBox
        $cbSsl.Text = "SSL / TLS"
        $cbSsl.Checked = $true
        $cbSsl.Location = New-Object Drawing.Point(190, $y)
        $cbSsl.ForeColor = $script:BrandText
        $content.Controls.Add($cbSsl)

        $rbGmail.Add_CheckedChanged({
            if ($rbGmail.Checked) { $tbHost.Text = "smtp.gmail.com"; $tbPort.Text = "587"; $cbSsl.Checked = $true }
        }.GetNewClosure())
        $rbOutlook.Add_CheckedChanged({
            if ($rbOutlook.Checked) { $tbHost.Text = "smtp.office365.com"; $tbPort.Text = "587"; $cbSsl.Checked = $true }
        }.GetNewClosure())

        $lnk = New-Object Windows.Forms.LinkLabel
        $lnk.Text = "Open Google App Passwords"
        $lnk.Location = New-Object Drawing.Point(450, 44)
        $lnk.AutoSize = $true
        $lnk.LinkColor = [System.Drawing.Color]::FromArgb(255, 180, 180)
        $lnk.Add_Click({ try { Start-Process "https://myaccount.google.com/apppasswords" } catch {} })
        $content.Controls.Add($lnk)

        $btnVerify = New-BrandButton -Text "Verify" -Location (New-Object Drawing.Point(40, 310)) -Size (New-Object Drawing.Size(100, 32)) -Primary
        $btnSkip = New-BrandButton -Text "Skip for now" -Location (New-Object Drawing.Point(160, 310)) -Size (New-Object Drawing.Size(120, 32))
        $btnNext = New-BrandButton -Text "Next" -Location (New-Object Drawing.Point(560, 310)) -Size (New-Object Drawing.Size(100, 32))
        $content.Controls.Add($btnVerify); $content.Controls.Add($btnSkip); $content.Controls.Add($btnNext)

        $btnVerify.Add_Click({
            $provider = if ($rbGmail.Checked) { "gmail" } elseif ($rbOutlook.Checked) { "outlook" } else { "smtp" }
            $portNum = 587
            [void][int]::TryParse($tbPort.Text, [ref]$portNum)
            Set-WizardMessage "Sending test email..."
            if ($script:WizForm) { $script:WizForm.Refresh() }
            $r = Test-SmtpSend -HostName $tbHost.Text -Port $portNum -EnableSsl $cbSsl.Checked `
                -Username $tbUser.Text -Password $tbPass.Text -FromAddress $tbFrom.Text -DisplayName $tbDisp.Text
            Set-WizardMessage $r.Message
            if ($r.Ok) {
                Save-DragonAISecret -Name "email_password" -PlainText $tbPass.Text
                Set-NonSecret $Progress "email_from_address" $tbFrom.Text
                Set-NonSecret $Progress "email_display_name" $tbDisp.Text
                Set-NonSecret $Progress "email_username" $tbUser.Text
                Set-NonSecret $Progress "email_smtp_host" $tbHost.Text
                Set-NonSecret $Progress "email_smtp_port" $portNum
                Set-NonSecret $Progress "email_smtp_ssl" $cbSsl.Checked
                Set-NonSecret $Progress "email_provider" $provider
                Set-StepValue $Progress "email" "success"
            } else {
                Set-StepValue $Progress "email" "failed"
            }
            Save-DragonAIOnboardingProgress $Progress
            Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
            Update-StatusStrip $statusStrip $Progress
        }.GetNewClosure())

        $btnSkip.Add_Click({
            Set-StepValue $Progress "email" "skipped"
            Save-DragonAIOnboardingProgress $Progress
            Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
            $script:CurrentStep = "crm"
            Show-CurrentStep
        }.GetNewClosure())

        $btnNext.Add_Click({
            $script:CurrentStep = "crm"
            Show-CurrentStep
        }.GetNewClosure())
    }

    function Show-StepCrm {
        Clear-Content
        Update-StatusStrip $statusStrip $Progress
        $content.Controls.Add((New-BrandLabel -Text "Connect CRM (Vtiger)" -Location (New-Object Drawing.Point(40, 16)) -Width 600 -Height 28 -Title))
        $y = 60
        $content.Controls.Add((New-BrandLabel -Text "Vtiger URL" -Location (New-Object Drawing.Point(40, $y)) -Width 140 -Height 20 -Muted))
        $tbUrl = New-BrandTextBox -Location (New-Object Drawing.Point(190, ($y - 2))) -Width 400
        $content.Controls.Add($tbUrl); $y += 32
        $content.Controls.Add((New-BrandLabel -Text "Username" -Location (New-Object Drawing.Point(40, $y)) -Width 140 -Height 20 -Muted))
        $tbUser = New-BrandTextBox -Location (New-Object Drawing.Point(190, ($y - 2))) -Width 300
        $content.Controls.Add($tbUser); $y += 32
        $content.Controls.Add((New-BrandLabel -Text "Access key" -Location (New-Object Drawing.Point(40, $y)) -Width 140 -Height 20 -Muted))
        $tbKey = New-BrandTextBox -Location (New-Object Drawing.Point(190, ($y - 2))) -Width 300 -Password
        $content.Controls.Add($tbKey)

        $btnVerify = New-BrandButton -Text "Verify" -Location (New-Object Drawing.Point(40, 200)) -Size (New-Object Drawing.Size(100, 32)) -Primary
        $btnSkip = New-BrandButton -Text "Skip for now" -Location (New-Object Drawing.Point(160, 200)) -Size (New-Object Drawing.Size(120, 32))
        $btnNext = New-BrandButton -Text "Next" -Location (New-Object Drawing.Point(560, 200)) -Size (New-Object Drawing.Size(100, 32))
        $content.Controls.Add($btnVerify); $content.Controls.Add($btnSkip); $content.Controls.Add($btnNext)

        $btnVerify.Add_Click({
            Set-WizardMessage "Checking CRM..."
            if ($script:WizForm) { $script:WizForm.Refresh() }
            $r = Test-VtigerLogin -BaseUrl $tbUrl.Text -Username $tbUser.Text -AccessKey $tbKey.Text
            Set-WizardMessage $r.Message
            if ($r.Ok) {
                Save-DragonAISecret -Name "crm_access_key" -PlainText $tbKey.Text
                Set-NonSecret $Progress "crm_url" $tbUrl.Text
                Set-NonSecret $Progress "crm_username" $tbUser.Text
                Set-StepValue $Progress "crm" "success"
            } else {
                Set-StepValue $Progress "crm" "failed"
            }
            Save-DragonAIOnboardingProgress $Progress
            Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
            Update-StatusStrip $statusStrip $Progress
        }.GetNewClosure())
        $btnSkip.Add_Click({
            Set-StepValue $Progress "crm" "skipped"
            Save-DragonAIOnboardingProgress $Progress
            Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
            $script:CurrentStep = "telephony"
            Show-CurrentStep
        }.GetNewClosure())
        $btnNext.Add_Click({ $script:CurrentStep = "telephony"; Show-CurrentStep }.GetNewClosure())
    }

    function Show-StepTelephony {
        Clear-Content
        Update-StatusStrip $statusStrip $Progress
        $content.Controls.Add((New-BrandLabel -Text "Connect telephony" -Location (New-Object Drawing.Point(40, 8)) -Width 600 -Height 28 -Title))
        $y = 44
        foreach ($pair in @(
            @{ l = "Twilio Account SID"; n = "sid" },
            @{ l = "Twilio Auth Token"; n = "tok"; p = $true },
            @{ l = "From phone (E.164)"; n = "from" },
            @{ l = "Bland API key"; n = "bland"; p = $true },
            @{ l = "Vapi API key"; n = "vapi"; p = $true },
            @{ l = "Test call to (optional)"; n = "dest" }
        )) {
            $content.Controls.Add((New-BrandLabel -Text $pair.l -Location (New-Object Drawing.Point(40, $y)) -Width 180 -Height 20 -Muted))
            $tb = New-BrandTextBox -Location (New-Object Drawing.Point(230, ($y - 2))) -Width 340 -Password:([bool]$pair.p)
            Set-Variable -Name ("tb_" + $pair.n) -Value $tb -Scope 1
            $content.Controls.Add($tb)
            $y += 28
        }

        $btnVerify = New-BrandButton -Text "Verify Twilio" -Location (New-Object Drawing.Point(40, 280)) -Size (New-Object Drawing.Size(120, 32)) -Primary
        $btnSkip = New-BrandButton -Text "Skip for now" -Location (New-Object Drawing.Point(180, 280)) -Size (New-Object Drawing.Size(120, 32))
        $btnNext = New-BrandButton -Text "Next" -Location (New-Object Drawing.Point(560, 280)) -Size (New-Object Drawing.Size(100, 32))
        $content.Controls.Add($btnVerify); $content.Controls.Add($btnSkip); $content.Controls.Add($btnNext)

        $btnVerify.Add_Click({
            if ([string]::IsNullOrWhiteSpace($tb_bland.Text) -and [string]::IsNullOrWhiteSpace($tb_vapi.Text)) {
                Set-WizardMessage "Warning: add Bland or Vapi key for voice AI (Twilio-only OK for now)."
            }
            Set-WizardMessage "Checking Twilio..."
            if ($script:WizForm) { $script:WizForm.Refresh() }
            $r = Test-TwilioAccount -AccountSid $tb_sid.Text -AuthToken $tb_tok.Text
            if ($r.Ok) {
                Save-DragonAISecret -Name "twilio_auth_token" -PlainText $tb_tok.Text
                if ($tb_bland.Text) { Save-DragonAISecret -Name "bland_api_key" -PlainText $tb_bland.Text }
                if ($tb_vapi.Text) { Save-DragonAISecret -Name "vapi_api_key" -PlainText $tb_vapi.Text }
                Set-NonSecret $Progress "twilio_account_sid" $tb_sid.Text
                Set-NonSecret $Progress "twilio_from_phone" $tb_from.Text
                $vp = if ($tb_bland.Text) { "bland" } elseif ($tb_vapi.Text) { "vapi" } else { "twilio-only" }
                Set-NonSecret $Progress "voice_provider" $vp
                if (-not [string]::IsNullOrWhiteSpace($tb_dest.Text)) {
                    $cr = Invoke-TwilioTestCall -AccountSid $tb_sid.Text -AuthToken $tb_tok.Text -FromPhone $tb_from.Text -ToPhone $tb_dest.Text
                    Set-WizardMessage "$($r.Message) $($cr.Message)"
                } else {
                    Set-WizardMessage "$($r.Message) (test call skipped)"
                }
                Set-StepValue $Progress "telephony" "success"
            } else {
                Set-WizardMessage $r.Message
                Set-StepValue $Progress "telephony" "failed"
            }
            Save-DragonAIOnboardingProgress $Progress
            Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
            Update-StatusStrip $statusStrip $Progress
        }.GetNewClosure())
        $btnSkip.Add_Click({
            Set-StepValue $Progress "telephony" "skipped"
            Save-DragonAIOnboardingProgress $Progress
            Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null
            $script:CurrentStep = "property_data"
            Show-CurrentStep
        }.GetNewClosure())
        $btnNext.Add_Click({ $script:CurrentStep = "property_data"; Show-CurrentStep }.GetNewClosure())
    }

    function Show-StepOptional {
        param([string]$Which)
        Clear-Content
        Update-StatusStrip $statusStrip $Progress
        $title = if ($Which -eq "property_data") { "Optional: property data API" } else { "Optional: dialer API" }
        $content.Controls.Add((New-BrandLabel -Text $title -Location (New-Object Drawing.Point(40, 16)) -Width 600 -Height 28 -Title))
        $content.Controls.Add((New-BrandLabel -Text "You can skip this and configure later." -Location (New-Object Drawing.Point(40, 52)) -Width 500 -Height 22 -Muted))

        $content.Controls.Add((New-BrandLabel -Text "Base URL" -Location (New-Object Drawing.Point(40, 90)) -Width 120 -Height 20 -Muted))
        $tbBase = New-BrandTextBox -Location (New-Object Drawing.Point(170, 88)) -Width 400
        $content.Controls.Add($tbBase)
        $content.Controls.Add((New-BrandLabel -Text "API key" -Location (New-Object Drawing.Point(40, 122)) -Width 120 -Height 20 -Muted))
        $tbKey = New-BrandTextBox -Location (New-Object Drawing.Point(170, 120)) -Width 400 -Password
        $content.Controls.Add($tbKey)
        $tbFrom = $null
        if ($Which -eq "dialer") {
            $content.Controls.Add((New-BrandLabel -Text "From number" -Location (New-Object Drawing.Point(40, 154)) -Width 120 -Height 20 -Muted))
            $tbFrom = New-BrandTextBox -Location (New-Object Drawing.Point(170, 152)) -Width 200
            $content.Controls.Add($tbFrom)
        }

        $btnSave = New-BrandButton -Text "Save" -Location (New-Object Drawing.Point(40, 220)) -Size (New-Object Drawing.Size(100, 32)) -Primary
        $btnSkip = New-BrandButton -Text "Skip for now" -Location (New-Object Drawing.Point(160, 220)) -Size (New-Object Drawing.Size(120, 32))
        $btnNext = New-BrandButton -Text "Next" -Location (New-Object Drawing.Point(560, 220)) -Size (New-Object Drawing.Size(100, 32))
        $content.Controls.Add($btnSave); $content.Controls.Add($btnSkip); $content.Controls.Add($btnNext)

        $btnSave.Add_Click({
            if ($Which -eq "property_data") {
                if ($tbKey.Text) { Save-DragonAISecret -Name "property_data_api_key" -PlainText $tbKey.Text }
                Set-NonSecret $Progress "property_data_base_url" $tbBase.Text
                Set-StepValue $Progress "property_data" "success"
                $script:CurrentStep = "dialer"
            } else {
                if ($tbKey.Text) { Save-DragonAISecret -Name "dialer_api_key" -PlainText $tbKey.Text }
                Set-NonSecret $Progress "dialer_base_url" $tbBase.Text
                if ($tbFrom) { Set-NonSecret $Progress "dialer_from_number" $tbFrom.Text }
                Set-StepValue $Progress "dialer" "success"
                $script:CurrentStep = "review"
            }
            Save-DragonAIOnboardingProgress $Progress
            Set-WizardMessage "Saved (secrets via DPAPI)."
            Show-CurrentStep
        }.GetNewClosure())
        $btnSkip.Add_Click({
            if ($Which -eq "property_data") {
                Set-StepValue $Progress "property_data" "skipped"
                $script:CurrentStep = "dialer"
            } else {
                Set-StepValue $Progress "dialer" "skipped"
                $script:CurrentStep = "review"
            }
            Save-DragonAIOnboardingProgress $Progress
            Show-CurrentStep
        }.GetNewClosure())
        $btnNext.Add_Click({
            if ($Which -eq "property_data") { $script:CurrentStep = "dialer" } else { $script:CurrentStep = "review" }
            Show-CurrentStep
        }.GetNewClosure())
    }

    function Show-StepReview {
        Clear-Content
        Update-StatusStrip $statusStrip $Progress
        $content.Controls.Add((New-BrandLabel -Text "Review & finish" -Location (New-Object Drawing.Point(40, 16)) -Width 600 -Height 28 -Title))
        $content.Controls.Add((New-BrandLabel -Text "Secret values are never shown here." -Location (New-Object Drawing.Point(40, 52)) -Width 500 -Height 22 -Muted))
        $y = 90
        foreach ($it in @(
            @{ n = "Welcome"; k = "welcome" },
            @{ n = "Models"; k = "models" },
            @{ n = "Email"; k = "email" },
            @{ n = "CRM"; k = "crm" },
            @{ n = "Telephony"; k = "telephony" },
            @{ n = "Property data"; k = "property_data" },
            @{ n = "Dialer"; k = "dialer" }
        )) {
            $st = Get-StepValue $Progress $it.k
            $color = switch ($st) {
                "success" { $script:BrandOk }
                "failed"  { $script:BrandFail }
                "skipped" { $script:BrandMuted }
                default   { $script:BrandPend }
            }
            $l = New-BrandLabel -Text ("{0}: {1}" -f $it.n, $st.ToUpper()) -Location (New-Object Drawing.Point(40, $y)) -Width 400 -Height 22
            $l.ForeColor = $color
            $content.Controls.Add($l)
            $y += 26
        }
        $reviewChat = Get-MapValue -Map $Progress.nonSecret -Name "chat_model" -Default ""
        $reviewImage = Get-MapValue -Map $Progress.nonSecret -Name "image_model" -Default ""
        if ($reviewChat -or $reviewImage) {
            $modelLine = "Default chat {0} (all bots inherit). Image {1}." -f $(if ($reviewChat) { $reviewChat } else { "grok-4.7" }), $(if ($reviewImage) { $reviewImage } else { "grok-imagine-image" })
            $content.Controls.Add((New-BrandLabel -Text $modelLine -Location (New-Object Drawing.Point(40, $y)) -Width 620 -Height 22 -Muted))
        }

        $btnFinish = New-BrandButton -Text "Finish" -Location (New-Object Drawing.Point(40, 280)) -Size (New-Object Drawing.Size(140, 36)) -Primary
        $content.Controls.Add($btnFinish)
        $btnFinish.Add_Click({
            Set-StepValue $Progress "review" "success"
            $Progress.profileId = $ProfId
            Save-DragonAIOnboardingProgress $Progress
            Write-ConnectorPlaceholders -Progress $Progress -ProfId $ProfId
            $bs = Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress
            Set-WizardMessage $bs.reason
            Write-WizardLog "WinForms wizard finished"
            [Windows.Forms.MessageBox]::Show(
                "$ProductName setup saved.`n`n$($bs.reason)`n`nSetup guide: $(Join-Path $InstallRoot 'docs\airmaze\SETUP_GUIDE.md')",
                "Dragon AI Agent Setup",
                [Windows.Forms.MessageBoxButtons]::OK,
                [Windows.Forms.MessageBoxIcon]::Information
            ) | Out-Null
            $script:WizResult = 0
            if ($script:WizForm) { $script:WizForm.Close() } else { $form.Close() }
        }.GetNewClosure())
    }

    function Show-CurrentStep {
        switch ($script:CurrentStep) {
            "welcome"       { Show-StepWelcome }
            "models"        { Show-StepModels }
            "email"         { Show-StepEmail }
            "crm"           { Show-StepCrm }
            "telephony"     { Show-StepTelephony }
            "property_data" { Show-StepOptional -Which "property_data" }
            "dialer"        { Show-StepOptional -Which "dialer" }
            "review"        { Show-StepReview }
            "done"          { Show-StepReview }
            default         { Show-StepWelcome }
        }
    }

    Show-CurrentStep
    [void]$form.ShowDialog()
    return $script:WizResult
}

function Invoke-WizardSelfTest {
    $failures = New-Object System.Collections.Generic.List[string]

    $progress = [pscustomobject]@{
        steps = [ordered]@{
            welcome       = "success"
            models        = "pending"
            email         = "pending"
            crm           = "pending"
            telephony     = "pending"
            property_data = "pending"
            dialer        = "pending"
        }
    }
    $line = Format-WizardStatusLine -Progress $progress
    $expected = "Welcome: OK / Models: pending"
    if ($line -ne $expected) {
        $failures.Add("Format-WizardStatusLine expected '$expected' got '$line'") | Out-Null
    }
    foreach ($banned in @("Email", "CRM", "Phone", "Dialer", "SUCCESS", "PENDING", "mail:", "ler:")) {
        if ($line.Contains($banned)) {
            $failures.Add("status line must not contain '$banned': $line") | Out-Null
        }
    }

    $bad = [pscustomobject]@{ Name = "not-a-control" }
    try {
        $set = Set-WizardControlText -Target $bad -Value "hello"
        if ($set) { $failures.Add("Set-WizardControlText must refuse PSCustomObject without Text") | Out-Null }
        if ($bad.PSObject.Properties["Text"]) { $failures.Add("must not add Text onto a bad object") | Out-Null }
    } catch {
        $failures.Add("Set-WizardControlText threw on PSCustomObject: $($_.Exception.Message)") | Out-Null
    }

    try {
        $setNull = Set-WizardControlText -Target $null -Value "x"
        if ($setNull) { $failures.Add("Set-WizardControlText must refuse null") | Out-Null }
    } catch {
        $failures.Add("Set-WizardControlText threw on null: $($_.Exception.Message)") | Out-Null
    }

    $ht = @{ Text = "existing" }
    try {
        $setHt = Set-WizardControlText -Target $ht -Value "overwrite"
        if ($setHt) { $failures.Add("Set-WizardControlText must refuse hashtable Text key") | Out-Null }
        if ([string]$ht.Text -eq "overwrite") { $failures.Add("must not overwrite hashtable Text key") | Out-Null }
    } catch {
        $failures.Add("Set-WizardControlText threw on hashtable: $($_.Exception.Message)") | Out-Null
    }

    $good = [pscustomobject]@{ Text = "old" }
    try {
        $setGood = Set-WizardControlText -Target $good -Value "new"
        if (-not $setGood) { $failures.Add("Set-WizardControlText should set an object that already has Text") | Out-Null }
        if ($good.Text -ne "new") { $failures.Add("settable Text was not updated") | Out-Null }
    } catch {
        $failures.Add("Set-WizardControlText threw on object with Text: $($_.Exception.Message)") | Out-Null
    }

    $inAppProgress = [pscustomobject]@{
        skipped = $false
        steps   = [ordered]@{
            welcome = "success"
            models  = "in_app"
            email   = "pending"
        }
    }
    $inAppLine = Format-WizardStatusLine -Progress $inAppProgress
    if ($inAppLine -ne "Welcome: OK / Models: in-app") {
        $failures.Add("in_app models must format as 'in-app', got '$inAppLine'") | Out-Null
    }
    $next = Get-FirstIncompleteStep -Progress $inAppProgress
    if ($next -ne "email") {
        $failures.Add("in_app models must skip the WinForms Models step (got '$next')") | Out-Null
    }

    if ($failures.Count -gt 0) {
        foreach ($f in $failures) { Write-Host "SELFTEST FAIL: $f" }
        return 1
    }
    Write-Host "SELFTEST OK: wizard Text guard + Welcome/Models status line"
    return 0
}

# --- Main -------------------------------------------------------------------

if ($SelfTest) {
    exit (Invoke-WizardSelfTest)
}

Write-WizardLog "=== Onboard-Wizard start InstallRoot=$InstallRoot ProfileId arg=$ProfileId Force=$Force ==="
$ProfId = Resolve-WizardProfileId
$Progress = Get-DragonAIOnboardingProgress
if ([string]::IsNullOrWhiteSpace([string]$Progress.profileId)) {
    $Progress | Add-Member -MemberType NoteProperty -Name profileId -Value $ProfId -Force
} else {
    $Progress.profileId = $ProfId
}
if ($Force) {
    # reset steps but keep nonSecret optional
    $Progress.skipped = $false
    foreach ($s in @("welcome","models","email","crm","telephony","property_data","dialer","review")) {
        Set-StepValue $Progress $s "pending"
    }
    Save-DragonAIOnboardingProgress $Progress
}

# Initialize bots to needs_setup until required complete
Update-DragonAIBotsFromProgress -ProfileId $ProfId -Progress $Progress | Out-Null

$exitCode = 0
if (Test-WinFormsAvailable) {
    Write-WizardLog "Using WinForms UI"
    try {
        $exitCode = Invoke-WinFormsWizard -Progress $Progress -ProfId $ProfId
    } catch {
        Write-WizardLog "WinForms failed ($($_.Exception.Message)); falling back to console" "WARN"
        $exitCode = Invoke-ConsoleWizard -Progress (Get-DragonAIOnboardingProgress) -ProfId $ProfId
    }
} else {
    Write-WizardLog "WinForms unavailable; console fallback"
    $exitCode = Invoke-ConsoleWizard -Progress $Progress -ProfId $ProfId
}

Write-WizardLog "=== Onboard-Wizard end exit=$exitCode ==="
exit $exitCode
