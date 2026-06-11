"""
agent.py — Universal Security Agent
========================================
Runs on: Windows | Android (Termux) | Linux
Reports system health & security data to your central Security Suite server.

SETUP:
------
1. Copy this file to the target device
2. Install Python: https://python.org (Windows) or Termux (Android)
3. Install dependencies: pip install psutil requests
4. Edit SERVER_URL below to your PC's local IP
5. Run: python agent.py

ANDROID (Termux):
-----------------
  pkg install python
  pip install psutil requests
  python agent.py

WINDOWS (other PC):
-------------------
  pip install psutil requests
  python agent.py
"""

import sys
import os
import time
import json
import socket
import uuid
import platform
import datetime
import threading
import requests

HAS_PSUTIL = True
try:
    import psutil
except ImportError:
    HAS_PSUTIL = False
# ─────────────────────────────────────────────────────────
# CONFIGURATION — Edit SERVER_URL to your PC's local IP
# ─────────────────────────────────────────────────────────
SERVER_URL = "http://192.168.1.3:8765"   # Your PC's IP (change if IP changes)
REPORT_INTERVAL = 30    # seconds between heartbeats
DEVICE_NAME = socket.gethostname()       # auto-detected
# Optional: override with a friendly name
# DEVICE_NAME = "My Android Phone"
# ─────────────────────────────────────────────────────────

DEVICE_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, socket.gethostname()))


def get_battery():
    """Get battery info if available (laptops, phones)."""
    try:
        # Standard psutil
        if HAS_PSUTIL:
            b = psutil.sensors_battery()
            if b:
                return {
                    "percent": round(b.percent, 1),
                    "plugged": b.power_plugged,
                    "charging": b.power_plugged and b.percent < 100
                }
        
        # Android Termux fallback
        if os.path.exists("/sys/class/power_supply/battery/capacity"):
            with open("/sys/class/power_supply/battery/capacity", "r") as f:
                cap = int(f.read().strip())
            plugged = False
            if os.path.exists("/sys/class/power_supply/battery/status"):
                with open("/sys/class/power_supply/battery/status", "r") as f:
                    status = f.read().strip()
                    plugged = status in ["Charging", "Full"]
            return {"percent": cap, "plugged": plugged, "charging": status == "Charging"}
    except Exception:
        pass
    return None


def get_wifi_ssid():
    """Try to get current WiFi network name."""
    try:
        if platform.system() == "Windows":
            import subprocess
            r = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                               capture_output=True, text=True, timeout=5)
            for line in r.stdout.splitlines():
                if "SSID" in line and "BSSID" not in line:
                    return line.split(":", 1)[-1].strip()
        elif platform.system() == "Linux":
            import subprocess
            r = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True, timeout=5)
            return r.stdout.strip() or None
    except Exception:
        pass
    return None


def get_open_ports_count():
    """Count listening ports quickly."""
    if not HAS_PSUTIL: return 0
    try:
        return len([c for c in psutil.net_connections() if c.status == "LISTEN"])
    except Exception:
        return 0


def get_network_io():
    """Get network bytes sent/received."""
    if not HAS_PSUTIL: return {}
    try:
        io = psutil.net_io_counters()
        return {
            "bytes_sent_mb": round(io.bytes_sent / 1024 / 1024, 1),
            "bytes_recv_mb": round(io.bytes_recv / 1024 / 1024, 1),
        }
    except Exception:
        return {}



