import os

filepath = r"C:\Users\acer\Desktop\Security Suite\dashboard\app.js"
with open(filepath, 'r', encoding='utf-8') as f:
    js = f.read()

# Make sure performNativeSearch supports Media Player interception
# Let's search for performNativeSearch and modify it if needed.
# Actually, the user clicks the links rendered by the search, so we need to intercept link clicks inside #search-results-list.

append_js = """
// ==========================================
// V2 MEGA UPDATE LOGIC
// ==========================================

// 1. Secure Media Player
document.getElementById('search-results-list').addEventListener('click', async function(e) {
    const a = e.target.closest('a');
    if (a && a.href) {
        if (a.href.includes('youtube.com') || a.href.includes('youtu.be')) {
            e.preventDefault();
            // Open media player
            document.getElementById('media-modal-overlay').style.display = 'block';
            document.getElementById('media-title').innerText = 'Extracting Secure Stream...';
            const vid = document.getElementById('secure-video-player');
            vid.src = '';
            
            try {
                const res = await fetch(`${API}/media/extract`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: a.href})
                });
                const data = await res.json();
                if (data.ok) {
                    document.getElementById('media-title').innerText = data.title;
                    vid.src = data.stream_url;
                    vid.play();
                } else {
                    document.getElementById('media-title').innerText = 'Error: ' + data.error;
                }
            } catch (err) {
                document.getElementById('media-title').innerText = 'Connection Error';
            }
        }
    }
});

function closeMediaPlayer() {
    document.getElementById('media-modal-overlay').style.display = 'none';
    document.getElementById('secure-video-player').pause();
    document.getElementById('secure-video-player').src = '';
}

// 2. Live Resource Graphs
let resourceChart = null;
function initResourceChart() {
    const ctx = document.getElementById('resourceChart');
    if (!ctx) return;
    
    resourceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'CPU Usage (%)',
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    data: [],
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'RAM Usage (%)',
                    borderColor: '#ff4444',
                    backgroundColor: 'rgba(255, 68, 68, 0.1)',
                    data: [],
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            animation: false,
            scales: {
                x: { display: false },
                y: { min: 0, max: 100, grid: { color: '#333' } }
            },
            plugins: {
                legend: { labels: { color: '#fff' } }
            }
        }
    });
}

async function updateResourceGraph() {
    if (!resourceChart) return;
    try {
        const res = await fetch(`${API}/system`);
        const data = await res.json();
        if (data.ok && data.data && data.data.system) {
            const cpu = data.data.system.cpu_percent;
            const ram = data.data.system.memory_percent;
            
            const now = new Date();
            const timeStr = now.getHours() + ':' + now.getMinutes() + ':' + now.getSeconds();
            
            resourceChart.data.labels.push(timeStr);
            resourceChart.data.datasets[0].data.push(cpu);
            resourceChart.data.datasets[1].data.push(ram);
            
            if (resourceChart.data.labels.length > 20) {
                resourceChart.data.labels.shift();
                resourceChart.data.datasets[0].data.shift();
                resourceChart.data.datasets[1].data.shift();
            }
            resourceChart.update();
        }
    } catch (e) { }
}

// 3. Geo-IP Tracker Map
let geoMap = null;
let geoMarker = null;

function initGeoMap() {
    const mapEl = document.getElementById('geoip-map');
    if (!mapEl) return;
    
    // Initialize map on default coords
    geoMap = L.map('geoip-map').setView([20, 0], 2);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO'
    }).addTo(geoMap);
}

async function trackIP() {
    const ip = document.getElementById('geoip-input').value.trim();
    if (!ip) return;
    
    try {
        const res = await fetch(`http://ip-api.com/json/${ip}`);
        const data = await res.json();
        if (data.status === 'success') {
            if (geoMarker) geoMap.removeLayer(geoMarker);
            geoMarker = L.marker([data.lat, data.lon]).addTo(geoMap)
                .bindPopup(`<b>${data.query}</b><br>${data.city}, ${data.country}<br>ISP: ${data.isp}`).openPopup();
            geoMap.setView([data.lat, data.lon], 10);
        } else {
            alert('IP not found or invalid');
        }
    } catch(err) {
        alert('Map API error');
    }
}

// 4. Dark Web Breach Scanner
async function scanBreach() {
    const email = document.getElementById('breach-email').value.trim();
    if (!email) return;
    
    const resultsDiv = document.getElementById('breach-results');
    resultsDiv.innerHTML = '<span style="color:var(--yellow)">Scanning Dark Web databases...</span>';
    
    try {
        const res = await fetch(`${API}/breach-check`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email: email})
        });
        const data = await res.json();
        
        if (!data.ok) {
            resultsDiv.innerHTML = `<span style="color:var(--danger)">Error: ${data.error}</span>`;
            return;
        }
        
        if (!data.found) {
            resultsDiv.innerHTML = `<span style="color:var(--green)">✅ Excellent! No breaches found for ${email}.</span>`;
        } else {
            let html = `<span style="color:var(--danger); font-size:20px; font-weight:bold;">⚠️ Found in ${data.breach_count} breaches!</span><br><br>`;
            data.breaches.forEach(b => {
                html += `<div style="background:#222; padding:10px; margin-bottom:10px; border-radius:4px; border-left:4px solid var(--danger);">
                    <b>${b.name}</b> (${b.date})<br>
                    <span style="font-size:12px; color:#aaa;">${b.description}...</span>
                </div>`;
            });
            resultsDiv.innerHTML = html;
        }
    } catch(e) {
        resultsDiv.innerHTML = `<span style="color:var(--danger)">Connection Error</span>`;
    }
}

// 5. Password Generator
function generateSecurePassword() {
    const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+~`|}{[]:;?><,./-=";
    let password = "";
    const values = new Uint32Array(20);
    window.crypto.getRandomValues(values);
    for (let i = 0; i < 20; i++) {
        password += charset[values[i] % charset.length];
    }
    document.getElementById('gen-password-display').innerText = password;
}

// Initialize on load
window.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        initResourceChart();
        initGeoMap();
        setInterval(updateResourceGraph, 2000);
    }, 1000);
});

"""

with open(filepath, 'a', encoding='utf-8') as f:
    f.write(append_js)
print("Injected JS modules!")
