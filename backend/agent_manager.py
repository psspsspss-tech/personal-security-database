"""
agent_manager.py — Remote Agent Registry
Manages check-ins from remote agents (other Windows PCs, Android Termux).
Stores latest heartbeat data per device.
"""

import json
import threading
import datetime
from pathlib import Path

_agents = {}           # keyed by device_id
_agents_lock = threading.Lock()
AGENTS_FILE = Path(__file__).parent / "agents.json"
OFFLINE_THRESHOLD_SECONDS = 120   # agent considered offline if no heartbeat for 2 min


def _load_from_disk():
    """Load saved agents on startup."""
    global _agents
    try:
        if AGENTS_FILE.exists():
            with open(AGENTS_FILE) as f:
                _agents = json.load(f)
    except Exception:
        _agents = {}


def _save_to_disk():
    """Persist agents to disk."""
    try:
        with open(AGENTS_FILE, "w") as f:
            json.dump(_agents, f, indent=2)
    except Exception:
        pass


def register_agent(data: dict) -> dict:
    """
    Register or update an agent heartbeat.
    Expected fields: device_id, hostname, os, ip, platform
    Optional: cpu, memory, battery, wifi_ssid, open_ports, alerts
    Returns the stored agent record.
    """
    device_id = data.get("device_id") or data.get("hostname", "unknown")
    now = datetime.datetime.now().isoformat()

    with _agents_lock:
        existing = _agents.get(device_id, {})
        agent = {
            **existing,
            **data,
            "device_id": device_id,
            "last_seen": now,
            "status": "online",
            "registered_at": existing.get("registered_at", now),
        }
        _agents[device_id] = agent
        _save_to_disk()
    return agent


def get_all_agents() -> list:
    """Return all agents with current online/offline status."""
    now = datetime.datetime.now()
    result = []
    with _agents_lock:
        for device_id, agent in _agents.items():
            a = dict(agent)
            try:
                last = datetime.datetime.fromisoformat(a.get("last_seen", ""))
                elapsed = (now - last).total_seconds()
                a["status"] = "online" if elapsed < OFFLINE_THRESHOLD_SECONDS else "offline"
                a["last_seen_seconds_ago"] = int(elapsed)
            except Exception:
                a["status"] = "offline"
                a["last_seen_seconds_ago"] = 9999
            result.append(a)
    # Sort: online first, then by hostname
    result.sort(key=lambda x: (0 if x["status"] == "online" else 1, x.get("hostname", "")))
    return result


def get_agent(device_id: str) -> dict:
    with _agents_lock:
        return _agents.get(device_id)


def remove_agent(device_id: str) -> bool:
    with _agents_lock:
        if device_id in _agents:
            del _agents[device_id]
            _save_to_disk()
            return True
    return False


def get_summary() -> dict:
    agents = get_all_agents()
    online = [a for a in agents if a["status"] == "online"]
    return {
        "total": len(agents),
        "online": len(online),
        "offline": len(agents) - len(online),
        "agents": agents
    }


# Load on import
_load_from_disk()
