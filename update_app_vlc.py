import re

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

# Replace extractAndPlayMedia completely
start = js.find('async function extractAndPlayMedia() {')
end = js.find('// --- CINEMA MODE ---')

if start != -1 and end != -1:
    js = js[:start] + js[end:]

advanced_logic = """
// --- ADVANCED PLAYER LOGIC ---
let currentHls = null;
const videoElem = document.getElementById('bs-video');
const iframeElem = document.getElementById('bs-iframe');
const controlsElem = document.getElementById('bs-controls');

function setupAdvancedPlayer(url, isRawStream) {
    videoElem.style.display = 'none';
    iframeElem.style.display = 'none';
    if(controlsElem) controlsElem.style.opacity = '0';
    
    if (currentHls) {
        currentHls.destroy();
        currentHls = null;
    }

    if (isRawStream) {
        videoElem.style.display = 'block';
        if(controlsElem) controlsElem.style.opacity = '1';
        
        if (url.includes('.m3u8')) {
            if (window.Hls && Hls.isSupported()) {
                currentHls = new Hls();
                currentHls.loadSource(url);
                currentHls.attachMedia(videoElem);
                currentHls.on(Hls.Events.MANIFEST_PARSED, function() {
                    videoElem.play();
                    updatePlayIcon(true);
                });
            } else if (videoElem.canPlayType('application/vnd.apple.mpegurl')) {
                videoElem.src = url;
                videoElem.addEventListener('loadedmetadata', function() {
                    videoElem.play();
                    updatePlayIcon(true);
                });
            }
        } else {
            videoElem.src = url;
            videoElem.play();
            updatePlayIcon(true);
        }
    } else {
        iframeElem.src = url;
        iframeElem.style.display = 'block';
    }
}

function formatTime(seconds) {
    if (isNaN(seconds)) return "00:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
}

function updatePlayIcon(playing) {
    const path = document.getElementById('bs-play-icon');
    if(!path) return;
    if (playing) {
        path.setAttribute('d', 'M6 19h4V5H6v14zm8-14v14h4V5h-4z');
    } else {
        path.setAttribute('d', 'M8 5v14l11-7z');
    }
}

if(videoElem) {
    videoElem.addEventListener('timeupdate', () => {
        document.getElementById('bs-time-current').innerText = formatTime(videoElem.currentTime);
        if(videoElem.duration) {
            const percent = (videoElem.currentTime / videoElem.duration) * 100;
            document.getElementById('bs-progress').value = percent;
        }
    });

    videoElem.addEventListener('loadedmetadata', () => {
        document.getElementById('bs-time-total').innerText = formatTime(videoElem.duration);
    });

    videoElem.addEventListener('play', () => updatePlayIcon(true));
    videoElem.addEventListener('pause', () => updatePlayIcon(false));
}

if(document.getElementById('bs-play-btn')) {
    document.getElementById('bs-play-btn').addEventListener('click', () => {
        if (videoElem.paused) videoElem.play();
        else videoElem.pause();
    });

    document.getElementById('bs-progress').addEventListener('input', (e) => {
        if(videoElem.duration) {
            videoElem.currentTime = (e.target.value / 100) * videoElem.duration;
        }
    });

    document.getElementById('bs-volume').addEventListener('input', (e) => {
        videoElem.volume = e.target.value;
    });

    document.getElementById('bs-speed').addEventListener('change', (e) => {
        videoElem.playbackRate = parseFloat(e.target.value);
    });

    document.getElementById('bs-pip-btn').addEventListener('click', async () => {
        if (document.pictureInPictureElement) {
            await document.exitPictureInPicture();
        } else if (videoElem.readyState !== 0) {
            await videoElem.requestPictureInPicture();
        }
    });

    document.getElementById('bs-fullscreen-btn').addEventListener('click', () => {
        const container = document.getElementById('media-player-container');
        if (!document.fullscreenElement) {
            container.requestFullscreen().catch(err => console.log(err));
        } else {
            document.exitFullscreen();
        }
    });
}

document.addEventListener('keydown', (e) => {
    // Only if panel-media is active and we are not typing in input
    if(document.getElementById('panel-media').style.display !== 'none' && document.activeElement.tagName !== 'INPUT') {
        if(e.code === 'Space') {
            e.preventDefault();
            if (videoElem.paused) videoElem.play();
            else videoElem.pause();
        } else if (e.code === 'ArrowRight') {
            videoElem.currentTime += 5;
        } else if (e.code === 'ArrowLeft') {
            videoElem.currentTime -= 5;
        } else if (e.code === 'KeyF') {
            const container = document.getElementById('media-player-container');
            if (!document.fullscreenElement) container.requestFullscreen();
            else document.exitFullscreen();
        }
    }
});

async function extractAndPlayMedia() {
    const urlInput = document.getElementById('media-url-input');
    const url = urlInput.value.trim();
    if (!url) return;

    const btn = document.getElementById('btn-play-media');
    const titleElem = document.getElementById('media-title');
    const container = document.getElementById('media-player-container');

    btn.disabled = true;
    btn.innerText = "Initiating Bloody Sweet Stream...";
    
    container.style.display = 'flex';
    titleElem.innerText = "Sniffing stream: " + url + " ...";
    setupAdvancedPlayer('', false); // clear

    try {
        const res = await fetch('http://127.0.0.1:5000/api/media/extract', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        const data = await res.json();
        
        if (data.ok) {
            titleElem.innerText = data.title;
            const targetUrl = data.stream_url || data.iframe_url;
            setupAdvancedPlayer(targetUrl, !!data.stream_url);
        } else {
            titleElem.innerText = "Extraction Failed: " + (data.error || "Unknown Error");
        }
    } catch (err) {
        titleElem.innerText = "Connection Error";
    }

    btn.disabled = false;
    btn.innerText = "Play";
}

"""

js += advanced_logic

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)