def get_local_ip():
    """Get the device's local network IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"


def get_mem_info():
    if HAS_PSUTIL:
        try:
            mem = psutil.virtual_memory()
            return round(mem.percent, 1), round(mem.used / 1024**3, 2), round(mem.total / 1024**3, 2)
        except Exception:
            pass
    try:
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            total = free = buffers = cached = 0
            for line in lines:
                if line.startswith("MemTotal:"): total = int(line.split()[1])
                elif line.startswith("MemFree:"): free = int(line.split()[1])
                elif line.startswith("Buffers:"): buffers = int(line.split()[1])
                elif line.startswith("Cached:"): cached = int(line.split()[1])
            used = total - free - buffers - cached
            if total > 0: return round((used/total)*100, 1), round(used/1048576, 2), round(total/1048576, 2)
    except Exception: pass
    return 0, 0, 0

def get_disk_info():
    if HAS_PSUTIL:
        try:
            disk = psutil.disk_usage("/")
            return round(disk.percent, 1), round(disk.free / 1024**3, 1)
        except Exception:
            pass
    try:
        st = os.statvfs("/")
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        percent = (used / total) * 100 if total > 0 else 0
        return round(percent, 1), round(free / 1024**3, 1)
    except Exception:
        return 0, 0

def get_uptime():
    if HAS_PSUTIL:
        try:
            return round((time.time() - psutil.boot_time()) / 3600, 1)
        except Exception:
            pass
    try:
        with open("/proc/uptime", "r") as f: return round(float(f.read().split()[0]) / 3600, 1)
    except Exception: return 0.0

def build_report():
    """Build a complete status report for this device."""
    mem_pct, mem_used, mem_total = get_mem_info()
    disk_pct, disk_free = get_disk_info()
    cpu_pct = 0.0
    if HAS_PSUTIL:
        try:
            cpu_pct = psutil.cpu_percent(interval=1)
        except Exception:
            pass

    # Detect Android Termux specifically
    plat_system = platform.system()
    if 'ANDROID_ROOT' in os.environ or 'PREFIX' in os.environ and 'termux' in os.environ['PREFIX']:
        plat_system = "Android (Termux)"
        
    report = {
        "device_id": DEVICE_ID,
        "hostname": DEVICE_NAME,
        "platform": plat_system,
        "platform_version": platform.version()[:50],
        "python_version": platform.python_version(),
        "ip": get_local_ip(),
        "cpu_percent": cpu_pct,
        "memory_percent": mem_pct,
        "memory_used_gb": mem_used,
        "memory_total_gb": mem_total,
        "disk_percent": disk_pct,
        "disk_free_gb": disk_free,
        "listening_ports": get_open_ports_count(),
        "wifi_ssid": get_wifi_ssid(),
        "battery": get_battery(),
        "network_io": get_network_io(),
        "uptime_hours": get_uptime(),
        "timestamp": datetime.datetime.now().isoformat(),
        "agent_version": "1.0.1"
    }

    # Quick security checks
    security = {}
    try:
        # Check if firewall is enabled (Windows only)
        if platform.system() == "Windows":
            import subprocess
            r = subprocess.run(
                ["netsh", "advfirewall", "show", "allprofiles", "state"],
                capture_output=True, text=True, timeout=5
            )
            security["firewall_on"] = "ON" in r.stdout
    except Exception:
        pass

    if security:
        report["security"] = security

    return report


def send_report(report):
    """POST the report to the central server."""
    try:
        r = requests.post(
            f"{SERVER_URL}/api/agent/heartbeat",
            json=report,
            timeout=8
        )
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False
    except Exception:
        return False


def main():
    print("=" * 50)
    print(f"  Security Agent — {DEVICE_NAME}")
    print(f"  Reporting to: {SERVER_URL}")
    print(f"  Interval: every {REPORT_INTERVAL}s")
    print("=" * 50)

    if "192.168.1.x" in SERVER_URL:
        print("\n  [!] ERROR: Edit SERVER_URL in this file first!")
        print("  [!] Set it to your PC's local IP address.")
        print("      Example: http://192.168.1.4:8765")
        print("\n  Find your PC's IP: run 'ipconfig' on your PC")
        print("  and look for IPv4 Address under WiFi adapter.\n")
        sys.exit(1)

    errors = 0
    while True:
        try:
            report = build_report()
            ok = send_report(report)
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            if ok:
                errors = 0
                cpu = report["cpu_percent"]
                mem = report["memory_percent"]
                print(f"  [{ts}] Heartbeat sent OK | CPU: {cpu}% | RAM: {mem}%")
            else:
                errors += 1
                print(f"  [{ts}] Failed to reach server (attempt {errors}) — will retry")
                if errors == 5:
                    print("  [!] Cannot reach server. Check SERVER_URL and network connection.")
        except Exception as e:
            print(f"  [ERROR] {e}")

        time.sleep(REPORT_INTERVAL)


if __name__ == "__main__":
    main()
