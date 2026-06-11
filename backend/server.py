"""
server.py — Personal Security Suite API Server
Flask REST API that the dashboard polls for real data.
Run with: python server.py
Dashboard will be served at http://localhost:8765
"""

import os
import sys
import json
import threading
import time
import datetime
import hashlib

# ─────────────────────────────────────────────
# Server version — changes every restart.
# All connected browsers auto-reload when this changes.
# ─────────────────────────────────────────────
SERVER_START_TIME = datetime.datetime.now()
SERVER_VERSION = hashlib.md5(
    SERVER_START_TIME.isoformat().encode()
).hexdigest()[:12]
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent dir to path so we can import sibling modules
BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))

import system_monitor as sysmon
import network_scanner as netscanner

# New modules — imported with graceful fallback
try:
    import event_log_analyzer as evtlog
    HAS_EVTLOG = True
except ImportError:
    HAS_EVTLOG = False

try:
    import dns_checker as dnschk
    HAS_DNS = True
except ImportError:
    HAS_DNS = False

try:
    import process_monitor as procmon
    HAS_PROCMON = True
except ImportError:
    HAS_PROCMON = False

try:
    import telegram_bot as tgbot
    HAS_TG = True
except ImportError:
    HAS_TG = False

try:
    import agent_manager as agentmgr
    HAS_AGENTS = True
except ImportError:
    HAS_AGENTS = False

CONFIG_FILE = BASE_DIR / "config.json"

def load_app_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

app = Flask(__name__, static_folder=str(ROOT_DIR / "dashboard"), static_url_path="")
CORS(app)


@app.after_request
def add_no_cache_headers(response):
    """Prevent browsers from caching CSS/JS/HTML so updates reach all devices immediately."""
    content_type = response.content_type or ''
    if any(t in content_type for t in ('text/html', 'text/css', 'javascript', 'application/json')):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Server-Version'] = SERVER_VERSION
    return response

# ─────────────────────────────────────────────
# Cache to avoid hammering the system
# ─────────────────────────────────────────────
_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = {
    "system": 10,      # seconds
    "devices": 60,
    "alerts": 5,
}

_bluetooth_cache = {"last_updated": None, "devices": [], "reporter": None}
_bt_lock = threading.Lock()


def get_cached(key, ttl, fetch_fn):
    with _cache_lock:
        entry = _cache.get(key)
        now = time.time()
        if entry and (now - entry["ts"]) < ttl:
            return entry["data"]
    data = fetch_fn()
    with _cache_lock:
        _cache[key] = {"data": data, "ts": time.time()}
    return data


def get_local_ip():
    """Get this machine's LAN IP address."""
    import socket as _sock
    try:
        s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ─────────────────────────────────────────────
# Serve Dashboard Static Files
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(str(ROOT_DIR / "dashboard"), "index.html")


@app.route("/sw.js")
def service_worker():
    """Serve service worker with correct scope header (must be at root)."""
    from flask import make_response
    resp = make_response(
        send_from_directory(str(ROOT_DIR / "dashboard"), "sw.js",
                            mimetype="application/javascript")
    )
    # Allow SW to control the entire site scope
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


@app.route("/manifest.json")
def manifest():
    svg_icon = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='512' height='512'%3E%3Crect width='24' height='24' fill='%23070711'/%3E%3Cpath fill='%2300d4ff' d='M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z'/%3E%3C/svg%3E"
    
    return jsonify({
        "name": "Security Command Center",
        "short_name": "SecCenter",
        "description": "Personal Security Dashboard",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#070711",
        "theme_color": "#00d4ff",
        "icons": [
            {"src": svg_icon, "sizes": "192x192 512x512", "type": "image/svg+xml", "purpose": "any maskable"}
        ]
    })


@app.route("/api/network-info")
def api_network_info():
    """Return local network info for QR code display."""
    ip = get_local_ip()
    return jsonify({
        "ok": True,
        "local_ip": ip,
        "port": 8765,
        "dashboard_url": f"http://{ip}:8765",
        "agent_heartbeat_url": f"http://{ip}:8765/api/agent/heartbeat"
    })


@app.route("/api/version")
def api_version():
    """
    Returns the current server version (changes every restart).
    Dashboard clients poll this every 30s — if version changes,
    they auto-reload to get the latest dashboard code.
    """
    return jsonify({
        "ok": True,
        "version": SERVER_VERSION,
        "started_at": SERVER_START_TIME.isoformat(),
        "uptime_seconds": int((datetime.datetime.now() - SERVER_START_TIME).total_seconds())
    })


# ─────────────────────────────────────────────
# Active Device Control Actions
# ─────────────────────────────────────────────

