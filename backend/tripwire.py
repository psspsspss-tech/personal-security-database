import os
import time
import threading
import datetime

TRIPWIRE_DIR = r"C:\Users\acer\Desktop\Passwords_DO_NOT_OPEN"
TRIPWIRE_FILE = os.path.join(TRIPWIRE_DIR, "bank_details.txt")

TRIPWIRE_ACTIVE = False
TRIPWIRE_BREACHED = False
TRIPWIRE_BREACH_INFO = None
_original_mtime = None

def setup_honeyfile():
    global _original_mtime
    if not os.path.exists(TRIPWIRE_DIR):
        os.makedirs(TRIPWIRE_DIR)
    
    if not os.path.exists(TRIPWIRE_FILE):
        with open(TRIPWIRE_FILE, "w") as f:
            f.write("ACCOUNT: 8892-1002-3991\nROUTING: 12200049\nPIN: 8392\n")
    
    _original_mtime = os.path.getmtime(TRIPWIRE_FILE)

def monitor_loop():
    global TRIPWIRE_BREACHED, TRIPWIRE_BREACH_INFO, _original_mtime
    while True:
        try:
            if not os.path.exists(TRIPWIRE_FILE):
                # File was deleted!
                TRIPWIRE_BREACHED = True
                TRIPWIRE_BREACH_INFO = {"time": datetime.datetime.now().strftime("%H:%M:%S"), "event": "FILE DELETED"}
                break
                
            current_mtime = os.path.getmtime(TRIPWIRE_FILE)
            if current_mtime != _original_mtime:
                # File was modified!
                TRIPWIRE_BREACHED = True
                TRIPWIRE_BREACH_INFO = {"time": datetime.datetime.now().strftime("%H:%M:%S"), "event": "FILE MODIFIED"}
                break
        except Exception:
            pass
        time.sleep(1)

def start_tripwire_daemon():
    global TRIPWIRE_ACTIVE
    try:
        setup_honeyfile()
        t = threading.Thread(target=monitor_loop, daemon=True)
        t.start()
        TRIPWIRE_ACTIVE = True
    except Exception as e:
        print(f"  [!] Failed to start Tripwire: {e}")
