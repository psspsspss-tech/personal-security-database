import urllib.request
import json

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', encoding='utf-8') as f:
    py = f.read()

doomscroll_logic = """
@app.route("/api/doomscroll")
def api_doomscroll():
    \"\"\"Fetches and aggregates social media feeds for the DoomScroll UI.\"\"\"
    import urllib.request
    import json
    import random
    
    # In the future, we can add RSS parsing for X/FB/Tumblr here.
    # For now, we will aggregate a massive feed from Reddit's media-heavy communities.
    subreddits = "memes+funny+pics+videos+aww+interestingasfuck+nextfuckinglevel"
    url = f"https://www.reddit.com/r/{subreddits}/hot.json?limit=100"
    
    posts = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 DoomScroll/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            for child in data.get('data', {}).get('children', []):
                post_data = child.get('data', {})
                if post_data.get('over_18'): continue # Skip NSFW
                
                post = {
                    "id": post_data.get("id"),
                    "title": post_data.get("title"),
                    "author": post_data.get("author"),
                    "subreddit": post_data.get("subreddit_name_prefixed"),
                    "score": post_data.get("score"),
                    "permalink": f"https://reddit.com{post_data.get('permalink')}",
                    "type": "link",
                    "media_url": None,
                    "thumbnail": None
                }
                
                # Check for video
                if post_data.get("is_video"):
                    post["type"] = "video"
                    post["media_url"] = post_data.get("secure_media", {}).get("reddit_video", {}).get("fallback_url")
                    post["thumbnail"] = post_data.get("thumbnail")
                # Check for image
                elif post_data.get("url", "").endswith((".jpg", ".png", ".gif", ".jpeg")):
                    post["type"] = "image"
                    post["media_url"] = post_data.get("url")
                # Skip text posts or unsupported links
                else:
                    continue
                    
                if post["media_url"]:
                    posts.append(post)
                    
        random.shuffle(posts)
        return jsonify({"ok": True, "posts": posts})
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
"""

start = py.find('@app.route("/api/eventlog")')
py = py[:start] + doomscroll_logic + '\n\n' + py[start:]

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', 'w', encoding='utf-8') as f:
    f.write(py)
