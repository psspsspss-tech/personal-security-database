import socket
import threading
import time
import datetime
import hashlib
import network_scanner as netscanner

HONEYPOT_PORTS = {
    21: "FTP (Fake File Transfer Protocol)",
    22: "SSH (Fake Secure Shell)",
    23: "Telnet (Fake Unencrypted Shell)",
    3389: "RDP (Fake Remote Desktop)"
}

BANNERS = {
    21: b"220 (vsFTPd 3.0.3)\r\n",
    22: b"SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.1\r\n",
    23: b"Ubuntu 20.04 LTS\r\nlogin: ",
    3389: b"\x03\x00\x00\x13\x0e\xd0\x00\x00\x12\x34\x00\x02\x09\x08\x00\x00\x00\x00\x00"
}

_active = False

def log_attack(ip, port):
    """Log the attack to the central alerts system."""
    now = datetime.datetime.now().isoformat()
    service_name = HONEYPOT_PORTS.get(port, f"Port {port}")
    
    alert = {
        "id": hashlib.md5(f"honeypot_{ip}_{port}_{time.time()}".encode()).hexdigest(),
        "timestamp": now,
        "severity": "critical",
        "title": "Honeypot Triggered!",
        "message": f"A hostile device ({ip}) attempted to connect to our fake {service_name} service.",
        "data": {"ip": ip, "port": port, "service": service_name},
        "acknowledged": False
    }
    
    netscanner.save_alert(alert)
    print(f"[HONEYPOT] ALARM! {ip} connected to fake port {port}!")

def handle_connection(client_socket, addr, port):
    ip = addr[0]
    try:
        # Ignore our own local system pings or network scanner pings if necessary
        # But for honeypot, we want to catch everything except maybe localhost
        if ip != "127.0.0.1":
            log_attack(ip, port)
            
        # Send fake banner to trick the scanner
        if port in BANNERS:
            client_socket.sendall(BANNERS[port])
            # Keep connection open for 1 second to capture any payload they send
            client_socket.settimeout(1.0)
            try:
                payload = client_socket.recv(1024)
                if payload:
                    print(f"[HONEYPOT] Received payload from {ip}: {payload}")
            except:
                pass
    finally:
        client_socket.close()

def start_listener(port):
    """Start listening on a specific fake port."""
    global _active
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind(("0.0.0.0", port))
        server_socket.listen(5)
        print(f"  Honeypot trap armed on Port {port}")
    except Exception as e:
        print(f"  [!] Failed to arm honeypot on Port {port}: {e}")
        return
        
    while _active:
        try:
            server_socket.settimeout(1.0) # 1 second timeout to allow checking _active
            client_socket, addr = server_socket.accept()
            threading.Thread(target=handle_connection, args=(client_socket, addr, port), daemon=True).start()
        except socket.timeout:
            continue
        except Exception as e:
            if _active:
                print(f"[HONEYPOT] Listener error on port {port}: {e}")
                
    server_socket.close()

def start_honeypot():
    """Ignite all honeypot listeners in the background."""
    global _active
    if _active: return
    _active = True
    
    print("\n  Arming Local Network Honeypot...")
    for port in HONEYPOT_PORTS.keys():
        threading.Thread(target=start_listener, args=(port,), daemon=True).start()

def stop_honeypot():
    global _active
    _active = False
