import os

html_path = r"C:\Users\acer\Desktop\Security Suite\dashboard\index.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Strip everything before <!DOCTYPE html>
idx = html.find('<!DOCTYPE html>')
if idx != -1:
    html = html[idx:]

# 2. Inject DoomScroll button properly into panel-toolkit
doom_icon = '''
    <div class="card" onclick="showTab('doomscroll'); loadDoomScroll();" style="cursor:pointer; display:flex; flex-direction:row; align-items:center; padding: 20px; margin-top:20px; background: #220033; border: 1px solid #aa00ff;">
      <svg style="width: 40px; height: 40px; margin-right: 20px; color: #aa00ff;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
      <div>
        <h3 style="color:#aa00ff; margin:0;">Open DoomScroll Feed</h3>
        <span style="color:#888; font-size:12px;">The ultimate unified hive-mind feed.</span>
      </div>
    </div>
'''

# Find the end of panel-toolkit to inject it
tk_idx = html.find('</section>', html.find('id="panel-toolkit"'))
if tk_idx != -1:
    html = html[:tk_idx] + doom_icon + "\n" + html[tk_idx:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print("Fixed!")
