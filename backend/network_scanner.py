"""
network_scanner.py — WiFi Network Device Scanner
Scans the local network for all connected devices.
Compares against the whitelist and logs unknown devices.
Uses ARP via subprocess (works without admin on most Windows systems).
"""

import subprocess
import re
import json
import os
import datetime
import socket
import struct
import ipaddress
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
WHITELIST_FILE = BASE_DIR / "whitelist.json"
ALERTS_FILE = BASE_DIR / "alerts.json"
LOG_FILE = BASE_DIR / "scan_log.json"

# Well-known OUI prefixes for vendor identification
OUI_VENDORS = {
    "00:50:56": "VMware",
    "00:0C:29": "VMware",
    "08:00:27": "VirtualBox",
    "B8:27:EB": "Raspberry Pi",
    "DC:A6:32": "Raspberry Pi",
    "E4:5F:01": "Raspberry Pi",
    "00:1A:11": "Google",
    "F4:F5:D8": "Google",
    "AC:67:B2": "Samsung",
    "00:26:B9": "Samsung",
    "3C:5A:B4": "Google (Nest)",
    "94:65:2D": "Apple",
    "A4:CF:12": "Xiaomi",
    "FC:F5:C4": "Xiaomi",
    "74:DA:38": "Edimax",
    "00:E0:4C": "Realtek",
    "00:1B:21": "Intel",
    "00:21:6B": "Intel",
}


def load_whitelist():
    """Load the device whitelist from file."""
    try:
        with open(WHITELIST_FILE, "r") as f:
            data = json.load(f)
            return {d["mac"].upper(): d for d in data.get("approved_devices", [])}
    except Exception:
        return {}


