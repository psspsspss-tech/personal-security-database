with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

modal_html = """
<!-- DoomScroll Modal -->
<div id="doom-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.9); z-index:9999; backdrop-filter:blur(10px);">
    <div style="position:absolute; top:15px; right:30px; font-size:40px; color:#aa00ff; cursor:pointer; text-shadow:0 0 10px rgba(170,0,255,0.5);" onclick="closeDoomModal()">&times;</div>
    <div id="doom-modal-content" style="width:80%; height:85%; margin:4% auto; background:#111; border:1px solid #aa00ff; border-radius:12px; overflow:hidden; box-shadow:0 0 30px rgba(170,0,255,0.2);"></div>
</div>
"""

if 'id="doom-modal"' not in html:
    html = html.replace('</body>', modal_html + '\n</body>')

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
