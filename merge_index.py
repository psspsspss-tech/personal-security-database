import os
import re

desktop_index = r"C:\Users\acer\Desktop\Security Suite\dashboard\index.html"

with open(desktop_index, 'r', encoding='utf-8') as f:
    d_content = f.read()

# 1. Replace the old Kali panel HTML
old_kali_panel = re.compile(r"<!-- ──────────── KALI TERMINAL TAB ──────────── -->\s*<section id=\"panel-kaliterminal\" class=\"panel\">.*?</section>", re.DOTALL)

new_kali_panel = """<!-- ──────────── KALI TERMINAL TAB ──────────── -->
  <section id="panel-kaliterminal" class="panel">
    <div class="panel-toolbar">
      <div class="panel-title-group">
        <h1 class="panel-heading">Offensive Security Terminal</h1>
        <span class="panel-sub">Live SSH connection to your NetHunter device (Matrix Style)</span>
      </div>
      <div class="toolbar-actions" id="kali-connect-form">
        <input type="text" id="kali-ip" class="form-input" placeholder="Phone IP (e.g. 192.168.1.15)" style="min-width: 160px;" />
        <input type="text" id="kali-user" class="form-input" placeholder="User" style="min-width: 80px;" value="kali" />
        <input type="password" id="kali-pass" class="form-input" placeholder="Pass (default: kali)" style="min-width: 140px;" />
        <button class="btn-primary" id="btn-kali-connect" onclick="connectKali()">Connect</button>
      </div>
    </div>
    
    <div class="card matrix-container" id="terminal-wrapper" style="background:#000; padding:10px; border-radius:8px;">
      <div id="terminal-overlay" class="terminal-overlay" style="display:flex; justify-content:center; align-items:center; min-height:400px;">
        <div class="matrix-text" style="color:#0f0; font-family:monospace; text-align:center;">Waiting for connection...<br/>Run 'service ssh start' on your phone.</div>
      </div>
      <div id="terminal-container" style="min-height:400px; width:100%;"></div>
    </div>
  </section>"""

d_content = old_kali_panel.sub(new_kali_panel, d_content)

# 2. Add CDN scripts before </body>
cdn_scripts = """<script src="https://cdn.jsdelivr.net/npm/socket.io-client@4.7.2/dist/socket.io.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
<script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
"""

d_content = d_content.replace("<script src=\"app.js", cdn_scripts + "<script src=\"app.js")

with open(desktop_index, 'w', encoding='utf-8') as f:
    f.write(d_content)

print("Merged index.html")
