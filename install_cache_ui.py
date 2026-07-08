import re

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

# 1. Add "The Cache" to sidebar
cache_li = """<li onclick="openCacheModal()">💾 The Cache Vault</li>
                <li onclick="openRadarModal()">"""
html = html.replace('<li onclick="openRadarModal()">', cache_li, 1)

# 2. Add Cache Vault Modal
cache_modal = """
<!-- CACHE MODAL -->
<div id="cache-modal" class="modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:9999; justify-content:center; align-items:center;">
  <div style="background:rgba(10,10,15,0.95); border:1px solid var(--cyan); border-radius:8px; padding:20px; width:700px; color:#fff; box-shadow: 0 0 20px var(--cyan); max-height:80vh; overflow:hidden; display:flex; flex-direction:column;">
     <h2 style="margin-top:0; border-bottom:1px solid var(--cyan); padding-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
        💾 The Cache Vault 
        <span style="font-size:12px; color:#888;">Local Disk Storage</span>
     </h2>
     
     <div style="display:flex; gap:10px; margin-top:10px;">
        <input type="text" id="cache-magnet-input" placeholder="Paste magnet link to permanently cache..." style="flex:1; background:#000; border:1px solid #333; color:#fff; padding:10px; border-radius:4px;">
        <button onclick="addCacheTask()" style="background:var(--cyan); color:#000; border:none; padding:10px 20px; border-radius:4px; font-weight:bold; cursor:pointer;">DOWNLOAD</button>
     </div>
     
     <div id="cache-results" style="margin-top:20px; flex:1; overflow-y:auto; background:#000; padding:10px; border-radius:4px;">
        Loading cache...
     </div>
     
     <button onclick="document.getElementById('cache-modal').style.display='none'" style="margin-top:20px; width:100%; padding:10px; background:#333; color:#fff; border:none; cursor:pointer; border-radius:4px;">CLOSE</button>
  </div>
</div>
</body>
"""
html = html.replace('</body>', cache_modal)

# 3. Add "Cache" button next to Sniffer Extract button
sniffer_btn = """<button class="btn" onclick="extractMedia()">EXTRACT</button>
              <button class="btn" style="background:#444;" onclick="openCacheModal()">CACHE</button>"""
html = html.replace('<button class="btn" onclick="extractMedia()">EXTRACT</button>', sniffer_btn)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
    f.write(html)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

cache_js = """
let cacheInterval = null;

function openCacheModal() {
    document.getElementById('cache-modal').style.display = 'flex';
    fetchCacheList();
    if (cacheInterval) clearInterval(cacheInterval);
    cacheInterval = setInterval(fetchCacheList, 2000);
}

// Ensure interval is cleared when closed
const origCloseCache = document.getElementById('cache-modal').querySelector('button[onclick*="none"]').onclick;
document.getElementById('cache-modal').querySelector('button[onclick*="none"]').onclick = function() {
    if (cacheInterval) clearInterval(cacheInterval);
    document.getElementById('cache-modal').style.display='none';
};

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function fetchCacheList() {
    try {
        const res = await fetch('http://127.0.0.1:8766/cache/list');
        const data = await res.json();
        const resDiv = document.getElementById('cache-results');
        
        if (data.ok) {
            if (data.cache.length === 0) {
                resDiv.innerHTML = "<div style='color:#888; text-align:center; margin-top:20px;'>Vault is empty.</div>";
                return;
            }
            
            let html = "";
            data.cache.forEach(t => {
                const percent = Math.round(t.progress * 100);
                const speed = formatBytes(t.downloadSpeed) + '/s';
                const downloaded = formatBytes(t.downloaded);
                const total = formatBytes(t.length);
                const isDone = percent === 100;
                
                html += `
                <div style="background:#111; border:1px solid #333; padding:15px; margin-bottom:10px; border-radius:4px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                        <strong style="color:var(--cyan); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:70%;">${t.name || 'Fetching Metadata...'}</strong>
                        <span style="color:#888; font-size:12px;">${isDone ? 'Completed' : speed}</span>
                    </div>
                    
                    <div style="background:#222; height:10px; border-radius:5px; overflow:hidden; margin-bottom:10px;">
                        <div style="background:${isDone ? 'var(--green)' : 'var(--cyan)'}; height:100%; width:${percent}%;"></div>
                    </div>
                    
                    <div style="display:flex; justify-content:space-between; font-size:12px; color:#aaa; align-items:center;">
                        <span>${percent}% (${downloaded} / ${total})</span>
                        <div>
                            ${isDone ? `<button onclick="playCached('${t.infoHash}')" style="background:var(--green); color:#000; border:none; padding:4px 10px; cursor:pointer; border-radius:2px; margin-right:5px; font-weight:bold;">PLAY</button>` : ''}
                            <button onclick="deleteCache('${t.magnet}')" style="background:#ff4444; color:#fff; border:none; padding:4px 10px; cursor:pointer; border-radius:2px;">TRASH</button>
                        </div>
                    </div>
                </div>`;
            });
            resDiv.innerHTML = html;
        }
    } catch(e) {
        console.error("Cache fetch error:", e);
    }
}

async function addCacheTask() {
    const magnet = document.getElementById('cache-magnet-input').value;
    if (!magnet) return;
    document.getElementById('cache-magnet-input').value = '';
    
    try {
        await fetch(`http://127.0.0.1:8766/cache/add?magnet=${encodeURIComponent(magnet)}`);
        fetchCacheList();
    } catch(e) {
        alert("Failed to add to cache");
    }
}

async function deleteCache(magnet) {
    if (!confirm("Delete this file permanently from disk?")) return;
    try {
        await fetch(`http://127.0.0.1:8766/cache/delete?magnet=${encodeURIComponent(magnet)}`);
        fetchCacheList();
    } catch(e) {}
}

function playCached(infoHash) {
    document.getElementById('cache-modal').style.display = 'none';
    if (cacheInterval) clearInterval(cacheInterval);
    
    // Play directly using the stream endpoint
    document.getElementById('video-player').src = `http://127.0.0.1:8766/play/${infoHash}`;
    document.getElementById('video-player').play();
}
"""

js = cache_js + "\n" + js

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)
