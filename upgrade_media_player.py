import re

# 1. Update index.html
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

html = html.replace(
    '<iframe id="sniffed-iframe" style="width:100%; height:100%; border:none; display:none; background:#000;"></iframe>',
    '<iframe id="sniffed-iframe" style="width:100%; height:100%; border:none; display:none; background:#000;"></iframe>\n        <select id="hls-quality" style="display:none; position:absolute; top:10px; right:10px; background:rgba(0,0,0,0.8); color:var(--primary); border:1px solid var(--primary); padding:5px; border-radius:5px; font-weight:bold; cursor:pointer; z-index:10;"></select>'
)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
    f.write(html)

# 2. Update app.js
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

# Add quality reset in setupAdvancedPlayer
q_reset = """    if (currentHls) {
        currentHls.destroy();
        currentHls = null;
    }
    
    const qSelect = document.getElementById('hls-quality');
    if(qSelect) { qSelect.style.display = 'none'; qSelect.innerHTML = ''; }"""
    
js = js.replace("""    if (currentHls) {
        currentHls.destroy();
        currentHls = null;
    }""", q_reset)

# Add MANIFEST_PARSED handler
hls_handler = """currentHls.on(Hls.Events.MANIFEST_PARSED, function(event, data) {
                    videoElem.play();
                    updatePlayIcon(true);
                    
                    const qSelect = document.getElementById('hls-quality');
                    if(qSelect && data.levels && data.levels.length > 0) {
                        qSelect.style.display = 'block';
                        qSelect.innerHTML = `<option value="-1">Auto Quality</option>`;
                        data.levels.forEach((level, idx) => {
                            qSelect.innerHTML += `<option value="${idx}">${level.height}p (${Math.round(level.bitrate/1000)}k)</option>`;
                        });
                        qSelect.onchange = (e) => {
                            currentHls.currentLevel = parseInt(e.target.value);
                        };
                    }
                });"""
                
js = re.sub(r'currentHls\.on\(Hls\.Events\.MANIFEST_PARSED, function\(\) \{.*?\}\);', hls_handler, js, flags=re.DOTALL)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)

# 3. Update server.py
with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', encoding='utf-8') as f:
    py = f.read()

idm_b64_logic = """                    # Look for m3u8 or mp4
                    m3u8 = re.findall(r'(https?://[^\s"\\'<>]*?\\.m3u8[^\s"\\'<>]*)', html)
                    if m3u8: return m3u8[0]
                    
                    # Look for Base64 encoded m3u8 URLs (common obfuscation)
                    import base64
                    b64_strings = re.findall(r'[A-Za-z0-9+/=]{30,}', html)
                    for s in b64_strings:
                        try:
                            dec = base64.b64decode(s).decode('utf-8')
                            if '.m3u8' in dec:
                                m = re.search(r'(https?://[^\s"\\'<>]*?\\.m3u8[^\s"\\'<>]*)', dec)
                                if m: return m.group(1)
                        except: pass"""

py = py.replace("""                    # Look for m3u8 or mp4
                    m3u8 = re.findall(r'(https?://[^\\s"\\'<>]*?\\.m3u8[^\\s"\\'<>]*)', html)
                    if m3u8: return m3u8[0]""", idm_b64_logic)

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', 'w', encoding='utf-8') as f:
    f.write(py)
