import re

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

if '<section id="panel-media"' not in html:
    html = html.replace('</main>', new_panel + '\n</main>')

# Add icon in drawer
bloody_sweet_icon = """
  <button class="drawer-item" onclick="showTab('media'); toggleDrawer();">
    <div class="drawer-icon">
      <svg style="color: #ff0000; filter: drop-shadow(0 0 5px rgba(255,0,0,0.5));" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>
    </div>
    <span>Bloody Sweet</span>
  </button>
"""

if '>Bloody Sweet</span>' not in html and 'class="drawer-grid"' in html:
    start_drawer = html.find('<div class="drawer-grid"')
    end_drawer = html.find('</div>', start_drawer)
    html = html[:end_drawer] + bloody_sweet_icon + html[end_drawer:]


with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
