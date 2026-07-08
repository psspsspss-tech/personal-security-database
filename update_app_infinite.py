import re

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

new_logic = """let isDoomLoading = false;
let doomObserver = null;

function setupDoomObserver() {
    if(doomObserver) doomObserver.disconnect();
    
    doomObserver = new IntersectionObserver((entries) => {
        if(entries[0].isIntersecting) {
            loadDoomScroll(true);
        }
    }, { rootMargin: "800px" }); // Load way before they hit the bottom
    
    const cards = document.querySelectorAll('#doomscroll-container .doom-card');
    if(cards.length > 0) {
        doomObserver.observe(cards[cards.length - 1]);
    }
}

async function loadDoomScroll(append = false) {
    if (isDoomLoading) return;
    isDoomLoading = true;
    
    const container = document.getElementById('doomscroll-container');
    
    if (!append) {
        container.innerHTML = '<div id="doom-loading" style="text-align:center; padding:50px; color:#aa00ff; font-weight:bold; grid-column: 1 / -1;">Connecting to The Hive...</div>';
    } else {
        const loadMsg = document.createElement('div');
        loadMsg.id = 'doom-loading';
        loadMsg.style = "text-align:center; padding:20px; color:#aa00ff; font-weight:bold; grid-column: 1 / -1;";
        loadMsg.innerText = "Pulling more from The Hive...";
        container.appendChild(loadMsg);
    }
    
    try {
        const res = await fetch('/api/doomscroll');
        const data = await res.json();
        
        const loader = document.getElementById('doom-loading');
        if(loader) loader.remove();
        
        if(data.ok && data.posts) {
            data.posts.forEach(post => {
                const card = document.createElement('div');
                card.className = 'doom-card';
                card.style.cursor = 'pointer';
                
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
                container.appendChild(card);
            });
            
            setupDoomObserver();
        } else {
            if(!append) container.innerHTML = `<div style="color:red; padding:20px; grid-column: 1 / -1;">Failed to load The Hive: ${data.error || 'Unknown error'}</div>`;
        }
    } catch(err) {
        if(!append) container.innerHTML = `<div style="color:red; padding:20px; grid-column: 1 / -1;">Connection Error to The Hive</div>`;
    }
    
    isDoomLoading = false;
}"""

js = re.sub(r'async function loadDoomScroll\(\) \{.*?\n\}(?=\n|$)', new_loadDoomScroll, js, flags=re.DOTALL)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)
