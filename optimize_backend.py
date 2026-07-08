import os
import re

server_path = r"C:\Users\acer\Desktop\Security Suite\backend\server.py"
sysmon_path = r"C:\Users\acer\Desktop\Security Suite\backend\system_monitor.py"

# 1. Update system_monitor.py
with open(sysmon_path, 'r', encoding='utf-8') as f:
    sysmon = f.read()

new_score_logic = """def calculate_security_score(firewall, defender, open_ports, pending_updates):
    \"\"\"Calculate an overall security score 0-100 with balanced caps.\"\"\"
    score = 100
    deductions = []

    # Firewall checks
    if firewall.get("status") == "ok":
        off_count = sum(1 for state in firewall.get("profiles", {}).values() if state != "ON")
        if off_count > 0:
            deduct = min(off_count * 10, 20)
            score -= deduct
            deductions.append(f"Firewall partially OFF (-{deduct})")
    else:
        score -= 20
        deductions.append("Could not verify firewall status (-20)")

    # Defender checks
    if defender.get("status") == "ok":
        if not defender.get("antivirus_enabled"):
            score -= 25
            deductions.append("Antivirus is disabled (-25)")
        if not defender.get("realtime_protection"):
            score -= 15
            deductions.append("Real-time protection is OFF (-15)")
        age = defender.get("signature_age_days", 0)
        if isinstance(age, int) and age > 7:
            score -= 5
            deductions.append(f"Antivirus signatures {age} days old (-5)")
    else:
        score -= 10
        deductions.append("Could not verify antivirus status (-10)")

    # Open ports
    risky_ports = [port for port in open_ports if port["port"] in [21, 23, 135, 139, 445, 3389, 5900]]
    if risky_ports:
        deduct = min(len(risky_ports) * 2, 15)
        score -= deduct
        deductions.append(f"{len(risky_ports)} risky port(s) open (-{deduct})")

    # Pending updates
    if pending_updates.get("status") == "ok":
        count = pending_updates.get("pending_count", 0)
        if count > 0:
            deduct = min(count * 2, 10)
            score -= deduct
            deductions.append(f"{count} pending updates (-{deduct})")

    return {
        "score": max(0, score),
        "deductions": deductions
    }"""

sysmon = re.sub(r'def calculate_security_score\(.*?return\s+\{\s*"score": max\(0, score\),\s*"deductions": deductions\s+\}', new_score_logic, sysmon, flags=re.DOTALL)
# Fallback if regex fails to match original function exactly
if "Calculate an overall security score 0-100 with balanced caps" not in sysmon:
    sysmon = re.sub(r'def calculate_security_score\(.*?return \{\n        "score": max\(0, score\),\n        "deductions": deductions\n    \}', new_score_logic, sysmon, flags=re.DOTALL)

with open(sysmon_path, 'w', encoding='utf-8') as f:
    f.write(sysmon)


# 2. Update server.py
with open(server_path, 'r', encoding='utf-8') as f:
    server = f.read()

# Replace subprocess.run with eventlet.tpool.execute
if 'from eventlet import tpool' not in server:
    server = server.replace('import eventlet', 'import eventlet\nfrom eventlet import tpool')

# Wrap subprocess calls
server = server.replace('r = subprocess.run(cmd, capture_output=True, text=True)', 'r = tpool.execute(subprocess.run, cmd, capture_output=True, text=True)')

# Remove duplicate routes
# Since there are two /api/device/block, we will remove the first one if it's identical or just comment it out.
# Let's remove the legacy deep-scan
server = re.sub(r'@app\.route\("/api/device/deep-scan", methods=\["POST"\]\)\s*def api_device_deep_scan\(\):.*?except Exception as e: return jsonify\(\{"ok": False, "error": str\(e\)\}\), 500\n', '', server, flags=re.DOTALL)

# Fix wake on lan route to match frontend
server = server.replace('@app.route("/api/device/wake"', '@app.route("/api/device/wol"')

# Delete the wildcard toolkit route if it exists: @app.route("/api/toolkit/<script_name>")
server = re.sub(r'@app\.route\("/api/toolkit/<script_name>"\)\ndef run_toolkit_script\(script_name\):.*?except Exception as e:\n\s*return jsonify\(\{"ok": False, "error": str\(e\)\}\), 500\n', '', server, flags=re.DOTALL)

with open(server_path, 'w', encoding='utf-8') as f:
    f.write(server)

print("Optimizations applied successfully.")
