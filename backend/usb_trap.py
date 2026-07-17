import subprocess
import threading
import time
import hashlib
import datetime
import network_scanner as netscanner

_active = False
_baseline = set()
_trap_thread = None

def get_usb_devices():
    """Run WMIC to get current USB devices."""
    devices = set()
    try:
        # Get DeviceID of all USB devices
        result = subprocess.run(
            ['wmic', 'path', 'Win32_PnPEntity', 'where', 'PNPClass=\'USB\'', 'get', 'DeviceID'],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        lines = result.stdout.split('\n')
        for line in lines[1:]: # Skip header
            line = line.strip()
            if line:
                devices.add(line)
    except Exception as e:
        print(f"[USB TRAP] Error reading USBs: {e}")
    return devices

def _trap_loop():
    global _active, _baseline
    while _active:
        time.sleep(3)
        current_devices = get_usb_devices()
        
        # Check for new devices not in baseline
        new_devices = current_devices - _baseline
        if new_devices:
            for dev in new_devices:
                # Trigger critical alert
                alert = {
                    "id": hashlib.md5(f"usb_{dev}_{time.time()}".encode()).hexdigest(),
                    "timestamp": datetime.datetime.now().isoformat(),
                    "severity": "critical",
                    "title": "PHYSICAL BREACH: Unknown USB Detected!",
                    "message": f"An unauthorized USB device was just plugged into the server.\nHardware ID: {dev}",
                    "data": {"device_id": dev},
                    "acknowledged": False
                }
                netscanner.save_alert(alert)
                print(f"\n[!] PHYSICAL BREACH ALARM: USB Plugged in! ({dev})\n")
            
            # Update baseline so we don't alert repeatedly for the same device
            _baseline.update(new_devices)

        # Handle removed devices
        removed_devices = _baseline - current_devices
        if removed_devices:
            _baseline.difference_update(removed_devices)

def arm_trap():
    global _active, _baseline, _trap_thread
    if _active:
        return
    print("  [USB TRAP] Baselining current USB devices...")
    _baseline = get_usb_devices()
    print(f"  [USB TRAP] Armed. Watching {len(_baseline)} known devices.")
    _active = True
    _trap_thread = threading.Thread(target=_trap_loop, daemon=True)
    _trap_thread.start()

def disarm_trap():
    global _active
    if not _active:
        return
    _active = False
    print("  [USB TRAP] Disarmed.")

def get_status():
    return {
        "armed": _active,
        "baseline_count": len(_baseline),
        "devices": list(_baseline)
    }
