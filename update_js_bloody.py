import re

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    js = f.read()

# Add toggleCinemaMode()
cinema_logic = """
// --- CINEMA MODE ---
let cinemaMode = false;
function toggleCinemaMode() {
    cinemaMode = !cinemaMode;
    const overlay = document.getElementById('cinema-overlay');
    const btn = document.getElementById('btn-cinema');
    if(cinemaMode) {
        overlay.style.display = 'block';
        btn.classList.add('active');
    } else {
        overlay.style.display = 'none';
        btn.classList.remove('active');
    }
}
"""

if 'function toggleCinemaMode()' not in js:
    js += '\n' + cinema_logic

# Update extractAndPlayMedia texts
js = js.replace('Extracting Secure Stream...', 'Initiating Bloody Sweet Stream...')
js = js.replace('Extracting...', 'Injecting...')

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
    f.write(js)
