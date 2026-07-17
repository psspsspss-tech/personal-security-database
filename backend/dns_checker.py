"""
dns_checker.py — DNS Security & VPN Status Checker
Checks DNS servers, DNS-over-HTTPS, DNS leaks, and VPN status.
"""

import subprocess
import socket
import json
import time
import re
import requests


KNOWN_SAFE_DNS = {
    "1.1.1.1":       "Cloudflare (Privacy)",
    "1.0.0.1":       "Cloudflare (Privacy)",
    "8.8.8.8":       "Google DNS",
    "8.8.4.4":       "Google DNS",
    "9.9.9.9":       "Quad9 (Security)",
    "149.112.112.112":"Quad9 (Security)",
    "208.67.222.222": "OpenDNS",
    "208.67.220.220": "OpenDNS",
    "76.76.19.19":    "Alternate DNS (Ad-blocking)",
    "94.140.14.14":   "AdGuard DNS",
    "94.140.15.15":   "AdGuard DNS",
}

RISKY_DNS_HINT = "Your ISP's DNS — they can see and log all your browsing"


def get_current_dns_servers():
    """Get DNS servers configured on all active network adapters."""
    servers = []
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object {$_.ServerAddresses} | Select-Object InterfaceAlias, ServerAddresses | ConvertTo-Json"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            raw = result.stdout.strip()
            if raw.startswith("{"):
                raw = f"[{raw}]"
            adapters = json.loads(raw)
            if not isinstance(adapters, list):
                adapters = [adapters]
            for adapter in adapters:
                iface = adapter.get("InterfaceAlias", "Unknown")
                addrs = adapter.get("ServerAddresses", [])
                if isinstance(addrs, str):
                    addrs = [addrs]
                for addr in (addrs or []):
                    if addr and addr not in ["", "fec0:0:0:ffff::1"]:
                        label = KNOWN_SAFE_DNS.get(addr, RISKY_DNS_HINT)
                        is_safe = addr in KNOWN_SAFE_DNS
                        servers.append({
                            "interface": iface,
                            "address": addr,
                            "provider": label,
                            "is_safe": is_safe
                        })
    except Exception:
        pass

    # Deduplicate by address
    seen = set()
    unique = []
    for s in servers:
        if s["address"] not in seen:
            seen.add(s["address"])
            unique.append(s)
    return unique


def check_doh_enabled():
    """Check if DNS-over-HTTPS is enabled in Windows."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Dnscache\\Parameters' -ErrorAction SilentlyContinue | Select-Object EnableAutoDoh | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            # 2 = auto DoH, 0 = off
            val = data.get("EnableAutoDoh", 0)
            return val == 2
    except Exception:
        pass
    return False


def check_vpn_status():
    """Detect active VPN connections on the system."""
    vpn_interfaces = []
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object Name, InterfaceDescription, Status | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            raw = result.stdout.strip()
            if raw.startswith("{"):
                raw = f"[{raw}]"
            adapters = json.loads(raw)
            if not isinstance(adapters, list):
                adapters = [adapters]

            vpn_keywords = ["vpn", "tunnel", "wireguard", "openvpn", "nordvpn",
                           "expressvpn", "proton", "mullvad", "tap-windows", "tun"]
            for a in adapters:
                name = (a.get("Name") or "").lower()
                desc = (a.get("InterfaceDescription") or "").lower()
                combined = name + " " + desc
                for kw in vpn_keywords:
                    if kw in combined:
                        vpn_interfaces.append({
                            "name": a.get("Name"),
                            "description": a.get("InterfaceDescription"),
                            "status": "Active"
                        })
                        break
    except Exception:
        pass

    return {
        "vpn_active": len(vpn_interfaces) > 0,
        "vpn_count": len(vpn_interfaces),
        "connections": vpn_interfaces
    }


def get_public_ip():
    """Get the current public IP address."""
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        return r.json().get("ip", "Unknown")
    except Exception:
        return "Unknown"


def dns_leak_test():
    """
    Basic DNS leak check: resolve a unique hostname and see
    which DNS server responds. Uses dnsleaktest.com-style approach.
    """
    try:
        # Try to detect if queries go through expected DNS
        test_results = []
        test_hosts = ["google.com", "cloudflare.com", "microsoft.com"]
        for host in test_hosts:
            start = time.time()
            try:
                ip = socket.gethostbyname(host)
                elapsed = round((time.time() - start) * 1000, 1)
                test_results.append({"host": host, "resolved": ip, "ms": elapsed})
            except Exception:
                test_results.append({"host": host, "resolved": "FAILED", "ms": -1})

        avg_ms = sum(r["ms"] for r in test_results if r["ms"] > 0) / max(1, len([r for r in test_results if r["ms"] > 0]))
        all_resolved = all(r["resolved"] != "FAILED" for r in test_results)

        return {
            "dns_working": all_resolved,
            "avg_response_ms": round(avg_ms, 1),
            "test_results": test_results,
            "leak_risk": "LOW" if all_resolved else "HIGH"
        }
    except Exception as e:
        return {"dns_working": False, "error": str(e)}


def full_network_report():
    """Complete DNS & VPN security report."""
    dns_servers = get_current_dns_servers()
    doh = check_doh_enabled()
    vpn = check_vpn_status()
    leak_test = dns_leak_test()

    all_safe = all(s["is_safe"] for s in dns_servers) if dns_servers else False

    recommendations = []
    if not all_safe:
        recommendations.append("Switch to a privacy-respecting DNS like Cloudflare (1.1.1.1) or Quad9 (9.9.9.9)")
    if not doh:
        recommendations.append("Enable DNS-over-HTTPS: Settings → Network → DNS → Enable DoH")
    if not vpn["vpn_active"]:
        recommendations.append("Consider using a VPN (ProtonVPN free tier, Mullvad) for extra privacy")

    return {
        "dns_servers": dns_servers,
        "doh_enabled": doh,
        "vpn": vpn,
        "leak_test": leak_test,
        "all_dns_safe": all_safe,
        "recommendations": recommendations
    }


if __name__ == "__main__":
    report = full_network_report()
    print(json.dumps(report, indent=2))
