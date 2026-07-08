import socket
import struct
import threading
import time
import json
from collections import deque

class PacketSniffer:
    def __init__(self):
        self.running = False
        self.packet_buffer = deque(maxlen=200) # Store last 200 packets
        self.sniffer_thread = None
        self.s = None

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def parse_packet(self, packet_data):
        try:
            # IP Header is first 20 bytes
            ip_header = packet_data[0:20]
            iph = struct.unpack('!BBHHHBBH4s4s', ip_header)
            
            version_ihl = iph[0]
            ihl = version_ihl & 0xF
            iph_length = ihl * 4
            
            protocol = iph[6]
            s_addr = socket.inet_ntoa(iph[8])
            d_addr = socket.inet_ntoa(iph[9])
            
            proto_name = "UNKNOWN"
            src_port = 0
            dst_port = 0
            
            if protocol == 6: # TCP
                proto_name = "TCP"
                tcp_header = packet_data[iph_length:iph_length+20]
                tcph = struct.unpack('!HHLLBBHHH', tcp_header)
                src_port = tcph[0]
                dst_port = tcph[1]
            elif protocol == 17: # UDP
                proto_name = "UDP"
                udph_length = 8
                udp_header = packet_data[iph_length:iph_length+8]
                udph = struct.unpack('!HHHH', udp_header)
                src_port = udph[0]
                dst_port = udph[1]
            elif protocol == 1: # ICMP
                proto_name = "ICMP"
                
            return {
                "timestamp": time.strftime("%H:%M:%S"),
                "protocol": proto_name,
                "src": f"{s_addr}:{src_port}" if src_port else s_addr,
                "dst": f"{d_addr}:{dst_port}" if dst_port else d_addr,
                "size": len(packet_data)
            }
        except Exception as e:
            return None

    def _sniff_loop(self):
        HOST = self.get_local_ip()
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
            self.s.bind((HOST, 0))
            
            # Include IP headers
            self.s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            
            # Enable promiscuous mode on Windows
            # SIO_RCVALL = 0x98000001
            self.s.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
            
            while self.running:
                try:
                    self.s.settimeout(1.0) # Check flag every second
                    packet_data, addr = self.s.recvfrom(65565)
                    parsed = self.parse_packet(packet_data)
                    if parsed:
                        self.packet_buffer.append(parsed)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Sniffer packet error: {e}")
                    
        except PermissionError:
            self.packet_buffer.append({"protocol": "SYS", "src": "SYSTEM", "dst": "WARNING", "size": 0, "error": "ADMINISTRATOR PRIVILEGES REQUIRED TO SNIFF PACKETS"})
            self.running = False
        except Exception as e:
            self.packet_buffer.append({"protocol": "SYS", "src": "SYSTEM", "dst": "ERROR", "size": 0, "error": str(e)})
            self.running = False
        finally:
            if self.s:
                try:
                    # Disable promiscuous mode
                    self.s.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
                    self.s.close()
                except:
                    pass

    def start(self):
        if self.running: return
        self.running = True
        self.packet_buffer.clear()
        self.packet_buffer.append({"protocol": "SYS", "src": "SYSTEM", "dst": "STARTUP", "size": 0, "timestamp": time.strftime("%H:%M:%S"), "info": "INITIALIZING SNIFFER..."})
        self.sniffer_thread = threading.Thread(target=self._sniff_loop, daemon=True)
        self.sniffer_thread.start()

    def stop(self):
        self.running = False
        if self.sniffer_thread:
            self.sniffer_thread.join(timeout=2.0)
            
    def get_packets(self):
        # Return currently buffered packets and clear the buffer
        packets = list(self.packet_buffer)
        self.packet_buffer.clear()
        return packets

# Global singleton
_instance = PacketSniffer()

def start_sniffer():
    _instance.start()

def stop_sniffer():
    _instance.stop()
    
def get_recent_packets():
    return _instance.get_packets()

def is_running():
    return _instance.running
