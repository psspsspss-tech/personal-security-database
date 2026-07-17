"""
process_monitor.py — Suspicious Process & Network Activity Monitor
Lists all processes with active network connections.
Flags unknown processes with outbound connections.
"""

import psutil
import json
import datetime
import os
import hashlib

# Processes that are always safe to ignore
SAFE_PROCESSES = {
    "system", "svchost.exe", "lsass.exe", "csrss.exe", "wininit.exe",
    "winlogon.exe", "services.exe", "smss.exe", "dwm.exe", "explorer.exe",
    "taskhostw.exe", "sihost.exe", "fontdrvhost.exe", "spoolsv.exe",
    "audiodg.exe", "conhost.exe", "dashost.exe", "searchindexer.exe",
    "searchhost.exe", "runtimebroker.exe", "securityhealthservice.exe",
    "mpdefendercoreservice.exe", "msmpeng.exe", "nissrv.exe",
    "chrome.exe", "firefox.exe", "msedge.exe", "opera.exe", "brave.exe",
    "python.exe", "pythonw.exe", "node.exe",
    "code.exe", "devenv.exe", "idea64.exe",
    "onedrive.exe", "dropbox.exe", "googledrivesync.exe",
    "steam.exe", "discord.exe", "slack.exe", "teams.exe",
    "zoom.exe", "skype.exe",
    "powershell.exe", "cmd.exe", "wsl.exe", "wslhost.exe",
    "vmware-vmx.exe", "vmnat.exe", "vmnetdhcp.exe",
    "antimalware service executable", "windows defender",
}

# Ports that normal user apps shouldn't be listening on
SUSPICIOUS_PORTS = {21, 22, 23, 25, 110, 143, 445, 3389, 4444, 5900, 6666, 7777, 8888, 9999, 31337}


def get_file_hash(path, max_size_mb=50):
    """Get MD5 hash of executable (for identifying unknown files)."""
    try:
        size = os.path.getsize(path) / (1024 * 1024)
        if size > max_size_mb:
            return None
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:12]
    except Exception:
        return None


def get_networked_processes():
    """Get all processes with active network connections."""
    proc_map = {}

    try:
        # Build connection → process map
        for conn in psutil.net_connections(kind="inet"):
            pid = conn.pid
            if not pid:
                continue

            if pid not in proc_map:
                try:
                    proc = psutil.Process(pid)
                    name = proc.name()
                    try:
                        exe = proc.exe()
                    except Exception:
                        exe = ""
                    try:
                        cpu = proc.cpu_percent(interval=0)
                    except Exception:
                        cpu = 0
                    try:
                        mem = round(proc.memory_info().rss / (1024 * 1024), 1)
                    except Exception:
                        mem = 0

                    proc_map[pid] = {
                        "pid": pid,
                        "name": name,
                        "exe": exe,
                        "cpu_percent": cpu,
                        "memory_mb": mem,
                        "connections": [],
                        "is_safe": name.lower() in SAFE_PROCESSES,
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Add connection info
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
            raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
            proc_map[pid]["connections"].append({
                "local": laddr,
                "remote": raddr,
                "status": conn.status,
                "suspicious_port": conn.laddr.port in SUSPICIOUS_PORTS if conn.laddr else False
            })

    except Exception:
        pass

    # Score each process
    results = []
    for pid, info in proc_map.items():
        suspicion_reasons = []

        name_lower = info["name"].lower()
        if not info["is_safe"]:
            suspicion_reasons.append("Unknown process")

        # Check for suspicious listening ports
        for conn in info["connections"]:
            if conn.get("suspicious_port"):
                port = conn["local"].split(":")[-1]
                suspicion_reasons.append(f"Listening on suspicious port {port}")

        # High CPU unknown process
        if info["cpu_percent"] > 50 and not info["is_safe"]:
            suspicion_reasons.append(f"High CPU: {info['cpu_percent']}%")

        # Outbound connections for unknown process
        outbound = [c for c in info["connections"] if c["remote"] and c["status"] == "ESTABLISHED"]
        if outbound and not info["is_safe"]:
            suspicion_reasons.append(f"{len(outbound)} outbound connection(s)")

        risk = "high" if len(suspicion_reasons) >= 2 else ("medium" if suspicion_reasons else "low")

        results.append({
            **info,
            "suspicion_reasons": suspicion_reasons,
            "risk": risk,
            "outbound_count": len([c for c in info["connections"] if c["remote"] and c["status"] == "ESTABLISHED"]),
            "listen_count": len([c for c in info["connections"] if c["status"] == "LISTEN"]),
        })

    # Sort: high risk first, then by name
    results.sort(key=lambda x: (0 if x["risk"] == "high" else 1 if x["risk"] == "medium" else 2, x["name"].lower()))
    return results


def get_summary():
    """Quick summary for dashboard."""
    procs = get_networked_processes()
    high_risk = [p for p in procs if p["risk"] == "high"]
    medium_risk = [p for p in procs if p["risk"] == "medium"]

    return {
        "total_networked_processes": len(procs),
        "high_risk_count": len(high_risk),
        "medium_risk_count": len(medium_risk),
        "processes": procs,
        "timestamp": datetime.datetime.now().isoformat()
    }


if __name__ == "__main__":
    data = get_summary()
    print(json.dumps(data, indent=2))
