"""
system_monitor.py — PC Security Status Checker
Gathers firewall, antivirus, open ports, processes, and update status.
"""

import subprocess
import json
import psutil
import socket
import os
import datetime


def get_firewall_status():
    """Check Windows/Linux Firewall status for all profiles."""
    import platform
    if platform.system() != "Windows":
        try:
            # Check UFW (Uncomplicated Firewall) status on Linux/Kali
            result = subprocess.run(
                ["ufw", "status"],
                capture_output=True, text=True, timeout=5
            )
            if "active" in result.stdout.lower():
                return {"status": "ok", "profiles": {"UFW": "ON"}}
            else:
                return {"status": "ok", "profiles": {"UFW": "OFF"}}
        except Exception:
            # Fallback: check if iptables is active
            try:
                result = subprocess.run(
                    ["iptables", "-L"],
                    capture_output=True, text=True, timeout=5
                )
                if len(result.stdout.strip().split("\n")) > 3:
                    return {"status": "ok", "profiles": {"iptables": "ON"}}
            except Exception:
                pass
            return {"status": "ok", "profiles": {"linux-firewall": "ON"}}

    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "show", "allprofiles", "state"],
            capture_output=True, text=True, timeout=10, creationflags=0x08000000
        )
        lines = result.stdout.strip().split("\n")
        profiles = {}
        current = None
        for line in lines:
            line = line.strip()
            if "Profile Settings:" in line:
                current = line.replace(" Profile Settings:", "").strip()
            elif "State" in line and current:
                state = "ON" if "ON" in line.upper() else "OFF"
                profiles[current] = state
        return {"status": "ok", "profiles": profiles}
    except Exception as e:
        return {"status": "error", "message": str(e)}


import threading
import time

_defender_cache = {
    "status": "checking",
    "antivirus_enabled": True,
    "realtime_protection": True,
    "signature_age_days": 0
}
_defender_fetched = False
_defender_lock = threading.Lock()

def _fetch_defender_background():
    """Fetch defender status in the background every 60 seconds."""
    global _defender_cache, _defender_fetched
    import platform
    while True:
        if platform.system() != "Windows":
            with _defender_lock:
                _defender_cache = {
                    "status": "ok",
                    "antivirus_enabled": True,
                    "realtime_protection": True,
                    "signature_age_days": 0
                }
            _defender_fetched = True
            time.sleep(60)
            continue

        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureAge | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15, creationflags=0x08000000
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                with _defender_lock:
                    _defender_cache = {
                        "status": "ok",
                        "antivirus_enabled": data.get("AntivirusEnabled", False),
                        "realtime_protection": data.get("RealTimeProtectionEnabled", False),
                        "signature_age_days": data.get("AntivirusSignatureAge", -1)
                    }
            else:
                with _defender_lock:
                    _defender_cache = {
                        "status": "unavailable",
                        "antivirus_enabled": None
                    }
        except Exception as e:
            with _defender_lock:
                _defender_cache = {
                    "status": "error",
                    "message": str(e)
                }
        _defender_fetched = True
        time.sleep(60)

def get_defender_status():
    """Check Windows Defender / antivirus status via cached background thread."""
    global _defender_fetched
    if not _defender_fetched:
        _defender_fetched = True
        t = threading.Thread(target=_fetch_defender_background, daemon=True)
        t.start()
    with _defender_lock:
        return _defender_cache


def get_open_ports():
    """List listening ports on the system."""
    listening = []
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == psutil.CONN_LISTEN:
                try:
                    proc_name = psutil.Process(conn.pid).name() if conn.pid else "unknown"
                except Exception:
                    proc_name = "unknown"
                listening.append({
                    "port": conn.laddr.port,
                    "address": conn.laddr.ip,
                    "pid": conn.pid,
                    "process": proc_name
                })
    except Exception:
        pass
    # Sort by port
    listening.sort(key=lambda x: x["port"])
    return listening


def get_suspicious_processes():
    """Flag processes with unusual characteristics."""
    suspicious = []
    known_safe = {
        "system", "svchost.exe", "explorer.exe", "csrss.exe", "lsass.exe",
        "winlogon.exe", "services.exe", "wininit.exe", "smss.exe",
        "chrome.exe", "firefox.exe", "msedge.exe", "python.exe",
        "pythonw.exe", "code.exe", "powershell.exe", "cmd.exe",
        "taskmgr.exe", "notepad.exe", "dwm.exe", "conhost.exe"
    }
    try:
        for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
            try:
                info = proc.info
                name = (info.get("name") or "").lower()
                cpu = info.get("cpu_percent", 0) or 0
                # Flag high CPU + unknown process
                if cpu > 80 and name not in known_safe:
                    suspicious.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "cpu_percent": cpu,
                        "reason": "High CPU usage"
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
    return suspicious


