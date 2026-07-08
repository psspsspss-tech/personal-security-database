with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

doom_js = """
// --- DOOMSCROLL LOGIC ---
async function loadDoomScroll() {
    const container = document.getElementById('doomscroll-container');
    container.innerHTML = '<div style="text-align:center; padding:50px; color:#aa00ff; font-weight:bold; grid-column: 1 / -1;">Connecting to The Hive...</div>';
    
    try {
        const res = await fetch('/api/doomscroll');
        const data = await res.json();
        if(data.ok && data.posts) {
            container.innerHTML = '';
            data.posts.forEach(post => {
                const card = document.createElement('div');
                card.className = 'doom-card';
                
                let mediaHtml = '';
                if(post.type === 'image') {
                    mediaHtml = `<img src="${post.media_url}" class="doom-media" loading="lazy" onclick="window.open('${post.permalink}', '_blank')" style="cursor:pointer;" />`;
                } else if (post.type === 'video') {
                    mediaHtml = `<video src="${post.media_url}" class="doom-media" controls preload="none" poster="${post.thumbnail || ''}" loop></video>`;
                }
                
                card.innerHTML = `
                    ${mediaHtml}
                    <div class="doom-content">
                        <div class="doom-title">${post.title}</div>
                        <div class="doom-meta">
                            <span>${post.subreddit}</span>
                            <span>👍 ${post.score}</span>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
        } else {
            container.innerHTML = `<div style="color:red; padding:20px; grid-column: 1 / -1;">Failed to load The Hive: ${data.error || 'Unknown error'}</div>`;
        }
    } catch(err) {
        container.innerHTML = `<div style="color:red; padding:20px; grid-column: 1 / -1;">Connection Error to The Hive</div>`;
    }
}
"""

if 'async function loadDoomScroll()' not in js:
    js += '\n' + doom_js

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)
