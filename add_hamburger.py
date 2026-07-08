import re

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

hamburger = """<button onclick="toggleDrawer()" class="btn-hamburger" style="background:transparent; border:none; cursor:pointer; margin-right:15px; display:flex; align-items:center; color: var(--text-primary); box-shadow:none !important; border:none !important; transform:none !important;">
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
    <line x1="3" y1="12" x2="21" y2="12"></line>
    <line x1="3" y1="6" x2="21" y2="6"></line>
    <line x1="3" y1="18" x2="21" y2="18"></line>
  </svg>
</button>
"""

if 'class="btn-hamburger"' not in html:
    html = html.replace('<div class="logo">', hamburger + '<div class="logo">')
    
    with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
        f.write(html)
        print("Added hamburger button.")
