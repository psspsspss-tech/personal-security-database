# ════════════════════════════════════════════════════════════════
#  check_security.ps1 — Security Audit Reporter
#  Personal Security Suite
#  Run as Administrator for best results
# ════════════════════════════════════════════════════════════════

$ErrorActionPreference = "SilentlyContinue"
$ReportFile = "$PSScriptRoot\..\backend\security_audit.txt"

function Section($title) {
    Write-Host "`n┌─────────────────────────────────────────────────┐" -ForegroundColor DarkCyan
    Write-Host "│  $($title.PadRight(47))│" -ForegroundColor Cyan
    Write-Host "└─────────────────────────────────────────────────┘" -ForegroundColor DarkCyan
}
function PASS($msg) { Write-Host "  ✓ PASS  $msg" -ForegroundColor Green  }
function FAIL($msg) { Write-Host "  ✗ FAIL  $msg" -ForegroundColor Red    }
function WARN($msg) { Write-Host "  ⚠ WARN  $msg" -ForegroundColor Yellow }
function INFO($msg) { Write-Host "  · INFO  $msg" -ForegroundColor Gray   }

$results = @()
function RecordResult($check, $status, $detail) {
    $results += [PSCustomObject]@{Check=$check; Status=$status; Detail=$detail}
}

Clear-Host
Write-Host @"
╔══════════════════════════════════════════════════════╗
║     🔍  Personal Security Suite — Audit Report      ║
╚══════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

Write-Host "  Computer : $env:COMPUTERNAME"
Write-Host "  User     : $env:USERNAME"
Write-Host "  Date     : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host ""

# ──────────────────────────────────────────────────────
Section "1. Windows Firewall"
# ──────────────────────────────────────────────────────
$fw = Get-NetFirewallProfile
foreach ($profile in $fw) {
    if ($profile.Enabled -eq "True") {
        PASS "$($profile.Name) profile: ON"
        RecordResult "Firewall $($profile.Name)" "PASS" "Enabled"
    } else {
        FAIL "$($profile.Name) profile: OFF — enable it!"
        RecordResult "Firewall $($profile.Name)" "FAIL" "Disabled"
    }
}

# ──────────────────────────────────────────────────────
Section "2. Windows Defender / Antivirus"
# ──────────────────────────────────────────────────────
try {
    $mpStatus = Get-MpComputerStatus
    if ($mpStatus.AntivirusEnabled) { PASS "Antivirus enabled" } else { FAIL "Antivirus DISABLED!" }
    if ($mpStatus.RealTimeProtectionEnabled) { PASS "Real-time protection ON" } else { FAIL "Real-time protection OFF!" }
    if ($mpStatus.BehaviorMonitorEnabled) { PASS "Behavior monitoring ON" } else { WARN "Behavior monitoring OFF" }
    if ($mpStatus.IoavProtectionEnabled) { PASS "IOAV (download) protection ON" } else { WARN "IOAV protection OFF" }

    $sigAge = $mpStatus.AntivirusSignatureAge
    if ($sigAge -le 3) {
        PASS "Signatures are up to date ($sigAge days old)"
    } elseif ($sigAge -le 7) {
        WARN "Signatures are $sigAge days old — consider updating"
    } else {
        FAIL "Signatures are $sigAge days old — UPDATE NOW!"
    }
    RecordResult "Antivirus" "$(if($mpStatus.AntivirusEnabled){'PASS'}else{'FAIL'})" "Enabled=$($mpStatus.AntivirusEnabled)"
} catch {
    WARN "Could not read Defender status — may need Admin rights"
    RecordResult "Antivirus" "WARN" "Could not read"
}

