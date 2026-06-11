# 🛡️ Personal Security Command Center

A real, multi-layered personal cybersecurity system for Windows. Protects your PC, monitors your home network, detects unauthorized devices, and hardens your system against common attacks.

---

## What's Included

| Component | Description |
|-----------|-------------|
| **Dashboard** | Real-time web UI — security score, network map, alerts |
| **Network Scanner** | Detects all WiFi devices, alerts on unknowns |
| **System Monitor** | Checks firewall, Defender, open ports, processes |
| **harden_windows.ps1** | One-click Windows security hardening |
| **check_security.ps1** | Full security audit with scored report |

---

## Quick Start

### Step 1 — Install Python
Download Python 3.9+ from [python.org](https://www.python.org/downloads/)  
✅ Check **"Add Python to PATH"** during install!

### Step 2 — Launch the Dashboard
Double-click **`start.bat`** — it will:
- Install required Python packages
- Start the security server
- Open the dashboard at `http://localhost:8765`

### Step 3 — Harden Your PC (Do This Once!)
Right-click PowerShell → **Run as Administrator**, then run:
```powershell
PowerShell -ExecutionPolicy Bypass -File "scripts\harden_windows.ps1"
```
Then restart your computer.

### Step 4 — Run a Security Audit
```powershell
PowerShell -ExecutionPolicy Bypass -File "scripts\check_security.ps1"
```

---

## Dashboard Features

### Overview Tab
- **Security Score** — live 0-100 score based on your actual system state
- **System Status** — CPU/RAM, hostname, uptime, pending updates
- **Recent Alerts** — unknown devices, anomalies

### Network Devices Tab
- Lists ALL devices currently on your WiFi
- 🟢 **Green** = Approved (whitelisted)
- 🔴 **Red** = Unknown (not approved)
- 🔵 **Blue** = This device
- Click **"Approve"** to whitelist trusted devices
- Click **"Rescan"** to do a fresh network sweep

### Open Ports Tab
- Lists all ports currently listening on your PC
- Flags risky ports (21, 23, 135, 139, 445, 3389, 5900)

### Alerts Tab
- Full history of security alerts
- Acknowledge alerts once reviewed

### Breach Check Tab
- Enter your email to check if it appeared in known data breaches
- Powered by Have I Been Pwned API

### Security Guide Tab
- Step-by-step hardening guide for PC, router, and Android

---

## Project Structure

```
security-suite/
├── start.bat                   ← Double-click to launch
├── dashboard/
│   ├── index.html              ← Dashboard UI
│   ├── style.css               ← Premium dark theme
│   └── app.js                  ← Real-time data + interactions
├── backend/
│   ├── server.py               ← Flask API server (port 8765)
│   ├── network_scanner.py      ← WiFi device scanner
│   ├── system_monitor.py       ← PC security checker
│   ├── whitelist.json          ← Your approved devices
│   ├── alerts.json             ← Alert history (auto-created)
│   └── requirements.txt        ← Python dependencies
└── scripts/
    ├── harden_windows.ps1      ← Security hardening (run as Admin)
    └── check_security.ps1      ← Security audit report
```

---

## Manual Server Start (Alternative to start.bat)

```bash
cd backend
pip install -r requirements.txt
python server.py
```
Then open `http://localhost:8765` in your browser.

---

## What the Hardening Script Does

| Action | Why |
|--------|-----|
| Enable firewall on all profiles | Blocks unwanted inbound connections |
| Block ports 21, 23, 135, 139, 445, 3389 | Close common attack vectors |
| Disable SMBv1 | Prevents EternalBlue/WannaCry |
| Disable WDigest | Prevents credential theft from memory |
| Disable LLMNR | Prevents MITM attacks on LAN |
| Disable Remote Registry | Prevents remote registry access |
| Enable Defender + real-time protection | Active malware protection |
| Enable network protection | Blocks malicious URLs |
| Disable AutoRun | Prevents USB malware |
| Enable audit logging | Logs unauthorized access attempts |
| Set account lockout (5 attempts) | Prevents brute-force attacks |
| Minimum password 12 chars | Stronger passwords required |

---

## Security Limitations (Be Honest With Yourself)

This system **dramatically** raises your security posture, but no system is 100% secure:

- Network scanner uses ARP — won't detect extremely sophisticated attackers
- Breach check requires internet access to HIBP API
- Physical access to your device bypasses most software security
- Always keep software updated — patches fix newly discovered vulnerabilities
- Use a VPN on public networks (not protected by this tool)

---

## Privacy

All data stays on your local machine. Nothing is sent externally except:
- The breach check (email hash sent to HIBP)
- Defender signature updates (to Microsoft)

---

*Built with Python, Flask, and vanilla HTML/CSS/JS. No cloud dependencies. 100% local.*
