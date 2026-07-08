import re

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', encoding='utf-8') as f:
    py = f.read()

new_logic = """def api_media_extract():
    \"\"\"Extract raw media stream URLs using yt-dlp and IDM-style deep scanning to bypass ads and tracking.\"\"\"
    import re
    import urllib.request
    from urllib.parse import urljoin
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

        # IDM-style Deep Sniffer Fallback
        def idm_deep_scan(target_url, depth=0):
            if depth > 2:
                return None
            try:
                req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    html = response.read().decode('utf-8', errors='ignore')
                    
                    # Look for m3u8 or mp4
                    m3u8 = re.findall(r'(https?://[^\s"\\'<>]*?\.m3u8[^\s"\\'<>]*)', html)
                    if m3u8: return m3u8[0]
                    
                    mp4 = re.findall(r'(https?://[^\s"\\'<>]*?\.mp4[^\s"\\'<>]*)', html)
                    if mp4: return mp4[0]
                    
                    # Look for iframes
                    iframes = re.findall(r'<iframe[^>]+src=["\\'](.*?)["\\']', html, re.IGNORECASE)
                    for iframe_src in iframes:
                        if iframe_src.startswith('//'): iframe_src = 'https:' + iframe_src
                        full_iframe_url = urljoin(target_url, iframe_src)
                        if 'youtube.com' in full_iframe_url: continue # Handled by yt_dlp
                        result = idm_deep_scan(full_iframe_url, depth + 1)
                        if result: return result
            except:
                pass
            return None

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
                    raise Exception("yt-dlp could not find stream URL")
                    
                return jsonify({
                    "ok": True,
                    "title": title,
                    "stream_url": stream_url
                })
        except Exception as e:
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
            
            # Fire IDM-Style Deep Sniffer!
            sniffed_url = idm_deep_scan(url)
            if sniffed_url:
                return jsonify({
                    "ok": True,
                    "title": "IDM Sniffed Stream",
                    "stream_url": sniffed_url
                })

            # Universal Web Embed Fallback for unsupported URLs and other errors
            return jsonify({
                "ok": True,
                "title": "Universal Web Embed (Direct)",
                "iframe_url": url
            })
            
    except Exception as e:
        # Catch generic exceptions and use universal fallback
        return jsonify({
            "ok": True,
            "title": "Universal Web Embed (Direct)",
            "iframe_url": request.get_json().get("url", "").strip() if request.is_json else ""
        })"""

start = py.find('def api_media_extract():')
end = py.find('@app.route("/api/eventlog")')

py = py[:start] + new_logic + '\n\n\n' + py[end:]

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', 'w', encoding='utf-8') as f:
    f.write(py)
