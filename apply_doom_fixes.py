import re

# 1. Update app.js
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

new_logic = """const seenDoomPosts = new Set();
let doomPage = 1;
let isDoomLoading = false;
let doomObserver = null;

function setupDoomObserver() {
    if(doomObserver) doomObserver.disconnect();
    
    doomObserver = new IntersectionObserver((entries) => {
        if(entries[0].isIntersecting) {
            doomPage++;
            loadDoomScroll(true);
        }
    }, { rootMargin: "800px" });
    
    const cards = document.querySelectorAll('.doom-card');
    if(cards.length > 0) {
        doomObserver.observe(cards[cards.length - 1]);
    }
}

async function loadDoomScroll(append = false) {
    if (isDoomLoading) return;
    isDoomLoading = true;
    
    const container = document.getElementById('doomscroll-container');
    const cols = [
        document.getElementById('doom-col-1'),
        document.getElementById('doom-col-2'),
        document.getElementById('doom-col-3')
    ];
    
    if (!append) {
        doomPage = 1;
        seenDoomPosts.clear();
        cols.forEach(col => col.innerHTML = '');
        
        const loader = document.createElement('div');
        loader.id = 'doom-loading';
        loader.style = "position:absolute; width:100%; text-align:center; padding:50px; color:#aa00ff; font-weight:bold;";
        loader.innerText = "Connecting to The Hive...";
        container.appendChild(loader);
    } else {
        const loadMsg = document.createElement('div');
        loadMsg.id = 'doom-loading';
        loadMsg.style = "position:absolute; bottom:0; width:100%; text-align:center; padding:20px; color:#aa00ff; font-weight:bold;";
        loadMsg.innerText = "Pulling more from The Hive...";
        container.appendChild(loadMsg);
    }
    
    try {
        const res = await fetch(`/api/doomscroll?page=${doomPage}`);
        const data = await res.json();
        
        const loader = document.getElementById('doom-loading');
        if(loader) loader.remove();
        
        if(data.ok && data.posts) {
            data.posts.forEach(post => {
                if(seenDoomPosts.has(post.id)) return;
                seenDoomPosts.add(post.id);
                
                const card = document.createElement('div');
                card.className = 'doom-card';
                card.style.cursor = 'pointer';
                card.style.marginBottom = '0'; // Let gap handle it
                
                let mediaHtml = '';
                if(post.type === 'image') {
                    mediaHtml = `<img src="${post.media_url}" class="doom-media" loading="lazy" />`;
                    card.onclick = () => openDoomModal(post.media_url, 'image');
                } else if (post.type === 'video') {
                    mediaHtml = `<video src="${post.media_url}" class="doom-media" controls preload="none" poster="${post.thumbnail || ''}" loop></video>`;
                    card.onclick = () => openDoomModal(post.media_url, 'video');
                } else if (post.type === 'article') {
                    mediaHtml = `<div style="padding:20px; background:linear-gradient(45deg, #1a0033, #000); border-bottom:1px solid #333;">
                                    <h3 style="margin:0; color:#aa00ff; font-size:18px;">📰 ${post.subreddit}</h3>
                                 </div>`;
                    card.onclick = () => openDoomModal(post.permalink, 'article');
                }
                
                card.innerHTML = `
                    ${mediaHtml}
                    <div class="doom-content">
                        <div class="doom-title">${post.title}</div>
                        <div class="doom-meta">
                            <span>${post.subreddit}</span>
                            <span>${post.score}</span>
                        </div>
                    </div>
                `;
                
                // Append to the shortest column
                let shortestCol = cols[0];
                let minHeight = shortestCol.offsetHeight;
                
                for(let i=1; i<cols.length; i++) {
                    if(cols[i].offsetHeight < minHeight) {
                        shortestCol = cols[i];
                        minHeight = cols[i].offsetHeight;
                    }
                }
                shortestCol.appendChild(card);
            });
            
            setupDoomObserver();
        } else {
            if(!append) container.innerHTML = `<div style="color:red; padding:20px; text-align:center; width:100%;">Failed to load The Hive: ${data.error || 'Unknown error'}</div>`;
        }
    } catch(err) {
        if(!append) container.innerHTML = `<div style="color:red; padding:20px; text-align:center; width:100%;">Connection Error to The Hive</div>`;
    }
    
    isDoomLoading = false;
}

// --- DOOMSCROLL MODAL LOGIC ---
function openDoomModal(url, type) {
    const modal = document.getElementById('doom-modal');
    const content = document.getElementById('doom-modal-content');
    modal.style.display = 'block';
    
    let downloadBtn = '';
    if (type === 'image' || type === 'video') {
        downloadBtn = `<button onclick="window.open('${url}', '_blank')" style="position:absolute; bottom:20px; right:20px; background:#aa00ff; color:white; padding:10px 20px; border:none; border-radius:5px; font-weight:bold; cursor:pointer; box-shadow:0 0 10px rgba(170,0,255,0.5); z-index:10001;">Download</button>`;
    }
    
    if (type === 'article') {
        content.innerHTML = `<iframe src="${url}" style="width:100%; height:100%; border:none; background:#fff;"></iframe>`;
    } else if (type === 'image') {
        content.innerHTML = `<img src="${url}" style="width:100%; height:100%; object-fit:contain; background:#000;" />${downloadBtn}`;
    } else if (type === 'video') {
        content.innerHTML = `<video src="${url}" style="width:100%; height:100%; object-fit:contain; background:#000;" controls autoplay></video>${downloadBtn}`;
    }
}
"""

