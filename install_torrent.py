import re

# 1. Update server.py
with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', encoding='utf-8') as f:
    py = f.read()

magnet_logic = """        if not url:
            return jsonify({"ok": False, "error": "URL required"}), 400

        # Torrent/Magnet Interceptor
        if url.startswith("magnet:") or url.endswith(".torrent"):
            import requests, urllib.parse
            try:
                res = requests.get(f"http://127.0.0.1:8766/stream?magnet={urllib.parse.quote(url)}", timeout=30)
                data = res.json()
                if data.get("ok"):
                    host_ip = request.host.split(':')[0]
                    stream_url = f"http://{host_ip}:8766{data['path']}"
                    return jsonify({
                        "ok": True,
                        "title": data.get("title", "P2P Stream"),
                        "stream_url": stream_url
                    })
                else:
                    return jsonify({"ok": False, "error": data.get("error", "Torrent failed")}), 400
            except Exception as e:
                return jsonify({"ok": False, "error": "Torrent Microservice Offline"}), 500
"""

py = py.replace("""        if not url:
            return jsonify({"ok": False, "error": "URL required"}), 400""", magnet_logic)

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', 'w', encoding='utf-8') as f:
    f.write(py)

# 2. Update start.bat
with open(r'C:\Users\acer\Desktop\Security Suite\start.bat', encoding='utf-8') as f:
    bat = f.read()

# Add logic to kill old node port 8766
bat = bat.replace("""for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8765 " ^| findstr "LISTENING"') do (
    echo  [*] Stopping old server (PID %%a)...
    taskkill /F /PID %%a >nul 2>&1
)""", """for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8765 " ^| findstr "LISTENING"') do (
    echo  [*] Stopping old server (PID %%a)...
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8766 " ^| findstr "LISTENING"') do (
    echo  [*] Stopping old torrent service (PID %%a)...
    taskkill /F /PID %%a >nul 2>&1
)""")

bat = bat.replace("""start "" "http://localhost:8765"
python server.py""", """start "" "http://localhost:8765"
start /B node torrent_service.js
python server.py""")

with open(r'C:\Users\acer\Desktop\Security Suite\start.bat', 'w', encoding='utf-8') as f:
    f.write(bat)
