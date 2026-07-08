import re

# 1. Update app.js (Fix onclick arguments and replace openDoomModal)
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

# Fix the arguments passed to openDoomModal
js = js.replace("() => openDoomModal(post.media_url, 'image');", "() => openDoomModal(post.media_url, 'image', post.permalink);")
js = js.replace("() => openDoomModal(post.media_url, 'video');", "() => openDoomModal(post.media_url, 'video', post.permalink);")
js = js.replace("() => openDoomModal(post.permalink, 'article');", "() => openDoomModal(post.permalink, 'article', post.permalink);")

new_modal_logic = """function openDoomModal(url, type, permalink) {
    const modal = document.getElementById('doom-modal');
    const content = document.getElementById('doom-modal-content');
    modal.style.display = 'block';
    
    let downloadBtn = '';
    if (type === 'image' || type === 'video') {
        downloadBtn = `<button id="doom-dl-btn" onclick="forceDoomDownload('${url}', '${type}')" style="position:absolute; bottom:20px; right:20px; background:var(--primary); color:#000; padding:10px 20px; border:none; border-radius:5px; font-weight:bold; cursor:pointer; box-shadow:0 0 10px rgba(0,255,204,0.5); z-index:10001;">Download</button>`;
    }
    
    // Create Flexbox Split Screen
    content.innerHTML = `
      <div id="doom-modal-media" style="flex:7; position:relative; display:flex; align-items:center; justify-content:center; background:#000; height:100%; overflow:hidden;"></div>
      <div id="doom-modal-comments" style="flex:3; background:var(--bg); border-left:1px solid var(--border); overflow-y:auto; padding:20px; color:var(--text); display:flex; flex-direction:column; gap:15px; height:100%;">
          <div style="color:var(--primary); font-weight:bold; text-align:center; padding:20px;">Fetching live comments...</div>
      </div>
    `;
    
    const mediaSide = document.getElementById('doom-modal-media');
    
    if (type === 'article') {
        mediaSide.innerHTML = `<iframe src="${url}" style="width:100%; height:100%; border:none; background:#fff;"></iframe>`;
    } else if (type === 'image') {
        mediaSide.innerHTML = `<img src="${url}" style="width:100%; height:100%; object-fit:contain; background:#000;" />${downloadBtn}`;
    } else if (type === 'video') {
        mediaSide.innerHTML = `<video src="${url}" style="width:100%; height:100%; object-fit:contain; background:#000;" controls autoplay></video>${downloadBtn}`;
    }
    
    // Fetch comments from backend proxy
    if(permalink) {
        fetch(`/api/comments?url=${encodeURIComponent(permalink)}`)
            .then(r => r.json())
            .then(data => {
                const commentSide = document.getElementById('doom-modal-comments');
                if(!commentSide) return;
                commentSide.innerHTML = '<h3 style="margin:0 0 10px 0; color:var(--primary); border-bottom:1px solid var(--border); padding-bottom:10px; flex-shrink:0;">Comments</h3>';
                if(data.ok && data.comments && data.comments.length > 0) {
                    data.comments.forEach(c => {
                        commentSide.innerHTML += `
                            <div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:8px; font-size:13px; flex-shrink:0;">
                                <div style="display:flex; justify-content:space-between; color:var(--primary); font-weight:bold; margin-bottom:5px;">
                                    <span>👤 ${c.author}</span>
                                    <span>👍 ${c.score}</span>
                                </div>
                                <div style="color:var(--text); line-height:1.4;">${c.body}</div>
                            </div>
                        `;
                    });
                } else {
                    commentSide.innerHTML += '<div style="color:#888;">No comments found.</div>';
                }
            })
            .catch(err => {
                const commentSide = document.getElementById('doom-modal-comments');
                if(commentSide) commentSide.innerHTML = '<div style="color:red;">Failed to load comments.</div>';
            });
    }
}"""

js = re.sub(r'function openDoomModal\(url, type\) \{.*?(?=function closeDoomModal)', new_modal_logic + '\n\n', js, flags=re.DOTALL)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)

# 2. Update server.py
with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', encoding='utf-8') as f:
    py = f.read()

comments_endpoint = """@app.route("/api/comments")
def api_comments():
    \"\"\"Backend proxy to fetch real Reddit comments for a post.\"\"\"
    import urllib.request
    import json
    url = request.args.get('url')
    if not url: return jsonify({"ok": False, "error": "No url provided"}), 400
    
    if 'redd.it' in url or 'reddit.com' in url:
        try:
            req = urllib.request.Request(url + '.json', headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode('utf-8'))
                comments = []
                # Reddit's json structure: data[1] contains the comments tree
                for child in data[1]['data']['children'][:20]:
                    cdata = child.get('data', {})
                    if cdata.get('body') and cdata.get('author') and cdata.get('author') != 'AutoModerator':
                        comments.append({
                            "author": cdata['author'],
                            "body": cdata['body'],
                            "score": cdata.get('score', 0)
                        })
                return jsonify({"ok": True, "comments": comments})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "comments": []})

@app.route("/api/doomscroll")"""

py = py.replace('@app.route("/api/doomscroll")', comments_endpoint)

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', 'w', encoding='utf-8') as f:
    f.write(py)

# 3. Update index.html modal container
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

html = html.replace(
    '<div id="doom-modal-content" style="width:100%; height:100%; display:flex; justify-content:center; align-items:center;"></div>',
    '<div id="doom-modal-content" style="width:100%; height:100%; display:flex; flex-direction:row;"></div>'
)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
