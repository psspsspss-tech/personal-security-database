import re

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

# 1. Add hls.js to head
hls_script = '<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>'
if hls_script not in html:
    html = html.replace('</head>', f'  {hls_script}\n</head>')

# 2. Replace media-player-container content
start = html.find('<div id="media-player-container"')
end = html.find('</div>\n  </div>\n</section>', start)

new_container = """<div id="media-player-container" class="player-glow" style="display:none; background:#000; border-radius:12px; border:1px solid #330000; overflow:hidden; position:relative; aspect-ratio:16/9; max-width:900px; margin:0 auto; flex-direction:column;">
      <div id="media-title" style="position:absolute; top:0; left:0; right:0; background:linear-gradient(to bottom, rgba(0,0,0,0.9), transparent); color:#ffdddd; margin:0; padding:15px; text-align:left; font-size:16px; font-weight:bold; z-index:10; pointer-events:none; text-shadow: 0 2px 4px rgba(0,0,0,0.8); transition: opacity 0.3s;">Loading...</div>
      
      <video id="bs-video" style="width:100%; height:100%; object-fit:contain; background:#000; display:none;" playsinline></video>
      <iframe id="bs-iframe" style="width:100%; height:100%; border:none; display:none;" allowfullscreen allow="autoplay; encrypted-media"></iframe>

      <div id="bs-controls" style="position:absolute; bottom:0; left:0; right:0; background:linear-gradient(to top, rgba(0,0,0,0.9), transparent); padding:20px 15px 10px; display:flex; flex-direction:column; gap:10px; transition: opacity 0.3s; opacity: 0;">
        <div style="display:flex; align-items:center; gap:10px; width:100%;">
            <span id="bs-time-current" style="color:#fff; font-size:12px; font-family:monospace; min-width:45px;">00:00</span>
            <input type="range" id="bs-progress" min="0" max="100" value="0" style="flex:1; cursor:pointer; accent-color:#ff0000;" />
            <span id="bs-time-total" style="color:#fff; font-size:12px; font-family:monospace; min-width:45px;">00:00</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; gap:15px; align-items:center;">
                <button id="bs-play-btn" style="background:none; border:none; color:#fff; cursor:pointer; padding:5px;"><svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path id="bs-play-icon" d="M8 5v14l11-7z"/></svg></button>
                <div style="display:flex; align-items:center; gap:5px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="#fff"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
                    <input type="range" id="bs-volume" min="0" max="1" step="0.05" value="1" style="width:80px; accent-color:#ff0000; cursor:pointer;" />
                </div>
            </div>
            <div style="display:flex; gap:15px; align-items:center;">
                <select id="bs-speed" style="background:transparent; color:#fff; border:1px solid #555; border-radius:4px; padding:2px 5px; cursor:pointer; outline:none;">
                    <option value="0.5" style="color:#000;">0.5x</option>
                    <option value="1" style="color:#000;" selected>1.0x</option>
                    <option value="1.5" style="color:#000;">1.5x</option>
                    <option value="2" style="color:#000;">2.0x</option>
                </select>
                <button id="bs-pip-btn" style="background:none; border:none; color:#fff; cursor:pointer; padding:5px;" title="Picture-in-Picture"><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M19 7h-8v6h8V7zm2-4H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16.01H3V4.98h18v14.03z"/></svg></button>
                <button id="bs-fullscreen-btn" style="background:none; border:none; color:#fff; cursor:pointer; padding:5px;"><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg></button>
            </div>
        </div>
      </div>
    </div>"""

html = html[:start] + new_container + html[end:]

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
