import re

# 1. Update app.js
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

# Fix broken images seamlessly
js = js.replace('class="doom-media" loading="lazy" />', 'class="doom-media" loading="lazy" onerror="this.closest(\'.doom-card\').style.display=\'none\';" />')

# Update the download logic to use the backend proxy for guaranteed mobile support
new_modal_logic = """// --- DOOMSCROLL MODAL LOGIC ---
async function forceDoomDownload(url, type) {
    const btn = document.getElementById('doom-dl-btn');
    if(btn) { btn.innerText = "Downloading..."; btn.style.opacity = "0.7"; }
    
    // Use the backend proxy to guarantee a forced download (bypasses CORS and Mobile restrictions)
    let ext = type === 'video' ? 'mp4' : 'jpg';
    let filename = `DoomScroll_Media_${Date.now()}.${ext}`;
    let proxyUrl = `/api/download?url=${encodeURIComponent(url)}&filename=${filename}`;
    
    const a = document.createElement('a');
    a.href = proxyUrl;
    // The backend will send Content-Disposition: attachment
    a.download = filename; 
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    setTimeout(() => {
        if(btn) { btn.innerText = "Download"; btn.style.opacity = "1"; }
    }, 1500);
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

# 2. Update server.py
with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', encoding='utf-8') as f:
    py = f.read()

proxy_logic = """@app.route("/api/download")
def api_download_media():
    \"\"\"Backend proxy to force download media files and bypass Mobile/CORS restrictions.\"\"\"
    import urllib.request
    from flask import Response
    
    url = request.args.get('url')
    filename = request.args.get('filename', 'doomscroll_media.jpg')
    
    if not url:
        return jsonify({"ok": False, "error": "No URL provided"}), 400
        
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": resp.headers.get("Content-Type", "application/octet-stream")
        }
        
        return Response(resp.read(), headers=headers)
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/doomscroll")"""

py = py.replace('@app.route("/api/doomscroll")', proxy_logic)

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', 'w', encoding='utf-8') as f:
    f.write(py)
