import re

# 1. Update index.html
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

vlc_btn = """<button id="bs-vlc-btn" style="background:none; border:1px solid var(--cyan); color:var(--cyan); border-radius:4px; cursor:pointer; font-weight:bold; padding:2px 8px; font-size:12px; margin-right:10px;" title="Copy Stream URL for VLC">VLC</button>
                <select id="hls-quality" """

html = html.replace('<select id="hls-quality" ', vlc_btn)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
    f.write(html)

# 2. Update app.js
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

vlc_logic = """
    document.getElementById('bs-vlc-btn').addEventListener('click', () => {
        let streamUrl = videoElem.src;
        if(currentHls && currentHls.url) streamUrl = currentHls.url;
        
        if(!streamUrl || streamUrl === window.location.href) {
            alert("No active stream found.");
            return;
        }
        
        navigator.clipboard.writeText(streamUrl).then(() => {
            alert("Stream URL copied to clipboard!\\n\\n1. Open your VLC App\\n2. Go to 'Open Network Stream'\\n3. Paste the URL and hit Play!");
        });
    });
}"""

js = js.replace('}\n\ndocument.addEventListener(\'keydown\', (e) => {', vlc_logic + '\n\ndocument.addEventListener(\'keydown\', (e) => {')

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)
