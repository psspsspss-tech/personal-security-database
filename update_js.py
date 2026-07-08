import re

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

# 1. Remove old click interceptor
start = js.find("document.getElementById('search-results-list').addEventListener('click'")
if start != -1:
    end = js.find("});", start) + 3
    js = js[:start] + js[end:]

# 2. Remove closeMediaPlayer
start = js.find("function closeMediaPlayer()")
if start != -1:
    end = js.find("}", start) + 1
    js = js[:start] + js[end:]

# 3. Add extractAndPlayMedia
new_js = """
// --- SECURE MEDIA PLAYER LOGIC ---
async function extractAndPlayMedia() {
    const urlInput = document.getElementById('media-url-input');
    const container = document.getElementById('media-player-container');
    const titleEl = document.getElementById('media-title');
    const btn = document.getElementById('btn-play-media');
    
    const url = urlInput.value.trim();
    if(!url) {
        showToast('Please enter a valid URL', 'error');
        return;
    }
    
    container.style.display = 'block';
    container.innerHTML = '<h3 id="media-title" style="position:absolute; top:0; left:0; right:0; background:rgba(0,0,0,0.8); color:#fff; margin:0; padding:10px; text-align:left; font-size:14px; z-index:10; pointer-events:none;">Extracting Secure Stream...</h3>';
    btn.disabled = true;
    btn.textContent = 'Extracting...';
    
    try {
        const res = await fetch(`${API}/media/extract`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({url: url})
        });
        const data = await res.json();
        
        if (data.ok) {
            let playerHtml = '';
            // If the backend returned an iframe_url (fallback), use an iframe
            if (data.iframe_url) {
                playerHtml = `<iframe src="${data.iframe_url}" style="width:100%; height:100%; border:none;" allowfullscreen allow="autoplay; encrypted-media"></iframe>`;
            } else {
                // Otherwise use the raw video stream
                playerHtml = `<video id="secure-video-player" controls autoplay style="width:100%; height:100%;"><source src="${data.stream_url}" type="video/mp4"></video>`;
            }
            container.innerHTML = `<h3 id="media-title" style="position:absolute; top:0; left:0; right:0; background:rgba(0,0,0,0.8); color:#fff; margin:0; padding:10px; text-align:left; font-size:14px; z-index:10; pointer-events:none;">${data.title}</h3>` + playerHtml;
        } else {
            container.innerHTML = `<div style="color:var(--danger); padding:40px;">Error: ${data.error}</div>`;
        }
    } catch (err) {
        container.innerHTML = `<div style="color:var(--danger); padding:40px;">Connection Error: ${err.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Play Securely';
    }
}
"""

js += "\n" + new_js

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)
