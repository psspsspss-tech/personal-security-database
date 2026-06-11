# AI System Architecture Guide
*This document is intended to be read by Large Language Models to quickly understand the codebase structure and context.*

## Project Context
The **Security Command Center** is a local network monitoring and personal cybersecurity tool. It combines a Python Flask backend with a vanilla HTML/JS/CSS frontend. It is designed to run on a Windows PC and serve a mobile-friendly dashboard to smartphones on the local network (LAN).

## Core Architecture
- **Backend (`backend/server.py`)**: A Flask application that serves the frontend, exposes `/api/*` endpoints, and manages the background scanning threads.
- **Frontend (`dashboard/app.js`, `index.html`, `style.css`)**: Vanilla JavaScript interacting with the Flask backend. It aggressively avoids caching via server headers to ensure instant updates. 
- **Auto-Update Mechanism**: The frontend polls `/api/version` every 30 seconds. The version hash changes whenever the server restarts. If the hash changes, the UI automatically prompts the user to reload, or in some cases automatically reloads, ensuring cross-device synchronization without websockets.

## Key Modules
### 1. Network Intelligence (`backend/network_scanner.py`)
- Continuously scans the LAN (using ARP on Windows) every 60 seconds.
- **OS Fingerprinting**: Probes specific ports (e.g., 62078 for Apple, 5555 for Android, 445 for Windows) to guess device OS.
- **MAC Randomization Detection**: Checks the second hex character of the MAC address to see if the device is using a randomized MAC (iOS/Android privacy feature).
- **Caching**: The background loop saves the results to memory (`_last_scan_result`). The `/api/devices` endpoint reads from this memory. **Important:** Any manual actions that alter the network state (like approving a device) MUST call `force_cache_update()` to instantly bypass the 60-second loop and update the UI.

### 2. Active Controls (Backend -> Frontend)
The system allows the user to take aggressive actions against devices on the network.
- **Deep Scan (`/api/device/deep-scan`)**: Probes the top 100 common ports on a target IP.
- **Block (`/api/device/block`)**: Executes `netsh advfirewall` on the host PC to instantly drop inbound traffic from the target IP.
- **Wake-on-LAN (`/api/device/wol`)**: Sends a magic packet to a target MAC address.

### 3. Scripts
- `check_security.ps1`: Audits Windows security policies and generates a score.
- `harden_windows.ps1`: Applies strict Windows security settings.

## Design Philosophy
- **Zero Cloud Dependencies**: All data is local. The whitelist and alerts are stored in simple JSON files in the `backend/` directory.
- **Aesthetic First**: The dashboard (`style.css`) uses premium gradients, glassmorphism, and custom animations to look like a high-end native iOS application.
- **No Build Tools**: No React, no Webpack, no Tailwind. Vanilla JS/CSS allows for absolute minimal friction and instant live-reloading.

## Future AI Instructions
If asked to add new features:
1. Always implement a corresponding backend API route in `server.py`.
2. Keep UI additions in `app.js` using template strings (e.g. `innerHTML = ...`).
3. If you modify a database/json file, update the `_last_scan_result` memory cache so the UI sees the change immediately.
