import sys
import os
import time
import webbrowser
import socket
import subprocess


# Ensure paths are correct for PyInstaller
if getattr(sys, 'frozen', False):
    ROOT_DIR = sys._MEIPASS
    os.chdir(ROOT_DIR)
    # Add ROOT_DIR to Python path so 'backend' and 'agent' modules are found
    sys.path.insert(0, str(ROOT_DIR))

def run_server():
    try:
        from backend import server
        print("[MASTER] Step 2/4: Running server.startup()...")
        server.startup()
        print("[MASTER] Step 3/4: Configuring logging...")
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        print("[MASTER] Step 4/4: Starting Flask app.run on port 8765...")
        server.app.run(host="0.0.0.0", port=8765, debug=False, use_reloader=False)
    except Exception as e:
        import traceback
        with open("server_crash.log", "w") as f:
            f.write(f"CRASH ERROR: {e}\n")
            traceback.print_exc(file=f)
        print(f"[MASTER] Server process crashed! Details written to server_crash.log")
        raise

def run_agent():
    # Wait for the Flask server to actually start listening on port 8765
    import socket
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        result = s.connect_ex(('127.0.0.1', 8765))
        s.close()
        if result == 0:
            break
        time.sleep(1)
        
    print("\n[MASTER] Server online! Starting local PC telemetry agent...")
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
    print("=" * 60)
    print("      INITIALIZING SECURITY COMMAND CENTER")
    print("=" * 60)
    
    # 1. Single-threaded import phase first to avoid Windows import lock / COM deadlocks
    print("[MASTER] Step 1/4: Importing backend server modules...")
    import importlib.util
    print("[MASTER] sys.path is:", sys.path)
    spec = importlib.util.find_spec("backend.server")
    print("[MASTER] Resolved backend.server spec to:", spec)
    from backend import server
    
    # 2. Spawning helper threads now that imports are safely completed
    import threading
    
    # Start the Local Agent process in a background thread (waits for port 8765)
    agent_thread = threading.Thread(target=run_agent, daemon=True)
    agent_thread.start()
    
    # Wait for server to boot, then open browser
    def open_browser_delayed():
        import socket
        # Wait for port 8765 to start listening
        while True:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            result = s.connect_ex(('127.0.0.1', 8765))
            s.close()
            if result == 0:
                break
            time.sleep(0.5)
            
        lan_ip = get_lan_ip()
        print(f"\n[MASTER] Dashboard is running!")
        print(f"[MASTER] To control from your iPhone, open: http://{lan_ip}:8765\n")
        webbrowser.open('http://127.0.0.1:8765')
        
    browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
    browser_thread.start()
    
    # 3. Run the server in the main thread (blocking)
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n[MASTER] Shutting down...")
        sys.exit(0)
