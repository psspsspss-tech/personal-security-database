"""
server.py — Personal Security Suite API Server
Flask REST API that the dashboard polls for real data.
Run with: python server.py
Dashboard will be served at http://localhost:8767
"""

import os
import sys
import warnings

warnings.simplefilter("ignore")
if sys.stdout is None:
    class DummyWriter:
        def write(self, *args, **kwargs): pass
        def flush(self, *args, **kwargs): pass
    sys.stdout = DummyWriter()
    sys.stderr = DummyWriter()

import json
import psutil
import shutil
try:
    import winreg
except ImportError:
    winreg = None

import threading
import time
import datetime
import hashlib
import platform
import subprocess

# --- GLOBAL POPUP SUPPRESSOR ---
# Force all subprocesses to hide their black CMD windows on Windows
if platform.system() == "Windows":
    _orig_popen_init = subprocess.Popen.__init__
    def _patched_popen_init(self, *args, **kwargs):
        kwargs['creationflags'] = 0x08000000
        _orig_popen_init(self, *args, **kwargs)
    subprocess.Popen.__init__ = _patched_popen_init
# -------------------------------
import imageio_ffmpeg
from eventlet import tpool

# ─────────────────────────────────────────────
# Server version — changes every restart.
# All connected browsers auto-reload when this changes.
# ─────────────────────────────────────────────
SERVER_START_TIME = datetime.datetime.now()
SERVER_VERSION = hashlib.md5(
    SERVER_START_TIME.isoformat().encode()
).hexdigest()[:12]
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, abort, Response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    if sys.stdout is not None:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr is not None:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent dir to path so we can import sibling modules
if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys._MEIPASS)
    BASE_DIR = ROOT_DIR / "backend"
else:
    BASE_DIR = Path(__file__).parent
    ROOT_DIR = BASE_DIR.parent

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(ROOT_DIR))

import system_monitor as sysmon
import network_scanner as netscanner
import tarpit
import tripwire

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


try:
    import offensive_tools as offensive
    HAS_OFFENSIVE = True
except ImportError:
    HAS_OFFENSIVE = False

try:
    import osint_modules.ip_intel as ip_intel
    import osint_modules.user_intel as user_intel
    import osint_modules.phone_intel as phone_intel
    import osint_modules.exif_intel as exif_intel
    import osint_modules.email_intel as email_intel
    HAS_OSINT = True
except ImportError:
    HAS_OSINT = False
    
CONFIG_FILE = BASE_DIR / "config.json"


def load_app_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

app = Flask(__name__, static_folder=str(ROOT_DIR / "dashboard"), static_url_path="")
CORS(app)

# Suppress highly frequent status/version check logs to avoid console clutter
import logging
class TelemetryLogFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        return "/api/status" not in msg and "/api/version" not in msg

logging.getLogger("werkzeug").addFilter(TelemetryLogFilter())

import secrets
VALID_TOKENS = {}

@app.before_request
def check_auth():
    if request.path.startswith("/api/") and request.path != "/api/login" and request.path != "/api/poll":
        if request.method == "OPTIONS":
            return
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            pass
        else:
            token = auth_header.split(" ")[1]
            if token not in VALID_TOKENS:
                pass



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

# ─────────────────────────────────────────────
# Action-tracking overlays (persisted to disk)
# State is saved to state.json so it survives server restarts.
# ─────────────────────────────────────────────
_STATE_FILE = BASE_DIR / "state.json"

def _load_state():
    """Load persisted state from disk."""
    global _blocked_ports, _stealth_active, _cyber_credits
    try:
        if _STATE_FILE.exists():
            with open(_STATE_FILE, "r") as f:
                s = json.load(f)
                _blocked_ports = set(s.get("blocked_ports", []))
                _stealth_active = bool(s.get("stealth_active", False))
                _cyber_credits = int(s.get("cyber_credits", 1000))
    except Exception:
        pass  # Ignore corrupt state files — start fresh

def _save_state():
    """Save current action state to disk."""
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump({
                "blocked_ports": list(_blocked_ports),
                "stealth_active": _stealth_active,
                "cyber_credits": _cyber_credits
            }, f)
    except Exception:
        pass

_blocked_ports = set()
_stealth_active = False
_cyber_credits = 1000
_load_state()   # ← Restore state from previous session on startup


def invalidate_cache(key):
    """Bust a specific cache entry so the next call re-reads live data."""
    with _cache_lock:
        _cache.pop(key, None)


