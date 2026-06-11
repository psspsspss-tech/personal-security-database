# How to Connect Your Device to the Security Dashboard

> Your central Security Dashboard is running on your PC at **http://192.168.1.4:8765**
> All devices must be on the **same WiFi network**.

---

## 📱 iPhone / iPad (iOS) — 30 Seconds

No apps to install. Works 100% in Safari.

1. Connect your iPhone to **your home WiFi**
2. Open **Safari** (not Chrome) and go to:
   ```
   http://192.168.1.4:8765
   ```
3. Tap the **Share** button (the box with an arrow at the bottom)
4. Tap **"Add to Home Screen"**
5. Tap **"Add"**

Your dashboard is now installed as an app icon on your iPhone home screen. Open it anytime to check your network security — **no internet needed, works purely on your WiFi**.

> **Tip:** You'll also receive Telegram alerts on your iPhone — set these up in the **Setup Alerts** tab.

---

## 🤖 Android — Browser (Quickest)

1. Connect to **your home WiFi**
2. Open **Chrome** and go to:
   ```
   http://192.168.1.4:8765
   ```
3. Tap the ⋮ menu → **"Add to Home screen"**

Done! You now have the dashboard as an app on Android.

---

## 🤖 Android — Termux Agent (Deep Monitoring)

Run the agent to send your Android's CPU, RAM, battery, and WiFi info to the dashboard.

1. Install **Termux** from [f-droid.org](https://f-droid.org) (NOT from Play Store — that version is outdated)
2. Open Termux and run these commands one by one:

```bash
pkg update -y
pkg install python -y
pip install psutil requests
curl -O http://192.168.1.4:8765/agent.py
python agent.py
```

3. Leave Termux running in the background. Your Android will now appear in the **Connect Devices** tab on the dashboard.

> To keep the agent running when Termux is in background, run: `termux-wake-lock` before starting the agent.

---

## 🖥️ Other Windows PC

1. Install Python from [python.org](https://python.org) — check **"Add to PATH"**
2. Open Command Prompt and run:

```cmd
pip install psutil requests
```

3. Open your browser and download the agent:
   ```
   http://192.168.1.4:8765/agent.py
   ```
   Save it anywhere (e.g., `C:\agent.py`)

4. In Command Prompt, navigate to where you saved it and run:
```cmd
python agent.py
```

5. The PC will now appear in the **Connect Devices** tab on the dashboard.

> **To run at startup on the other PC:** Press `Win+R`, type `shell:startup`, and place a shortcut to `agent.py` there.

---

## 🔐 Is This Secure?

- The dashboard is only accessible on your **local home network** (not the internet)
- No data leaves your home network
- The agent only reports hardware metrics (CPU, RAM, battery, WiFi name) — no personal files or browsing history
- You can remove any device from the **Connect Devices** tab at any time

---

## ❓ Can't Connect?

- Make sure the device is on the **same WiFi network** as your PC
- Make sure `start.bat` is running on your PC
- Try pinging your PC: open Termux/CMD and type `ping 192.168.1.4`
- If your PC's IP changed, re-check it with `ipconfig` on your PC (look for "IPv4 Address" under WiFi)
