import re

# 1. Update index.html
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    html = f.read()

cast_btn = """<button id="bs-cast-btn" style="background:none; border:1px solid #fff; color:#fff; border-radius:4px; cursor:pointer; font-weight:bold; padding:2px 8px; font-size:12px; margin-right:10px; transition:0.2s;" title="Cast to Smart TV">CAST</button>
                <button id="bs-vlc-btn" """

html = html.replace('<button id="bs-vlc-btn" ', cast_btn)

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', 'w', encoding='utf-8') as f:
    f.write(html)

# 2. Update app.js
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

cast_logic = """
    const castBtn = document.getElementById('bs-cast-btn');
    if(castBtn) {
        castBtn.addEventListener('click', async () => {
            let streamUrl = videoElem.src;
            if(currentHls && currentHls.url) streamUrl = currentHls.url;
            
            if(!streamUrl || streamUrl === window.location.href) {
                alert("No active stream to cast.");
                return;
            }

            castBtn.innerText = "SCANNING...";

            try {
                const hostIp = window.location.hostname;
                const res = await fetch(`http://${hostIp}:8766/cast/devices`);
                const data = await res.json();
                
                if(!data.ok || data.devices.length === 0) {
                    alert("No Smart TVs or Chromecasts found on your Wi-Fi network.\\nEnsure your TV is turned on and connected to the same network.");
                    castBtn.innerText = "CAST";
                    return;
                }

                let deviceNames = data.devices.map((d, i) => `${i+1}. ${d.name} (${d.type.toUpperCase()})`).join('\\n');
                let choice = prompt(`Discovered Devices:\\n\\n${deviceNames}\\n\\nEnter the number to cast to:`);
                
                if(choice) {
                    let idx = parseInt(choice) - 1;
                    if(data.devices[idx]) {
                        const dev = data.devices[idx];
                        castBtn.innerText = "CONNECTING...";
                        if(streamUrl.startsWith('/play/')) {
                            streamUrl = `http://${hostIp}:8766${streamUrl}`;
                        }
                        
                        const castRes = await fetch(`http://${hostIp}:8766/cast/play?deviceId=${encodeURIComponent(dev.id)}&type=${dev.type}&streamUrl=${encodeURIComponent(streamUrl)}&title=P2P+Dashboard+Stream`);
                        const castData = await castRes.json();
                        if(castData.ok) {
                            alert(`Successfully beamed to ${dev.name}!\\nEnjoy the 5.1 surround sound.`);
                        } else {
                            alert("Cast failed: " + castData.error);
                        }
                    }
                }
            } catch(e) {
                alert("Error scanning for devices.");
                console.error(e);
            }
            castBtn.innerText = "CAST";
        });
    }
"""

js = js.replace("document.getElementById('bs-vlc-btn').addEventListener('click', () => {", cast_logic + "\n    document.getElementById('bs-vlc-btn').addEventListener('click', () => {")

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)