@app.route("/api/device/deep-scan", methods=["POST"])
def api_device_deep_scan():
    """Run an aggressive port scan on a specific IP."""
    data = request.get_json(force=True)
    ip = data.get("ip")
    if not ip:
        return jsonify({"ok": False, "error": "IP required"}), 400
    try:
        open_ports = netscanner.action_deep_scan(ip)
        return jsonify({"ok": True, "open_ports": open_ports})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/device/block", methods=["POST"])
def api_device_block():
    """Block a specific IP via Windows Firewall."""
    data = request.get_json(force=True)
    ip = data.get("ip")
    if not ip:
        return jsonify({"ok": False, "error": "IP required"}), 400
    try:
        success = netscanner.action_block_ip(ip)
        return jsonify({"ok": success})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/device/wol", methods=["POST"])
def api_device_wol():
    """Send a Wake-on-LAN packet to a specific MAC."""
    data = request.get_json(force=True)
    mac = data.get("mac")
    if not mac:
        return jsonify({"ok": False, "error": "MAC required"}), 400
    try:
        success = netscanner.action_wol(mac)
        return jsonify({"ok": success})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ─────────────────────────────────────────────
# Agent API Routes (remote devices check in here)
# ─────────────────────────────────────────────
@app.route("/api/agent/heartbeat", methods=["POST"])
def api_agent_heartbeat():
    """Receive a heartbeat from a remote agent."""
    if not HAS_AGENTS:
        return jsonify({"ok": False, "error": "Agent manager not available"}), 503
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"ok": False, "error": "No data"}), 400
        agent = agentmgr.register_agent(data)

        # Fire Telegram alert if new device
        if HAS_TG and data.get("_first_seen"):
            tgbot.send_message(
                f"📱 New device connected: <b>{data.get('hostname')}</b>\n"
                f"Platform: {data.get('platform')} | IP: {data.get('ip')}"
            )
        return jsonify({"ok": True, "message": "Heartbeat received", "device_id": agent["device_id"]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/agents", methods=["GET"])
def api_get_agents():
    """List all registered remote agents."""
    if not HAS_AGENTS:
        return jsonify({"ok": True, "data": {"total": 0, "online": 0, "offline": 0, "agents": []}})
    try:
        summary = agentmgr.get_summary()
        return jsonify({"ok": True, "data": summary})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/agents/<device_id>", methods=["DELETE"])
def api_remove_agent(device_id):
    """Remove an agent from the registry."""
    if not HAS_AGENTS:
        return jsonify({"ok": False, "error": "Not available"}), 503
    try:
        ok = agentmgr.remove_agent(device_id)
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/agent/setup-info")
def api_agent_setup_info():
    """Return setup instructions pre-filled with this server's IP."""
    ip = get_local_ip()
    return jsonify({
        "ok": True,
        "server_ip": ip,
        "dashboard_url": f"http://{ip}:8765",
        "heartbeat_url": f"http://{ip}:8765/api/agent/heartbeat",
        "android_steps": [
            "Install Termux from F-Droid (https://f-droid.org)",
            "Open Termux and run: pkg update && pkg install python",
            "Run: pip install psutil requests",
            f"Download agent.py from: http://{ip}:8765/agent.py",
            "Run: python agent.py"
        ],
        "windows_steps": [
            "Install Python from https://python.org",
            "Open Command Prompt and run: pip install psutil requests",
            f"Download agent.py from: http://{ip}:8765/agent.py",
            "Run: python agent.py"
        ],
        "ios_steps": [
            f"Open Safari and go to: http://{ip}:8765",
            "Tap the Share button (box with arrow)",
            "Tap 'Add to Home Screen'",
            "Tap 'Add' — the dashboard is now installed as an app!"
        ]
    })


@app.route("/agent.py")
def serve_agent():
    """Serve the agent.py script so other devices can download it easily."""
    return send_from_directory(str(ROOT_DIR), "agent.py", mimetype="text/plain")


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────
@app.route("/api/status")
def api_status():
    """Overall security status — used by dashboard header."""
    try:
        report = get_cached("system", CACHE_TTL["system"], sysmon.full_report)
        scan = netscanner.get_last_scan() or {}
        devices = scan.get("devices", [])
        unknown_count = sum(1 for d in devices if d.get("status") == "unknown")

        return jsonify({
            "ok": True,
            "security_score": report["security_score"]["score"],
            "deductions": report["security_score"]["deductions"],
            "firewall_ok": all(v == "ON" for v in report["firewall"].get("profiles", {}).values()),
            "antivirus_ok": report["defender"].get("antivirus_enabled", False),
            "realtime_ok": report["defender"].get("realtime_protection", False),
            "unknown_devices": unknown_count,
            "pending_updates": report["pending_updates"].get("pending_count", -1),
            "system": report["system"],
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/system")
def api_system():
    """Detailed system security report."""
    try:
        report = get_cached("system", CACHE_TTL["system"], sysmon.full_report)
        return jsonify({"ok": True, "data": report})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/devices")
def api_devices():
    """Network device scan results."""
    try:
        scan = netscanner.get_last_scan()
        if scan is None:
            # Trigger a fresh scan synchronously if none yet
            scan = netscanner.scan_and_check()
            netscanner._last_scan_result = scan
        return jsonify({"ok": True, "data": scan})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/scan", methods=["POST"])
def api_trigger_scan():
    """Manually trigger a network scan."""
    try:
        result = netscanner.scan_and_check()
        netscanner._last_scan_result = result
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/whitelist", methods=["GET"])
def api_get_whitelist():
    """Get all whitelisted devices."""
    try:
        whitelist = netscanner.load_whitelist()
        return jsonify({"ok": True, "data": list(whitelist.values())})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/whitelist/add", methods=["POST"])
def api_whitelist_add():
    """Add a device to the whitelist."""
    try:
        body = request.get_json()
        mac = body.get("mac", "").strip()
        name = body.get("name", "").strip() or "Unknown Device"
        notes = body.get("notes", "").strip()
        if not mac:
            return jsonify({"ok": False, "error": "MAC address required"}), 400
        success = netscanner.add_to_whitelist(mac, name, notes)
        return jsonify({"ok": success})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/whitelist/remove", methods=["POST"])
def api_whitelist_remove():
    """Remove a device from the whitelist."""
    try:
        body = request.get_json()
        mac = body.get("mac", "").strip()
        if not mac:
            return jsonify({"ok": False, "error": "MAC address required"}), 400
        success = netscanner.remove_from_whitelist(mac)
        return jsonify({"ok": success})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/alerts", methods=["GET"])
def api_alerts():
    """Get recent security alerts."""
    try:
        alerts = netscanner.load_alerts()
        return jsonify({"ok": True, "data": alerts, "count": len(alerts)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/alerts/acknowledge", methods=["POST"])
def api_acknowledge_alert():
    """Acknowledge an alert."""
    try:
        body = request.get_json()
        alert_id = body.get("id")
        alerts = netscanner.load_alerts()
        for alert in alerts:
            if alert.get("id") == alert_id:
                alert["acknowledged"] = True
        alerts_file = BASE_DIR / "alerts.json"
        with open(alerts_file, "w") as f:
            json.dump(alerts, f, indent=2)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/ports")
def api_ports():
    """Get list of open ports."""
    try:
        ports = sysmon.get_open_ports()
        return jsonify({"ok": True, "data": ports})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/breach-check", methods=["POST"])
def api_breach_check():
    """Check if an email has been in known data breaches via HIBP API."""
    import requests as req
    import hashlib

    try:
        body = request.get_json()
        email = body.get("email", "").strip()
        if not email:
            return jsonify({"ok": False, "error": "Email required"}), 400

        # Use haveibeenpwned.com API (public, no key needed for basic check)
        headers = {"User-Agent": "PersonalSecuritySuite/1.0"}
        response = req.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            breaches = response.json()
            return jsonify({
                "ok": True,
                "found": True,
                "breach_count": len(breaches),
                "breaches": [{"name": b.get("Name"), "date": b.get("BreachDate"), "description": b.get("Description", "")[:200]} for b in breaches[:10]]
            })
        elif response.status_code == 404:
            return jsonify({"ok": True, "found": False, "breach_count": 0, "breaches": []})
        else:
            return jsonify({"ok": False, "error": f"HIBP API returned {response.status_code}. You may need an API key for this feature."}), 502
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/eventlog")
def api_event_log():
    """Windows Security Event Log — failed logins, lockouts, etc."""
    if not HAS_EVTLOG:
        return jsonify({"ok": False, "error": "Event log module not available"}), 503
    try:
        hours = int(request.args.get("hours", 24))
        data = get_cached(f"evtlog_{hours}", 60, lambda: evtlog.get_failed_login_summary(hours_back=hours))
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/dns")
def api_dns():
    """DNS servers, VPN status, and network security report."""
    if not HAS_DNS:
        return jsonify({"ok": False, "error": "DNS module not available"}), 503
    try:
        data = get_cached("dns", 30, dnschk.full_network_report)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/processes")
def api_processes():
    """Networked process monitor — suspicious processes with connections."""
    if not HAS_PROCMON:
        return jsonify({"ok": False, "error": "Process monitor not available"}), 503
    try:
        data = get_cached("processes", 15, procmon.get_summary)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/config", methods=["GET"])
def api_get_config():
    """Get current app configuration (without sensitive tokens)."""
    try:
        cfg = load_app_config()
        # Mask the bot token
        tg = cfg.get("telegram", {})
        if tg.get("bot_token"):
            tg["bot_token_set"] = True
            tg["bot_token"] = "***hidden***"
        return jsonify({"ok": True, "data": cfg})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/config", methods=["POST"])
def api_save_config():
    """Save configuration (Telegram token, chat_id, alert settings)."""
    try:
        body = request.get_json()
        cfg = load_app_config()
        # Update telegram section
        if "telegram" in body:
            tg_new = body["telegram"]
            if "bot_token" in tg_new and tg_new["bot_token"] != "***hidden***":
                cfg.setdefault("telegram", {})["bot_token"] = tg_new["bot_token"]
            if "chat_id" in tg_new:
                cfg.setdefault("telegram", {})["chat_id"] = tg_new["chat_id"]
            if "enabled" in tg_new:
                cfg.setdefault("telegram", {})["enabled"] = tg_new["enabled"]
        if "alerts" in body:
            cfg["alerts"] = body["alerts"]
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/telegram/test", methods=["POST"])
def api_telegram_test():
    """Send a test Telegram message."""
    if not HAS_TG:
        return jsonify({"ok": False, "error": "Telegram module not available"}), 503
    try:
        ok, err = tgbot.send_test_message()
        return jsonify({"ok": ok, "error": err})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/telegram/get-chatid", methods=["POST"])
def api_telegram_get_chatid():
    """Auto-detect Telegram chat_id from recent bot messages."""
    if not HAS_TG:
        return jsonify({"ok": False, "error": "Telegram module not available"}), 503
    try:
        body = request.get_json()
        token = body.get("bot_token", "").strip()
        if not token:
            return jsonify({"ok": False, "error": "bot_token required"}), 400
        chat_id, err = tgbot.get_chat_id(token)
        if chat_id:
            return jsonify({"ok": True, "chat_id": chat_id})
        return jsonify({"ok": False, "error": err})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────
# Bluetooth Surveillance (NetHunter)
# ─────────────────────────────────────────────

@app.route("/api/bluetooth/update", methods=["POST"])
def api_bt_update():
    """Receive BT radar data from NetHunter agent."""
    try:
        body = request.get_json()
        with _bt_lock:
            _bluetooth_cache["devices"] = body.get("devices", [])
            _bluetooth_cache["reporter"] = body.get("reporter", "Unknown")
            import datetime
            _bluetooth_cache["last_updated"] = datetime.datetime.now().isoformat()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/bluetooth", methods=["GET"])
def api_bt_get():
    """Serve BT radar data to the dashboard."""
    with _bt_lock:
        return jsonify({"ok": True, "data": _bluetooth_cache})

# ─────────────────────────────────────────────
# Mobile Toolkit (Offensive/Diagnostic)
# ─────────────────────────────────────────────

@app.route("/api/toolkit/ping", methods=["POST"])
def api_toolkit_ping():
    try:
        ip = request.get_json().get("ip")
        if not ip: return jsonify({"ok": False, "error": "IP required"}), 400
        cmd = ["ping", "-n", "4", "-w", "1000", ip] if platform.system() == "Windows" else ["ping", "-c", "4", "-W", "1", ip]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return jsonify({"ok": True, "output": r.stdout})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/toolkit/traceroute", methods=["POST"])
def api_toolkit_traceroute():
    try:
        ip = request.get_json().get("ip")
        if not ip: return jsonify({"ok": False, "error": "IP required"}), 400
        cmd = ["tracert", "-d", "-h", "15", "-w", "500", ip] if platform.system() == "Windows" else ["traceroute", "-n", "-m", "15", "-w", "1", ip]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return jsonify({"ok": True, "output": r.stdout})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ─────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────
def startup():
    """Initialize background tasks on server start."""
    lan_ip = get_local_ip()
    print("=" * 55)
    print("  Personal Security Command Center — ONLINE")
    print("=" * 55)
    print(f"  This PC   :  http://localhost:8765")
    print(f"  iPhone/Android:  http://{lan_ip}:8765   <-- use this!")
    print(f"  Server version:  {SERVER_VERSION}")
    print("=" * 55)
    print("\n  Starting background network scanner...")
    # Do an initial scan in background
    threading.Thread(target=lambda: setattr(
        netscanner, '_last_scan_result', netscanner.scan_and_check()
    ), daemon=True).start()
    # Start continuous scanner (every 90 seconds)
    netscanner.start_background_scanner(interval=90)
    print("  Network scanner active")
    print(f"\n  Open on iPhone: http://{lan_ip}:8765\n")


if __name__ == "__main__":
    startup()
    app.run(host="0.0.0.0", port=8765, debug=False, use_reloader=False)
