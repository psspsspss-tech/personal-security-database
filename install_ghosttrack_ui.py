import re

filepath = r"C:\Users\acer\Desktop\Security Suite\dashboard\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add GhostTrack to sidebar drawer
gt_drawer = """    <button class="drawer-item" id="drawer-tab-ghosttrack" onclick="showTab('ghosttrack'); closeDrawer()">
      <div class="drawer-icon" style="color:var(--cyan)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></div>
      <span>GhostTrack OSINT</span>
    </button>"""

if 'id="drawer-tab-ghosttrack"' not in html:
    # Insert right before Setup drawer item
    html = html.replace('    <button class="drawer-item" id="drawer-tab-setup"', gt_drawer + '\n    <button class="drawer-item" id="drawer-tab-setup"')

# 2. Add Network Sonar & Cache Vault drawer buttons if not already present
sonar_drawer = """    <button class="drawer-item" id="drawer-tab-radar" onclick="openRadarModal(); closeDrawer()">
      <div class="drawer-icon" style="color:var(--cyan)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/><path d="M2 12h20"/></svg></div>
      <span>Network Sonar</span>
    </button>"""

cache_drawer = """    <button class="drawer-item" id="drawer-tab-cache" onclick="openCacheModal(); closeDrawer()">
      <div class="drawer-icon" style="color:var(--green)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg></div>
      <span>The Cache Vault</span>
    </button>"""

if 'id="drawer-tab-radar"' not in html:
    html = html.replace('    <button class="drawer-item" id="drawer-tab-ports"', sonar_drawer + '\n    <button class="drawer-item" id="drawer-tab-ports"')

if 'id="drawer-tab-cache"' not in html:
    html = html.replace('    <button class="drawer-item" id="drawer-tab-ports"', cache_drawer + '\n    <button class="drawer-item" id="drawer-tab-ports"')

# 3. Add panel-ghosttrack HTML after panel-setup
gt_panel = """
  <!-- ──────────────────────────────────────── GHOSTTRACK OSINT PANEL ──────────────────────────────────────── -->
  <section id="panel-ghosttrack" class="panel">
    <div class="panel-toolbar">
      <div class="panel-title-group">
        <h1 class="panel-heading">GhostTrack OSINT Terminal</h1>
        <span class="panel-sub">Trace IP addresses, phone numbers, emails, usernames, and analyze EXIF/Reverse search media</span>
      </div>
    </div>
    
    <div class="card" style="margin-bottom: 20px;">
      <div class="card-header">
        <h2 class="card-title">Omni-Search Query</h2>
      </div>
      <div style="padding: 20px;">
        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 15px;">
          Enter any target identifier: an IP address, domain name, email address, phone number (include country code, e.g. +1), or username.
        </p>
        <div style="display: flex; gap: 10px; margin-bottom: 20px; align-items: center; flex-wrap: wrap;">
          <input type="text" id="gt-target" placeholder="Target identifier (e.g. 8.8.8.8, +15551234567, admin@gmail.com, sherlock)..." class="form-input" style="flex: 1; padding: 12px; margin: 0; background: var(--bg-card); color: var(--text-primary); border: 2px solid var(--border);">
          <button onclick="startGhostTrackHunt()" class="btn-scan" style="padding: 12px 24px; white-space: nowrap; margin: 0;">INITIATE SCAN</button>
        </div>
        
        <div style="display: flex; gap: 15px; flex-wrap: wrap; justify-content: center; border-top: 1px solid var(--bg-secondary); padding-top: 15px;">
          <!-- EXIF Upload Trigger -->
          <label class="btn-sm" style="cursor: pointer; background: var(--bg-secondary); color: var(--text-primary); border: 2px solid var(--border); padding: 8px 16px; font-weight: bold; display: flex; align-items: center; gap: 8px; box-shadow: 2px 2px 0px var(--border);">
            <svg style="width: 16px; height: 16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
            Upload Image for EXIF Forensics
            <input type="file" id="gt-exif-upload" accept="image/jpeg, image/png, image/jpg" onchange="uploadGtExif(this)" style="display: none;">
          </label>
          
          <!-- Reverse Search Trigger -->
          <label class="btn-sm" style="cursor: pointer; background: var(--bg-secondary); color: var(--text-primary); border: 2px solid var(--border); padding: 8px 16px; font-weight: bold; display: flex; align-items: center; gap: 8px; box-shadow: 2px 2px 0px var(--border);">
            <svg style="width: 16px; height: 16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            Reverse Image/Video Search (SauceNAO)
            <input type="file" id="gt-reverse-upload" accept="image/*,video/*" onchange="uploadGtReverse(this)" style="display: none;">
          </label>
        </div>
      </div>
    </div>
    
    <!-- Progress Indicator -->
    <div id="gt-progress-container" class="card" style="display: none; margin-bottom: 20px; border-color: var(--cyan);">
      <div style="padding: 20px; text-align: center;">
        <div style="font-weight: bold; margin-bottom: 10px; font-family: var(--font-mono);" id="gt-status-text">Extracting Intelligence...</div>
        <div style="background: var(--bg-secondary); height: 12px; border: 2px solid var(--border); overflow: hidden; border-radius: 6px;">
          <div id="gt-progress-bar" style="background: var(--cyan); height: 100%; width: 0%; transition: width 0.2s;"></div>
        </div>
      </div>
    </div>
    
    <!-- Results Section -->
    <div id="gt-results-card" class="card" style="display: none; border-color: var(--cyan);">
      <div class="card-header" style="background: rgba(0, 212, 255, 0.05); display: flex; justify-content: space-between; align-items: center;">
        <h2 class="card-title" style="color: var(--cyan);">Intelligence Report</h2>
        <span style="font-family: var(--font-mono); font-size: 11px; font-weight: bold; color: var(--green); text-transform: uppercase;">● OSINT Telemetry Received</span>
      </div>
      <div class="card-body" id="gt-results" style="padding: 20px;">
        <!-- Dynamic results will be injected here by app.js -->
      </div>
    </div>
  </section>"""

if 'id="panel-ghosttrack"' not in html:
    # Find the end of panel-setup section
    setup_idx = html.find('id="panel-setup"')
    if setup_idx != -1:
        section_end = html.find('</section>', setup_idx)
        if section_end != -1:
            insert_pos = section_end + len('</section>')
            html = html[:insert_pos] + "\n" + gt_panel + html[insert_pos:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(html)

print("GhostTrack OSINT UI successfully injected into index.html")
