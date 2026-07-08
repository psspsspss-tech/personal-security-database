import re

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

# 1. Remove media-modal-overlay
html = re.sub(r'<div id="media-modal-overlay"[\s\S]*?</div>\s*</div>\s*</div>', '', html)
html = re.sub(r'<div id="media-modal-overlay".*?</video>\s*</div>\s*</div>\s*</div>', '', html, flags=re.DOTALL)

# Let's do a more robust removal for the modal
start_idx = html.find('<div id="media-modal-overlay"')
if start_idx != -1:
    end_idx = html.find('</div>', html.find('</div>', html.find('</div>', start_idx)+1)+1)+6
    html = html[:start_idx] + html[end_idx:]

# 2. Add panel-media before panel-more
panel_media = """
<section id="panel-media" class="panel">
  <div class="panel-toolbar">
    <div class="panel-title-group">
      <h1 class="panel-heading">Secure Media Player</h1>
      <span class="panel-sub">Watch videos without ads or tracking.</span>
    </div>
  </div>
  <div class="card" style="padding:40px; text-align:center;">
    <div style="display:flex; justify-content:center; gap:10px; margin-bottom:20px;">
      <input type="url" id="media-url-input" placeholder="Paste YouTube or video link here..." style="width:100%; max-width:600px; padding:12px; border-radius:8px; border:1px solid var(--border); background:var(--bg); color:var(--text); font-size:16px;" />
      <button onclick="extractAndPlayMedia()" class="btn-primary" id="btn-play-media" style="padding:12px 24px; border-radius:8px; font-weight:bold;">Play Securely</button>
    </div>
    <div id="media-player-container" style="display:none; background:#000; border-radius:8px; overflow:hidden; position:relative; aspect-ratio:16/9; max-width:800px; margin:0 auto; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
      <h3 id="media-title" style="position:absolute; top:0; left:0; right:0; background:rgba(0,0,0,0.8); color:#fff; margin:0; padding:10px; text-align:left; font-size:14px; z-index:10; pointer-events:none;">Loading...</h3>
      <!-- We will inject either a video element or an iframe here dynamically -->
    </div>
  </div>
</section>
"""

if 'id="panel-media"' not in html:
    html = html.replace('<section id="panel-more" class="panel">', panel_media + '\n<section id="panel-more" class="panel">')

# 3. Add tool card in panel-more
tool_card = """
    <div class="tool-card" onclick="showTab('media')" style="cursor:pointer; display:flex; flex-direction:column; align-items:center; justify-content:center; padding: 20px;">
      <svg style="width: 40px; height: 40px; margin-bottom: 10px; color: var(--primary);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>
      <span style="font-weight: 700;">Media Player</span>
    </div>
"""

if "showTab('media')" not in html:
    html = html.replace('<div class="tool-card" onclick="showTab(\'setup\')"', tool_card + '    <div class="tool-card" onclick="showTab(\'setup\')"')

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
