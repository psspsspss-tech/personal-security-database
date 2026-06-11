import multiprocessing
import sys
import os
import time
import webbrowser
import socket
import subprocess

# Prevent subprocess from spawning console windows on Windows PyInstaller apps
if sys.platform == "win32":
    original_popen = subprocess.Popen
    def patched_popen(*args, **kwargs):
        kwargs['creationflags'] = kwargs.get('creationflags', 0) | 0x08000000 # CREATE_NO_WINDOW
        return original_popen(*args, **kwargs)
    subprocess.Popen = patched_popen

# Ensure paths are correct for PyInstaller
if getattr(sys, 'frozen', False):
    ROOT_DIR = sys._MEIPASS
    os.chdir(ROOT_DIR)
    # Add ROOT_DIR to Python path so 'backend' and 'agent' modules are found
    sys.path.insert(0, str(ROOT_DIR))

def run_server():
    from backend import server
    print("\n[MASTER] Starting backend server...")
    server.startup()
    # Suppress werkzeug logs if you want it cleaner
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    server.app.run(host="0.0.0.0", port=8765, debug=False, use_reloader=False)

def run_agent():
    # Give the server a few seconds to boot up
    time.sleep(3)
    
    print("\n[MASTER] Starting local PC telemetry agent...")
    import agent
    
    # Override server URL to point to localhost so it always connects locally
    agent.SERVER_URL = "http://127.0.0.1:8765"
    
    # Run the background reporting loop
    agent.main()

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    # Required for Windows executables using multiprocessing
    multiprocessing.freeze_support()
    
    print("=" * 60)
    print("      INITIALIZING SECURITY COMMAND CENTER")
    print("=" * 60)
    
    # Start the Server process
    server_process = multiprocessing.Process(target=run_server)
    server_process.daemon = True
    server_process.start()
    
    # Start the Local Agent process
    agent_process = multiprocessing.Process(target=run_agent)
    agent_process.daemon = True
    agent_process.start()
    
    # Wait for server to boot, then open browser
    time.sleep(2)
    lan_ip = get_lan_ip()
    print(f"\n[MASTER] Dashboard is running!")
    print(f"[MASTER] To control from your iPhone, open: http://{lan_ip}:8765\n")
    
    # Open locally
    webbrowser.open('http://127.0.0.1:8765')
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MASTER] Shutting down...")
        server_process.terminate()
        agent_process.terminate()
        sys.exit(0)
