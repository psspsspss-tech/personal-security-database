# ════════════════════════════════════════════════════════════════
#  harden_windows.ps1 — Windows Security Hardening Script
#  Personal Security Suite
#  Run as ADMINISTRATOR: Right-click PowerShell → Run as Administrator
# ════════════════════════════════════════════════════════════════
#Requires -RunAsAdministrator

$ErrorActionPreference = "Continue"
$LogFile = "$PSScriptRoot\..\backend\hardening_log.txt"

function Log($msg, $color = "White") {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line -ForegroundColor $color
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
}

function Section($title) {
    Write-Host "`n═══════════════════════════════════════════" -ForegroundColor DarkCyan
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════" -ForegroundColor DarkCyan
}

function OK($msg)   { Log "  ✓ $msg" "Green"  }
function WARN($msg) { Log "  ⚠ $msg" "Yellow" }
function ERR($msg)  { Log "  ✕ $msg" "Red"    }
function INFO($msg) { Log "  · $msg" "Gray"   }

Clear-Host
Write-Host @"
╔══════════════════════════════════════════════════════╗
║      🛡  Personal Security Suite — Hardening        ║
║          Windows Security Configuration Script       ║
╚══════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

Log "Starting hardening script" "Cyan"
Log "System: $env:COMPUTERNAME | User: $env:USERNAME" "Gray"
Start-Sleep -Seconds 1

# ──────────────────────────────────────────────────────
# 1. WINDOWS FIREWALL
# ──────────────────────────────────────────────────────
Section "1. Windows Firewall"

try {
    Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
    OK "Firewall enabled on ALL profiles (Domain, Private, Public)"
} catch { ERR "Failed to enable firewall: $_" }

# Block inbound by default on public networks
try {
    Set-NetFirewallProfile -Profile Public -DefaultInboundAction Block -DefaultOutboundAction Allow
    OK "Public profile: Block all inbound connections (most secure for public WiFi)"
} catch { WARN "Could not set public profile inbound rules" }

