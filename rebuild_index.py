import builtins
import os
import re
import subprocess

original_open = builtins.open

class DummyFile:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def write(self, text): pass
    def close(self): pass

def custom_open(file, mode='r', *args, **kwargs):
    if "index.html" in str(file).replace("\\", "/"):
        return original_open(file, mode, *args, **kwargs)
    else:
        if 'w' in mode or 'a' in mode:
            return DummyFile()
        else:
            return original_open(file, mode, *args, **kwargs)

builtins.open = custom_open

scripts = [
    "merge_index.py",
    "apply_neo_brutalism.py",
    "inject_ui.py",
    "update_index.py",
    "update_frontend_doom.py",
    "update_frontend_html.py",
    "update_index_modal.py",
    "apply_final_polish.py",
    "apply_comments.py",
    "upgrade_media_player.py",
    "update_bloody_sweet.py",
    "add_vlc_btn.py",
    "add_cast_btn.py",
    "install_ui.py",
    "install_casino_ui.py",
    "install_cache_ui.py",
    "install_toolkit_ui.py",
    "install_ghosttrack_ui.py",
    "add_hamburger.py"
]

html_path = r"C:\Users\acer\Desktop\Security Suite\dashboard\index.html"

subprocess.run(["git", "checkout", "dashboard/index.html"], cwd=r"C:\Users\acer\Desktop\Security Suite")

for script in scripts:
    print(f"Running {script}...")
    try:
        with original_open(script, 'r', encoding='utf-8') as f:
            code = f.read()
            
        # Patching update_index.py
        if script == "update_index.py":
            code = code.replace(
                '''html.replace('<section id="panel-more" class="panel">', panel_media + '\\n<section id="panel-more" class="panel">')''',
                '''html.replace('</main>', panel_media + '\\n</main>')'''
            )
            
        # Patching update_frontend_doom.py
        if script == "update_frontend_doom.py":
            code = code.replace(
                '''html.find('id="panel-more"')''',
                '''html.find('id="panel-toolkit"')'''
            )

        exec(code, globals())
        
        with original_open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if content.count('<html') > 1:
            print(f"DUPLICATION DETECTED AFTER {script}!")
            break
            
    except Exception as e:
        print(f"Error in {script}: {e}")

# Inject Tarpit & Tripwire & Overlay
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
      <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">Monitoring the Honey File <code>Desktop\\\\Passwords_DO_NOT_OPEN</code>. If a rogue process touches it, the alarm sounds.</p>
      <div id="tripwire-logs" style="background:#000; padding:10px; border-radius:8px; border:1px solid #333; height:200px; overflow-y:auto; font-family:monospace; font-size:12px; color:var(--green);">
        [System] Tripwire armed and monitoring file hashes.
      </div>
    </div>
'''

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

with original_open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Only inject tripwire into the overview panel! Not every single section!
# Find the end of panel-overview
idx = html.find('</section>', html.find('id="panel-overview"'))
if idx != -1:
    html = html[:idx] + tripwireHTML + "\\n" + html[idx:]

# Inject overlay at the end
if '</body>' in html:
    html = html.replace('</body>', overlayHTML + '\\n</body>')

with original_open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Done rebuilding completely!")
