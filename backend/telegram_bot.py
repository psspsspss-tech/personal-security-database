"""
telegram_bot.py — Telegram Alert Notification System
Sends real-time security alerts to your Telegram phone.
Setup: Create a bot via @BotFather, paste token in config.json.
"""

import json
import requests
import datetime
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


def is_enabled():
    config = load_config()
    tg = config.get("telegram", {})
    return tg.get("enabled", False) and tg.get("bot_token") and tg.get("chat_id")


def send_message(text, parse_mode="HTML"):
    """Send a message to Telegram. Returns (success, error_msg)."""
    config = load_config()
    tg = config.get("telegram", {})

    token = tg.get("bot_token", "")
    chat_id = tg.get("chat_id", "")

    if not token or not chat_id:
        return False, "Telegram not configured"

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }, timeout=8)
        if resp.status_code == 200:
            return True, None
        else:
            return False, f"API error {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, str(e)


def send_alert_unknown_device(device):
    """Send alert for unknown network device."""
    if not is_enabled():
        return False, "Not enabled"
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    msg = (
        f"🚨 <b>SECURITY ALERT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Unknown device on your network!\n\n"
        f"📍 IP: <code>{device.get('ip', 'Unknown')}</code>\n"
        f"🔑 MAC: <code>{device.get('mac', 'Unknown')}</code>\n"
        f"🏭 Vendor: {device.get('vendor', 'Unknown')}\n"
        f"🕐 Time: {ts}\n\n"
        f"<b>Action:</b> Open Security Dashboard → Network Devices to approve or block."
    )
    return send_message(msg)


def send_alert_failed_logins(count, threshold):
    """Send alert for brute force login attempts."""
    if not is_enabled():
        return False, "Not enabled"
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    msg = (
        f"🔐 <b>BRUTE FORCE ALERT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ {count} failed login attempts detected!\n\n"
        f"🕐 Detected at: {ts}\n"
        f"📊 Threshold: {threshold} attempts\n\n"
        f"<b>Action:</b> Check Event Logs tab in Security Dashboard."
    )
    return send_message(msg)


def send_alert_firewall_down():
    """Send alert when firewall is disabled."""
    if not is_enabled():
        return False, "Not enabled"
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    msg = (
        f"🔥 <b>FIREWALL ALERT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🚨 Windows Firewall is DISABLED!\n\n"
        f"🕐 Detected at: {ts}\n\n"
        f"<b>Action:</b> Re-enable immediately via Windows Security Center."
    )
    return send_message(msg)


def send_test_message():
    """Send a test message to verify configuration."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = (
        f"✅ <b>Security Suite Connected!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Your Personal Security Command Center is now sending alerts to this chat.\n\n"
        f"🕐 Setup time: {ts}\n\n"
        f"You will receive alerts for:\n"
        f"• Unknown devices on your WiFi\n"
        f"• Brute force login attempts\n"
        f"• Firewall disabled\n"
        f"• High-risk processes"
    )
    return send_message(msg)


def get_chat_id(bot_token):
    """Auto-detect chat_id from recent messages sent to the bot."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("result", [])
            if results:
                last = results[-1]
                chat = last.get("message", {}).get("chat", {})
                return str(chat.get("id", "")), None
            return None, "No messages found. Send any message to your bot first, then try again."
        return None, f"API error: {resp.status_code}"
    except Exception as e:
        return None, str(e)


if __name__ == "__main__":
    ok, err = send_test_message()
    print("Sent:", ok, "| Error:", err)
