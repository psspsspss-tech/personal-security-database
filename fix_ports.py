import re

html_path = r"C:\Users\acer\Desktop\Security Suite\dashboard\index.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

pattern = r'</section>\s*<th>Port</th>\s*<th>Address</th>\s*<th>Process</th>\s*<th>PID</th>\s*<th>Risk</th>\s*</tr>\s*</thead>'

fixed_part = '''</section>

  <!-- ──────────── PORTS TAB ──────────── -->
  <section id="panel-ports" class="panel">
    <div class="panel-toolbar">
      <div class="panel-title-group">
        <h1 class="panel-heading">Open Ports & Connections</h1>
        <span class="panel-sub">Monitor active network listeners and connections</span>
      </div>
      <button class="btn-primary" onclick="loadPorts()">🔄 Scan Ports</button>
    </div>
    
    <div class="card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Port</th>
              <th>Address</th>
              <th>Process</th>
              <th>PID</th>
              <th>Risk</th>
            </tr>
          </thead>'''

if re.search(pattern, html):
    html = re.sub(pattern, fixed_part, html)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print("Fixed panel-ports!")
else:
    print("Regex not found!")
