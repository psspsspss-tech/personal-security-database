import re

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', encoding='utf-8') as f:
    py = f.read()

new_logic = """def api_media_extract():
    \"\"\"Extract raw media stream URLs using yt-dlp to bypass ads and tracking.\"\"\"
    import re
    try:
        import yt_dlp
        from yt_dlp.utils import DownloadError
        body = request.get_json()
        url = body.get("url", "").strip()
        if not url:
            return jsonify({"ok": False, "error": "URL required"}), 400

        # Helper to extract youtube ID
        def get_yt_id(url):
            m = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11}).*', url)
            return m.group(1) if m else None

        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'simulate': True,
            'forceurl': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get('url')
                title = info.get('title', 'Video')
                
                if not stream_url:
                    return jsonify({"ok": False, "error": "Could not extract stream URL"}), 400
                    
                return jsonify({
                    "ok": True,
                    "title": title,
                    "stream_url": stream_url
                })
        except DownloadError as e:
            err_msg = str(e).lower()
            # If 429 Too Many Requests occurs and it's YouTube, use fallback embed
            if '429' in err_msg or 'too many requests' in err_msg or 'sign in to confirm you' in err_msg:
                yt_id = get_yt_id(url)
                if yt_id:
                    iframe_url = f"https://www.youtube-nocookie.com/embed/{yt_id}?autoplay=1&dnt=1"
                    return jsonify({
                        "ok": True,
                        "title": "Secure Privacy Stream (YouTube)",
                        "iframe_url": iframe_url
                    })
            # Otherwise re-raise
            raise e
            
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500"""

start = py.find('def api_media_extract():')
end = py.find('@app.route("/api/eventlog")')

py = py[:start] + new_logic + '\n\n\n' + py[end:]

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', 'w', encoding='utf-8') as f:
    f.write(py)
