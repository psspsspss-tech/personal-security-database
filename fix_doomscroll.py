import re

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', encoding='utf-8') as f:
    py = f.read()

new_logic = """@app.route("/api/doomscroll")
def api_doomscroll():
    \"\"\"Fetches and aggregates social media feeds for the DoomScroll UI.\"\"\"
    import urllib.request
    import json
    import random
    
    posts = []
    
    # Due to Reddit's aggressive API blocking (403), we use a public meme API
    try:
        url = "https://meme-api.com/gimme/50"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            for meme in data.get('memes', []):
                if meme.get('nsfw'): continue
                
                posts.append({
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

    if not posts:
        return jsonify({"ok": False, "error": "All aggregation sources blocked."}), 500
        
    random.shuffle(posts)
    return jsonify({"ok": True, "posts": posts})
"""

# Replace the old logic
start = py.find('@app.route("/api/doomscroll")')
end = py.find('@app.route("/api/eventlog")')

py = py[:start] + new_logic + '\n\n' + py[end:]

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', 'w', encoding='utf-8') as f:
    f.write(py)
