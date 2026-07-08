import pystray
from PIL import Image, ImageDraw
import webbrowser
import subprocess
import os
import sys

def create_image():
    # Generate a simple shield icon
    image = Image.new('RGB', (64, 64), color='black')
    draw = ImageDraw.Draw(image)
    draw.polygon([(32, 5), (10, 15), (10, 40), (32, 60), (54, 40), (54, 15)], fill='green', outline='white')
    draw.polygon([(32, 10), (15, 18), (15, 38), (32, 55), (49, 38), (49, 18)], fill='#00ff88')
    return image

def open_dashboard(icon, item):
    webbrowser.open("http://localhost:8765")

def start_server(icon, item):
    # Try using scheduled task first
    res = subprocess.run(["schtasks", "/run", "/tn", "SecuritySuiteServer"], capture_output=True)
    if res.returncode != 0:
        # Fallback if task doesn't exist
        server_path = os.path.join(os.path.dirname(__file__), 'backend', 'server.py')
        subprocess.Popen([sys.executable, server_path], creationflags=subprocess.CREATE_NO_WINDOW)

def stop_server(icon, item):
    subprocess.run(["schtasks", "/end", "/tn", "SecuritySuiteServer"], capture_output=True)
    # Also kill python instances running server.py just in case
    subprocess.run(["powershell", "-Command", "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match 'server.py' } | ForEach-Object { $_.Terminate() }"], capture_output=True)

def exit_action(icon, item):
    icon.stop()

menu = pystray.Menu(
    pystray.MenuItem("Security Command Center", None, enabled=False),
    pystray.Menu.SEPARATOR,
    pystray.MenuItem("Open Dashboard", open_dashboard, default=True),
    pystray.MenuItem("Start Server (Admin)", start_server),
    pystray.MenuItem("Stop Server", stop_server),
    pystray.Menu.SEPARATOR,
    pystray.MenuItem("Exit Tray", exit_action)
)

icon = pystray.Icon("SecuritySuite", create_image(), "Security Suite", menu)

if __name__ == "__main__":
    icon.run()