js = re.sub(r'let isDoomLoading = false;\nlet doomObserver = null;.*function closeDoomModal\(\) {', new_logic + '\n\nfunction closeDoomModal() {', js, flags=re.DOTALL)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)

# 2. Update server.py
with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', encoding='utf-8') as f:
    py = f.read()

server_sub = """@app.route("/api/doomscroll")
def api_doomscroll():
    \"\"\"Fetches and aggregates social media feeds and news for the DoomScroll UI.\"\"\"
    import urllib.request
    import json
    import xml.etree.ElementTree as ET
    import random
    
    page = request.args.get('page', '1')
    memes = []
    articles = []
    
    # 1. Fetch Memes (The Hive)
    try:
        url = "https://meme-api.com/gimme/30"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            for meme in data.get('memes', []):
                if meme.get('nsfw'): continue
                memes.append({
                    "id": meme.get("postLink"),
                    "title": meme.get("title"),
                    "author": meme.get("author"),
                    "subreddit": meme.get("subreddit"),
                    "score": meme.get("ups"),
                    "permalink": meme.get("postLink"),
                    "type": "image",
                    "media_url": meme.get("url"),
                    "thumbnail": None
                })
    except Exception as e:
        print("Meme API Error:", e)

    # 2. Fetch News (RSS) ONLY on Page 1
    if page == '1':
        rss_feeds = [
            "https://techcrunch.com/feed/",
            "http://feeds.bbci.co.uk/news/world/rss.xml"
        ]
        for feed in rss_feeds:
            try:
                req = urllib.request.Request(feed, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as r:
                    tree = ET.fromstring(r.read())
                    for item in tree.findall('.//item')[:15]:
                        title = item.find('title')
                        link = item.find('link')
                        if title is not None and link is not None:
                            articles.append({
                                "id": link.text,
                                "title": title.text,
                                "author": "News",
                                "subreddit": "Breaking News",
                                "score": "📰",
                                "permalink": link.text,
                                "type": "article",
                                "media_url": None,
                                "thumbnail": None
                            })
            except Exception as e:
                print("RSS Error:", e)
"""
py = re.sub(r'@app.route\("/api/doomscroll"\).*?print\("RSS Error:", e\)', server_sub, py, flags=re.DOTALL)

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', 'w', encoding='utf-8') as f:
    f.write(py)
