import re

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

# Replace the forceDoomDownload function with native share API
new_dl_logic = """async function forceDoomDownload(url, type) {
    const btn = document.getElementById('doom-dl-btn');
    if(btn) { btn.innerText = "Processing..."; btn.style.opacity = "0.7"; }
    
    try {
        // Fetch the raw media data
        let proxyUrl = `/api/download?url=${encodeURIComponent(url)}`;
        const res = await fetch(proxyUrl);
        const blob = await res.blob();
        
        let ext = type === 'video' ? 'mp4' : 'jpg';
        let filename = `DoomScroll_${Date.now()}.${ext}`;
        const file = new File([blob], filename, { type: blob.type });

        // Trigger native mobile Share Sheet (allows direct "Save to Photos")
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
            await navigator.share({
                files: [file],
                title: 'Save to Photos',
            });
        } else {
            // Fallback for desktop browsers
            const blobUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(blobUrl);
        }
    } catch(e) {
        console.error("Share failed", e);
        // Absolute fallback
        let ext = type === 'video' ? 'mp4' : 'jpg';
        let filename = `DoomScroll_${Date.now()}.${ext}`;
        let proxyUrl = `/api/download?url=${encodeURIComponent(url)}&filename=${filename}`;
        const a = document.createElement('a');
        a.href = proxyUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }
    
    if(btn) { btn.innerText = "Save to Photos"; btn.style.opacity = "1"; }
}"""

js = re.sub(r'async function forceDoomDownload\(url, type\) \{.*?(?=function openDoomModal)', new_dl_logic + '\n\n', js, flags=re.DOTALL)

# Update the button text from Download to Save to Photos
js = js.replace('z-index:10001;">Download</button>', 'z-index:10001;">Save to Photos</button>')

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)
