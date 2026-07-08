import re

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

# Add CSS for DoomScroll
style_block = """
<style>
.masonry-grid {
    column-count: 3;
    column-gap: 20px;
    padding: 20px;
}
@media (max-width: 900px) { .masonry-grid { column-count: 2; } }
@media (max-width: 600px) { .masonry-grid { column-count: 1; } }

.doom-card {
    break-inside: avoid;
    margin-bottom: 20px;
    background: #111;
    border: 1px solid #333;
    border-radius: 12px;
    overflow: hidden;
    color: #eee;
    transition: transform 0.2s;
    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
}
.doom-card:hover {
    transform: translateY(-5px);
    border-color: #aa00ff;
    box-shadow: 0 8px 25px rgba(170,0,255,0.2);
}
.doom-media {
    width: 100%;
    display: block;
    background: #000;
}
.doom-content {
    padding: 15px;
}
.doom-title {
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 10px;
    line-height: 1.4;
}
.doom-meta {
    font-size: 11px;
    color: #888;
    display: flex;
    justify-content: space-between;
}
</style>
"""

if '.masonry-grid {' not in html:
    html = html.replace('</head>', style_block + '</head>')

# Add DoomScroll Panel
doom_panel = """
<section id="panel-doomscroll" class="panel" style="padding:0;">
  <div class="panel-toolbar" style="background: rgba(10,10,15,0.95); border-bottom: 1px solid #333; position:sticky; top:0; z-index:100; backdrop-filter:blur(10px);">
    <div class="panel-title-group">
      <h1 class="panel-heading" style="color:#aa00ff; text-shadow: 0 0 10px rgba(170,0,255,0.5);">DoomScroll</h1>
      <span class="panel-sub" style="color:#888;">The ultimate unified hive-mind feed.</span>
    </div>
    <button onclick="loadDoomScroll()" class="btn-primary" style="background:#aa00ff; border:none; padding:8px 15px; border-radius:20px; font-weight:bold;">Refresh</button>
  </div>
  <div id="doomscroll-container" class="masonry-grid" style="max-width:1400px; margin:0 auto;">
    <!-- Cards injected here -->
  </div>
</section>
"""

if 'id="panel-doomscroll"' not in html:
    html = html.replace('</main>', doom_panel + '\n</main>')

# Add icon in drawer
doom_icon = """
  <button class="drawer-item" onclick="showTab('doomscroll'); toggleDrawer(); loadDoomScroll();">
    <div class="drawer-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
    </div>
    <span>DoomScroll</span>
  </button>
"""

if '>DoomScroll</span>' not in html and 'class="drawer-grid"' in html:
    start_drawer = html.find('<div class="drawer-grid"')
    end_drawer = html.find('</div>', start_drawer)
    html = html[:end_drawer] + doom_icon + html[end_drawer:]

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
