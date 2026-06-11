"""
event_log_analyzer.py — Windows Security Event Log Parser
Reads Windows Security logs for failed logins, lockouts, new accounts.
Event IDs:
  4625 = Failed login attempt
  4740 = Account locked out
  4720 = New user account created
  4726 = User account deleted
  4648 = Logon with explicit credentials (RunAs)
  4624 = Successful logon
"""

import subprocess
import json
import datetime
import re


RISKY_EVENT_IDS = {
    4625: {"name": "Failed Login",       "severity": "medium", "icon": "🔐"},
    4740: {"name": "Account Locked Out", "severity": "high",   "icon": "🔒"},
    4720: {"name": "Account Created",    "severity": "high",   "icon": "👤"},
    4726: {"name": "Account Deleted",    "severity": "high",   "icon": "🗑️"},
    4648: {"name": "RunAs Login",        "severity": "medium", "icon": "⚡"},
    4624: {"name": "Successful Login",   "severity": "low",    "icon": "✅"},
}


def get_security_events(max_events=200, hours_back=24):
    """
    Read Windows Security event log via PowerShell.
    Returns list of event dicts.
    """
    event_ids = ",".join(str(i) for i in RISKY_EVENT_IDS.keys())

    # PowerShell script to extract events as JSON
    ps_script = f"""
$cutoff = (Get-Date).AddHours(-{hours_back})
$ids = @({event_ids})
$events = Get-WinEvent -FilterHashtable @{{
    LogName = 'Security'
    Id = $ids
    StartTime = $cutoff
}} -MaxEvents {max_events} -ErrorAction SilentlyContinue

$results = foreach ($e in $events) {{
    [PSCustomObject]@{{
        Id        = $e.Id
        Time      = $e.TimeCreated.ToString('yyyy-MM-ddTHH:mm:ss')
        Message   = ($e.Message -split '\\n')[0..2] -join ' '
        Level     = $e.LevelDisplayName
    }}
}}
$results | ConvertTo-Json -Depth 3
"""

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []

        raw = result.stdout.strip()
        # Handle single object vs array
        if raw.startswith('{'):
            raw = f"[{raw}]"

        events_raw = json.loads(raw)
        if not isinstance(events_raw, list):
            events_raw = [events_raw]

        events = []
        for e in events_raw:
            eid = int(e.get("Id", 0))
            meta = RISKY_EVENT_IDS.get(eid, {"name": "Unknown", "severity": "low", "icon": "ℹ️"})
            msg = e.get("Message", "")

            # Extract username from message if present
            username = ""
            un_match = re.search(r"Account Name:\s+(\S+)", msg)
            if un_match:
                username = un_match.group(1)

            events.append({
                "id": eid,
                "name": meta["name"],
                "severity": meta["severity"],
                "icon": meta["icon"],
                "time": e.get("Time", ""),
                "username": username,
                "message": msg[:200]
            })

        return events

    except Exception as e:
        return []


def get_failed_login_summary(hours_back=24):
    """Count failed logins, find top offending usernames."""
    events = get_security_events(hours_back=hours_back)
    failed = [e for e in events if e["id"] == 4625]
    lockouts = [e for e in events if e["id"] == 4740]
    successes = [e for e in events if e["id"] == 4624]
    new_accounts = [e for e in events if e["id"] == 4720]

    # Count by username
    user_counts = {}
    for e in failed:
        u = e["username"] or "unknown"
        user_counts[u] = user_counts.get(u, 0) + 1

    top_targets = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    brute_force_risk = "HIGH" if len(failed) > 20 else ("MEDIUM" if len(failed) > 5 else "LOW")

    return {
        "period_hours": hours_back,
        "failed_logins": len(failed),
        "account_lockouts": len(lockouts),
        "successful_logins": len(successes),
        "new_accounts": len(new_accounts),
        "brute_force_risk": brute_force_risk,
        "top_targeted_users": [{"username": u, "attempts": c} for u, c in top_targets],
        "recent_events": events[:50]
    }


if __name__ == "__main__":
    summary = get_failed_login_summary()
    print(json.dumps(summary, indent=2))
