import ctypes
import sys
import subprocess

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if is_admin():
    # We are admin, add the firewall rule
    print("Running as admin. Adding firewall rule for Port 8767...")
    cmd = 'New-NetFirewallRule -DisplayName "Security Suite Server" -Direction Inbound -LocalPort 8767 -Protocol TCP -Action Allow'
    result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
    if result.returncode == 0:
        print("Firewall rule added successfully! You can now access the suite on your phone.")
    else:
        print("Error adding firewall rule:")
        print(result.stderr)
else:
    # Re-run the program with admin rights
    print("Requesting administrator privileges...")
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
