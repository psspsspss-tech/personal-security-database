import os
import subprocess

html_file = r"C:\Users\acer\Desktop\Security Suite\dashboard\index.html"

# 1. Reset
subprocess.run(["git", "checkout", "dashboard/index.html"], cwd=r"C:\Users\acer\Desktop\Security Suite")

# 2. Rebuild
subprocess.run(["python", "rebuild_index.py"], cwd=r"C:\Users\acer\Desktop\Security Suite")

# 3. Read rebuilt
with open(html_file, "r", encoding="utf-8") as f:
    html = f.read()

# 4. Inject Cards cleanly
tripwireHTML = '''
    <!-- The Infinite Tarpit -->
    <div class="card" style="border: 1px solid #bb86fc; box-shadow: 0 4px 15px rgba(187,134,252,0.1); margin-top:20px;">
      <div style="font-size:16px; font-weight:700; color:#bb86fc; margin-bottom:12px; display:flex; justify-content:space-between;">
        <span>The Infinite Tarpit</span>
        <button onclick="refreshTarpitLogs()" style="background:#bb86fc; color:#000; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;">↻ Refresh</button>
      </div>
      <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">Active defense fake SSH server. Automated port scanners getting trapped will be displayed here.</p>
      <div id="tarpit-logs" style="background:#000; padding:10px; border-radius:8px; border:1px solid #333; height:200px; overflow-y:auto; font-family:monospace; font-size:12px; color:#bb86fc;">
        Waiting for victims...
      </div>
    </div>

    <!-- Ransomware Tripwire -->
    <div class="card" style="border: 1px solid #cf6679; box-shadow: 0 4px 15px rgba(207,102,121,0.1); margin-top:20px;">
      <div style="font-size:16px; font-weight:700; color:#cf6679; margin-bottom:12px; display:flex; justify-content:space-between;">
        <span>Ransomware Tripwire</span>
        <span id="tripwire-badge" style="background:var(--green); color:#000; padding:2px 8px; border-radius:12px; font-size:10px; font-weight:bold;">ARMED</span>
      </div>
      <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">Monitoring the Honey File <code>Desktop\Passwords_DO_NOT_OPEN</code>. If a rogue process touches it, the alarm sounds.</p>
      <div id="tripwire-logs" style="background:#000; padding:10px; border-radius:8px; border:1px solid #333; height:200px; overflow-y:auto; font-family:monospace; font-size:12px; color:var(--green);">
        [System] Tripwire armed and monitoring file hashes.
      </div>
    </div>
'''

if '<!-- Live Resource Graphs -->' in html:
    html = html.replace('<!-- Live Resource Graphs -->', tripwireHTML + '\n    <!-- Live Resource Graphs -->')

# 5. Inject Overlay
overlayHTML = '''
<div id="tripwire-alert-screen" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(255,0,0,0.95); z-index:999999; flex-direction:column; justify-content:center; align-items:center; color:white;">
  <svg style="width:100px; height:100px; margin-bottom:20px; animation: pulse 1s infinite;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
  <h1 style="font-size:60px; font-family:monospace; margin:0; text-align:center;">CRITICAL BREACH DETECTED</h1>
  <p style="font-size:24px; font-family:monospace; margin-bottom:30px;" id="tripwire-alert-text">Ransomware Tripwire triggered!</p>
  <button onclick="resetTripwireAlarm()" style="padding:15px 30px; font-size:20px; font-weight:bold; font-family:monospace; background:#000; color:var(--danger); border:2px solid var(--danger); cursor:pointer; border-radius:8px;">DISMISS & RESET ALARM</button>
</div>
<style>
@keyframes pulse { 0% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.2); opacity: 0.8; } 100% { transform: scale(1); opacity: 1; } }
</style>
'''

if '</body>' in html:
    html = html.replace('</body>', overlayHTML + '\n</body>')

with open(html_file, "w", encoding="utf-8") as f:
    f.write(html)
