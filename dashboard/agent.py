#!/usr/bin/env python3
"""
NetHunter Remote Agent - Security Command Center
Run this script on your Kali NetHunter device (or Termux).
It will silently connect to your dashboard, register itself,
and wait for remote commands to execute.
"""

import sys
import time
import json
import uuid
import platform
import subprocess
import urllib.request
import urllib.error

# We dynamically figure out the server URL based on where this was downloaded from,
# or let the user type it if they run it standalone.
SERVER_URL = "http://localhost:5000" # We'll ask the user to input this if it's wrong
POLL_INTERVAL = 5
DEVICE_ID = "nethunter_" + str(uuid.getnode())[:8]

def get_sys_info():
    return {
        "device_id": DEVICE_ID,
        "hostname": platform.node() or "NetHunter",
        "os": platform.system(),
        "platform": platform.platform(),
        "ip": "Local IP"
    }

def register(server_url):
    url = f"{server_url}/api/agents/heartbeat"
    data = json.dumps(get_sys_info()).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        return False

def fetch_commands(server_url):
    url = f"{server_url}/api/agents/poll/{DEVICE_ID}"
    try:
        response = urllib.request.urlopen(url, timeout=5)
        data = json.loads(response.read().decode('utf-8'))
        if data.get("ok"):
            return data.get("commands", [])
    except Exception:
        pass
    return []

def post_result(server_url, cmd_id, command, output, error=False):
    url = f"{server_url}/api/agents/result/{DEVICE_ID}"
    payload = {
        "id": cmd_id,
        "command": command,
        "output": output,
        "error": error,
        "timestamp": time.time()
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def execute_command(server_url, cmd_dict):
    cmd_id = cmd_dict.get("id")
    command = cmd_dict.get("command")
    print(f"[*] Executing remote command: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]:\n" + result.stderr
            
        post_result(server_url, cmd_id, command, output, error=(result.returncode != 0))
    except subprocess.TimeoutExpired:
        post_result(server_url, cmd_id, command, "[ERROR] Command timed out after 30 seconds.", error=True)
    except Exception as e:
        post_result(server_url, cmd_id, command, f"[ERROR] Failed to execute: {str(e)}", error=True)

def main():
    print(f"[*] Starting NetHunter Agent [ID: {DEVICE_ID}]")
    
    server_url = input("Enter Dashboard URL (e.g. http://192.168.1.100:5000): ").strip()
    if not server_url.startswith("http"):
        server_url = "http://" + server_url
        
    print(f"[*] Connecting to {server_url} ...")
    if register(server_url):
        print("[+] Successfully registered with dashboard. Waiting for commands...")
    else:
        print("[-] Registration failed. Make sure the dashboard is running.")
        sys.exit(1)
        
    heartbeat_counter = 0
    while True:
        try:
            cmds = fetch_commands(server_url)
            for c in cmds:
                execute_command(server_url, c)
                
            heartbeat_counter += 1
            if heartbeat_counter >= 6:
                register(server_url)
                heartbeat_counter = 0
                
        except KeyboardInterrupt:
            print("\n[*] Shutting down agent.")
            sys.exit(0)
        except Exception:
            pass
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