# Block dangerous inbound ports
$dangerousPorts = @(21, 23, 135, 137, 138, 139, 445, 3389, 5900)
foreach ($port in $dangerousPorts) {
    $ruleName = "Block-Risky-Port-$port"
    try {
        $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
        if (-not $existing) {
            New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP `
                -LocalPort $port -Action Block -Profile Any -Enabled True | Out-Null
            OK "Blocked inbound port $port (risky service)"
        } else {
            INFO "Port $port already blocked"
        }
    } catch { WARN "Could not block port ${port}: $_" }
}

# ──────────────────────────────────────────────────────
# 2. DISABLE LEGACY / INSECURE PROTOCOLS
# ──────────────────────────────────────────────────────
Section "2. Disabling Legacy Protocols"

# Disable SMBv1 (EternalBlue exploit vector)
try {
    Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force
    OK "SMBv1 disabled (prevents EternalBlue/WannaCry attacks)"
} catch { WARN "Could not disable SMBv1: $_" }

# Disable Telnet client
try {
    Disable-WindowsOptionalFeature -Online -FeatureName TelnetClient -NoRestart -ErrorAction SilentlyContinue | Out-Null
    OK "Telnet client disabled"
} catch { INFO "Telnet client not present (already disabled)" }

# Disable Remote Registry service
try {
    $svc = Get-Service -Name "RemoteRegistry" -ErrorAction SilentlyContinue
    if ($svc) {
        Stop-Service -Name "RemoteRegistry" -Force -ErrorAction SilentlyContinue
        Set-Service -Name "RemoteRegistry" -StartupType Disabled
        OK "Remote Registry service disabled"
    } else {
        INFO "Remote Registry not running"
    }
} catch { WARN "Could not disable Remote Registry: $_" }

# Disable WDigest (prevents credential theft from memory)
try {
    $path = "HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest"
    if (!(Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
    Set-ItemProperty -Path $path -Name "UseLogonCredential" -Value 0 -Type DWord
    OK "WDigest authentication disabled (prevents credential theft from memory)"
} catch { WARN "Could not disable WDigest: $_" }

# ──────────────────────────────────────────────────────
# 3. WINDOWS DEFENDER
# ──────────────────────────────────────────────────────
Section "3. Windows Defender Hardening"

try {
    Set-MpPreference -DisableRealtimeMonitoring $false
    OK "Real-time protection ENABLED"
} catch { WARN "Could not enable real-time protection: $_" }

try {
    Set-MpPreference -MAPSReporting Advanced
    Set-MpPreference -SubmitSamplesConsent SendAllSamples
    OK "Cloud-delivered protection enhanced (MAPS Advanced)"
} catch { WARN "Cloud protection configuration skipped: $_" }

try {
    Set-MpPreference -PUAProtection Enabled
    OK "Potentially Unwanted Application (PUA) protection enabled"
} catch { WARN "PUA protection: $_" }

try {
    Set-MpPreference -EnableNetworkProtection Enabled
    OK "Network protection enabled (blocks malicious URLs)"
} catch { WARN "Network protection: $_" }

try {
    Update-MpSignature -ErrorAction SilentlyContinue
    OK "Antivirus signatures updated"
} catch { WARN "Could not update signatures — check internet connection" }

# ──────────────────────────────────────────────────────
# 4. DISABLE AUTORUN (USB Attack Prevention)
# ──────────────────────────────────────────────────────
Section "4. AutoRun / AutoPlay (USB Attack Prevention)"

try {
    $path = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer"
    if (!(Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
    Set-ItemProperty -Path $path -Name "NoDriveTypeAutoRun" -Value 255 -Type DWord
    OK "AutoRun disabled for ALL drive types (prevents USB malware)"
} catch { WARN "Could not disable AutoRun: $_" }

try {
    Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\IniFileMapping\Autorun.inf" `
        -Name "(Default)" -Value "@SYS:DoesNotExist" -ErrorAction SilentlyContinue
    OK "Autorun.inf execution blocked"
} catch { INFO "Autorun.inf block already set or not applicable" }

# ──────────────────────────────────────────────────────
# 5. AUDIT LOGGING
# ──────────────────────────────────────────────────────
Section "5. Enabling Security Audit Logging"

$auditCategories = @(
    @{ Name = "Account Logon";       Success = $true;  Failure = $true },
    @{ Name = "Logon/Logoff";        Success = $true;  Failure = $true },
    @{ Name = "Account Management";  Success = $true;  Failure = $true },
    @{ Name = "Privilege Use";       Success = $false; Failure = $true },
    @{ Name = "Object Access";       Success = $false; Failure = $true }
)

foreach ($cat in $auditCategories) {
    try {
        $successFlag = if ($cat.Success) { "enable" } else { "disable" }
        $failFlag    = if ($cat.Failure) { "enable" } else { "disable" }
        auditpol /set /subcategory:"$($cat.Name)" /success:$successFlag /failure:$failFlag 2>&1 | Out-Null
        OK "Audit logging: $($cat.Name) (Success=$($cat.Success), Failure=$($cat.Failure))"
    } catch { WARN "Audit: $($cat.Name) — $_" }
}

# Increase Security event log size
try {
    wevtutil sl Security /ms:102400000 2>&1 | Out-Null
    OK "Security event log size increased to ~100MB"
} catch { WARN "Could not resize Security log" }

# ──────────────────────────────────────────────────────
# 6. PASSWORD & ACCOUNT POLICIES
# ──────────────────────────────────────────────────────
Section "6. Account Security Policies"

try {
    # Minimum password length: 12
    net accounts /minpwlen:12 2>&1 | Out-Null
    OK "Minimum password length set to 12 characters"
} catch { WARN "Could not set password length" }

try {
    # Account lockout: lock after 5 failed attempts
    net accounts /lockoutthreshold:5 2>&1 | Out-Null
    OK "Account lockout after 5 failed login attempts"
} catch { WARN "Could not set lockout threshold" }

try {
    net accounts /lockoutduration:30 2>&1 | Out-Null
    OK "Lockout duration: 30 minutes"
} catch { WARN "Could not set lockout duration" }

# ──────────────────────────────────────────────────────
# 7. ADDITIONAL REGISTRY HARDENING
# ──────────────────────────────────────────────────────
Section "7. Registry Security Hardening"

# Disable LLMNR (used in MITM attacks)
try {
    $path = "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient"
    if (!(Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
    Set-ItemProperty -Path $path -Name "EnableMulticast" -Value 0 -Type DWord
    OK "LLMNR disabled (prevents Man-in-the-Middle attacks on local network)"
} catch { WARN "Could not disable LLMNR: $_" }

# Disable NetBIOS over TCP/IP (legacy protocol, attack vector)
try {
    $adapters = Get-WmiObject Win32_NetworkAdapterConfiguration -Filter "IPEnabled=True"
    foreach ($adapter in $adapters) {
        $adapter.SetTcpipNetbios(2) | Out-Null
    }
    OK "NetBIOS over TCP/IP disabled on all adapters"
} catch { WARN "Could not disable NetBIOS: $_" }

# Disable print spooler (PrintNightmare fix) — optional
# Uncomment if you don't use printers:
# try {
#     Stop-Service -Name Spooler -Force; Set-Service -Name Spooler -StartupType Disabled
#     OK "Print Spooler disabled (PrintNightmare mitigation)"
# } catch { WARN "Print Spooler: $_" }

# Enable Structured Exception Handler Overwrite Protection (SEHOP)
try {
    $path = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\kernel"
    Set-ItemProperty -Path $path -Name "DisableExceptionChainValidation" -Value 0 -Type DWord
    OK "SEHOP (exception chain validation) enabled"
} catch { WARN "SEHOP: $_" }

# ──────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────
Write-Host "`n╔══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              ✓ Hardening Complete!                  ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Log "═══ HARDENING COMPLETE ═══" "Green"
Log "Log saved to: $LogFile" "Gray"

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart your computer for all changes to take effect"
Write-Host "  2. Run check_security.ps1 to verify the hardening"
Write-Host "  3. Open the Security Dashboard to see your updated score"
Write-Host ""
Write-Host "Log file: $LogFile" -ForegroundColor Gray
Write-Host ""
