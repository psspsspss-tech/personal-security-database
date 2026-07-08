# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
# Aegis Shield (Antivirus / System Protection)
# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
@app.route("/api/aegis/scan", methods=["GET"])
def api_aegis_scan():
    try:
        processes = []
        temp_dir = os.environ.get('TEMP', 'C:\\Windows\\Temp').lower()
        appdata_local_temp = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp').lower()

        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                info = proc.info
                path = (info['exe'] or "").lower()
                suspicious = bool(path and (temp_dir in path or appdata_local_temp in path))
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "path": info['exe'] or "Access Denied",
                    "suspicious": suspicious
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        startup_items = []
        if winreg:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(key, i)
                        startup_items.append({"name": name, "path": val})
                        i += 1
                    except OSError:
                        break
            except Exception:
                pass
                
        hosts_ok = True
        try:
            hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            if os.path.exists(hosts_path):
                with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                    if len(f.readlines()) > 100:
                        hosts_ok = False
        except Exception:
            pass

        return jsonify({"ok": True, "data": {
            "processes": processes,
            "startup": startup_items,
            "hosts_ok": hosts_ok
        }})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/aegis/kill", methods=["POST"])
def api_aegis_kill():
    try:
        pid = request.get_json().get("pid")
        if not pid: return jsonify({"ok": False, "error": "PID required"}), 400
        p = psutil.Process(int(pid))
        p.terminate()
        p.wait(timeout=3)
        return jsonify({"ok": True, "message": f"Process {pid} terminated."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/aegis/disable_startup", methods=["POST"])
def api_aegis_disable_startup():
    try:
        name = request.get_json().get("name")
        if not name or not winreg: return jsonify({"ok": False, "error": "Name required or not on Windows"}), 400
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
        return jsonify({"ok": True, "message": f"Startup item '{name}' disabled."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/aegis/clean_temp", methods=["POST"])
def api_aegis_clean_temp():
    try:
        freed = 0
        folders = [os.environ.get('TEMP', r'C:\Users\Default\AppData\Local\Temp'), r"C:\Windows\Temp"]
        for folder in folders:
            if os.path.exists(folder):
                for item in os.listdir(folder):
                    item_path = os.path.join(folder, item)
                    try:
                        if os.path.isfile(item_path):
                            size = os.path.getsize(item_path)
                            os.remove(item_path)
                            freed += size
                        elif os.path.isdir(item_path):
                            size = sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, _, filenames in os.walk(item_path) for filename in filenames)
                            shutil.rmtree(item_path)
                            freed += size
                    except Exception:
                        pass
        mb = freed / (1024.0 * 1024.0)
        return jsonify({"ok": True, "message": f"Cleared {mb:.1f} MB of temporary files."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/aegis/reset_hosts", methods=["POST"])
def api_aegis_reset_hosts():
    try:
        path = r"C:\Windows\System32\drivers\etc\hosts"
        content = "# Copyright (c) 1993-2009 Microsoft Corp.\n#\n# This is a sample HOSTS file used by Microsoft TCP/IP for Windows.\n#\n# This file contains the mappings of IP addresses to host names.\n127.0.0.1       localhost\n::1             localhost\n"
        with open(path, "w", encoding="ascii") as f:
            f.write(content)
        return jsonify({"ok": True, "message": "Hosts file reset to defaults."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/aegis/defender_scan", methods=["POST"])
def api_aegis_defender_scan():
    try:
        path = r"C:\Program Files\Windows Defender\MpCmdRun.exe"
        if os.path.exists(path):
            subprocess.Popen([path, "-Scan", "-ScanType", "1"], creationflags=subprocess.CREATE_NO_WINDOW)
            return jsonify({"ok": True, "message": "Defender Scan Triggered Successfully"})
        return jsonify({"ok": False, "error": "Windows Defender command-line tool not found."}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
# Startup
# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
def startup():
    """Initialize background tasks on server start."""
    print("=" * 55)
    print("  [*] Personal Security Suite -- Starting Up")
    print("=" * 55)
    print(f"  Dashboard: http://localhost:8765")
    print(f"  API Base:  http://localhost:8765/api/")
    print("=" * 55)
    print("\n  Starting background network scanner...")
    # Do an initial scan in background
    threading.Thread(target=lambda: setattr(
        netscanner, '_last_scan_result', netscanner.scan_and_check()
    ), daemon=True).start()
    # Start continuous scanner (every 90 seconds)
    netscanner.start_background_scanner(interval=90)
    print("  Network scanner active")
    print("  All systems ready. Open your browser!\n")


