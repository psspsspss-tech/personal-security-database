"""
Unified NetHunter Agent
- Scans Bluetooth (if available)
- Scans WiFi (wlan0)
- Connects to Dashboard for Remote Kali Shell
"""

import subprocess
import time
import requests
import socket
import sys
import threading

# ─────────────────────────────────────────────────────────
SERVER_URL = "http://192.168.1.10:8765"   # Primary target (updated to match your current IP)
FALLBACK_URLS = ["http://127.0.0.1:8765", "http://security-suite.local:8765"]
# ─────────────────────────────────────────────────────────

def get_active_server_url():
    """Test primary URL and fallbacks, return the first one that responds."""
    # First try the configured SERVER_URL
    try:
        r = requests.get(f"{SERVER_URL}/api/status", timeout=2)
        if r.status_code == 200:
            return SERVER_URL
    except Exception:
        pass

    # Try local and mDNS fallbacks
    for url in FALLBACK_URLS:
        try:
            r = requests.get(f"{url}/api/status", timeout=2)
            if r.status_code == 200:
                print(f"[*] Found active server at fallback URL: {url}")
                return url
        except Exception:
            pass

    return SERVER_URL # default back to primary if all fail


def get_bt_devices():
    devices = []
    try:
        proc = subprocess.Popen(["bluetoothctl", "scan", "on"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(SCAN_DURATION)
        proc.terminate()
        proc.wait()

        r = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if line.startswith("Device "):
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    devices.append({"mac": parts[1], "name": parts[2]})
    except Exception:
        pass
    return devices

def get_wifi_networks():
    networks = []
    try:
        # Using iw dev wlan0 scan
        r = subprocess.run(["iw", "dev", "wlan0", "scan"], capture_output=True, text=True)
        current_bssid = ""
        current_ssid = ""
        current_sig = ""
        current_sec = "Open"
        
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("BSS "):
                if current_bssid:
                    networks.append({"bssid": current_bssid, "ssid": current_ssid, "signal": current_sig, "security": current_sec})
                current_bssid = line.split(" ")[1].split("(")[0]
                current_ssid = "<Hidden>"
                current_sec = "Open"
            elif line.startswith("SSID:"):
                current_ssid = line.split("SSID:")[1].strip()
            elif line.startswith("signal:"):
                current_sig = line.split("signal:")[1].strip()
            elif "WPA" in line or "RSN" in line:
                current_sec = "WPA2/3"
                
        if current_bssid:
             networks.append({"bssid": current_bssid, "ssid": current_ssid, "signal": current_sig, "security": current_sec})
    except Exception:
        pass
    return networks

ACTIVE_URL = SERVER_URL

def remote_shell_thread():
    while True:
        try:
            r = requests.get(f"{ACTIVE_URL}/api/kali/poll", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("ok") and data.get("command"):
                    cmd = data["command"]
                    print(f"[*] Remote Shell Executing: {cmd}")
                    try:
                        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True, errors="replace")
                    except subprocess.CalledProcessError as e:
                        out = e.output
                    except Exception as e:
                        out = f"[Agent Error] {str(e)}\n"
                    
                    try:
                        requests.post(f"{ACTIVE_URL}/api/kali/output", json={"output": out}, timeout=5)
                    except Exception as e:
                        print(f"[!] Failed to send output to dashboard: {e}")
        except Exception as e:
            pass
        time.sleep(2)

def check_for_updates():
    """Download the latest agent script from the server and auto-update if different."""
    try:
        r = requests.get(f"{ACTIVE_URL}/nethunter_agent.py", timeout=5)
        if r.status_code == 200:
            server_code = r.text
            with open(__file__, "r", encoding="utf-8") as f:
                local_code = f.read()
            
            if server_code.strip() != local_code.strip() and len(server_code) > 100:
                print("[*] New agent update detected on server! Overwriting local file...")
                with open(__file__, "w", encoding="utf-8") as f:
                    f.write(server_code)
                print("[*] Restarting agent with updated script...")
                time.sleep(1)
                import os
                import sys
                os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        print(f"[-] Auto-update check failed: {e}")

def main():
    global ACTIVE_URL
    print("[*] Resolving dashboard server address...")
    ACTIVE_URL = get_active_server_url()
    
    print("=" * 50)
    print("  Unified NetHunter Surveillance & Shell Node  ")
    print(f"  Reporting to: {ACTIVE_URL}")
    print("=" * 50)

    # Start shell polling thread
    t = threading.Thread(target=remote_shell_thread, daemon=True)
    t.start()
    print("[+] Remote Shell connected. Listening for commands...")

    # Main telemetry loop
    attempt = 1
    while True:
        # Check for remote updates
        check_for_updates()

        print(f"[*] Sweeping WiFi and BT spectrums...")
        bt = get_bt_devices()
        wf = get_wifi_networks()
        
        reporter = socket.gethostname() or "NetHunter"
        
        try:
            r1 = requests.post(f"{ACTIVE_URL}/api/bluetooth/update", json={"reporter": reporter, "devices": bt}, timeout=5)
            r2 = requests.post(f"{ACTIVE_URL}/api/wifi/update", json={"reporter": reporter, "networks": wf}, timeout=5)
            if r1.status_code == 200 or r2.status_code == 200:
                print(f"[+] Beamed {len(bt)} BT devices and {len(wf)} WiFi networks.")
                attempt = 1 # reset attempt counter on successful ping
        except Exception:
            print(f"[-] Failed to reach server (attempt {attempt}) - will retry")
            attempt += 1
            # Re-resolve in case server IP has changed on network bounce
            ACTIVE_URL = get_active_server_url()
            
        time.sleep(REPORT_INTERVAL)

if __name__ == "__main__":
    main()