# ──────────────────────────────────────────────────────
Section "3. Windows Updates"
# ──────────────────────────────────────────────────────
try {
    $updateCount = (New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search('IsInstalled=0').Updates.Count
    if ($updateCount -eq 0) {
        PASS "System is fully up to date"
        RecordResult "Windows Updates" "PASS" "0 pending"
    } elseif ($updateCount -le 5) {
        WARN "$updateCount pending update(s) — install soon"
        RecordResult "Windows Updates" "WARN" "$updateCount pending"
    } else {
        FAIL "$updateCount pending updates — install immediately!"
        RecordResult "Windows Updates" "FAIL" "$updateCount pending"
    }
} catch {
    WARN "Could not check Windows Update status"
    RecordResult "Windows Updates" "WARN" "Could not check"
}

# ──────────────────────────────────────────────────────
Section "4. Legacy Protocol Check"
# ──────────────────────────────────────────────────────

# SMBv1
try {
    $smb1 = Get-SmbServerConfiguration | Select-Object -ExpandProperty EnableSMB1Protocol
    if ($smb1 -eq $false) {
        PASS "SMBv1 is disabled (good - no EternalBlue risk)"
        RecordResult "SMBv1" "PASS" "Disabled"
    } else {
        FAIL "SMBv1 is ENABLED — run harden_windows.ps1 to fix!"
        RecordResult "SMBv1" "FAIL" "Enabled"
    }
} catch { WARN "Could not check SMBv1 status" }

# Remote Registry
try {
    $remReg = Get-Service -Name "RemoteRegistry"
    if ($remReg.StartType -eq "Disabled") {
        PASS "Remote Registry service: Disabled"
        RecordResult "Remote Registry" "PASS" "Disabled"
    } else {
        WARN "Remote Registry is: $($remReg.StartType) — disable it"
        RecordResult "Remote Registry" "WARN" $remReg.StartType
    }
} catch { INFO "Remote Registry: not found" }

# WDigest
try {
    $wdigest = Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest" -Name UseLogonCredential -ErrorAction SilentlyContinue
    if ($wdigest.UseLogonCredential -eq 0) {
        PASS "WDigest disabled (credentials not stored in plaintext)"
        RecordResult "WDigest" "PASS" "Disabled"
    } else {
        FAIL "WDigest ENABLED — passwords may be stored in memory!"
        RecordResult "WDigest" "FAIL" "Enabled"
    }
} catch { INFO "WDigest key not found (likely disabled by default)" }

# LLMNR
try {
    $llmnr = Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient" -Name EnableMulticast -ErrorAction SilentlyContinue
    if ($llmnr.EnableMulticast -eq 0) {
        PASS "LLMNR disabled (no MITM risk)"
        RecordResult "LLMNR" "PASS" "Disabled"
    } else {
        WARN "LLMNR enabled — MITM attacks possible on local network"
        RecordResult "LLMNR" "WARN" "Enabled"
    }
} catch { WARN "LLMNR status: unknown" }

# ──────────────────────────────────────────────────────
Section "5. Account Security"
# ──────────────────────────────────────────────────────
try {
    $policy = net accounts 2>&1
    $minPwLen = ($policy | Select-String "Minimum password length").ToString() -replace ".*:\s*", ""
    $lockout  = ($policy | Select-String "Lockout threshold").ToString()       -replace ".*:\s*", ""

    $minPwLenInt = [int]($minPwLen.Trim())
    if ($minPwLenInt -ge 12) {
        PASS "Minimum password length: $minPwLen (good - 12+)"
    } elseif ($minPwLenInt -ge 8) {
        WARN "Minimum password length: $minPwLen (recommend 12+)"
    } else {
        FAIL "Minimum password length too short: $minPwLen (must be 12+)"
    }
    RecordResult "Password Length" "$(if($minPwLenInt -ge 12){'PASS'}else{'WARN'})" "$minPwLen chars"

    $lockoutInt = [int]($lockout.Trim() -replace "\D","")
    if ($lockoutInt -gt 0 -and $lockoutInt -le 5) {
        PASS "Account lockout: after $lockout failed attempts"
    } elseif ($lockoutInt -eq 0) {
        FAIL "No account lockout set — brute force attacks possible!"
    } else {
        WARN "Lockout threshold is $lockout (recommend 5 or less)"
    }
    RecordResult "Account Lockout" "$(if($lockoutInt -gt 0 -and $lockoutInt -le 5){'PASS'}else{'WARN'})" "Threshold: $lockout"
} catch {
    WARN "Could not read account policy"
}

# ──────────────────────────────────────────────────────
Section "6. Open Risky Ports"
# ──────────────────────────────────────────────────────
$riskyPorts = @(21, 23, 135, 139, 445, 3389, 5900)
$openConnections = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue
foreach ($port in $riskyPorts) {
    $open = $openConnections | Where-Object { $_.LocalPort -eq $port }
    if ($open) {
        FAIL "Port $port is OPEN — this is a risky service!"
        RecordResult "Port $port" "FAIL" "Open"
    } else {
        PASS "Port $port is closed"
        RecordResult "Port $port" "PASS" "Closed"
    }
}

# ──────────────────────────────────────────────────────
Section "7. BitLocker Drive Encryption"
# ──────────────────────────────────────────────────────
try {
    $bl = Get-BitLockerVolume -MountPoint "C:" -ErrorAction SilentlyContinue
    if ($bl.ProtectionStatus -eq "On") {
        PASS "BitLocker ON — drive C: is encrypted"
        RecordResult "BitLocker" "PASS" "Encrypted"
    } else {
        WARN "BitLocker is OFF — your data is unencrypted if device is stolen"
        INFO "Enable: Control Panel → BitLocker Drive Encryption"
        RecordResult "BitLocker" "WARN" "Not encrypted"
    }
} catch {
    INFO "BitLocker: Could not read status"
}

# ──────────────────────────────────────────────────────
# FINAL SCORE
# ──────────────────────────────────────────────────────
$passCount = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$failCount = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
$warnCount = ($results | Where-Object { $_.Status -eq "WARN" }).Count
$total = $results.Count

$score = [math]::Round((($passCount / $total) * 100), 0)

Write-Host "`n╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                  AUDIT SUMMARY                      ║" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host ("║  Security Score: {0,3}%   " -f $score).PadRight(55) + "║" -ForegroundColor $(if($score -ge 80){"Green"}elseif($score -ge 60){"Yellow"}else{"Red"})
Write-Host "║  PASS:  $($passCount.ToString().PadRight(5)) WARN:  $($warnCount.ToString().PadRight(5)) FAIL:  $($failCount.ToString().PadRight(40))║" -ForegroundColor White
Write-Host "╚══════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

if ($failCount -gt 0) {
    Write-Host "ACTION REQUIRED: Run harden_windows.ps1 as Administrator to fix FAIL items!" -ForegroundColor Red
}

# Save report
$reportContent = "Security Audit Report — $(Get-Date)`n" +
    "Computer: $env:COMPUTERNAME | User: $env:USERNAME`n" +
    "Score: $score% | PASS: $passCount | WARN: $warnCount | FAIL: $failCount`n`n"
foreach ($r in $results) {
    $reportContent += "[$($r.Status)] $($r.Check): $($r.Detail)`n"
}
$reportContent | Out-File -FilePath $ReportFile -Encoding UTF8
Write-Host "Full report saved to: $ReportFile" -ForegroundColor Gray
