import re

# 1. Update index.html
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

# Add Engine Selector to video player
engine_ui = """<select id="engine-selector" style="background:none; border:1px solid #fff; color:#fff; border-radius:4px; font-weight:bold; padding:2px; font-size:12px; margin-right:10px;">
                    <option value="alpha" style="color:#000;">Alpha</option>
                    <option value="beta" style="color:#000;">Beta</option>
                </select>
                <button id="bs-cast-btn" """
html = html.replace('<button id="bs-cast-btn" ', engine_ui)

# Add Device Radar to sidebar
sidebar_li = """<li onclick="openRadarModal()">📡 Device Radar</li>
                <li onclick="alert('Module loading...')">"""
html = html.replace("<li onclick=\"alert('Module loading...')\">", sidebar_li, 1)

# Add Radar Modal
radar_modal = """
<div id="radar-modal" class="modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:9999; justify-content:center; align-items:center;">
  <div style="background:rgba(10,10,15,0.95); border:1px solid var(--cyan); border-radius:8px; padding:20px; width:600px; color:#fff; box-shadow: 0 0 20px var(--cyan);">
     <h2 style="margin-top:0; border-bottom:1px solid var(--cyan); padding-bottom:10px; display:flex; justify-content:space-between;">
        📡 Network Sonar 
        <button onclick="runRadarScan()" style="background:var(--cyan); color:#000; padding:5px 15px; border:none; border-radius:4px; cursor:pointer; font-weight:bold; font-size:14px;">SCAN</button>
     </h2>
     <div id="radar-results" style="margin-top:20px; height:350px; overflow-y:auto; font-family:monospace; background:#000; padding:10px; border-radius:4px;">
        Click SCAN to initiate an ARP sweep on the local subnet...
     </div>
     <button onclick="document.getElementById('radar-modal').style.display='none'" style="margin-top:20px; width:100%; padding:10px; background:#333; color:#fff; border:none; cursor:pointer; border-radius:4px;">CLOSE</button>
  </div>
</div>
</body>
"""
html = html.replace('</body>', radar_modal)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
    f.write(html)

# 2. Update app.js
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

# Add Radar Logic
radar_js = """
function openRadarModal() {
    document.getElementById('radar-modal').style.display = 'flex';
}

async function runRadarScan() {
    const resDiv = document.getElementById('radar-results');
    resDiv.innerHTML = "<span style='color:var(--cyan);'>Initiating ARP sweep... Please wait.</span>";
    try {
        const res = await fetch('/api/radar/scan');
        const data = await res.json();
        if(data.ok) {
            let html = "<table style='width:100%; text-align:left; border-collapse:collapse;'>";
            html += "<tr style='color:var(--cyan); border-bottom:1px solid #333;'><th>IP Address</th><th>MAC Address</th><th>Type</th></tr>";
            data.devices.forEach(d => {
                html += `<tr><td style='padding:5px 0;'>${d.ip}</td><td>${d.mac}</td><td>${d.type}</td></tr>`;
            });
            html += "</table>";
            resDiv.innerHTML = html;
        } else {
            resDiv.innerHTML = "<span style='color:red;'>Scan failed: " + data.error + "</span>";
        }
    } catch(e) {
        resDiv.innerHTML = "<span style='color:red;'>Error: " + e.message + "</span>";
    }
}
"""

js = radar_js + "\n" + js

# Add Engine Logic
engine_js = """
    let currentEngine = 'alpha';
    let baseRawUrl = '';
    
    document.getElementById('engine-selector').addEventListener('change', (e) => {
        currentEngine = e.target.value;
        if(videoElem.src && !videoElem.src.includes('blob:')) {
            if(!baseRawUrl) {
                baseRawUrl = videoElem.src;
            } else if(videoElem.src.includes('/api/media/transcode/live')) {
                const urlParams = new URLSearchParams(videoElem.src.substring(videoElem.src.indexOf('?')));
                baseRawUrl = urlParams.get('url');
            }
            
            if(currentEngine === 'beta') {
                videoElem.src = `/api/media/transcode/live?url=${encodeURIComponent(baseRawUrl)}&ss=${videoElem.currentTime}`;
            } else {
                videoElem.src = baseRawUrl;
            }
            videoElem.play();
        }
    });
"""

js = js.replace("document.getElementById('bs-cast-btn').addEventListener('click', async () => {", engine_js + "\n    document.getElementById('bs-cast-btn').addEventListener('click', async () => {")

# Patch progress bar logic
progress_logic = """
        progressBarContainer.addEventListener('click', (e) => {
            const rect = progressBarContainer.getBoundingClientRect();
            const pos = (e.clientX - rect.left) / rect.width;
            if (currentHls) {
                const newTime = pos * videoElem.duration;
                videoElem.currentTime = newTime;
                currentHls.startLoad(newTime);
            } else {
                const newTime = pos * videoElem.duration;
                if(currentEngine === 'beta') {
                    if(!baseRawUrl) baseRawUrl = videoElem.src;
                    if(baseRawUrl.includes('/api/media/transcode/live')) {
                        const urlParams = new URLSearchParams(baseRawUrl.substring(baseRawUrl.indexOf('?')));
                        baseRawUrl = urlParams.get('url');
                    }
                    videoElem.src = `/api/media/transcode/live?url=${encodeURIComponent(baseRawUrl)}&ss=${newTime}`;
                    videoElem.play();
                } else {
                    videoElem.currentTime = newTime;
                }
            }
        });
"""

# Regex replace progress bar
js = re.sub(r'progressBarContainer\.addEventListener\(\'click\', \(e\) => \{.*?\}\);', progress_logic.strip(), js, flags=re.DOTALL)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)
