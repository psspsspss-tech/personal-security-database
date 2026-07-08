import os

filepath = r"C:\Users\acer\Desktop\Security Suite\dashboard\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Insert Resource Graphs into panel-overview
graph_html = """
    <!-- Live Resource Graphs -->
    <div class="card" style="margin-top:20px;">
      <div class="card-header"><h2 class="card-title">Live System Resources</h2></div>
      <div style="padding:20px;">
        <canvas id="resourceChart" height="80"></canvas>
      </div>
    </div>
"""
# Find end of stat-grid in panel-overview
if 'id="panel-overview"' in html:
    idx = html.find('</div>', html.find('<div class="stat-grid"', html.find('id="panel-overview"')))
    if idx != -1:
        # Actually it's better to append before the closing </section> of panel-overview
        end_idx = html.find('</section>', html.find('id="panel-overview"'))
        html = html[:end_idx] + graph_html + html[end_idx:]


# 2. Add panel-breach and panel-toolkit (if missing) before panel-search
breach_panel = """
<section id="panel-breach" class="panel">
  <div class="panel-toolbar">
    <div class="panel-title-group">
      <h1 class="panel-heading">Dark Web Breach Scanner</h1>
      <span class="panel-sub">Powered by HaveIBeenPwned API</span>
    </div>
  </div>
  <div class="card" style="padding:40px; text-align:center;">
    <h3 style="margin-bottom:20px;">Check Email for Breaches</h3>
    <div style="display:flex; justify-content:center; gap:10px;">
      <input type="email" id="breach-email" placeholder="Enter your email address..." style="width:100%; max-width:400px; padding:10px; border-radius:8px; border:1px solid var(--border); background:var(--bg); color:var(--text);" />
      <button onclick="scanBreach()" class="btn-primary" style="padding:10px 20px; border-radius:8px;">Scan</button>
    </div>
    <div id="breach-results" style="margin-top:20px; text-align:left;"></div>
  </div>
</section>
"""

toolkit_panel = """
<section id="panel-toolkit" class="panel">
  <div class="panel-toolbar">
    <div class="panel-title-group">
      <h1 class="panel-heading">Hacker Toolkit</h1>
      <span class="panel-sub">Utilities and Trackers</span>
    </div>
  </div>
  <div class="stat-grid">
    <div class="card">
      <div class="card-header"><h2 class="card-title">Geo-IP Tracker</h2></div>
      <div style="padding:20px;">
        <div style="display:flex; gap:10px; margin-bottom:15px;">
          <input type="text" id="geoip-input" placeholder="Enter IP address (e.g. 8.8.8.8)" style="flex:1; padding:8px; border-radius:4px; border:1px solid var(--border); background:var(--bg); color:var(--text);" />
          <button onclick="trackIP()" class="btn-primary" style="padding:8px 15px; border-radius:4px;">Track</button>
        </div>
        <div id="geoip-map" style="height:250px; background:#111; border-radius:8px; border:1px solid var(--border);"></div>
      </div>
    </div>
    
    <div class="card">
      <div class="card-header"><h2 class="card-title">Military-Grade Password Gen</h2></div>
      <div style="padding:20px; text-align:center;">
        <div id="gen-password-display" style="font-family:monospace; font-size:24px; padding:20px; background:#000; color:var(--green); border-radius:8px; margin-bottom:15px; word-break:break-all;">Click to Generate</div>
        <button onclick="generateSecurePassword()" class="btn-primary" style="padding:10px 20px; border-radius:8px;">Generate Secure Password</button>
      </div>
    </div>
  </div>
</section>
"""

# Insert panels before panel-search
search_idx = html.find('<section id="panel-search"')
if search_idx != -1:
    html = html[:search_idx] + breach_panel + toolkit_panel + html[search_idx:]

# 3. Add Media Player Modal
media_modal = """
<div class="modal-overlay" id="media-modal-overlay" style="display:none; background:rgba(0,0,0,0.95); z-index:9999;" onclick="closeMediaPlayer()">
  <div style="position:absolute; top:20px; right:30px; cursor:pointer; color:var(--danger); font-size:40px;" onclick="closeMediaPlayer()">✕</div>
  <div style="width:90%; max-width:1200px; margin: 100px auto; background:#000; border:2px solid var(--border); border-radius:12px; overflow:hidden;" onclick="event.stopPropagation()">
    <div style="padding:15px; background:#111; border-bottom:1px solid var(--border); display:flex; justify-content:space-between;">
      <h3 id="media-title" style="margin:0; color:var(--cyan); font-family:var(--font-mono);">Secure Media Player</h3>
      <span style="color:var(--green); font-size:12px; font-family:monospace;">● SECURE DIRECT STREAM</span>
    </div>
    <video id="secure-video-player" controls autoplay style="width:100%; max-height:75vh; outline:none; background:#000;"></video>
  </div>
</div>
"""
# Insert before </body>
body_idx = html.find('</body>')
if body_idx != -1:
    html = html[:body_idx] + media_modal + html[body_idx:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(html)
print("Injected UI modules!")
