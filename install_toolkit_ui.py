import re

filepath = r"C:\Users\acer\Desktop\Security Suite\dashboard\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    html = f.read()

# Locate the panel-toolkit section
toolkit_start = html.find('<section id="panel-toolkit" class="panel">')
if toolkit_start != -1:
    # Find the matching closing tag for this section
    # Since panel sections don't have nested section tags, we can find the next </section> after toolkit_start
    toolkit_end = html.find('</section>', toolkit_start)
    if toolkit_end != -1:
        toolkit_end += len('</section>')
        
        # Define the new dual-column toolkit HTML
        new_toolkit_panel = """<section id="panel-toolkit" class="panel">
    <div class="panel-toolbar">
      <div class="panel-title-group">
        <h1 class="panel-heading">Offensive & Diagnostic Toolkit</h1>
        <span class="panel-sub">Run tools and control active NetHunter drone nodes</span>
      </div>
    </div>
    
    <div class="toolkit-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;">
      
      <!-- Left Column: Local Audit Suite -->
      <div class="card" style="display: flex; flex-direction: column;">
        <div class="card-header">
          <h2 class="card-title">Local Audit Suite</h2>
        </div>
        <div style="padding: 16px; flex: 1; display: flex; flex-direction: column; gap: 15px;">
          <div>
            <h4 style="margin-bottom: 8px; color: var(--text-secondary); font-size: 12px; font-weight: bold; text-transform: uppercase;">1. Select Diagnostic Tool</h4>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
              <button id="btn-tool-ping" class="btn-sm" style="background:#ffcc00; padding: 6px 12px;" onclick="selectAuditTool('ping')">PING</button>
              <button id="btn-tool-traceroute" class="btn-sm" style="background:#fff; padding: 6px 12px;" onclick="selectAuditTool('traceroute')">TRACEROUTE</button>
              <button id="btn-tool-nmap" class="btn-sm" style="background:#fff; padding: 6px 12px;" onclick="selectAuditTool('nmap')">NMAP</button>
              <button id="btn-tool-nikto" class="btn-sm" style="background:#fff; padding: 6px 12px;" onclick="selectAuditTool('nikto')">NIKTO</button>
              <button id="btn-tool-sqlmap" class="btn-sm" style="background:#fff; padding: 6px 12px;" onclick="selectAuditTool('sqlmap')">SQLMAP</button>
            </div>
          </div>
          
          <div>
            <h4 style="margin-bottom: 8px; color: var(--text-secondary); font-size: 12px; font-weight: bold; text-transform: uppercase;">2. Target Configuration</h4>
            <div style="display: flex; gap: 10px;">
              <input type="text" id="audit-target-input" placeholder="Enter IP or domain to ping (e.g. 8.8.8.8)" class="form-input" style="flex: 1; padding: 10px; margin: 0; background: var(--bg-card); color: var(--text-primary); border: 2px solid var(--border);">
              <button id="btn-run-audit" class="btn-scan" onclick="executeAuditTool()" style="padding: 10px 20px; white-space: nowrap; margin: 0;">RUN AUDIT</button>
            </div>
          </div>
          
          <div style="flex: 1; display: flex; flex-direction: column; min-height: 250px;">
            <h4 style="margin-bottom: 8px; color: var(--text-secondary); font-size: 12px; font-weight: bold; text-transform: uppercase;">3. Audit Console</h4>
            <pre id="audit-console" style="background: #000; color: #00ffcc; padding: 12px; border: 2px solid #111; overflow-y: auto; font-family: var(--font-mono); font-size: 12px; flex: 1; margin: 0; white-space: pre-wrap; text-align: left;">[System] Local Audit Suite ready. Select a tool and enter a target.</pre>
          </div>
        </div>
      </div>
      
      <!-- Right Column: NetHunter Drone Terminal -->
      <div class="card" style="display: flex; flex-direction: column;">
        <div class="card-header">
          <h2 class="card-title">NetHunter Drone Terminal</h2>
        </div>
        <div style="padding: 16px; flex: 1; display: flex; flex-direction: column; gap: 15px;">
          <div>
            <h4 style="margin-bottom: 8px; color: var(--text-secondary); font-size: 12px; font-weight: bold; text-transform: uppercase;">1. Connect to Drone Node</h4>
            <select id="terminal-agent-select" class="form-input" style="width: 100%; padding: 10px; margin: 0; background: var(--bg-card); color: var(--text-primary); border: 2px solid var(--border);">
              <option value="">Select Target Drone...</option>
            </select>
          </div>
          
          <div style="flex: 1; display: flex; flex-direction: column; min-height: 250px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <h4 style="color: var(--text-secondary); font-size: 12px; font-weight: bold; text-transform: uppercase; margin: 0;">2. Interactive Shell Output</h4>
              <button class="btn-sm" style="padding: 2px 8px; font-size: 11px;" onclick="clearTerminal()">Clear</button>
            </div>
            <div id="kali-terminal" style="background: #000; padding: 10px; border: 2px solid #111; overflow: hidden; flex: 1; min-height: 250px;"></div>
          </div>
        </div>
      </div>
      
    </div>
  </section>"""
        
        html = html[:toolkit_start] + new_toolkit_panel + html[toolkit_end:]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        print("Injected dual-column toolkit UI successfully.")
else:
    print("Could not find panel-toolkit section in index.html.")
