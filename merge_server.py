import os
import re

desktop_server = r"C:\Users\acer\Desktop\Security Suite\backend\server.py"

with open(desktop_server, 'r', encoding='utf-8') as f:
    d_content = f.read()

# 1. Imports
d_content = d_content.replace(
    "from pathlib import Path\nfrom flask import Flask, jsonify, request, send_from_directory, abort\nfrom flask_cors import CORS",
    "import eventlet\neventlet.monkey_patch()\nimport paramiko\nfrom pathlib import Path\nfrom flask import Flask, jsonify, request, send_from_directory, abort\nfrom flask_cors import CORS\nfrom flask_socketio import SocketIO, emit"
)

# 2. Add offensive_tools
d_content = d_content.replace(
    "import network_scanner as netscanner\n",
    "import network_scanner as netscanner\nimport offensive_tools as offensive\n"
)

# 3. Add socketio
d_content = d_content.replace(
    "CORS(app)\n",
    "CORS(app)\nsocketio = SocketIO(app, cors_allowed_origins=\"*\", async_mode='eventlet')\n"
)

# 4. Remove old Kali global vars
d_content = re.sub(r"_kali_terminal = \{\"queue\": \[\], \"output\": \"\"\}\n_kali_lock = threading\.Lock\(\)\n", "", d_content)

# 5. Replace app.run with socketio.run
d_content = d_content.replace(
    'app.run(host="0.0.0.0", port=8765, debug=False, use_reloader=False)',
    'socketio.run(app, host="0.0.0.0", port=8765, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)'
)

# 6. We need to append the SSH sessions and offensive tools routes.
ssh_and_offensive_code = """
# ─────────────────────────────────────────────
# SSH Terminal Sessions (WebSSH)
# ─────────────────────────────────────────────
ssh_sessions = {}

@socketio.on('ssh_connect')
def handle_ssh_connect(data):
    ip = data.get('ip')
    username = data.get('username', 'kali')
    password = data.get('password')
    sid = request.sid
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, port=22, username=username, password=password, timeout=5)
        
        channel = client.invoke_shell(term='xterm-256color', width=100, height=30)
        channel.setblocking(False)
        
        ssh_sessions[sid] = {'client': client, 'channel': channel}
        emit('ssh_status', {'status': 'connected'})
        
        socketio.start_background_task(read_from_ssh, sid, channel)
        
    except Exception as e:
        print(f"SSH Connection Error to {ip}: {str(e)}")
        emit('ssh_status', {'status': 'error', 'message': str(e)})

def read_from_ssh(sid, channel):
    while sid in ssh_sessions:
        if channel.recv_ready():
            try:
                data = channel.recv(4096).decode('utf-8', errors='replace')
                if data:
                    socketio.emit('ssh_output', {'data': data}, to=sid)
            except Exception:
                break
        else:
            socketio.sleep(0.01)

@socketio.on('ssh_input')
def handle_ssh_input(data):
    sid = request.sid
    if sid in ssh_sessions:
        channel = ssh_sessions[sid]['channel']
        if channel.send_ready():
            channel.send(data.get('input', ''))

@socketio.on('ssh_resize')
def handle_ssh_resize(data):
    sid = request.sid
    if sid in ssh_sessions:
        channel = ssh_sessions[sid]['channel']
        cols = data.get('cols', 100)
        rows = data.get('rows', 30)
        try:
            channel.resize_pty(width=cols, height=rows)
        except Exception:
            pass

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in ssh_sessions:
        try:
            ssh_sessions[sid]['client'].close()
        except Exception:
            pass
        del ssh_sessions[sid]

@app.route("/api/device/scan", methods=["POST"])
def api_device_scan():
    try:
        body = request.get_json()
        ip = body.get("ip")
        if not ip: return jsonify({"ok": False, "error": "IP required"}), 400
        result = offensive.python_port_scan(ip)
        return jsonify(result)
    except Exception as e: return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/device/block", methods=["POST"])
def api_device_block():
    try:
        body = request.get_json()
        ip = body.get("ip")
        mac = body.get("mac")
        action = body.get("action", "block")
        if not ip: return jsonify({"ok": False, "error": "IP required"}), 400
        if action == "unblock": return jsonify(offensive.arp_unblock(ip))
        if not mac: return jsonify({"ok": False, "error": "MAC required for blocking"}), 400
        scan = netscanner.get_last_scan() or {}
        gateway = scan.get("gateway")
        return jsonify(offensive.arp_block(ip, mac, gateway))
    except Exception as e: return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/device/wake", methods=["POST"])
def api_device_wake():
    try:
        body = request.get_json()
        mac = body.get("mac")
        if not mac: return jsonify({"ok": False, "error": "MAC required"}), 400
        return jsonify(offensive.wake_on_lan(mac))
    except Exception as e: return jsonify({"ok": False, "error": str(e)}), 500
"""

# Find a good place to inject the new routes (e.g., right before Startup)
d_content = d_content.replace(
    "# ─────────────────────────────────────────────\n# Startup\n# ─────────────────────────────────────────────",
    ssh_and_offensive_code + "\n# ─────────────────────────────────────────────\n# Startup\n# ─────────────────────────────────────────────"
)

with open(desktop_server, 'w', encoding='utf-8') as f:
    f.write(d_content)

print("Merged server.py")
