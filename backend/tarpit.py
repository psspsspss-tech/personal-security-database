import socket
import threading
import time
import datetime

TARPIT_LOGS = []
TARPIT_ACTIVE = False
TARPIT_PORT = 22

def handle_tarpit_connection(conn, addr):
    ip = addr[0]
    TARPIT_LOGS.insert(0, {
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "ip": ip,
        "status": "TRAPPED"
    })
    # Keep log size reasonable
    if len(TARPIT_LOGS) > 100:
        TARPIT_LOGS.pop()
        
    try:
        # Send fake SSH banner to bait scanners into thinking it's an SSH server
        conn.sendall(b"SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.1\r\n")
        
        # Infinite garbage loop (1 null byte every 10 seconds)
        # This forces the attacker's TCP connection to stay open infinitely, wasting their resources.
        while True:
            conn.sendall(b"\x00")
            time.sleep(10)
    except Exception:
        pass # Connection eventually closed or timed out by attacker
    finally:
        try:
            conn.close()
        except:
            pass

def run_tarpit_server(port):
    global TARPIT_ACTIVE, TARPIT_PORT
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Prevent "Address already in use" errors
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        s.listen(10)
        TARPIT_PORT = port
        TARPIT_ACTIVE = True
        
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_tarpit_connection, args=(conn, addr), daemon=True).start()
    except Exception as e:
        print(f"  [!] Failed to start Tarpit on port {port}: {e}")
        if port == 22:
            print("      Falling back to Port 2222...")
            run_tarpit_server(2222)

def start_tarpit_daemon():
    """Starts the Tarpit in a background thread."""
    t = threading.Thread(target=run_tarpit_server, args=(22,), daemon=True)
    t.start()