def save_whitelist(devices_list):
    """Save updated whitelist to file."""
    try:
        data = {
            "approved_devices": devices_list,
            "last_updated": datetime.datetime.now().isoformat(),
            "notes": "Managed by Security Suite dashboard."
        }
        with open(WHITELIST_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def add_to_whitelist(mac, name, notes=""):
    """Add a device to the whitelist."""
    whitelist = load_whitelist()
    mac_upper = mac.upper()
    whitelist[mac_upper] = {
        "mac": mac_upper,
        "name": name,
        "notes": notes,
        "approved_at": datetime.datetime.now().isoformat()
    }
    success = save_whitelist(list(whitelist.values()))
    if success:
        force_cache_update()
    return success


def remove_from_whitelist(mac):
    """Remove a device from the whitelist."""
    whitelist = load_whitelist()
    mac_upper = mac.upper()
    if mac_upper in whitelist:
        del whitelist[mac_upper]
        success = save_whitelist(list(whitelist.values()))
        if success:
            force_cache_update()
        return success
    return False


def get_local_ip():
    """Get the local machine's IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_gateway():
    """Get the default gateway IP."""
    try:
        result = subprocess.run(
            ["ipconfig"], capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.split("\n"):
            if "Default Gateway" in line:
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    return match.group(1)
    except Exception:
        pass
    return None


def get_subnet():
    """Derive /24 subnet from local IP."""
    ip = get_local_ip()
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return "192.168.1.0/24"


import urllib.request
import urllib.error

MAC_CACHE_FILE = BASE_DIR / "mac_cache.json"

def load_mac_cache():
    try:
        with open(MAC_CACHE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_mac_cache(cache):
    try:
        with open(MAC_CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except:
        pass

_mac_cache = load_mac_cache()

def is_mac_randomized(mac):
    """Check if MAC is locally administered (randomized)."""
    if not mac or len(mac) < 2:
        return False
    # The second character of the first octet determines if it's local
    # If the second hex digit is 2, 6, A, or E, it is locally administered.
    second_char = mac[1].upper()
    return second_char in ['2', '6', 'A', 'E']

def lookup_vendor(mac):
    """Advanced MAC vendor lookup with randomization detection and API cache."""
    if not mac or mac == "Unknown":
        return "Unknown"
    
    if is_mac_randomized(mac):
        return "Randomized MAC (Private)"

    # Check local hardcoded cache first
    prefix = mac[:8].upper()
    if prefix in OUI_VENDORS:
        return OUI_VENDORS[prefix]

    # Check disk cache
    if mac in _mac_cache:
        return _mac_cache[mac]

    # Try live API (non-blocking, fast timeout)
    try:
        req = urllib.request.Request(
            f"https://api.macvendors.com/{mac}", 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=1.0) as response:
            vendor = response.read().decode('utf-8').strip()
            _mac_cache[mac] = vendor
            save_mac_cache(_mac_cache)
            return vendor
    except Exception:
        pass
    
    return "Unknown"

def os_fingerprint(ip):
    """Fast port scan to guess the operating system or device platform."""
    ports_to_check = [
        (62078, "Apple (iOS/macOS)"),
        (5555, "Android"),
        (445, "Windows/PC"),
        (8009, "Google Cast / Nest"),
        (53, "Router/Gateway")
    ]
    for port, platform in ports_to_check:
        try:
            with socket.create_connection((ip, port), timeout=0.1):
                return platform
        except Exception:
            pass
    return "Unknown"

def resolve_hostname(ip):
    """Attempt reverse DNS lookup for a hostname."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ""

# ─── ACTIVE CONTROL ACTIONS ───

def grab_banner(ip, port):
    """Attempt to grab the service banner from an open port."""
    try:
        with socket.create_connection((ip, port), timeout=0.5) as s:
            if port in [80, 443, 8080, 8443]:
                s.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
            banner = s.recv(1024).decode('utf-8', errors='ignore').strip()
            # Clean up the banner for display (just take the first line)
            if banner:
                return banner.split('\n')[0][:100] 
    except Exception:
        pass
    return None

def assess_port_risk(port):
    """Categorize the risk level of an open port."""
    high_risk = {21: "FTP (Unencrypted)", 23: "Telnet (Unencrypted)", 135: "RPC", 139: "NetBIOS", 445: "SMB (Ransomware target)"}
    medium_risk = {22: "SSH", 3389: "RDP", 5900: "VNC"}
    
    if port in high_risk:
        return "high", high_risk[port]
    elif port in medium_risk:
        return "medium", medium_risk[port]
    else:
        return "low", "Standard/Unknown Service"

def action_deep_scan(ip):
    """Aggressively scan top ports and grab banners for vulnerability assessment."""
    top_ports = [21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,1723,3306,3389,5900,8080,8443,5555,62078,8009]
    open_ports_details = []
    
    for p in top_ports:
        try:
            with socket.create_connection((ip, p), timeout=0.2):
                banner = grab_banner(ip, p)
                risk_level, service_desc = assess_port_risk(p)
                
                open_ports_details.append({
                    "port": p,
                    "service": service_desc,
                    "banner": banner if banner else "No banner returned",
                    "risk": risk_level
                })
        except Exception:
            pass
            
    # Sort by risk (high first)
    risk_order = {"high": 0, "medium": 1, "low": 2}
    open_ports_details.sort(key=lambda x: risk_order[x["risk"]])
    
    return open_ports_details

def action_block_ip(ip):
    """Instantly block an IP address from communicating with this PC via Windows Firewall."""
    rule_name = f"SecuritySuite_Block_{ip}"
    cmd = f'netsh advfirewall firewall add rule name="{rule_name}" dir=in action=block remoteip={ip}'
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
        return True
    except Exception as e:
        return False

def action_wol(mac):
    """Send a Wake-on-LAN magic packet to turn on a sleeping device."""
    try:
        mac_clean = mac.replace(':', '').replace('-', '')
        if len(mac_clean) != 12:
            return False
        data = bytes.fromhex('FF' * 6 + mac_clean * 16)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(data, ('255.255.255.255', 9))
        s.close()
        return True
    except Exception:
        return False



def arp_scan_windows():
    """
    Scan local network using ARP cache + ping sweep.
    Returns list of {ip, mac, hostname, vendor} dicts.
    """
    devices = []
    seen_macs = set()

    # Step 1: Ping sweep to populate ARP cache
    subnet = get_subnet()
    try:
        net = ipaddress.ip_network(subnet, strict=False)
        # Ping all hosts (fire-and-forget for speed)
        ping_procs = []
        for host in list(net.hosts())[:254]:
            p = subprocess.Popen(
                ["ping", "-n", "1", "-w", "300", str(host)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            ping_procs.append(p)
        # Wait briefly for pings to complete
        time.sleep(2)
        for p in ping_procs:
            try:
                p.terminate()
            except Exception:
                pass
    except Exception:
        pass

    # Step 2: Read ARP cache
    try:
        result = subprocess.run(
            ["arp", "-a"], capture_output=True, text=True, timeout=15
        )
        local_ip = get_local_ip()

        for line in result.stdout.split("\n"):
            # Match lines like: "  192.168.1.5          aa-bb-cc-dd-ee-ff     dynamic"
            match = re.search(
                r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})',
                line
            )
            if match:
                ip = match.group(1)
                mac = match.group(2).upper().replace("-", ":")

                # Skip broadcast and multicast
                if mac in ["FF:FF:FF:FF:FF:FF", "00:00:00:00:00:00"]:
                    continue
                if ip.endswith(".255") or ip.startswith("224.") or ip.startswith("239."):
                    continue
                if mac in seen_macs:
                    continue

                seen_macs.add(mac)
                vendor = lookup_vendor(mac)
                hostname = resolve_hostname(ip)
                os_guess = os_fingerprint(ip)
                is_random = is_mac_randomized(mac)

                # Label self
                label = ""
                if ip == local_ip:
                    label = "This Device"

                devices.append({
                    "ip": ip,
                    "mac": mac,
                    "hostname": hostname or ip,
                    "vendor": vendor,
                    "os_guess": os_guess,
                    "is_randomized_mac": is_random,
                    "label": label,
                    "last_seen": datetime.datetime.now().isoformat()
                })
    except Exception as e:
        pass

    return devices


def load_alerts():
    """Load existing alerts."""
    try:
        with open(ALERTS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_alert(alert):
    """Append a new alert to the alerts file."""
    alerts = load_alerts()
    alerts.insert(0, alert)
    # Keep only last 100 alerts
    alerts = alerts[:100]
    try:
        with open(ALERTS_FILE, "w") as f:
            json.dump(alerts, f, indent=2)
    except Exception:
        pass


def scan_and_check():
    """
    Full scan: get devices, check against whitelist, fire alerts for unknowns.
    Returns scan result dict.
    """
    devices = arp_scan_windows()
    whitelist = load_whitelist()
    local_ip = get_local_ip()

    results = []
    unknown_count = 0
    new_unknowns = []

    for device in devices:
        mac = device["mac"]
        is_self = device["ip"] == local_ip
        is_approved = mac in whitelist or is_self

        if not is_approved:
            unknown_count += 1
            new_unknowns.append(device)

        result = {
            **device,
            "status": "self" if is_self else ("approved" if is_approved else "unknown"),
            "approved_name": whitelist.get(mac, {}).get("name", "") if is_approved else ""
        }
        results.append(result)

    # Fire alerts for unknown devices
    for device in new_unknowns:
        alert = {
            "id": f"unknown_{device['mac']}_{int(time.time())}",
            "type": "unknown_device",
            "severity": "high",
            "title": "Unknown Device Detected",
            "message": f"Device {device['mac']} ({device['ip']}) joined your network",
            "device": device,
            "timestamp": datetime.datetime.now().isoformat(),
            "acknowledged": False
        }
        save_alert(alert)

    # Log the scan
    scan_log = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_devices": len(results),
        "approved": len(results) - unknown_count,
        "unknown": unknown_count
    }
    try:
        logs = []
        if LOG_FILE.exists():
            with open(LOG_FILE) as f:
                logs = json.load(f)
        logs.insert(0, scan_log)
        logs = logs[:500]  # keep last 500 scans
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=2)
    except Exception:
        pass

    return {
        "devices": results,
        "summary": scan_log,
        "local_ip": local_ip,
        "gateway": get_gateway(),
        "subnet": get_subnet()
    }


