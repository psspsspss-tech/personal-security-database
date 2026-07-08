import urllib.request
import re
from urllib.parse import urljoin

def deep_scan(url, depth=0):
    if depth > 2:
        return None
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            
            # 1. Look for m3u8 or mp4
            m3u8 = re.findall(r'(https?://[^\s"\'<>]*?\.m3u8[^\s"\'<>]*)', html)
            if m3u8: return m3u8[0]
            
            mp4 = re.findall(r'(https?://[^\s"\'<>]*?\.mp4[^\s"\'<>]*)', html)
            if mp4: return mp4[0]
            
            # 2. Look for iframes
            iframes = re.findall(r'<iframe[^>]+src=["\'](.*?)["\']', html, re.IGNORECASE)
            for iframe_src in iframes:
                full_iframe_url = urljoin(url, iframe_src)
                print(f"Found iframe: {full_iframe_url}")
                result = deep_scan(full_iframe_url, depth + 1)
                if result: return result
                
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

res = deep_scan("https://shuttletv.su/watch/124364?s=4&e=8")
print("DEEP SCAN RESULT:", res)
