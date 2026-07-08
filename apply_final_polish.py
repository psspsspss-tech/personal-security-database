import re

# 1. Update index.html
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

# Replace the style block
new_style = """<style>
/* DoomScroll Final CSS */
.doom-col { flex: 1; display: flex; flex-direction: column; gap: 20px; }
@media (max-width: 900px) {
    #doom-col-3 { display: none !important; }
}
@media (max-width: 600px) {
    #doom-col-2 { display: none !important; }
    #doomscroll-container { padding: 10px !important; gap: 10px !important; }
}

.doom-card {
    break-inside: avoid;
    margin-bottom: 0;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    color: var(--text);
    transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
.doom-card:hover {
    transform: translateY(-5px);
    border-color: var(--primary);
    box-shadow: 0 8px 25px rgba(0,255,204,0.2);
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
</style>"""

html = re.sub(r'<style>\n\.masonry-grid \{.*?</style>', new_style, html, flags=re.DOTALL)

# Fix purple inline styles
html = html.replace('color:#aa00ff; text-shadow: 0 0 10px rgba(170,0,255,0.5);', 'color:var(--primary);')
html = html.replace('background:#aa00ff;', 'background:var(--primary); color:#000;')
html = html.replace('color: #aa00ff; filter: drop-shadow(0 0 5px rgba(170,0,255,0.5));', 'color:var(--primary);')

# Fix modal purple styles
html = html.replace('color:#aa00ff; cursor:pointer; text-shadow:0 0 10px rgba(170,0,255,0.5);', 'color:var(--primary); cursor:pointer;')
html = html.replace('border:1px solid #aa00ff; border-radius:12px; overflow:hidden; box-shadow:0 0 30px rgba(170,0,255,0.2);', 'border:1px solid var(--primary); border-radius:12px; overflow:hidden; box-shadow:0 0 30px rgba(0,255,204,0.2);')

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
    f.write(html)

# 2. Update app.js
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

# Fix purple loaders and articles
js = js.replace('color:#aa00ff;', 'color:var(--primary);')
js = js.replace('background:linear-gradient(45deg, #1a0033, #000);', 'background:var(--bg); border:1px solid var(--border);')

# Update the column logic
old_col_logic = """let shortestCol = cols[0];
                let minHeight = shortestCol.offsetHeight;
                
                for(let i=1; i<cols.length; i++) {
                    if(cols[i].offsetHeight < minHeight) {
                        shortestCol = cols[i];
                        minHeight = cols[i].offsetHeight;
                    }
                }
                shortestCol.appendChild(card);"""

new_col_logic = """let visibleCols = cols.filter(c => window.getComputedStyle(c).display !== 'none');
                let shortestCol = visibleCols[0];
                let minHeight = shortestCol.offsetHeight;
                
                for(let i=1; i<visibleCols.length; i++) {
                    if(visibleCols[i].offsetHeight < minHeight) {
                        shortestCol = visibleCols[i];
                        minHeight = visibleCols[i].offsetHeight;
                    }
                }
                shortestCol.appendChild(card);"""

js = js.replace(old_col_logic, new_col_logic)

# Update modal download logic
new_modal_logic = """// --- DOOMSCROLL MODAL LOGIC ---
async function forceDoomDownload(url, type) {
    const btn = document.getElementById('doom-dl-btn');
    if(btn) { btn.innerText = "Downloading..."; btn.style.opacity = "0.7"; }
    try {
        const res = await fetch(url);
        const blob = await res.blob();
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        
        let ext = type === 'video' ? 'mp4' : 'jpg';
        a.download = `DoomScroll_Media_${Date.now()}.${ext}`;
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
    } catch(e) {
        window.open(url, '_blank');
    }
    if(btn) { btn.innerText = "Download"; btn.style.opacity = "1"; }
}

function openDoomModal(url, type) {
    const modal = document.getElementById('doom-modal');
    const content = document.getElementById('doom-modal-content');
    modal.style.display = 'block';
    
    let downloadBtn = '';
    if (type === 'image' || type === 'video') {
        downloadBtn = `<button id="doom-dl-btn" onclick="forceDoomDownload('${url}', '${type}')" style="position:absolute; bottom:20px; right:20px; background:var(--primary); color:#000; padding:10px 20px; border:none; border-radius:5px; font-weight:bold; cursor:pointer; box-shadow:0 0 10px rgba(0,255,204,0.5); z-index:10001;">Download</button>`;
    }
    
    if (type === 'article') {
        content.innerHTML = `<iframe src="${url}" style="width:100%; height:100%; border:none; background:#fff;"></iframe>`;
    } else if (type === 'image') {
        content.innerHTML = `<img src="${url}" style="width:100%; height:100%; object-fit:contain; background:#000;" />${downloadBtn}`;
    } else if (type === 'video') {
        content.innerHTML = `<video src="${url}" style="width:100%; height:100%; object-fit:contain; background:#000;" controls autoplay></video>${downloadBtn}`;
    }
}"""

js = re.sub(r'// --- DOOMSCROLL MODAL LOGIC ---.*?(?=function closeDoomModal)', new_modal_logic + '\n\n', js, flags=re.DOTALL)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)
