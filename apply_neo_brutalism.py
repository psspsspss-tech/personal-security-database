import os
import re

css_path = r"C:\Users\acer\Desktop\Security Suite\dashboard\style.css"
html_path = r"C:\Users\acer\Desktop\Security Suite\dashboard\index.html"

# 1. READ CSS
with open(css_path, 'r', encoding='utf-8') as f:
    css = f.read()

# 2. REPLACE :root
new_root = """:root {
  --bg-primary: #f4f0ea;
  --bg-secondary: #e8e6df;
  --bg-card: #ffffff;
  --bg-card-hover: #fffae6;
  --bg-glass: #ffffff;

  --border: #111111;
  --border-glow: #111111;

  --text-primary: #111111;
  --text-secondary: #333333;
  --text-muted: #555555;

  --cyan: #33ccff; 
  --purple: #ff3366; 
  --green: #00e699;
  --red: #ff3366;
  --orange: #ff6600;
  --yellow: #ffcc00;
  --blue: #33ccff;

  --gradient-main: var(--purple);
  --gradient-green: var(--green);
  --gradient-red: var(--red);

  --radius: 0px;
  --radius-sm: 0px;
  --radius-lg: 0px;

  --shadow: 6px 6px 0px #111111;
  --shadow-glow: 8px 8px 0px var(--purple);

  --font: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Courier New', monospace;
}"""

css = re.sub(r':root\s*\{[^}]+\}', new_root, css, count=1)

# 3. APPEND OVERRIDES
overrides = """
/* --- NEO-BRUTALISM OVERRIDES --- */
body {
    background-image: 
      linear-gradient(to right, rgba(0,0,0,0.05) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(0,0,0,0.05) 1px, transparent 1px) !important;
    background-size: 40px 40px !important;
}

.stat-card, .tool-card, .device-card, .panel, .header, .bottom-nav, .modal-content, .drawer, .alert-banner {
    border: 3px solid var(--border) !important;
    box-shadow: var(--shadow) !important;
    border-radius: 0 !important;
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    transition: 0.1s !important;
}

.stat-card:hover, .tool-card:hover, .device-card:hover {
    transform: translate(-4px, -4px) !important;
    box-shadow: 10px 10px 0px var(--purple) !important;
}

button, .btn-scan, .btn-primary, .nav-tab, .drawer-item {
    border: 3px solid var(--border) !important;
    box-shadow: 4px 4px 0px var(--border) !important;
    border-radius: 0 !important;
    background: var(--yellow) !important;
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    transition: 0.1s !important;
    cursor: pointer !important;
}

button:hover, .btn-scan:hover, .btn-primary:hover, .nav-tab:hover, .drawer-item:hover {
    background: var(--purple) !important;
    color: #fff !important;
    box-shadow: 6px 6px 0px var(--border) !important;
}

button:active, .btn-scan:active, .btn-primary:active, .nav-tab:active, .drawer-item:active {
    transform: translate(4px, 4px) !important;
    box-shadow: 0px 0px 0px transparent !important;
}

input, select, textarea {
    border: 3px solid var(--border) !important;
    border-radius: 0 !important;
    background: #fff !important;
    color: var(--text-primary) !important;
    box-shadow: 4px 4px 0px rgba(0,0,0,0.1) !important;
}

.header-left .logo svg path:first-child {
    fill: var(--text-primary) !important;
    stroke: none !important;
}
.header-left .logo svg path:last-child {
    fill: none !important;
    stroke: var(--bg-card) !important;
}

/* Fix SVG text legibility */
.score-ring-mini circle:first-child, .score-ring circle:first-child {
    stroke: #ccc !important;
}
.score-ring-mini circle:last-child, .score-ring circle:last-child {
    stroke: var(--green) !important;
}
#score-value-mini, .score-value-mini, .score-value {
    fill: var(--text-primary) !important;
    color: var(--text-primary) !important;
}
.logo-title {
    color: var(--text-primary) !important;
    font-weight: 800 !important;
}
.nav-tab.active, .drawer-item.active {
    background: var(--green) !important;
    color: var(--text-primary) !important;
}

h1, h2, h3, h4, .score-label {
    text-transform: uppercase !important;
    letter-spacing: -1px !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
}

.status-pill {
    background: var(--green) !important;
    border: 3px solid var(--border) !important;
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    box-shadow: 4px 4px 0px var(--border) !important;
}

.pulse-dot {
    background: #fff !important;
    border: 2px solid var(--border) !important;
}

/* Darken icons to be visible on light cards */
svg {
    stroke: var(--text-primary);
}
.icon-blue, .icon-purple, .icon-green, .icon-orange {
    background: #fff !important;
    border: 2px solid var(--border) !important;
    box-shadow: 2px 2px 0px var(--border) !important;
}
.stat-card-icon { color: var(--text-primary) !important; }

/* Fix WebSSH terminal visibility on light theme */
#terminal-container {
    padding: 10px;
    border: 3px solid var(--border) !important;
    background: #000 !important; /* Terminal needs to stay dark */
    box-shadow: var(--shadow) !important;
}
.matrix-text {
    color: #00ff00 !important;
    background: #000 !important;
    padding: 10px;
    border: 3px solid var(--border) !important;
}

/* Override existing gradients */
.gradient-text {
    background: none !important;
    color: var(--text-primary) !important;
    -webkit-text-fill-color: var(--text-primary) !important;
}
"""

if "/* --- NEO-BRUTALISM OVERRIDES --- */" not in css:
    css += "\n" + overrides

with open(css_path, 'w', encoding='utf-8') as f:
    f.write(css)

# 4. UPDATE HTML
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Change fonts
html = html.replace('family=Inter:wght@300;400;500;600;700;800', 'family=Space+Grotesk:wght@400;500;700')
# Bump css/js versions
html = re.sub(r'style\.css\?v=\d+', 'style.css?v=153', html)
html = re.sub(r'app\.js\?v=\d+', 'app.js?v=153', html)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("Neo-Brutalism applied successfully.")
