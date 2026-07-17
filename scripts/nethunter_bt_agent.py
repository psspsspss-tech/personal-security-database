#!/usr/bin/env python3
"""
nethunter_bt_agent.py — Bluetooth Surveillance Node
===================================================
Runs on: Kali NetHunter (Android) or any Linux with bluetoothctl
Purpose: Sweeps the local physical area for Bluetooth and BLE devices
         and streams the data to your Security Command Center.

SETUP:
------
1. Copy this file to your NetHunter device.
2. Edit SERVER_URL below to your Windows PC's IP address.
3. Ensure bluetooth is unblocked: `rfkill unblock bluetooth`
4. Run: `python3 nethunter_bt_agent.py`
"""

import subprocess
import time
import requests
import socket
import sys

# ─────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────
SERVER_URL = "http://192.168.1.3:8765"   # Edit this to your PC's IP
SCAN_DURATION = 10                       # Seconds to actively scan
REPORT_INTERVAL = 15                     # Seconds between scans
# ─────────────────────────────────────────────────────────

def get_bt_devices():
    """Uses bluetoothctl to scan and list nearby devices."""
    devices = []
    try:
        print(f"[*] Sweeping Bluetooth spectrum for {SCAN_DURATION}s...")
        # Start scanning in background
        proc = subprocess.Popen(["bluetoothctl", "scan", "on"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(SCAN_DURATION)
        proc.terminate()
        proc.wait()

        # Read discovered devices
        r = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if line.startswith("Device "):
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    mac = parts[1]
                    name = parts[2]
                    # Filter out un-named phantom devices if desired, but for surveillance we want everything
                    devices.append({"mac": mac, "name": name})
    except FileNotFoundError:
        print("[!] Error: 'bluetoothctl' not found. Are you on Kali/Linux?")
    except Exception as e:
        print(f"[!] Error scanning BT: {e}")
        
    return devices

def main():
    print("=" * 50)
    print("  NetHunter Bluetooth Surveillance Node  ")
    print(f"  Reporting to: {SERVER_URL}")
    print("=" * 50)

    if "192.168.1.x" in SERVER_URL:
        print("\n[!] ERROR: Edit SERVER_URL in this file to point to your PC's IP!\n")
        sys.exit(1)

    while True:
        devices = get_bt_devices()
        payload = {
            "reporter": socket.gethostname() or "NetHunter",
            "devices": devices
        }
        
        try:
            r = requests.post(f"{SERVER_URL}/api/bluetooth/update", json=payload, timeout=5)
            if r.status_code == 200:
                print(f"[+] Successfully beamed {len(devices)} devices to dashboard.")
            else:
                print(f"[-] Server returned {r.status_code}: {r.text}")
        except requests.exceptions.ConnectionError:
            print("[-] Connection Error: Cannot reach dashboard server.")
        except Exception as e:
            print(f"[-] Failed to send to server: {e}")
            
        print(f"[*] Sleeping for {REPORT_INTERVAL}s...\n")
        time.sleep(REPORT_INTERVAL)

if __name__ == "__main__":
    main()
