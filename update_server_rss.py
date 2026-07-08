import re

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', encoding='utf-8') as f:
    py = f.read()

new_logic = """@app.route("/api/doomscroll")
def api_doomscroll():
    \"\"\"Fetches and aggregates social media feeds and news for the DoomScroll UI.\"\"\"
    import urllib.request
    import json
    import xml.etree.ElementTree as ET
    import random
    
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

    # 2. Fetch News (RSS)
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
            
    # 3. The Beautiful Algorithm (Interleave memes and news)
    # We want a healthy mix: 2 memes, then 1 news article
    random.shuffle(memes)
    random.shuffle(articles)
    
    final_feed = []
    while memes or articles:
        if memes: final_feed.append(memes.pop(0))
        if memes: final_feed.append(memes.pop(0))
        if articles: final_feed.append(articles.pop(0))

    if not final_feed:
        return jsonify({"ok": False, "error": "All aggregation sources failed."}), 500
        
    return jsonify({"ok": True, "posts": final_feed})
"""

# Replace the old logic
start = py.find('@app.route("/api/doomscroll")')
end = py.find('@app.route("/api/eventlog")')

py = py[:start] + new_logic + '\n\n' + py[end:]

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', 'w', encoding='utf-8') as f:
    f.write(py)