def get_adjusted_score():
    """Return the current score and deductions, subtracting penalties directly from a base of 100 to ensure perfect visual alignment."""
    report = get_cached("system", CACHE_TTL["system"], sysmon.full_report)
    score = 100
    new_deductions = []

    # Get base deductions from system report
    base_deductions = report.get("security_score", {}).get("deductions", [])

    # Calculate unblocked ports
    open_risky_ports = [p["port"] for p in report.get("open_ports", []) if p["port"] in [21, 23, 135, 139, 445, 3389, 5900]]
    if _stealth_active:
        unblocked_risky = []
    else:
        unblocked_risky = [p for p in open_risky_ports if p not in _blocked_ports]

    # Filter and apply penalties dynamically to avoid masking other issues
    for d in base_deductions:
        if "risky port" in d:
            if len(unblocked_risky) > 0:
                penalty = len(unblocked_risky) * 5
                new_deductions.append(f"{len(unblocked_risky)} risky port(s) open & exposed (-{penalty})")
                score -= penalty
        else:
            # Parse the penalty from other deductions (e.g. "Antivirus is disabled (-20)")
            penalty = 0
            if "(-" in d and d.endswith(")"):
                try:
                    penalty = int(d.split("(-")[-1].replace(")", "").strip())
                except Exception:
                    pass
            new_deductions.append(d)
            score -= penalty

    score = max(0, min(100, score))
    return score, new_deductions


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
    """Get this machine's LAN IP address, prioritizing WiFi/LAN and avoiding loopback/Tailscale."""
    import socket as _sock
    try:
        hostname = _sock.gethostname()
        _, _, ips = _sock.gethostbyname_ex(hostname)
        lan_ips = []
        for ip in ips:
            if ip.startswith("127."):
                continue
            if ip.startswith("100."):
                continue
            if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
                lan_ips.append(ip)
        if lan_ips:
            return lan_ips[0]
            
        s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        if ip != "127.0.0.1":
            return ip
    except Exception:
        pass
        
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

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r


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
    ip = get_local_ip()
    domain = "z14-55n.tailfffdbc.ts.net"
    local_url = f"https://{ip}:8767"
    local_heartbeat = f"https://{ip}:8767/api/agent/heartbeat"
    
    if os.path.exists(f"{domain}.crt"):
        url = f"https://{domain}:8767"
        heartbeat = f"https://{domain}:8767/api/agent/heartbeat"
    else:
        url = local_url
        heartbeat = local_heartbeat
        
    return jsonify({
        "ok": True,
        "local_ip": ip,
        "port": 8767,
        "dashboard_url": url,
        "local_dashboard_url": local_url,
        "agent_heartbeat_url": heartbeat,
        "local_agent_heartbeat_url": local_heartbeat,
        "tunnel_url": CLOUDFLARE_TUNNEL_URL
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


# C2 Command Queues
C2_COMMANDS = {}
C2_RESULTS = {}

@app.route("/api/agents/<device_id>/command", methods=["POST"])
def api_agent_post_command(device_id):
    data = request.json or {}
    cmd = data.get("cmd")
    if cmd:
        if device_id not in C2_COMMANDS:
            C2_COMMANDS[device_id] = []
        C2_COMMANDS[device_id].append(cmd)
    return jsonify({"ok": True})

@app.route("/api/agent/<device_id>/commands", methods=["GET"])
def api_agent_get_commands(device_id):
    cmds = C2_COMMANDS.pop(device_id, [])
    return jsonify({"ok": True, "commands": cmds})

@app.route("/api/agent/<device_id>/results", methods=["POST"])
def api_agent_post_results(device_id):
    data = request.json or {}
    if device_id not in C2_RESULTS:
        C2_RESULTS[device_id] = []
    C2_RESULTS[device_id].append(data)
    return jsonify({"ok": True})

@app.route("/api/agents/<device_id>/results", methods=["GET"])
def api_agent_get_results(device_id):
    res = C2_RESULTS.pop(device_id, [])
    return jsonify({"ok": True, "data": res})



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
    domain = "z14-55n.tailfffdbc.ts.net"
    if os.path.exists(f"{domain}.crt"):
        url = f"https://{domain}:8767"
        heartbeat = f"https://{domain}:8767/api/agent/heartbeat"
    else:
        url = f"https://{ip}:8767"
        heartbeat = f"https://{ip}:8767/api/agent/heartbeat"

    return jsonify({
        "ok": True,
        "server_ip": ip,
        "dashboard_url": url,
        "heartbeat_url": heartbeat,
        "android_steps": [
            "Install Termux from F-Droid (https://f-droid.org)",
            "Open Termux and run: pkg update && pkg install python",
            "Run: pip install psutil requests",
            f"Download agent.py from: {url}/agent.py",
            "Run: python agent.py"
        ],
        "windows_steps": [
            "Install Python from https://python.org",
            "Open Command Prompt and run: pip install psutil requests",
            f"Download agent.py from: {url}/agent.py",
            "Run: python agent.py"
        ],
        "ios_steps": [
            f"Open Safari and go to: {url}",
            "Tap the Share button (box with arrow)",
            "Tap 'Add to Home Screen'",
            "Tap 'Add' — the dashboard is now installed as an app!"
        ]
    })


@app.route("/agent.py")
def serve_agent():
    """Serve the agent.py script so other devices can download it easily."""
    return send_from_directory(str(ROOT_DIR), "agent.py", mimetype="text/plain")


@app.route("/nethunter_agent.py")
def serve_nethunter_agent():
    """Serve the nethunter_agent.py script so remote Kali nodes can auto-update."""
    scripts_dir = ROOT_DIR / "scripts"
    if (scripts_dir / "nethunter_agent.py").exists():
        return send_from_directory(str(scripts_dir), "nethunter_agent.py", mimetype="text/plain")
    return send_from_directory(str(ROOT_DIR), "nethunter_agent.py", mimetype="text/plain")


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

        # Use the adjusted score that factors in actions taken this session
        adj_score, adj_deductions = get_adjusted_score()

        return jsonify({
            "ok": True,
            "security_score": adj_score,
            "deductions": adj_deductions,
            "firewall_ok": all(v == "ON" for v in report["firewall"].get("profiles", {}).values()) or _stealth_active,
            "antivirus_ok": report["defender"].get("antivirus_enabled", False),
            "realtime_ok": report["defender"].get("realtime_protection", False),
            "unknown_devices": unknown_count,
            "pending_updates": report["pending_updates"].get("pending_count", -1),
            "system": report["system"],
            "timestamp": datetime.datetime.now().isoformat(),
            "blocked_ports": list(_blocked_ports),
            "stealth_active": _stealth_active
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


@app.route("/api/credits", methods=["GET"])
def api_get_credits():
    """Get current Cyber Credits balance."""
    return jsonify({"ok": True, "credits": _cyber_credits})


@app.route("/api/local-movies", methods=["GET"])
def api_get_local_movies():
    """Get list of movie files in the dashboard/local_movies directory."""
    import os
    movies_dir = os.path.join(ROOT_DIR, "dashboard", "local_movies")
    if not os.path.exists(movies_dir):
        try:
            os.makedirs(movies_dir, exist_ok=True)
        except Exception:
            pass
    
    video_extensions = (".mp4", ".webm", ".mkv", ".avi", ".mov")
    files = []
    try:
        if os.path.exists(movies_dir):
            for f in os.listdir(movies_dir):
                if f.lower().endswith(video_extensions):
                    files.append(f)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
        
    return jsonify({"ok": True, "movies": sorted(files)})


@app.route("/api/lan-proxy", methods=["GET"])
def api_lan_proxy():
    """Proxy directory listing request to another LAN server to bypass CORS."""
    url = request.args.get("url")
    if not url:
        return jsonify({"ok": False, "error": "Missing url"}), 400
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        r.raise_for_status()
        return jsonify({"ok": True, "content": r.text})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/story-proxy", methods=["GET"])
def api_story_proxy():
    """Proxy lore list request to the Node.js backend on port 3000 to bypass CORS."""
    url = "http://localhost:3000/api/lore"
    try:
        r = requests.get(url, timeout=3)
        r.raise_for_status()
        # The Node.js server returns a JSON array of stories. We package it as {"ok": True, "stories": [...]}
        return jsonify({"ok": True, "stories": r.json()})
    except Exception as e:
        # Fallback to local mock stories in the exact format if Node.js server is offline
        mock_stories = [
            {
                "id": "cyber-1",
                "title": "Neon Grid Syndicate",
                "synopsis": "A rogue decker attempts to infiltrate the mainframe of a corrupt megastructure.",
                "theme": "cyberpunk",
                "chapters": [
                    {
                        "title": "Chapter 1: The Breach",
                        "text": "The rain fell like static over the neon spires of Neo-Minato. Kael checked his cyberdeck. The firewall of the Megacorp was down, but the grid was alive. He had 30 seconds to copy the data before the security AI fried his brain...",
                        "image": "https://images.unsplash.com/photo-1515621061946-eff1c2a352bd?w=600&auto=format&fit=crop",
                        "music": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
                    },
                    {
                        "title": "Chapter 2: Netrunner Escape",
                        "text": "Sirens wailed in the physical world as Kael pulled the jack. His synapses sizzled from the feedback loop. Grabbing his coat, he slipped into the dark alleyways. Cybernetic enforcement guards were already closing in on his location...",
                        "image": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=600&auto=format&fit=crop",
                        "music": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
                    }
                ]
            },
            {
                "id": "tactical-1",
                "title": "Operation Blackout",
                "synopsis": "An elite spec-ops team is deployed to disable a hijacked satellite tracking station.",
                "theme": "tactical",
                "chapters": [
                    {
                        "title": "Chapter 1: Insertion",
                        "text": "The transport chopper hovered silently in the freezing mountain air. Sergeant Miller checked his night-vision goggles. 'Green light, go, go, go,' he whispered. One by one, the team rappelled into the snowy dark...",
                        "image": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=600&auto=format&fit=crop",
                        "music": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3"
                    },
                    {
                        "title": "Chapter 2: Under Fire",
                        "text": "Sparks flew as a bullet clipped the console next to Miller. The tracking station was heavily fortified. 'Suppressing fire!' he roared, firing his carbine into the shadows. They had to upload the virus before dawn...",
                        "image": "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=600&auto=format&fit=crop",
                        "music": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3"
                    }
                ]
            },
            {
                "id": "fantasy-1",
                "title": "The Last Rune",
                "synopsis": "A young wizard uncovers the secret to unlocking the dragon gates of Oakhaven.",
                "theme": "fantasy",
                "chapters": [
                    {
                        "title": "Chapter 1: The Crypt",
                        "text": "Eldrin traced the glowing rune on the ancient stone door. Deep in the Catacombs of Oakhaven, the whispers of the sleeping dragon grew louder. He raised his staff, the blue crystal radiating light, and spoke the command word...",
                        "image": "https://images.unsplash.com/photo-1519074002996-a69e7ac46a42?w=600&auto=format&fit=crop",
                        "music": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3"
                    },
                    {
                        "title": "Chapter 2: Awakening",
                        "text": "With a low rumble, the stone door ground open. Gold and bones lay piled high in the cavern. In the center, a pair of ancient yellow eyes opened. The dragon breathed a low growl, waiting for the wizard to speak...",
                        "image": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=600&auto=format&fit=crop",
                        "music": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3"
                    }
                ]
            }
        ]
        return jsonify({"ok": True, "stories": mock_stories, "is_mock": True})



@app.route("/api/radio/proxy", methods=["GET"])
def api_radio_proxy():
    """Proxy live audio streams to bypass CORS and mixed-content blocking."""
    url = request.args.get("url")
    if not url:
        return "Missing url parameter", 400
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        req = requests.get(url, stream=True, timeout=8)
        content_type = req.headers.get("Content-Type", "audio/mpeg")
        
        def generate():
            for chunk in req.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
                    
        response = Response(generate(), content_type=content_type)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
    except Exception as e:
        return str(e), 500


@app.route("/api/gaming/hangman", methods=["GET"])
def api_hangman_word():
    """Returns a random security word for the Hackman game, simulating a secure passcode packet."""
    import random
    words = [
        "CYBERSECURITY", "FIREWALL", "HONEYPOT", "RANSOMWARE", "PHISHING",
        "DECRYPTION", "ANTIVIRUS", "TRIPWIRE", "INTRUSION", "ENCRYPTION",
        "MALWARE", "SPYWARE", "ROOTKIT", "VULNERABILITY", "SANDBOX",
        "BACKDOOR", "EXPLOIT", "PAYLOAD", "KEYLOGGER", "SPAMMER",
        "BOTNET", "PHREAKING", "STEALTH", "SPOOFING", "WIRETAP"
    ]
    word = random.choice(words)
    sig = hashlib.sha256(word.encode()).hexdigest()[:8].upper()
    return jsonify({
        "ok": True,
        "word": word,
        "signature": f"PKT-{sig}",
        "hacker_threat": random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    })


@app.route("/api/credits/update", methods=["POST"])
def api_update_credits():
    """Update Cyber Credits balance (add/subtract)."""
    global _cyber_credits
    try:
        body = request.get_json()
        delta = int(body.get("delta", 0))
        
        # Ensure we don't drop below 0 if deducting
        if delta < 0 and _cyber_credits + delta < 0:
            return jsonify({"ok": False, "error": "Insufficient credits"}), 400
            
        _cyber_credits += delta
        _save_state()
        return jsonify({"ok": True, "credits": _cyber_credits})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/breach-check", methods=["POST"])
def api_breach_check():
    """Check if an email has been in known data breaches via XposedOrNot API."""
    import requests as req

    try:
        body = request.get_json()
        email = body.get("email", "").strip()
        if not email:
            return jsonify({"ok": False, "error": "Email required"}), 400

        headers = {"User-Agent": "PersonalSecuritySuite/1.0"}
        
        # 1. Get the list of breaches for the email
        res = req.get(f'https://api.xposedornot.com/v1/check-email/{email}', headers=headers, timeout=10)
        if res.status_code == 404:
            return jsonify({"ok": True, "found": False, "breach_count": 0, "breaches": []})
            
        data = res.json()
        breach_names = data.get('breaches', [[]])[0]
        
        if not breach_names:
            return jsonify({"ok": True, "found": False, "breach_count": 0, "breaches": []})
        
        # 2. Get breach details
        details_res = req.get('https://api.xposedornot.com/v1/breaches', headers=headers, timeout=10)
        details_data = details_res.json().get('exposedBreaches', [])
        
        # Create a mapping
        details_map = {b['breachID']: b for b in details_data}
        
        breaches_out = []
        for name in breach_names[:10]:
            info = details_map.get(name, {})
            date_str = info.get('breachedDate', '')
            if date_str and 'T' in date_str:
                date_str = date_str.split('T')[0]
            elif not date_str:
                date_str = 'Unknown'
                
            desc = info.get('exposureDescription', 'Data breach on ' + name)
            domain = info.get('domain', '')
            exposed_data = info.get('exposedData', [])
            
            breaches_out.append({
                'name': name,
                'date': date_str,
                'description': desc,
                'domain': domain,
                'exposed_data': exposed_data
            })
            
        return jsonify({
            "ok": True,
            "found": True,
            "breach_count": len(breach_names),
            "breaches": breaches_out
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/media/extract", methods=["POST"])
def api_media_extract():
    """Extract raw media stream URLs using yt-dlp and IDM-style deep scanning to bypass ads and tracking."""
    import re
    import urllib.request
    from urllib.parse import urljoin
    try:
        import yt_dlp
        from yt_dlp.utils import DownloadError
        body = request.get_json()
        url = body.get("url", "").strip()
        if not url:
            return jsonify({"ok": False, "error": "URL required"}), 400

        # Torrent/Magnet Interceptor
        if url.startswith("magnet:") or url.endswith(".torrent"):
            import urllib.parse
            import requests
            try:
                # Query the Node WebTorrent microservice to resolve metadata and get file path
                node_res = requests.get(f"http://127.0.0.1:8766/stream?magnet={urllib.parse.quote(url)}", timeout=15)
                node_data = node_res.json()
                if node_data.get("ok"):
                    host_ip = request.host.split(':')[0]
                    stream_url = f"http://{host_ip}:8766{node_data.get('path')}"
                    return jsonify({
                        "ok": True,
                        "title": node_data.get("title", "Bloody Sweet P2P Stream"),
                        "stream_url": stream_url
                    })
                else:
                    return jsonify({"ok": False, "error": node_data.get("error", "Failed to resolve torrent")})
            except Exception as e:
                return jsonify({"ok": False, "error": f"Torrent service error: {e}"})


        # Helper to extract youtube ID
        def get_yt_id(url):
            m = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11}).*', url)
            return m.group(1) if m else None

        # IDM-style Deep Sniffer Fallback
        def idm_deep_scan(target_url, depth=0):
            if depth > 2:
                return None
            try:
                req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    html = response.read().decode('utf-8', errors='ignore')
                    
                    # Look for m3u8 or mp4
                    m3u8 = re.findall(r'(https?://[^\s"\'<>]*?\.m3u8[^\s"\'<>]*)', html)
                    if m3u8: return m3u8[0]
                    
                    # Look for Base64 encoded m3u8 URLs (common obfuscation)
                    import base64
                    b64_strings = re.findall(r'[A-Za-z0-9+/=]{30,}', html)
                    for s in b64_strings:
                        try:
                            dec = base64.b64decode(s).decode('utf-8')
                            if '.m3u8' in dec:
                                m = re.search(r'(https?://[^\s"\'<>]*?\.m3u8[^\s"\'<>]*)', dec)
                                if m: return m.group(1)
                        except: pass
                    
                    mp4 = re.findall(r'(https?://[^\s"\'<>]*?\.mp4[^\s"\'<>]*)', html)
                    if mp4: return mp4[0]
                    
                    # Look for iframes
                    iframes = re.findall(r'<iframe[^>]+src=["\'](.*?)["\']', html, re.IGNORECASE)
                    for iframe_src in iframes:
                        if iframe_src.startswith('//'): iframe_src = 'https:' + iframe_src
                        full_iframe_url = urljoin(target_url, iframe_src)
                        if 'youtube.com' in full_iframe_url: continue # Handled by yt_dlp
                        result = idm_deep_scan(full_iframe_url, depth + 1)
                        if result: return result
            except:
                pass
            return None

        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'simulate': True,
            'forceurl': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get('url')
                title = info.get('title', 'Video')
                
                if not stream_url:
                    raise Exception("yt-dlp could not find stream URL")
                    
                return jsonify({
                    "ok": True,
                    "title": title,
                    "stream_url": stream_url
                })
        except Exception as e:
            err_msg = str(e).lower()
            # If 429 Too Many Requests occurs and it's YouTube, use fallback embed
            if '429' in err_msg or 'too many requests' in err_msg or 'sign in to confirm you' in err_msg:
                yt_id = get_yt_id(url)
                if yt_id:
                    iframe_url = f"https://www.youtube-nocookie.com/embed/{yt_id}?autoplay=1&dnt=1"
                    return jsonify({
                        "ok": True,
                        "title": "Secure Privacy Stream (YouTube)",
                        "iframe_url": iframe_url
                    })
            
            # Fire IDM-Style Deep Sniffer!
            sniffed_url = idm_deep_scan(url)
            if sniffed_url:
                return jsonify({
                    "ok": True,
                    "title": "IDM Sniffed Stream",
                    "stream_url": sniffed_url
                })

            # Universal Web Embed Fallback for unsupported URLs and other errors
            return jsonify({
                "ok": True,
                "title": "Universal Web Embed (Direct)",
                "iframe_url": url
            })
            
    except Exception as e:
        # Catch generic exceptions and use universal fallback
        return jsonify({
            "ok": True,
            "title": "Universal Web Embed (Direct)",
            "iframe_url": request.get_json().get("url", "").strip() if request.is_json else ""
        })



@app.route("/api/download")
def api_download_media():
    """Backend proxy to force download media files and bypass Mobile/CORS restrictions."""
    import urllib.request
    from flask import Response
    
    url = request.args.get('url')
    filename = request.args.get('filename', 'doomscroll_media.jpg')
    
    if not url:
        return jsonify({"ok": False, "error": "No URL provided"}), 400
        
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": resp.headers.get("Content-Type", "application/octet-stream")
        }
        
        return Response(resp.read(), headers=headers)
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/comments")
def api_comments():
    """Backend proxy to fetch real Reddit comments for a post."""
    import urllib.request
    import json
    url = request.args.get('url')
    if not url: return jsonify({"ok": False, "error": "No url provided"}), 400

    if 'redd.it' in url or 'reddit.com' in url:
        try:
            req = urllib.request.Request(url + '.json', headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode('utf-8'))
                comments = []
                for child in data[1]['data']['children'][:20]:
                    cdata = child.get('data', {})
                    if cdata.get('body') and cdata.get('author') and cdata.get('author') != 'AutoModerator':
                        comments.append({
                            "author": cdata['author'],
                            "body": cdata['body'],
                            "score": cdata.get('score', 0)
                        })
                return jsonify({"ok": True, "comments": comments})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "comments": []})

@app.route("/api/doomscroll")
def api_doomscroll():
    """Fetches and aggregates social media feeds and news for the DoomScroll UI."""
    import urllib.request
    import json
    import xml.etree.ElementTree as ET
    import random

    page = request.args.get('page', '1')
    memes = []
    articles = []

    MEME_SUBREDDITS = [
        "memes", "dankmemes", "me_irl", "gaming", "funny",
        "ProgrammerHumor", "interestingasfuck", "oddlysatisfying",
        "technicallythetruth", "Wellthatsucks", "cursedimages",
        "mildlyinteresting", "aww", "Damnthatsinteresting",
        "therewasanattempt", "onejob", "HolUp"
    ]
    import random as _rand
    # Each page picks a different set for variety
    page_int = int(page) if str(page).isdigit() else 1
    _rand.seed(page_int * 13 + _rand.randint(0, 999))
    chosen_subs = _rand.sample(MEME_SUBREDDITS, min(5, len(MEME_SUBREDDITS)))
    seen_urls = set()

    for sub in chosen_subs:
        try:
            meme_url = f"https://meme-api.com/gimme/{sub}/12"
            req = urllib.request.Request(meme_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as response:
                data = json.loads(response.read().decode('utf-8'))
                for meme in data.get('memes', []):
                    if meme.get('nsfw') or meme.get('spoiler'): continue
                    media = meme.get("url", "")
                    # Only actual image posts, no galleries/videos, no duplicates
                    if not any(media.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        continue
                    if media in seen_urls: continue
                    seen_urls.add(media)
                    memes.append({
                        "id": meme.get("postLink", media),
                        "title": meme.get("title"),
                        "author": meme.get("author"),
                        "subreddit": f"r/{meme.get('subreddit', sub)}",
                        "score": meme.get("ups"),
                        "permalink": meme.get("postLink"),
                        "type": "image",
                        "media_url": media,
                        "thumbnail": None
                    })
        except Exception as e:
            print(f"Meme API Error ({sub}):", e)

    # 2. Fetch News (RSS) ONLY on Page 1
    if page == '1':
        rss_feeds = [
            ("https://techcrunch.com/feed/", "TechCrunch"),
            ("http://feeds.bbci.co.uk/news/world/rss.xml", "BBC World News"),
            ("https://feeds.feedburner.com/TheHackersNews", "The Hacker News"),
        ]
        import re as _re
        for feed_url, feed_name in rss_feeds:
            try:
                req = urllib.request.Request(feed_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as r:
                    raw = r.read()
                    tree = ET.fromstring(raw)
                    for item in tree.findall('.//item')[:8]:
                        title = item.find('title')
                        link = item.find('link')
                        if title is None or link is None:
                            continue
                        thumb = None
                        mc = item.find('{http://search.yahoo.com/mrss/}content')
                        if mc is not None:
                            thumb = mc.get('url')
                        if not thumb:
                            mt = item.find('{http://search.yahoo.com/mrss/}thumbnail')
                            if mt is not None:
                                thumb = mt.get('url')
                        if not thumb:
                            enc = item.find('enclosure')
                            if enc is not None and 'image' in (enc.get('type') or ''):
                                thumb = enc.get('url')
                        if not thumb:
                            desc = item.find('description')
                            if desc is not None and desc.text:
                                m = _re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc.text)
                                if m:
                                    thumb = m.group(1)
                        articles.append({
                            "id": link.text,
                            "title": title.text,
                            "author": feed_name,
                            "subreddit": feed_name,
                            "score": "📰",
                            "permalink": link.text,
                            "type": "article",
                            "media_url": thumb,
                            "thumbnail": thumb
                        })
            except Exception as e:
                print(f"RSS Error ({feed_name}):", e)

    # 3. Interleave: 3 memes then 1 news article
    random.shuffle(memes)
    random.shuffle(articles)

    final_feed = []
    while memes or articles:
        # Pull up to 3 memes
        for _ in range(3):
            if memes:
                final_feed.append(memes.pop(0))
        # Pull 1 article
        if articles:
            final_feed.append(articles.pop(0))

    if not final_feed:
        return jsonify({"ok": False, "error": "All aggregation sources failed."}), 500

    return jsonify({"ok": True, "posts": final_feed})



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
        
        # Mask the SauceNAO API key
        if cfg.get("saucenao_api_key"):
            cfg["saucenao_api_key_set"] = True
            cfg["saucenao_api_key"] = "***hidden***"
        else:
            cfg["saucenao_api_key_set"] = False
            cfg["saucenao_api_key"] = ""
            
        return jsonify({"ok": True, "data": cfg})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/config", methods=["POST"])
def api_save_config():
    """Save configuration (Telegram token, chat_id, alert settings, SauceNAO key)."""
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
        if "saucenao_api_key" in body:
            s_key = body["saucenao_api_key"]
            if s_key != "***hidden***":
                cfg["saucenao_api_key"] = s_key.strip()
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


@app.route("/api/radar/scan", methods=["GET"])
def api_radar_scan():
    """Run an on-demand local network ARP sweep (Network Sonar)."""
    try:
        import network_scanner
        raw_devices = network_scanner.arp_scan_windows()
        whitelist = network_scanner.load_whitelist()
        whitelist_macs = {mac.upper() for mac in whitelist.keys()}
        
        devices = []
        for d in raw_devices:
            mac_upper = d.get("mac", "").upper()
            is_approved = mac_upper in whitelist_macs
            dev_type = "Approved" if is_approved else "Unknown"
            devices.append({
                "ip": d.get("ip", "—"),
                "mac": d.get("mac", "—"),
                "type": dev_type
            })
        return jsonify({"ok": True, "devices": devices})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────
# Mobile Toolkit (Offensive/Diagnostic)
# ─────────────────────────────────────────────

@app.route("/api/firewall/stealth", methods=["POST"])
def api_firewall_stealth():
    global _stealth_active
    try:
        if platform.system() == "Windows":
            subprocess.run("netsh advfirewall set allprofiles state on", shell=True, check=True, creationflags=0x08000000)
            subprocess.run("netsh advfirewall set allprofiles firewallpolicy blockinbound,allowoutbound", shell=True, check=True, creationflags=0x08000000)
            _stealth_active = True
            _save_state()   # Persist to disk so state survives restart
            # Bust the system cache so /api/status immediately reflects the change
            invalidate_cache("system")
            new_score, _ = get_adjusted_score()
            return jsonify({"ok": True, "message": "Stealth Mode Enabled. All inbound connections blocked.", "new_score": new_score})
        else:
            return jsonify({"ok": False, "error": "Stealth Mode is only supported on Windows."}), 400
    except subprocess.CalledProcessError as e:
        return jsonify({"ok": False, "error": "Access Denied. Administrator privileges required to change firewall settings."}), 403
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/firewall/stealth-off", methods=["POST"])
def api_firewall_stealth_off():
    global _stealth_active
    try:
        if platform.system() == "Windows":
            subprocess.run("netsh advfirewall set allprofiles firewallpolicy allowinbound,allowoutbound",
                           shell=True, check=True, creationflags=0x08000000)
            _stealth_active = False
            _save_state()
            invalidate_cache("system")
            new_score, _ = get_adjusted_score()
            return jsonify({"ok": True, "message": "Stealth Mode disabled.", "new_score": new_score})
        else:
            return jsonify({"ok": False, "error": "Only supported on Windows."}), 400
    except subprocess.CalledProcessError:
        return jsonify({"ok": False, "error": "Access Denied. Run as Administrator."}), 403
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
@app.route("/api/firewall/enable", methods=["POST"])
def api_firewall_enable():
    try:
        if platform.system() == "Windows":
            subprocess.run("netsh advfirewall set allprofiles state on", shell=True, check=True, creationflags=0x08000000)
            invalidate_cache("system")
            new_score, _ = get_adjusted_score()
            return jsonify({"ok": True, "message": "Windows Firewall enabled for all profiles.", "new_score": new_score})
        else:
            return jsonify({"ok": False, "error": "Only supported on Windows."}), 400
    except subprocess.CalledProcessError:
        return jsonify({"ok": False, "error": "Access Denied. Administrator privileges required."}), 403
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/defender/open", methods=["POST"])
def api_defender_open():
    try:
        if platform.system() == "Windows":
            subprocess.run("powershell Start-Process windows-defender:", shell=True, check=True, creationflags=0x08000000)
            return jsonify({"ok": True, "message": "Windows Defender settings opened."})
        else:
            return jsonify({"ok": False, "error": "Only supported on Windows."}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/defender/update", methods=["POST"])
def api_defender_update():
    try:
        if platform.system() == "Windows":
            # Run MpCmdRun.exe -SignatureUpdate
            cmd = '"C:\\Program Files\\Windows Defender\\MpCmdRun.exe" -SignatureUpdate'
            subprocess.Popen(cmd, shell=True, creationflags=0x08000000)
            return jsonify({"ok": True, "message": "Defender signature update triggered."})
        else:
            return jsonify({"ok": False, "error": "Only supported on Windows."}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/system/open-update", methods=["POST"])
def api_system_open_update():
    try:
        if platform.system() == "Windows":
            subprocess.run("powershell Start-Process ms-settings:windowsupdate", shell=True, check=True, creationflags=0x08000000)
            return jsonify({"ok": True, "message": "Windows Update Settings opened."})
        else:
            return jsonify({"ok": False, "error": "Only supported on Windows."}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/firewall/block-port", methods=["POST"])
def api_firewall_block_port():
    global _blocked_ports
    try:
        if platform.system() == "Windows":
            data = request.json or {}
            port = data.get("port")
            if not port:
                return jsonify({"ok": False, "error": "Port number is required."}), 400

            rule_name = f"SecuritySuite Block Port {port}"
            # Remove existing rule if present (avoid duplicates)
            subprocess.run(f'netsh advfirewall firewall delete rule name="{rule_name}"', shell=True, creationflags=0x08000000)

            # Add the inbound block rule
            cmd = f'netsh advfirewall firewall add rule name="{rule_name}" dir=in action=block protocol=TCP localport={port}'
            subprocess.run(cmd, shell=True, check=True, creationflags=0x08000000)

            # Track the blocked port and bust the cache for an immediate score update
            _blocked_ports.add(int(port))
            _save_state()   # Persist to disk so state survives restart
            invalidate_cache("system")
            new_score, _ = get_adjusted_score()
            return jsonify({"ok": True, "message": f"Port {port} blocked successfully.", "new_score": new_score})
        else:
            return jsonify({"ok": False, "error": "Firewall blocking is only supported on Windows."}), 400
    except subprocess.CalledProcessError as e:
        return jsonify({"ok": False, "error": "Access Denied. Administrator privileges required to change firewall settings."}), 403
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/firewall/blocked-ports", methods=["GET"])
def api_firewall_blocked_ports():
    """Return ports currently blocked by SecuritySuite."""
    return jsonify({"ok": True, "ports": list(_blocked_ports)})

@app.route("/api/firewall/unblock-port", methods=["POST"])
def api_firewall_unblock_port():
    """Remove a SecuritySuite firewall block for a given port."""
    global _blocked_ports
    try:
        if platform.system() == "Windows":
            data = request.json or {}
            port = data.get("port")
            if not port:
                return jsonify({"ok": False, "error": "Port number is required."}), 400
            rule_name = f"SecuritySuite Block Port {port}"
            subprocess.run(f'netsh advfirewall firewall delete rule name="{rule_name}"',
                           shell=True, creationflags=0x08000000)
            _blocked_ports.discard(int(port))
            _save_state()
            invalidate_cache("system")
            new_score, _ = get_adjusted_score()
            return jsonify({"ok": True, "message": f"Port {port} unblocked.", "new_score": new_score})
        else:
            return jsonify({"ok": False, "error": "Only supported on Windows."}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/toolkit/ping", methods=["POST"])
def api_toolkit_ping():
    try:
        ip = request.get_json().get("ip")
        if not ip: return jsonify({"ok": False, "error": "IP required"}), 400
        cmd = ["ping", "-n", "4", "-w", "1000", ip] if platform.system() == "Windows" else ["ping", "-c", "4", "-W", "1", ip]
        r = tpool.execute(subprocess.run, cmd, capture_output=True, text=True)
        return jsonify({"ok": True, "output": r.stdout})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/toolkit/traceroute", methods=["POST"])
def api_toolkit_traceroute():
    try:
        ip = request.get_json().get("ip")
        if not ip: return jsonify({"ok": False, "error": "IP required"}), 400
        cmd = ["tracert", "-d", "-h", "15", "-w", "500", ip] if platform.system() == "Windows" else ["traceroute", "-n", "-m", "15", "-w", "1", ip]
        r = tpool.execute(subprocess.run, cmd, capture_output=True, text=True)
        return jsonify({"ok": True, "output": r.stdout})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/toolkit/duckduckgo", methods=["POST"])
def api_toolkit_duckduckgo():
    try:
        subprocess.Popen("explorer.exe shell:AppsFolder\\DuckDuckGo.DesktopBrowser_ya2fgkz3nks94!App", shell=True)
        return jsonify({"ok": True, "output": "DuckDuckGo launched successfully."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/toolkit/nmap", methods=["POST"])
def api_toolkit_nmap():
    try:
        ip = request.get_json().get("ip")
        if not ip: return jsonify({"ok": False, "error": "IP required"}), 400
        # Fast scan without ping to bypass firewalls
        cmd = ["nmap", "-T4", "-F", "-Pn", ip]
        r = tpool.execute(subprocess.run, cmd, capture_output=True, text=True)
        return jsonify({"ok": True, "output": r.stdout if r.stdout else r.stderr})
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "nmap is not installed or not in PATH."}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/toolkit/nikto", methods=["POST"])
def api_toolkit_nikto():
    try:
        ip = request.get_json().get("ip")
        if not ip: return jsonify({"ok": False, "error": "Target required"}), 400
        cmd = ["nikto", "-h", ip, "-maxtime", "30s"] # Limit to 30s for demo
        r = tpool.execute(subprocess.run, cmd, capture_output=True, text=True)
        return jsonify({"ok": True, "output": r.stdout if r.stdout else r.stderr})
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "nikto is not installed or not in PATH."}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/toolkit/sqlmap", methods=["POST"])
def api_toolkit_sqlmap():
    try:
        ip = request.get_json().get("ip")
        if not ip: return jsonify({"ok": False, "error": "Target URL required"}), 400
        # Add http if missing to prevent sqlmap from complaining
        if not ip.startswith("http"):
            ip = "http://" + ip
        cmd = ["sqlmap", "-u", ip, "--batch", "--level=1", "--risk=1"]
        r = tpool.execute(subprocess.run, cmd, capture_output=True, text=True)
        return jsonify({"ok": True, "output": r.stdout if r.stdout else r.stderr})
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "sqlmap is not installed or not in PATH."}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def api_login():
    """Simple lock screen authentication."""
    try:
        body = request.get_json()
        pin = body.get("pin")
        
        if pin == "3333":
            token = secrets.token_hex(32)
            VALID_TOKENS[token] = True
            return jsonify({"ok": True, "token": token})
        else:
            return jsonify({"ok": False, "error": "Invalid PIN"}), 401
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────
# Data Breach Scanner
# ─────────────────────────────────────────────
@app.route("/api/breach/password", methods=["POST"])
def api_breach_password():
    """Check if a password has been leaked using HaveIBeenPwned API (K-Anonymity model)."""
    try:
        body = request.get_json()
        password = body.get("password")
        if not password:
            return jsonify({"ok": False, "error": "Password required"}), 400
            
        import hashlib
        import requests
        
        # Securely hash the password (SHA-1)
        sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix, suffix = sha1_hash[:5], sha1_hash[5:]
        
        # We ONLY send the first 5 characters of the hash to the API.
        # This is the K-Anonymity model - they never receive the password or full hash.
        url = f"https://api.pwnedpasswords.com/range/{prefix}"
        response = requests.get(url, timeout=5)
        
        if response.status_code != 200:
            return jsonify({"ok": False, "error": "Failed to query breach database"}), 502
            
        # The API returns a list of matching suffixes and their breach count
        hashes = (line.split(':') for line in response.text.splitlines())
        count = next((int(count) for hash_suffix, count in hashes if hash_suffix == suffix), 0)
        
        return jsonify({
            "ok": True, 
            "pwned": count > 0, 
            "count": count,
            "message": f"This password has been seen {count} times in data breaches." if count > 0 else "Good news! This password has not been found in any known breaches."
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
@app.route("/api/device/offensive-scan", methods=["POST"])
def api_device_offensive_scan():
    try:
        body = request.get_json()
        ip = body.get("ip")
        if not ip: return jsonify({"ok": False, "error": "IP required"}), 400
        result = tpool.execute(offensive.python_port_scan, ip)
        return jsonify(result)
    except Exception as e: return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/device/block", methods=["POST"])
def api_device_block_arp():
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
        return jsonify(tpool.execute(offensive.arp_block, ip, mac, gateway))
    except Exception as e: return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/device/wol", methods=["POST"])
def api_device_wol_arp():
    try:
        body = request.get_json()
        mac = body.get("mac")
        if not mac: return jsonify({"ok": False, "error": "MAC required"}), 400
        return jsonify(offensive.wake_on_lan(mac))
    except Exception as e: return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────
# Startup
@app.route("/api/search", methods=["POST"])
def api_search_proxy():
    try:
        data = request.json or {}
        query = data.get("q", "").strip()
        if not query:
            return jsonify({"ok": False, "error": "Empty query"}), 400

        # Fetch from DuckDuckGo Lite (no JS required)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.post("https://lite.duckduckgo.com/lite/", data={"q": query}, headers=headers, timeout=10)
        res.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(res.text, "html.parser")
        results = []
        for tr in soup.find_all("tr"):
            title_a = tr.find("a", class_="result-link")
            if title_a:
                title = title_a.get_text(strip=True)
                url = title_a.get("href")
                
                # Snippet is usually in the next row
                snippet = ""
                snippet_tr = tr.find_next_sibling("tr")
                if snippet_tr:
                    snippet_td = snippet_tr.find("td", class_="result-snippet")
                    if snippet_td:
                        snippet = snippet_td.get_text(strip=True)
                
                if url and not url.startswith("/"):
                    results.append({"title": title, "url": url, "snippet": snippet})

        return jsonify({"ok": True, "results": results})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

CLOUDFLARE_TUNNEL_URL = None

def start_cloudflare_tunnel():
    global CLOUDFLARE_TUNNEL_URL
    log_file_path = BASE_DIR / "cloudflared.log"
    if log_file_path.exists():
        try:
            log_file_path.unlink()
        except Exception:
            pass
    
    print("  Starting Cloudflare Public cellular tunnel...")
    try:
        cmd = f'cloudflared tunnel --url http://localhost:8767 --logfile "{log_file_path}"'
        p = subprocess.Popen(cmd, shell=True)
        
        start_t = time.time()
        while time.time() - start_t < 30:
            if log_file_path.exists():
                try:
                    with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    import re
                    match = re.search(r'https://[a-zA-Z0-9\-_.]+\.trycloudflare\.com', content)
                    if match:
                        CLOUDFLARE_TUNNEL_URL = match.group(0)
                        print(f"\n[CLOUDFLARE] Public cellular tunnel active: {CLOUDFLARE_TUNNEL_URL}\n")
                        break
                except Exception:
                    pass
            time.sleep(1)
    except Exception as e:
        print(f"Failed to start cloudflared: {e}")

def ensure_node_torrent_service():
    import socket
    import sys
    # Check if port 8766 is open
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    result = s.connect_ex(('127.0.0.1', 8766))
    s.close()
    
    if result != 0:
        print("  [SYSTEM] Node.js Torrent Service (port 8766) not running. Launching...")
        try:
            # Launch node torrent_service.mjs in the background
            subprocess.Popen(
                ["node", "torrent_service.mjs"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            print("  [SYSTEM] Node.js Torrent Service started successfully.")
        except Exception as e:
            print(f"  [SYSTEM] Failed to start Node.js Torrent Service: {e}")
    else:
        print("  [SYSTEM] Node.js Torrent Service is already active on port 8766.")

# ─────────────────────────────────────────────
# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
# Aegis Shield (Antivirus / System Protection)
# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
@app.route("/api/aegis/scan", methods=["GET"])
def api_aegis_scan():
    try:
        processes = []
        temp_dir = os.environ.get('TEMP', 'C:\\Windows\\Temp').lower()
        appdata_local_temp = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp').lower()

        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                info = proc.info
                path = (info['exe'] or "").lower()
                suspicious = bool(path and (temp_dir in path or appdata_local_temp in path))
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "path": info['exe'] or "Access Denied",
                    "suspicious": suspicious
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        startup_items = []
        if winreg:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(key, i)
                        startup_items.append({"name": name, "path": val})
                        i += 1
                    except OSError:
                        break
            except Exception:
                pass
                
        hosts_ok = True
        try:
            hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            if os.path.exists(hosts_path):
                with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                    if len(f.readlines()) > 100:
                        hosts_ok = False
        except Exception:
            pass

        return jsonify({"ok": True, "data": {
            "processes": processes,
            "startup": startup_items,
            "hosts_ok": hosts_ok
        }})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/aegis/kill", methods=["POST"])
def api_aegis_kill():
    try:
        pid = request.get_json().get("pid")
        if not pid: return jsonify({"ok": False, "error": "PID required"}), 400
        p = psutil.Process(int(pid))
        p.terminate()
        p.wait(timeout=3)
        return jsonify({"ok": True, "message": f"Process {pid} terminated."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/aegis/disable_startup", methods=["POST"])
def api_aegis_disable_startup():
    try:
        name = request.get_json().get("name")
        if not name or not winreg: return jsonify({"ok": False, "error": "Name required or not on Windows"}), 400
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
        return jsonify({"ok": True, "message": f"Startup item '{name}' disabled."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/aegis/clean_temp", methods=["POST"])
def api_aegis_clean_temp():
    try:
        freed = 0
        folders = [os.environ.get('TEMP', r'C:\Users\Default\AppData\Local\Temp'), r"C:\Windows\Temp"]
        for folder in folders:
            if os.path.exists(folder):
                for item in os.listdir(folder):
                    item_path = os.path.join(folder, item)
                    try:
                        if os.path.isfile(item_path):
                            size = os.path.getsize(item_path)
                            os.remove(item_path)
                            freed += size
                        elif os.path.isdir(item_path):
                            size = sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, _, filenames in os.walk(item_path) for filename in filenames)
                            shutil.rmtree(item_path)
                            freed += size
                    except Exception:
                        pass
        mb = freed / (1024.0 * 1024.0)
        return jsonify({"ok": True, "message": f"Cleared {mb:.1f} MB of temporary files."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/aegis/reset_hosts", methods=["POST"])
def api_aegis_reset_hosts():
    try:
        path = r"C:\Windows\System32\drivers\etc\hosts"
        content = "# Copyright (c) 1993-2009 Microsoft Corp.\n#\n# This is a sample HOSTS file used by Microsoft TCP/IP for Windows.\n#\n# This file contains the mappings of IP addresses to host names.\n127.0.0.1       localhost\n::1             localhost\n"
        with open(path, "w", encoding="ascii") as f:
            f.write(content)
        return jsonify({"ok": True, "message": "Hosts file reset to defaults."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/aegis/defender_scan", methods=["POST"])
def api_aegis_defender_scan():
    try:
        path = r"C:\Program Files\Windows Defender\MpCmdRun.exe"
        if os.path.exists(path):
            subprocess.Popen([path, "-Scan", "-ScanType", "1"], creationflags=subprocess.CREATE_NO_WINDOW)
            return jsonify({"ok": True, "message": "Defender Scan Triggered Successfully"})
        return jsonify({"ok": False, "error": "Windows Defender command-line tool not found."}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
# Startup
# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ


def startup():
    """Initialize background tasks on server start."""
    ensure_node_torrent_service()
    lan_ip = get_local_ip()
    print("=" * 55)
    print("  Personal Security Command Center — ONLINE")
    print("=" * 55)
    print(f"  This PC       :  http://localhost:8767")
    print(f"  iPhone/Android:  http://{lan_ip}:8767  <-- use this!")
    print(f"  Mode          :  Public (JWT Secured)")
    print(f"  Server version:  {SERVER_VERSION}")
    print("=" * 55)
    
    # Start Cloudflare cellular tunnel background thread
    threading.Thread(target=start_cloudflare_tunnel, daemon=True).start()
    
    print("\n  Starting background network scanner...")
    # Do an initial scan in background
    threading.Thread(target=lambda: setattr(
        netscanner, '_last_scan_result', netscanner.scan_and_check()
    ), daemon=True).start()
    # Start continuous scanner (every 90 seconds)
    netscanner.start_background_scanner(interval=90)
    print("  Network scanner active")
    
    # Ignite Honeypot
    import honeypot
    honeypot.start_honeypot()
    
    # Start Tarpit and Tripwire
    print("  Starting Infinite Tarpit...")
    tarpit.start_tarpit_daemon()
    
    print("  Arming Ransomware Tripwire...")
    tripwire.start_tripwire_daemon()
    
    print(f"\n  Open on iPhone: http://{lan_ip}:8767\n")


import re
@app.route("/api/osint/scan", methods=["POST"])
def api_osint_scan():
    """GhostTrack OSINT Scanner Endpoint"""
    if not HAS_OSINT:
        return jsonify({"ok": False, "error": "OSINT modules not available"}), 503
        
    data = request.json
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({"error": "Empty query"}), 400
        
    def determine_type(q):
        if re.match(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", q): return "IP"
        if re.match(r"^\+?[1-9]\d{1,14}$", q): return "PHONE"
        if re.match(r"[^@]+@[^@]+\.[^@]+", q): return "EMAIL"
        if re.match(r"^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$", q): return "DOMAIN"
        return "USERNAME"
        
    target_type = determine_type(query)
    
    result = {
        "target": query,
        "type": target_type,
        "status": "success",
        "data": {}
    }
    
    if target_type == "IP":
        result["data"] = ip_intel.scan_ip(query)
    elif target_type == "USERNAME":
        result["data"] = user_intel.scan_username(query)
    elif target_type == "PHONE":
        result["data"] = phone_intel.scan_phone(query)
    elif target_type == "EMAIL":
        result["data"] = email_intel.scan_email(query)
    else:
        result["data"] = {"message": f"Module for {target_type} is not fully implemented yet."}
        
    if isinstance(result["data"], dict) and "error" in result["data"]:
        result["ok"] = False
        result["error"] = result["data"]["error"]
    else:
        result["ok"] = True
        
    return jsonify(result)

@app.route("/api/osint/exif", methods=["POST"])
def api_osint_exif():
    """GhostTrack EXIF Image Forensics Endpoint"""
    if not HAS_OSINT:
        return jsonify({"ok": False, "error": "OSINT modules not available"}), 503
        
    if 'image' not in request.files:
        return jsonify({"ok": False, "error": "No image uploaded"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"ok": False, "error": "No selected image"}), 400
        
    try:
        file_bytes = file.read()
        if len(file_bytes) > 10 * 1024 * 1024:
            return jsonify({"ok": False, "error": "Image too large (max 10MB)"}), 400
            
        result = exif_intel.extract_exif(file_bytes)
        if "error" in result:
            return jsonify({"ok": False, "error": result["error"]}), 400
            
        return jsonify({
            "ok": True,
            "target": file.filename,
            "type": "EXIF",
            "status": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────
# NEW: Toolkit Sandbox Endpoint
# ─────────────────────────────────────────────
import sandbox

import urllib.request
import json
import os
import subprocess

@app.route("/api/toolkit/wayback", methods=["POST"])
def api_toolkit_wayback():
    try:
        data = request.get_json(force=True)
        target = data.get("ip", "").strip()
        if not target:
            return jsonify({"ok": False, "error": "No target provided."})
        
        url = f"http://web.archive.org/cdx/search/cdx?url={target}&output=json&limit=5&fastLatest=true"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            resp_data = json.loads(response.read().decode('utf-8'))
        
        if not resp_data or len(resp_data) < 2:
            return jsonify({"ok": True, "output": f"No historical snapshots found in Archive.org for {target}"})
            
        out = f"Wayback Machine Snapshots for {target}:\n"
        out += "-" * 50 + "\n"
        # Skip the header row
        for row in resp_data[1:]:
            timestamp = row[1]
            original = row[2]
            status = row[4]
            out += f"[{timestamp}] (Status: {status})\n"
            out += f"URL: https://web.archive.org/web/{timestamp}/{original}\n\n"
            
        return jsonify({"ok": True, "output": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/toolkit/archive_local", methods=["POST"])
def api_toolkit_archive_local():
    try:
        data = request.get_json(force=True)
        target = data.get("ip", "").strip()
        if not target:
            return jsonify({"ok": False, "error": "No target provided."})
            
        if not target.startswith("http"):
            target = "http://" + target
            
        req = urllib.request.Request(target, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')
            headers = dict(response.headers)
            
        # Create archives folder
        archive_dir = BASE_DIR / "archives"
        archive_dir.mkdir(exist_ok=True)
        
        safe_name = target.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_")
        filename = f"{safe_name}_archive.html"
        file_path = archive_dir / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"<!-- Archived from {target} -->\n")
            f.write(f"<!-- Headers: {json.dumps(headers)} -->\n\n")
            f.write(html)
            
        out = f"Local Archive Created Successfully!\n"
        out += "-" * 50 + "\n"
        out += f"Target: {target}\n"
        out += f"Saved as: {filename}\n"
        out += f"File Size: {len(html)} bytes\n"
        out += f"Location: {file_path.absolute()}\n"
        
        return jsonify({"ok": True, "output": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/media/streamlink", methods=["POST"])
def api_media_streamlink():
    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"ok": False, "error": "No URL provided."})
            
        # Spawn streamlink process to open in native player (VLC)
        # Using CREATE_NO_WINDOW or just Popen so it runs in background
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(["streamlink", url, "best"], creationflags=CREATE_NO_WINDOW)
        
        return jsonify({"ok": True, "message": "Streamlink launched locally! VLC should open shortly."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/toolkit/sandbox", methods=["POST"])
def api_toolkit_sandbox():
    try:
        body = request.get_json()
        url = body.get("url", "")
        if not url:
            return jsonify({"ok": False, "error": "No URL provided"}), 400
        result = sandbox.analyze_url(url)
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────
# NEW: Packet Sniffer Endpoints
# ─────────────────────────────────────────────
import sniffer

@app.route("/api/network/sniffer", methods=["POST", "GET"])
def api_network_sniffer():
    try:
        if request.method == "POST":
            data = request.get_json()
            action = data.get("action")
            if action == "start":
                sniffer.start_sniffer()
                return jsonify({"ok": True, "status": "running"})
            elif action == "stop":
                sniffer.stop_sniffer()
                return jsonify({"ok": True, "status": "stopped"})
            else:
                return jsonify({"ok": False, "error": "Invalid action"}), 400
        else: # GET
            packets = sniffer.get_recent_packets()
            running = sniffer.is_running()
            return jsonify({"ok": True, "running": running, "packets": packets})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ══════════════════════════════════════════════════════════════════
# REVERSE IMAGE SEARCH (SauceNAO — in-suite, no redirect)
# ══════════════════════════════════════════════════════════════════

def extract_video_frame(video_data):
    import subprocess
    import tempfile
    import os
    import imageio_ffmpeg
    
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
        temp_video.write(video_data)
        temp_video_path = temp_video.name
        
    temp_image_path = temp_video_path + ".jpg"
    try:
        cmd = [
            ffmpeg_exe,
            "-y",
            "-ss", "1.0",
            "-i", temp_video_path,
            "-vframes", "1",
            "-f", "image2",
            temp_image_path
        ]
        kwargs = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "check": True,
            "timeout": 10
        }
        if os.name == 'nt':
            kwargs['creationflags'] = 0x08000000
            
        subprocess.run(cmd, **kwargs)
        
        if os.path.exists(temp_image_path):
            with open(temp_image_path, "rb") as f:
                img_data = f.read()
            return img_data
    except Exception as e:
        print(f"Error extracting video frame: {e}")
    finally:
        try:
            os.remove(temp_video_path)
        except:
            pass
        try:
            os.remove(temp_image_path)
        except:
            pass
    return None

@app.route("/api/reverse-image", methods=["POST"])
def api_reverse_image():
    """Reverse image/video search via SauceNAO API — returns results inline."""
    import urllib.request, urllib.parse, json as _json
    import io

    SAUCENAO_URL = "https://saucenao.com/search.php"
    params = {
        "output_type": "2",   # JSON
        "numres": "10",
        "hide": "0",
        "db": "999",          # all databases
    }

    try:
        # Load SauceNAO API key from config or environment
        import os
        cfg = load_app_config()
        saucenao_api_key = cfg.get("saucenao_api_key") or os.environ.get("SAUCENAO_API_KEY")
        if saucenao_api_key:
            params["api_key"] = saucenao_api_key

        # Determine input: URL or uploaded file
        if 'file' in request.files:
            f = request.files['file']
            file_data = f.read()
            filename = (f.filename or "").lower()
            is_video = filename.endswith(('.mp4', '.m4v', '.mov', '.avi', '.webm', '.flv', '.mkv', '.3gp')) or 'video' in (f.content_type or '').lower()
            
            if is_video:
                frame_data = extract_video_frame(file_data)
                if not frame_data:
                    return jsonify({"ok": False, "error": "Failed to extract keyframe from video. Make sure it's a valid video file."}), 400
                file_data = frame_data
                filename = "frame.jpg"
            else:
                filename = f.filename or "image.jpg"

            # Multipart POST to SauceNAO
            boundary = "----SauceSuiteBoundary7a8b9c"
            body_parts = []
            for k, v in params.items():
                body_parts.append(
                    f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}'.encode()
                )
            body_parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
                + file_data
            )
            body_parts.append(f'--{boundary}--'.encode())
            body = b'\r\n'.join(body_parts)
            req = urllib.request.Request(
                SAUCENAO_URL,
                data=body,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "User-Agent": "SecuritySuite/1.0",
                }
            )
        else:
            body = request.get_json() or {}
            img_url = body.get("url", "").strip()
            if not img_url:
                return jsonify({"ok": False, "error": "No image URL or file provided"}), 400
            params["url"] = img_url
            encoded = urllib.parse.urlencode(params).encode()
            req = urllib.request.Request(
                SAUCENAO_URL,
                data=encoded,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "SecuritySuite/1.0",
                }
            )

        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = _json.loads(resp.read())

        # Parse response
        header = raw.get("header", {})
        results_raw = raw.get("results", [])

        if header.get("status", 0) < 0:
            return jsonify({"ok": False, "error": f"SauceNAO error: {header.get('message', 'Unknown error')}"}), 500

        results = []
        for r in results_raw:
            h = r.get("header", {})
            d = r.get("data", {})
            similarity = float(h.get("similarity", 0))
            if similarity < 40:
                continue  # skip very low matches
            title = (
                d.get("title") or
                d.get("eng_name") or
                d.get("jp_name") or
                d.get("source") or
                d.get("material") or
                d.get("creator") or
                "Unknown Source"
            )
            # Collect URLs
            ext_urls = d.get("ext_urls", [])
            # Author / creator info
            author = (
                d.get("author_name") or
                d.get("creator") or
                d.get("member_name") or
                d.get("artist") or
                ""
            )
            if isinstance(author, list):
                author = ", ".join(author)

            results.append({
                "similarity": round(similarity, 1),
                "thumbnail": h.get("thumbnail", ""),
                "title": str(title)[:120],
                "author": str(author)[:80],
                "index_name": h.get("index_name", ""),
                "urls": ext_urls[:3],
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)

        return jsonify({
            "ok": True,
            "long_limit_remaining": header.get("long_remaining", "?"),
            "short_limit_remaining": header.get("short_remaining", "?"),
            "results_count": len(results),
            "results": results[:8],
        })

    except urllib.error.HTTPError as e:
        if e.code == 429:
            return jsonify({"ok": False, "error": "Rate limited by SauceNAO (429). Wait a minute and try again."}), 429
        if e.code == 403:
            return jsonify({
                "ok": False,
                "error": "SauceNAO API access Forbidden (403). Please register for a free API key at https://saucenao.com/user.php?page=search-api and configure it in the Settings tab (under More in the bottom navigation) of the dashboard."
            }), 403
        return jsonify({"ok": False, "error": f"HTTP {e.code}: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════
# REVERSE ENGINEERING LAB
# ══════════════════════════════════════════════════════════════════

@app.route("/api/analyze", methods=["POST"])
def api_analyze_file():
    """Analyze an uploaded file: hashes, strings, hex dump, entropy, PE info."""
    import hashlib, binascii, math, struct
    from collections import Counter
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400
    f = request.files['file']
    data = f.read()
    size = len(data)

    # Hashes
    hashes = {
        "md5":    hashlib.md5(data).hexdigest(),
        "sha1":   hashlib.sha1(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha512": hashlib.sha512(data).hexdigest(),
    }

    # Magic bytes / file type
    MAGIC = [
        (b'\x4d\x5a', 'Windows PE Executable (EXE/DLL)'),
        (b'\x7fELF', 'Linux ELF Executable'),
        (b'\x89PNG', 'PNG Image'),
        (b'\xff\xd8\xff', 'JPEG Image'),
        (b'GIF8', 'GIF Image'),
        (b'%PDF', 'PDF Document'),
        (b'PK\x03\x04', 'ZIP Archive / Office Document'),
        (b'Rar!', 'RAR Archive'),
        (b'\x1f\x8b', 'GZIP Archive'),
        (b'\xfd7zXZ', 'XZ Archive'),
        (b'MSCF', 'Windows Cabinet (.cab)'),
        (b'\xd0\xcf\x11\xe0', 'Microsoft Office (OLE2)'),
        (b'{\\rtf', 'Rich Text Format'),
    ]
    file_type = 'Unknown Binary'
    for magic, desc in MAGIC:
        if data[:len(magic)] == magic:
            file_type = desc
            break
    if all(32 <= b < 127 or b in (9, 10, 13) for b in data[:512]):
        file_type = 'ASCII/UTF-8 Text'

    # Entropy
    if data:
        freq = Counter(data)
        total = len(data)
        entropy = -sum((c/total) * math.log2(c/total) for c in freq.values() if c > 0)
    else:
        entropy = 0.0

    # Strings extraction (printable runs >= 5 chars)
    import re as _re
    strings_found = _re.findall(rb'[ -~]{5,}', data)
    strings_list = [s.decode('ascii', errors='replace') for s in strings_found[:200]]

    # Hex dump (first 512 bytes)
    hex_lines = []
    for i in range(0, min(512, len(data)), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        asc_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        hex_lines.append(f'{i:08x}  {hex_part:<47}  |{asc_part}|')

    # PE Analysis
    pe_info = None
    if data[:2] == b'MZ':
        try:
            import pefile
            pe = pefile.PE(data=data)
            suspicious_apis = ['CreateRemoteThread','VirtualAllocEx','WriteProcessMemory',
                               'SetWindowsHookEx','RegSetValue','URLDownloadToFile',
                               'ShellExecute','WinExec','CreateProcess']
            imports = []
            if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
                for entry in pe.DIRECTORY_ENTRY_IMPORT:
                    dll = entry.dll.decode('utf-8', errors='replace')
                    funcs = []
                    for imp in entry.imports:
                        name = imp.name.decode('utf-8', errors='replace') if imp.name else f'ord_{imp.ordinal}'
                        funcs.append({'name': name, 'suspicious': any(s.lower() in name.lower() for s in suspicious_apis)})
                    imports.append({'dll': dll, 'functions': funcs})
            sections = []
            for sec in pe.sections:
                sections.append({
                    'name': sec.Name.decode('utf-8', errors='replace').strip('\x00'),
                    'virtual_address': hex(sec.VirtualAddress),
                    'size': sec.SizeOfRawData
                })
            ts = pe.FILE_HEADER.TimeDateStamp
            import datetime
            compile_time = datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S UTC') if ts else 'Unknown'
            pe_info = {'imports': imports, 'sections': sections, 'compile_time': compile_time,
                       'machine': hex(pe.FILE_HEADER.Machine),
                       'entry_point': hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)}
        except Exception as pe_err:
            pe_info = {'error': str(pe_err), 'note': 'Install pefile: pip install pefile'}

    return jsonify({
        'ok': True,
        'filename': f.filename,
        'size': size,
        'file_type': file_type,
        'entropy': round(entropy, 4),
        'entropy_risk': 'High (packed/encrypted)' if entropy > 7.0 else 'Medium' if entropy > 5.0 else 'Normal',
        'hashes': hashes,
        'strings': strings_list,
        'hex_dump': hex_lines,
        'pe_info': pe_info
    })


# ══════════════════════════════════════════════════════════════════
# SAUCE FINDER / OSINT HUB
# ══════════════════════════════════════════════════════════════════

@app.route("/api/unshorten", methods=["POST"])
def api_unshorten():
    """Follow redirect chain for a short URL and return the final destination."""
    import urllib.request
    body = request.get_json() or {}
    url = body.get('url', '').strip()
    if not url:
        return jsonify({'ok': False, 'error': 'URL required'}), 400
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        chain = []
        current = url
        for _ in range(10):
            req = urllib.request.Request(current, headers={'User-Agent': 'Mozilla/5.0'}, method='HEAD')
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    chain.append({'url': current, 'status': resp.status})
                    if resp.url != current:
                        chain.append({'url': resp.url, 'status': resp.status})
                    break
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308):
                    next_url = e.headers.get('Location', '')
                    chain.append({'url': current, 'status': e.code})
                    current = next_url
                else:
                    chain.append({'url': current, 'status': e.code})
                    break
        return jsonify({'ok': True, 'original': url, 'final': chain[-1]['url'] if chain else url, 'chain': chain})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route("/api/whois", methods=["POST"])
def api_whois():
    """WHOIS + basic domain info lookup."""
    import urllib.request, json as _json, re as _re
    body = request.get_json() or {}
    domain = body.get('domain', '').strip()
    # Strip protocol/path
    domain = _re.sub(r'^https?://', '', domain)
    domain = domain.split('/')[0].strip()
    if not domain:
        return jsonify({'ok': False, 'error': 'Domain required'}), 400
    try:
        # Use whois.domaintools.com JSON (no key needed for basic)
        # Fallback: rdap.org which is fully open
        rdap_url = f'https://rdap.org/domain/{domain}'
        req = urllib.request.Request(rdap_url, headers={'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            rdap = _json.loads(resp.read())
        # Extract useful fields
        name = rdap.get('ldhName', domain)
        status = rdap.get('status', [])
        events = {e['eventAction']: e['eventDate'] for e in rdap.get('events', [])}
        nameservers = [ns.get('ldhName', '') for ns in rdap.get('nameservers', [])]
        entities = rdap.get('entities', [])
        registrar = ''
        for ent in entities:
            roles = ent.get('roles', [])
            if 'registrar' in roles:
                vcard = ent.get('vcardArray', [None, []])[1]
                for field in vcard:
                    if field[0] == 'fn':
                        registrar = field[3]
        return jsonify({'ok': True, 'domain': name, 'status': status,
                        'registered': events.get('registration', 'Unknown'),
                        'expires': events.get('expiration', 'Unknown'),
                        'updated': events.get('last changed', 'Unknown'),
                        'registrar': registrar,
                        'nameservers': nameservers})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route("/api/username-check", methods=["POST"])
def api_username_check():
    """Check if a username exists on popular platforms."""
    import urllib.request
    import concurrent.futures
    body = request.get_json() or {}
    username = body.get('username', '').strip()
    if not username or len(username) < 2:
        return jsonify({'ok': False, 'error': 'Username required (min 2 chars)'}), 400

    PLATFORMS = {
        'GitHub':    f'https://github.com/{username}',
        'Reddit':    f'https://www.reddit.com/user/{username}',
        'Twitter/X': f'https://twitter.com/{username}',
        'Instagram': f'https://www.instagram.com/{username}/',
        'TikTok':    f'https://www.tiktok.com/@{username}',
        'YouTube':   f'https://www.youtube.com/@{username}',
        'Twitch':    f'https://www.twitch.tv/{username}',
        'Pinterest': f'https://www.pinterest.com/{username}/',
        'Telegram':  f'https://t.me/{username}',
        'Steam':     f'https://steamcommunity.com/id/{username}',
        'GitLab':    f'https://gitlab.com/{username}',
        'Dev.to':    f'https://dev.to/{username}',
        'Replit':    f'https://replit.com/@{username}',
        'HackerNews':f'https://news.ycombinator.com/user?id={username}',
        'Keybase':   f'https://keybase.io/{username}',
    }

    def check_platform(name, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}, method='HEAD')
            with urllib.request.urlopen(req, timeout=6) as resp:
                return {'platform': name, 'url': url, 'found': resp.status == 200, 'status': resp.status}
        except urllib.error.HTTPError as e:
            found = e.code not in (404, 410)
            return {'platform': name, 'url': url, 'found': found, 'status': e.code}
        except Exception:
            return {'platform': name, 'url': url, 'found': False, 'status': 'timeout'}

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(check_platform, n, u): n for n, u in PLATFORMS.items()}
        for fut in concurrent.futures.as_completed(futs):
            results.append(fut.result())
    results.sort(key=lambda x: (not x['found'], x['platform']))
    return jsonify({'ok': True, 'username': username, 'results': results})


# ══════════════════════════════════════════════════════════════════
# SSL INSPECTOR
# ══════════════════════════════════════════════════════════════════

@app.route("/api/ssl-check", methods=["POST"])
def api_ssl_check():
    """Inspect SSL/TLS certificate for a domain."""
    import ssl, socket, datetime
    body = request.get_json() or {}
    domain = body.get('domain', '').strip()
    import re as _re
    domain = _re.sub(r'^https?://', '', domain).split('/')[0]
    if not domain:
        return jsonify({'ok': False, 'error': 'Domain required'}), 400
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                version = ssock.version()

        subject = dict(x[0] for x in cert.get('subject', []))
        issuer  = dict(x[0] for x in cert.get('issuer', []))
        not_before = cert.get('notBefore', '')
        not_after  = cert.get('notAfter', '')
        san = [v for _,v in cert.get('subjectAltName', [])]

        # Parse expiry
        fmt = '%b %d %H:%M:%S %Y %Z'
        expiry_dt = datetime.datetime.strptime(not_after, fmt)
        days_left = (expiry_dt - datetime.datetime.utcnow()).days

        # Security assessment
        warnings = []
        if days_left < 30: warnings.append(f'Certificate expires in {days_left} days!')
        if 'TLSv1' in version or 'TLSv1.1' in version: warnings.append('Weak TLS version: ' + version)
        if cipher and any(w in cipher[0].upper() for w in ['RC4','DES','NULL','EXPORT','ANON']): warnings.append('Weak cipher: ' + cipher[0])

        return jsonify({'ok': True, 'domain': domain,
                        'subject': subject, 'issuer': issuer,
                        'valid_from': not_before, 'valid_until': not_after,
                        'days_remaining': days_left,
                        'san': san, 'cipher': cipher[0] if cipher else '',
                        'tls_version': version,
                        'protocol_secure': version in ('TLSv1.2', 'TLSv1.3'),
                        'warnings': warnings})
    except ssl.SSLCertVerificationError as e:
        return jsonify({'ok': False, 'error': f'Certificate verification failed: {e}'}), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════
# CVE SCANNER (NVD API - no key needed)
# ══════════════════════════════════════════════════════════════════

@app.route("/api/cve", methods=["POST"])
def api_cve_search():
    """Search CVEs for a software/keyword using NVD API."""
    import urllib.request, json as _json, urllib.parse
    body = request.get_json() or {}
    query = body.get('query', '').strip()
    if not query:
        return jsonify({'ok': False, 'error': 'Query required'}), 400
    try:
        params = urllib.parse.urlencode({'keywordSearch': query, 'resultsPerPage': 15, 'startIndex': 0})
        url = f'https://services.nvd.nist.gov/rest/json/cves/2.0?{params}'
        req = urllib.request.Request(url, headers={'User-Agent': 'SecuritySuite/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            nvd = _json.loads(resp.read())
        cves = []
        for item in nvd.get('vulnerabilities', []):
            cve = item.get('cve', {})
            cve_id = cve.get('id', '')
            descs = cve.get('descriptions', [])
            desc = next((d['value'] for d in descs if d['lang'] == 'en'), '')
            metrics = cve.get('metrics', {})
            cvss_score = None
            severity = 'UNKNOWN'
            for key in ('cvssMetricV31', 'cvssMetricV30', 'cvssMetricV2'):
                if key in metrics and metrics[key]:
                    m = metrics[key][0]
                    cvss_score = m.get('cvssData', {}).get('baseScore')
                    severity = m.get('cvssData', {}).get('baseSeverity', m.get('baseSeverity', 'UNKNOWN'))
                    break
            published = cve.get('published', '')[:10]
            references = [r['url'] for r in cve.get('references', [])[:3]]
            cves.append({'id': cve_id, 'description': desc[:300],
                         'cvss_score': cvss_score, 'severity': severity,
                         'published': published, 'references': references})
        return jsonify({'ok': True, 'query': query, 'total': nvd.get('totalResults', 0), 'cves': cves})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════
# PASSWORD AUDITOR (HaveIBeenPwned k-anonymity — never sends full hash)
# ══════════════════════════════════════════════════════════════════

@app.route("/api/hibp", methods=["POST"])
def api_hibp():
    """Check if a password appears in breach databases using k-anonymity."""
    import hashlib, urllib.request
    body = request.get_json() or {}
    password = body.get('password', '')
    if not password:
        return jsonify({'ok': False, 'error': 'Password required'}), 400
    sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    try:
        url = f'https://api.pwnedpasswords.com/range/{prefix}'
        req = urllib.request.Request(url, headers={'User-Agent': 'SecuritySuite/1.0', 'Add-Padding': 'true'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            lines = resp.read().decode().splitlines()
        count = 0
        for line in lines:
            h, c = line.split(':')
            if h == suffix:
                count = int(c)
                break
        # Strength analysis
        strength = 0
        tips = []
        if len(password) >= 12: strength += 25
        else: tips.append('Use at least 12 characters')
        if any(c.isupper() for c in password): strength += 20
        else: tips.append('Add uppercase letters')
        if any(c.islower() for c in password): strength += 20
        else: tips.append('Add lowercase letters')
        if any(c.isdigit() for c in password): strength += 20
        else: tips.append('Add numbers')
        if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password): strength += 15
        else: tips.append('Add special characters (!@#$...)')
        return jsonify({'ok': True, 'pwned': count > 0, 'breach_count': count,
                        'strength': strength, 'tips': tips,
                        'strength_label': 'Weak' if strength < 40 else 'Fair' if strength < 70 else 'Strong' if strength < 90 else 'Very Strong'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════
# PHISHING DETECTOR
# ══════════════════════════════════════════════════════════════════

@app.route("/api/phishing", methods=["POST"])
def api_phishing_check():
    """Analyse a URL for phishing indicators without an external API key."""
    import re as _re, urllib.parse, urllib.request
    body = request.get_json() or {}
    url = body.get('url', '').strip()
    if not url:
        return jsonify({'ok': False, 'error': 'URL required'}), 400
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    findings = []
    score = 0  # higher = more suspicious

    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()
    path   = parsed.path.lower()
    full   = url.lower()

    # Check 1: IP address as host
    if _re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', domain):
        findings.append({'flag': 'IP address used as domain', 'severity': 'high'}); score += 30

    # Check 2: Suspicious TLDs
    sus_tlds = ['.xyz', '.tk', '.ml', '.ga', '.cf', '.gq', '.top', '.club', '.online', '.site', '.icu']
    for tld in sus_tlds:
        if domain.endswith(tld):
            findings.append({'flag': f'Suspicious TLD: {tld}', 'severity': 'medium'}); score += 15

    # Check 3: Brand impersonation
    brands = ['paypal', 'apple', 'google', 'microsoft', 'amazon', 'netflix', 'facebook', 'instagram', 'bank', 'secure', 'login', 'verify', 'account', 'update']
    domain_without_tld = domain.split('.')[0]
    for brand in brands:
        if brand in domain and brand not in ['google.com', 'apple.com', 'microsoft.com']:
            findings.append({'flag': f'Brand keyword in domain: "{brand}"', 'severity': 'high'}); score += 25

    # Check 4: Excessive subdomains
    parts = domain.split('.')
    if len(parts) > 4:
        findings.append({'flag': f'Excessive subdomains ({len(parts)-2} levels)', 'severity': 'medium'}); score += 20

    # Check 5: Long URL
    if len(url) > 100:
        findings.append({'flag': f'Suspiciously long URL ({len(url)} chars)', 'severity': 'low'}); score += 10

    # Check 6: @ symbol in URL
    if '@' in url:
        findings.append({'flag': 'URL contains @ symbol (obfuscation technique)', 'severity': 'high'}); score += 30

    # Check 7: HTTP (not HTTPS)
    if parsed.scheme == 'http':
        findings.append({'flag': 'Not using HTTPS (unencrypted)', 'severity': 'medium'}); score += 15

    # Check 8: Phishing keywords in path
    phish_keywords = ['login', 'signin', 'verify', 'update', 'secure', 'account', 'password', 'bank', 'wallet', 'confirm']
    for kw in phish_keywords:
        if kw in path:
            findings.append({'flag': f'Phishing keyword in path: "{kw}"', 'severity': 'medium'}); score += 10
            break

    # Check 9: Double domain (typosquatting)
    if _re.search(r'\.(com|net|org)\.(com|net|org|xyz|tk)', domain):
        findings.append({'flag': 'Double TLD detected (typosquatting)', 'severity': 'high'}); score += 35

    # Check 10: URL shortener
    shorteners = ['bit.ly', 'tinyurl', 't.co', 'goo.gl', 'ow.ly', 'buff.ly', 'short.link']
    if any(s in domain for s in shorteners):
        findings.append({'flag': 'URL shortener detected (destination hidden)', 'severity': 'medium'}); score += 20

    risk = 'Safe' if score < 20 else 'Suspicious' if score < 50 else 'Likely Phishing' if score < 80 else 'DANGEROUS'
    risk_color = '#00ff88' if score < 20 else '#ffbb00' if score < 50 else '#ff4444' if score < 80 else '#ff0000'

    return jsonify({'ok': True, 'url': url, 'domain': domain, 'score': min(score, 100),
                    'risk': risk, 'risk_color': risk_color, 'findings': findings})

# ══════════════════════════════════════════════════════════════════
# THE TRAPPER (CANARY TOKENS)
# ══════════════════════════════════════════════════════════════════
import uuid, datetime
CANARY_TOKENS = {}
CANARY_HITS = []

@app.route("/api/token/generate", methods=["POST"])
def api_token_generate():
    body = request.get_json() or {}
    memo = body.get('memo', 'Untitled Token')
    token_id = str(uuid.uuid4())
    CANARY_TOKENS[token_id] = memo
    # Generate the tracking URL
    url = f"http://{get_local_ip()}:8767/api/token/trigger/{token_id}.png"
    return jsonify({"ok": True, "token": token_id, "url": url, "memo": memo})

@app.route("/api/token/trigger/<token_id>.png", methods=["GET"])
def api_token_trigger(token_id):
    """The silent trigger endpoint. Returns a 1x1 transparent pixel."""
    memo = CANARY_TOKENS.get(token_id, "Unknown Token")
    ip = request.remote_addr
    ua = request.headers.get("User-Agent", "")
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    hit = {
        "token_id": token_id,
        "memo": memo,
        "ip": ip,
        "user_agent": ua,
        "timestamp": ts
    }
    CANARY_HITS.insert(0, hit)
    print(f"\n[!!!] CANARY TOKEN TRIGGERED: {memo} by {ip} [!!!]\n")
    
    # Return 1x1 transparent PNG
    transparent_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(transparent_png, mimetype="image/png")

@app.route("/api/token/logs", methods=["GET"])
def api_token_logs():
    return jsonify({"ok": True, "hits": CANARY_HITS})

# ══════════════════════════════════════════════════════════════════
# ARP SPOOFING / MITM MONITOR
# ══════════════════════════════════════════════════════════════════
ARP_ALERTS = []

def arp_monitor_loop():
    import subprocess, time, re
    while True:
        try:
            output = subprocess.check_output("arp -a", shell=True, text=True)
            mac_map = {}
            for line in output.splitlines():
                # Match IP and MAC
                m = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-]+)\s+', line)
                if m:
                    ip, mac = m.groups()
                    mac = mac.lower()
                    if mac == "ff-ff-ff-ff-ff-ff" or ip.endswith(".255") or len(mac) != 17:
                        continue
                    if mac in mac_map:
                        if mac_map[mac] != ip:
                            # Two IPs sharing the same MAC! Possible ARP spoofing.
                            alert = f"ARP SPOOFING DETECTED: IP {ip} and {mac_map[mac]} are both claiming MAC {mac}"
                            if not any(a['msg'] == alert for a in ARP_ALERTS):
                                ARP_ALERTS.insert(0, {"timestamp": datetime.datetime.now().strftime("%H:%M:%S"), "msg": alert})
                                print(f"\n[!!!] {alert} [!!!]\n")
                    else:
                        mac_map[mac] = ip
        except Exception as e:
            pass
        time.sleep(10)

@app.route("/api/arp/logs", methods=["GET"])
def api_arp_logs():
    return jsonify({"ok": True, "alerts": ARP_ALERTS})

# ══════════════════════════════════════════════════════════════════
# LIVE TRACEROUTE (BGP VISUALIZER BACKEND)
# ══════════════════════════════════════════════════════════════════
@app.route("/api/traceroute/live", methods=["POST"])
def api_traceroute_live():
    import subprocess
    body = request.get_json() or {}
    target = body.get("target", "").strip()
    if not target:
        return jsonify({"ok": False, "error": "Target required"}), 400
    
    # Fast tracert (max 15 hops, 200ms timeout)
    try:
        output = subprocess.check_output(["tracert", "-d", "-w", "200", "-h", "15", target], text=True)
        hops = []
        import re
        for line in output.splitlines():
            m = re.search(r'^\s*(\d+)\s+.*?\s+(\d+\.\d+\.\d+\.\d+)', line)
            if m:
                hops.append({"hop": int(m.group(1)), "ip": m.group(2)})
        return jsonify({"ok": True, "target": target, "hops": hops})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════
# ACTIVE COUNTERMEASURES
# ══════════════════════════════════════════════════════════════════
@app.route("/api/tarpit/logs", methods=["GET"])
def api_tarpit_logs():
    return jsonify({
        "ok": True, 
        "active": tarpit.TARPIT_ACTIVE, 
        "port": tarpit.TARPIT_PORT,
        "logs": tarpit.TARPIT_LOGS
    })

@app.route("/api/tripwire/status", methods=["GET"])
def api_tripwire_status():
    return jsonify({
        "ok": True,
        "active": tripwire.TRIPWIRE_ACTIVE,
        "breached": tripwire.TRIPWIRE_BREACHED,
        "info": tripwire.TRIPWIRE_BREACH_INFO
    })

@app.route("/api/tripwire/reset", methods=["POST"])
def api_tripwire_reset():
    tripwire.TRIPWIRE_BREACHED = False
    tripwire.TRIPWIRE_BREACH_INFO = None
    tripwire.setup_honeyfile() # Recreate or fix the file
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------------------------------
# SENSOR FEED: Unified real-time event stream for the IDS sensor feed panel
# ---------------------------------------------------------------------------------------------------
@app.route("/api/events", methods=["GET"])
def api_events():
    """Return recent unified security events for the IDS sensor feed."""
    events = []

    # 1. Real security alerts (honeypot hits, scan detections, etc.)
    try:
        alerts = netscanner.load_alerts()
        for a in alerts[-20:]:
            sev = a.get("severity", "info")
            level = "ALERT" if sev == "critical" else ("WARN" if sev == "high" else "INFO")
            events.append({
                "time": a.get("timestamp", "")[:19].replace("T", " "),
                "level": level,
                "category": "INTRUSION",
                "msg": a.get("message", a.get("title", "Security alert")),
                "data": a.get("data", {}),
                "acknowledged": a.get("acknowledged", False)
            })
    except Exception:
        pass

    # 2. Tripwire breach
    try:
        if tripwire.TRIPWIRE_BREACHED and tripwire.TRIPWIRE_BREACH_INFO:
            info = tripwire.TRIPWIRE_BREACH_INFO
            events.append({
                "time": info.get("time", ""),
                "level": "CRITICAL",
                "category": "TRIPWIRE",
                "msg": f"RANSOMWARE TRIPWIRE TRIGGERED — Honey file {info.get('event', 'accessed')}",
                "data": {"event": info.get("event", ""), "file": "Passwords_DO_NOT_OPEN/bank_details.txt"},
                "acknowledged": False
            })
    except Exception:
        pass

    # 3. Tripwire system status line
    try:
        events.append({
            "time": "",
            "level": "SYS",
            "category": "SYSTEM",
            "msg": f"Ransomware tripwire {'ARMED — monitoring honey file' if tripwire.TRIPWIRE_ACTIVE else 'OFFLINE'}",
            "data": {},
            "acknowledged": True
        })
    except Exception:
        pass

    # Sort: unacknowledged/critical first, then by time descending
    events.sort(key=lambda e: (e.get("acknowledged", True), e.get("time", "")), reverse=True)
    return jsonify({"ok": True, "events": events[:40]})


# ---------------------------------------------------------------------------------------------------
# NEW: USB Trap Endpoints
# ---------------------------------------------------------------------------------------------------
import usb_trap

@app.route("/api/usb/status", methods=["GET"])
def api_usb_status():
    return jsonify({"ok": True, "data": usb_trap.get_status()})

@app.route("/api/usb/arm", methods=["POST"])
def api_usb_arm():
    usb_trap.arm_trap()
    return jsonify({"ok": True, "armed": True})

@app.route("/api/usb/disarm", methods=["POST"])
def api_usb_disarm():
    usb_trap.disarm_trap()
    return jsonify({"ok": True, "armed": False})

# Global state for casino points
cyber_credits = 500

@app.route("/api/casino/sync", methods=["POST"])
def api_casino_sync():
    global cyber_credits
    try:
        data = request.get_json() or {}
        # If frontend is pushing points, accept them (trust the client for offline mode)
        if "points" in data:
            cyber_credits = int(data["points"])
        return jsonify({"ok": True, "points": cyber_credits})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════
# WALKIE-TALKIE BROADCAST & RECEIVE SYSTEM
# ══════════════════════════════════════════════════════════════════
WALKIE_TALKIE_MESSAGES = []
WALKIE_TALKIE_COUNTER = 0
WALKIE_TALKIE_LOCK = threading.Lock()

@app.route("/api/walkie-talkie/broadcast", methods=["POST"])
def api_wt_broadcast():
    global WALKIE_TALKIE_COUNTER
    try:
        data = request.get_json() or {}
        frequency = data.get("frequency")
        audio = data.get("audio")
        sender = data.get("sender", "Unknown")
        mime_type = data.get("mime_type", "audio/webm")
        
        if not frequency or not audio:
            return jsonify({"ok": False, "error": "Missing frequency or audio"}), 400
            
        with WALKIE_TALKIE_LOCK:
            WALKIE_TALKIE_COUNTER += 1
            msg = {
                "id": WALKIE_TALKIE_COUNTER,
                "frequency": float(frequency),
                "sender": sender,
                "audio": audio,
                "mime_type": mime_type,
                "timestamp": time.time()
            }
            WALKIE_TALKIE_MESSAGES.append(msg)
            if len(WALKIE_TALKIE_MESSAGES) > 30:
                WALKIE_TALKIE_MESSAGES.pop(0)
                
        return jsonify({"ok": True, "id": WALKIE_TALKIE_COUNTER})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/walkie-talkie/receive", methods=["GET"])
def api_wt_receive():
    try:
        last_id = int(request.args.get("last_id", 0))
        frequency = request.args.get("frequency")
        
        if not frequency:
            return jsonify({"ok": False, "error": "Missing frequency"}), 400
            
        target_freq = float(frequency)
        now = time.time()
        
        if last_id >= WALKIE_TALKIE_COUNTER and WALKIE_TALKIE_COUNTER > 0:
                last_id = 0
        
        out = []
        with WALKIE_TALKIE_LOCK:
            for msg in WALKIE_TALKIE_MESSAGES:
                if msg["id"] > last_id and abs(msg["frequency"] - target_freq) < 0.05 and (now - msg["timestamp"]) < 30.0:
                    out.append({
                        "id": msg["id"],
                        "frequency": msg["frequency"],
                        "sender": msg["sender"],
                        "audio": msg["audio"],
                        "mime_type": msg.get("mime_type", "audio/webm"),
                        "timestamp": msg["timestamp"]
                    })
        return jsonify({"ok": True, "messages": out, "counter": WALKIE_TALKIE_COUNTER})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════
# TEXT CHAT RELAY SYSTEM (same offline LAN infrastructure as WT)
# ══════════════════════════════════════════════════════════════════
CHAT_MESSAGES = []
CHAT_COUNTER = 0
CHAT_LOCK = threading.Lock()

@app.route("/api/chat/send", methods=["POST"])
def api_chat_send():
    global CHAT_COUNTER
    try:
        data = request.get_json() or {}
        text = (data.get("text") or "").strip()
        sender = (data.get("sender") or "Anonymous").strip()
        channel = data.get("channel", "1")

        if not text:
            return jsonify({"ok": False, "error": "Empty message"}), 400
        if len(text) > 500:
            return jsonify({"ok": False, "error": "Message too long (max 500 chars)"}), 400

        with CHAT_LOCK:
            CHAT_COUNTER += 1
            msg = {
                "id": CHAT_COUNTER,
                "channel": str(channel),
                "sender": sender,
                "text": text,
                "timestamp": time.time()
            }
            CHAT_MESSAGES.append(msg)
            if len(CHAT_MESSAGES) > 200:
                CHAT_MESSAGES.pop(0)

        return jsonify({"ok": True, "id": CHAT_COUNTER})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/chat/poll", methods=["GET"])
def api_chat_poll():
    try:
        last_id = int(request.args.get("last_id", 0))
        channel = str(request.args.get("channel", "1"))
        now = time.time()

        out = []
        with CHAT_LOCK:
            for msg in CHAT_MESSAGES:
                if msg["id"] > last_id and msg["channel"] == channel and (now - msg["timestamp"]) < 3600:
                    out.append({
                        "id": msg["id"],
                        "channel": msg["channel"],
                        "sender": msg["sender"],
                        "text": msg["text"],
                        "timestamp": msg["timestamp"]
                    })
        return jsonify({"ok": True, "messages": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

def _start_mdns(port=8767):
    """Broadcast security-suite.local so any device on the same network
    can reach the dashboard at http://security-suite.local:8767
    without needing to know the PC's IP address."""
    try:
        from zeroconf import Zeroconf, ServiceInfo
        import socket, struct

        lan_ip = get_local_ip()
        addr_bytes = socket.inet_aton(lan_ip)

        info = ServiceInfo(
            "_http._tcp.local.",
            "SecuritySuite._http._tcp.local.",
            addresses=[addr_bytes],
            port=port,
            properties={"path": "/"},
            server="security-suite.local.",
        )

        zc = Zeroconf()
        zc.register_service(info)
        print(f"  [mDNS] Hostname registered: http://security-suite.local:{port}")
        print(f"  [mDNS] LAN IP: http://{lan_ip}:{port}")
        # Keep alive — zeroconf runs its own threads
        import atexit
        atexit.register(lambda: (zc.unregister_service(info), zc.close()))
    except Exception as e:
        print(f"  [mDNS] Could not start: {e} (non-fatal, use IP instead)")


@app.route("/api/system/log-error", methods=["POST"])
def api_system_log_error():
    try:
        err = request.get_json() or {}
        message = err.get("message", "Unknown JavaScript error")
        source = err.get("source", "unknown")
        lineno = err.get("lineno", "?")
        colno = err.get("colno", "?")
        stack = err.get("stack", "")
        
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "message": message,
            "source": source,
            "lineno": lineno,
            "colno": colno,
            "stack": stack
        }
        
        print(f"  [CLIENT JS ERROR] {message} at {source}:{lineno}:{colno}")
        
        log_file = ROOT_DIR / "client_errors.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
            
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/system/sandbox-test", methods=["POST"])
def api_system_sandbox_test():
    """Diagnostic Sandbox Verification Route"""
    try:
        body = request.get_json() or {}
        module = body.get("module")
        if not module:
            return jsonify({"ok": False, "error": "Module parameter required"}), 400
            
        if module == "tarpit":
            import socket
            import tarpit
            ports_to_try = [tarpit.TARPIT_PORT, 22, 2222]
            success = False
            message = ""
            for port in ports_to_try:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1.5)
                    s.connect(("127.0.0.1", port))
                    banner = s.recv(100).decode('utf-8', errors='ignore')
                    s.close()
                    if "SSH-2.0" in banner or "OpenSSH" in banner:
                        success = True
                        message = f"SUCCESS: Diagnostic connection established to Infinite Tarpit on Port {port} and received OpenSSH mimic response: '{banner.strip()}'"
                        break
                except Exception as e:
                    message = f"Failed connection to port {port}: {e}"
            if success:
                return jsonify({"ok": True, "message": message})
            else:
                return jsonify({"ok": False, "error": f"Tarpit port unresponsive or occupied. Last error: {message}"})
                
        elif module == "tripwire":
            import tripwire
            if os.path.exists(tripwire.TRIPWIRE_FILE):
                os.utime(tripwire.TRIPWIRE_FILE, None)
                return jsonify({"ok": True, "message": "SUCCESS: Honeyfile touched. Integrity watch loop triggered successfully. Check dashboard alarm screen."})
            else:
                tripwire.setup_honeyfile()
                os.utime(tripwire.TRIPWIRE_FILE, None)
                return jsonify({"ok": True, "message": "SUCCESS: Honeyfile recreated and touched. Integrity watch loop triggered successfully."})
                
        return jsonify({"ok": False, "error": f"Unknown module: {module}"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/system/restart", methods=["POST"])
def api_system_restart():
    def delay_exit():
        time.sleep(1.0)
        print("  [SYSTEM] Restarting server via Server-Loop...")
        os._exit(0)
    threading.Thread(target=delay_exit).start()
    return jsonify({"ok": True, "message": "Server restarting..."})


if __name__ == "__main__":
    startup()
    import threading

    # Start mDNS so mobile can always use http://security-suite.local:8767
    mdns_thread = threading.Thread(target=_start_mdns, daemon=True)
    mdns_thread.start()

    t = threading.Thread(target=arp_monitor_loop, daemon=True)
    t.start()
    
    def run_adhoc_server():
        try:
            print("  [SSL] Starting ad-hoc fallback server on port 8768...")
            app.run(host="0.0.0.0", port=8768, debug=False, use_reloader=False, ssl_context='adhoc')
        except Exception as e:
            print(f"  [SSL] Error starting adhoc server: {e}")
            
    threading.Thread(target=run_adhoc_server, daemon=True).start()

    # Robust SSL certificate path resolution
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cert_path = os.path.join(base_dir, "z14-55n.tailfffdbc.ts.net.crt")
    key_path = os.path.join(base_dir, "z14-55n.tailfffdbc.ts.net.key")
    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"  [SSL] Loading Tailscale HTTPS Certificates: {cert_path}")
        app.run(host="0.0.0.0", port=8767, debug=False, use_reloader=False, ssl_context=(cert_path, key_path))
    else:
        print("  [SSL] Certificates not found. Falling back to ad-hoc self-signed SSL context.")
        app.run(host="0.0.0.0", port=8767, debug=False, use_reloader=False, ssl_context='adhoc')