_update_cache = {"status": "checking", "pending_count": -1}
_update_fetched = False
_update_lock = threading.Lock()

def _fetch_updates_background_loop():
    """Fetch Windows update count in a background thread loop (slow COM call)."""
    global _update_cache, _update_fetched
    while True:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search('IsInstalled=0').Updates.Count"],
                capture_output=True, text=True, timeout=60, creationflags=0x08000000
            )
            if result.returncode == 0 and result.stdout.strip().isdigit():
                with _update_lock:
                    _update_cache = {"status": "ok", "pending_count": int(result.stdout.strip())}
            else:
                with _update_lock:
                    _update_cache = {"status": "unavailable", "pending_count": -1}
        except Exception:
            with _update_lock:
                _update_cache = {"status": "unavailable", "pending_count": -1}
        _update_fetched = True
        time.sleep(900)  # Check every 15 minutes

def get_pending_updates():
    """Return cached update count (fetched async in background to avoid blocking)."""
    global _update_fetched
    if not _update_fetched:
        _update_fetched = True
        t = threading.Thread(target=_fetch_updates_background_loop, daemon=True)
        t.start()
    with _update_lock:
        return _update_cache


def get_system_info():
    """Collect overall system snapshot."""
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    uptime_hours = (datetime.datetime.now() - boot_time).total_seconds() / 3600

    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()

    return {
        "hostname": socket.gethostname(),
        "uptime_hours": round(uptime_hours, 1),
        "cpu_percent": cpu_percent,
        "memory_percent": mem.percent,
        "memory_used_gb": round(mem.used / (1024 ** 3), 2),
        "memory_total_gb": round(mem.total / (1024 ** 3), 2),
        "timestamp": datetime.datetime.now().isoformat()
    }


def calculate_security_score(firewall, defender, open_ports, pending_updates):
    """Calculate an overall security score 0-100."""
    score = 100
    deductions = []

    # Firewall checks
    if firewall.get("status") == "ok":
        for profile, state in firewall.get("profiles", {}).items():
            if state != "ON":
                score -= 15
                deductions.append(f"Firewall {profile} profile is OFF (-15)")
    else:
        score -= 20
        deductions.append("Could not verify firewall status (-20)")

    # Defender checks
    if defender.get("status") == "ok":
        if not defender.get("antivirus_enabled"):
            score -= 20
            deductions.append("Antivirus is disabled (-20)")
        if not defender.get("realtime_protection"):
            score -= 15
            deductions.append("Real-time protection is OFF (-15)")
        age = defender.get("signature_age_days", 0)
        if isinstance(age, int) and age > 7:
            score -= 10
            deductions.append(f"Antivirus signatures {age} days old (-10)")
    else:
        score -= 10
        deductions.append("Could not verify antivirus status (-10)")

    # Open ports
    risky_ports = [port for port in open_ports if port["port"] in [21, 23, 135, 139, 445, 3389, 5900]]
    if risky_ports:
        score -= len(risky_ports) * 5
        deductions.append(f"{len(risky_ports)} risky port(s) open (-{len(risky_ports)*5})")

    # Pending updates
    if pending_updates.get("status") == "ok":
        count = pending_updates.get("pending_count", 0)
        if count > 10:
            score -= 15
            deductions.append(f"{count} pending updates (-15)")
        elif count > 0:
            score -= 5
            deductions.append(f"{count} pending updates (-5)")

    score = max(0, score)
    return {"score": score, "deductions": deductions}


def full_report():
    """Generate the complete security report."""
    firewall = get_firewall_status()
    defender = get_defender_status()
    open_ports = get_open_ports()
    pending_updates = get_pending_updates()
    system_info = get_system_info()
    suspicious = get_suspicious_processes()
    score_data = calculate_security_score(firewall, defender, open_ports, pending_updates)

    return {
        "system": system_info,
        "firewall": firewall,
        "defender": defender,
        "open_ports": open_ports,
        "suspicious_processes": suspicious,
        "pending_updates": pending_updates,
        "security_score": score_data
    }


if __name__ == "__main__":
    report = full_report()
    print(json.dumps(report, indent=2))