# Background continuous scanner
_scanner_thread = None
_last_scan_result = None
_scan_lock = threading.Lock()


def _background_scan_loop(interval=60):
    """Continuously scan in background every `interval` seconds."""
    global _last_scan_result
    while True:
        try:
            result = scan_and_check()
            with _scan_lock:
                _last_scan_result = result
        except Exception:
            pass
        time.sleep(interval)


def start_background_scanner(interval=60):
    """Start the background scanner thread."""
    global _scanner_thread
    if _scanner_thread is None or not _scanner_thread.is_alive():
        _scanner_thread = threading.Thread(
            target=_background_scan_loop,
            args=(interval,),
            daemon=True
        )
        _scanner_thread.start()


def get_last_scan():
    """Get the most recent scan result."""
    with _scan_lock:
        return _last_scan_result

def force_cache_update():
    """Instantly update the active scan cache so UI refreshes without waiting for the next 60s background loop."""
    global _last_scan_result
    with _scan_lock:
        if _last_scan_result is not None:
            whitelist = load_whitelist()
            local_ip = get_local_ip()
            for device in _last_scan_result.get("devices", []):
                mac = device["mac"]
                is_self = device["ip"] == local_ip
                is_approved = mac in whitelist or is_self
                device["status"] = "self" if is_self else ("approved" if is_approved else "unknown")
                if is_approved:
                    device["approved_name"] = whitelist.get(mac, {}).get("name", "")


if __name__ == "__main__":
    print("Scanning network... please wait.")
    result = scan_and_check()
    print(json.dumps(result, indent=2))
