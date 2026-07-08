import re

html_path = r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Inject IDs to drawer items
drawer_replaces = {
    'onclick="showTab(\'ports\');': 'id="drawer-tab-ports" onclick="showTab(\'ports\');',
    'onclick="showTab(\'alerts\');': 'id="drawer-tab-alerts" onclick="showTab(\'alerts\');',
    'onclick="showTab(\'breach\');': 'id="drawer-tab-breach" onclick="showTab(\'breach\');',
    'onclick="showTab(\'bluetooth\');': 'id="drawer-tab-bluetooth" onclick="showTab(\'bluetooth\');',
    'onclick="showTab(\'eventlog\');': 'id="drawer-tab-eventlog" onclick="showTab(\'eventlog\');',
    'onclick="showTab(\'dns\');': 'id="drawer-tab-dns" onclick="showTab(\'dns\');',
    'onclick="showTab(\'processes\');': 'id="drawer-tab-processes" onclick="showTab(\'processes\');',
    'onclick="showTab(\'connect\');': 'id="drawer-tab-connect" onclick="showTab(\'connect\');',
    'onclick="showTab(\'setup\');': 'id="drawer-tab-setup" onclick="showTab(\'setup\');',
}
for old, new in drawer_replaces.items():
    if old in html and new not in html:
        html = html.replace(old, new)

# 2. Add Casino and Radio drawer items right before Setup
casino_drawer = """    <button class="drawer-item" id="drawer-tab-casino" onclick="showTab('casino'); closeDrawer()">
      <div class="drawer-icon" style="color:var(--purple)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3 6 6 1-4 4 1 6-6-3-6 3 1-6-4-4 6-1 3-6z"/></svg></div>
      <span>Cyber Casino</span>
      <span class="badge" id="casino-badge" style="background:var(--cyan); color:#000;">New</span>
    </button>

    <button class="drawer-item" id="drawer-tab-radio" onclick="showTab('radio'); closeDrawer()">
      <div class="drawer-icon" style="color:#ff00ea"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9M7.7 16.3c-2.3-2.3-2.3-6.2 0-8.5m1.4 7.1c-1.6-1.6-1.6-4.1 0-5.7m1.4 4.3c-.8-.8-.8-2.1 0-2.9M12 12a1 1 0 1 1-1-1 1 1 0 0 1 1 1zM19.1 4.9C23 8.8 23 15.2 19.1 19.1M16.3 7.7c2.3 2.3 2.3 6.2 0 8.5m-1.4-7.1c1.6 1.6 1.6 4.1 0 5.7m-1.4-4.3c.8.8.8 2.1 0 2.9"/></svg></div>
      <span>Radio &amp; Comm</span>
    </button>
"""

if 'id="drawer-tab-casino"' not in html:
    html = html.replace('    <button class="drawer-item" id="drawer-tab-setup"', casino_drawer + '\n    <button class="drawer-item" id="drawer-tab-setup"')

# 3. Add panel-radio and panel-casino HTML after panel-setup
panels_html = """
  <!-- ──────────────────────────────────────── RADIO & COMM PANEL ──────────────────────────────────────── -->
  <section id="panel-radio" class="panel" style="padding-bottom: 120px;">
    <div class="panel-toolbar">
      <div class="panel-title-group">
        <h1 class="panel-heading">Radio &amp; Communications</h1>
        <span class="panel-sub">Offline P2P Walkie-Talkie &amp; FM Chiptune Synth Player</span>
      </div>
    </div>

    <div class="dns-grid">
      <!-- WALKIE TALKIE PANEL -->
      <div class="card" style="border-color: #ff00ea; box-shadow: 0 0 15px rgba(255, 0, 234, 0.1);">
        <div class="card-header" style="background: rgba(255,0,234,0.03); display:flex; justify-content:space-between; align-items:center;">
          <h2 class="card-title" style="color: #ff00ea; display:flex; align-items:center; gap:8px;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v6m-4 1v12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2z"/></svg>
            Walkie-Talkie (PTT)
          </h2>
          <div id="wt-status-led" style="width:12px; height:12px; border-radius:50%; background:#333; box-shadow: 0 0 8px #333; transition:0.3s;"></div>
        </div>
        <div class="card-body" style="padding: 20px;">
          <!-- LCD Display -->
          <div style="background:#0a150f; border:3px solid #1a3324; border-radius:4px; padding:15px; font-family:monospace; color:#39ff14; text-shadow:0 0 6px #39ff14; margin-bottom:20px; box-shadow:inset 0 0 10px rgba(0,255,0,0.5);">
            <div style="display:flex; justify-content:space-between; font-size:11px; color:#227733; margin-bottom:5px;">
              <span>CHIPTUNE RF NETWORK</span>
              <span id="wt-battery">SIG: █ █ █ █ █</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:5px;">
              <span id="wt-lcd-freq" style="font-size:32px; font-weight:bold;">92.4 <span style="font-size:14px;">MHz</span></span>
              <span id="wt-lcd-state" style="font-size:14px; background:#113a1a; padding:2px 6px; border-radius:2px;">STANDBY</span>
            </div>
            <div style="font-size:11px; color:#2dbd11;" id="wt-lcd-info">ONLINE DUAL-BAND TRANSCEIVER</div>
          </div>

          <!-- Controls -->
          <div style="display:flex; flex-direction:column; gap:15px;">
            <div>
              <label style="font-size:11px; color:var(--text-muted); font-weight:bold; display:block; margin-bottom:5px;">CHANNEL / FREQUENCY</label>
              <select id="wt-frequency" onchange="updateWtFrequency(this.value)" style="width:100%; padding:10px; background:var(--bg-card); color:var(--text-primary); border:3px solid #111; box-shadow:2px 2px 0px #111; font-family:monospace; font-weight:bold;">
                <option value="92.4">92.4 MHz - Channel Alpha (Rap)</option>
                <option value="98.5">98.5 MHz - Channel Beta (Pop)</option>
                <option value="104.2">104.2 MHz - Channel Gamma (Rock)</option>
                <option value="107.9">107.9 MHz - Channel Delta (Numbers Stn)</option>
              </select>
            </div>

            <!-- Big PTT Button -->
            <div style="text-align:center; padding:10px 0;">
              <button id="btn-ptt" style="width:120px; height:120px; border-radius:50%; border:6px solid #111; background:radial-gradient(circle, #ff0055 0%, #990033 100%); color:#fff; font-weight:900; font-size:16px; font-family:'Space Grotesk', sans-serif; cursor:pointer; box-shadow:6px 6px 0px #111, inset 0 0 10px rgba(255,255,255,0.3); outline:none; transition: 0.1s; user-select:none; -webkit-user-select:none;">PTT</button>
              <p style="font-size:11px; color:var(--text-muted); margin-top:8px;">Hold click / touch to broadcast voice</p>
            </div>
          </div>
        </div>
      </div>

      <!-- FM SYNTH RADIO -->
      <div class="card" style="border-color: var(--cyan); box-shadow: 0 0 15px rgba(0, 212, 255, 0.1);">
        <div class="card-header" style="background: rgba(0,212,255,0.03); display:flex; justify-content:space-between; align-items:center;">
          <h2 class="card-title" style="color: var(--cyan); display:flex; align-items:center; gap:8px;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 18v-6a9 9 0 0 1 18 0v6M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3M3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3"/></svg>
            FM Offline Synth Tuner
          </h2>
          <!-- Speaker Grill animation or visualizer -->
          <div style="display:flex; gap:2px; height:15px; align-items:flex-end;" id="fm-visualizer">
            <div class="vis-bar" style="width:3px; height:5px; background:var(--cyan); transition:0.1s;"></div>
            <div class="vis-bar" style="width:3px; height:8px; background:var(--cyan); transition:0.1s;"></div>
            <div class="vis-bar" style="width:3px; height:3px; background:var(--cyan); transition:0.1s;"></div>
            <div class="vis-bar" style="width:3px; height:11px; background:var(--cyan); transition:0.1s;"></div>
            <div class="vis-bar" style="width:3px; height:6px; background:var(--cyan); transition:0.1s;"></div>
          </div>
        </div>
        <div class="card-body" style="padding: 20px;">
          <!-- Radio Dial Area -->
          <div style="background:#111; border:3px solid #333; border-radius:4px; padding:15px; margin-bottom:20px; position:relative; overflow:hidden;">
            <!-- Analog scale background -->
            <div style="height:35px; border-bottom:1px solid #444; position:relative; display:flex; justify-content:space-between; align-items:flex-end; font-family:monospace; font-size:10px; color:#666; padding-bottom:4px; user-select:none;">
              <span style="left:5%">90</span>
              <span style="left:25%">95</span>
              <span style="left:50%">100</span>
              <span style="left:75%">105</span>
              <span style="left:95%">110</span>
              
              <!-- Red needle indicator -->
              <div id="fm-needle" style="position:absolute; bottom:0; left:12%; width:2px; height:30px; background:#ff3333; box-shadow:0 0 8px #ff3333; transition:left 0.1s ease-out; z-index:5;"></div>
            </div>
            
            <!-- Frequency LCD readout -->
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px;">
              <span style="font-family:monospace; font-size:24px; font-weight:bold; color:var(--cyan); text-shadow:0 0 8px rgba(0,212,255,0.5);" id="fm-lcd-freq">92.4 MHz</span>
              <span style="font-family:monospace; font-size:11px; color:#555;" id="fm-lcd-station">STATION PRESET ALPHA</span>
            </div>
          </div>

          <!-- Tuner Slider -->
          <div style="margin-bottom:20px;">
            <input type="range" id="fm-tuner-slider" min="88.0" max="108.0" step="0.1" value="92.4" oninput="tuneFmRadio(this.value)" style="width:100%; height:12px; border-radius:6px; background:#222; outline:none; border:2px solid #444; -webkit-appearance:none; cursor:ew-resize;">
          </div>

          <!-- Presets Quick-Buttons -->
          <div style="margin-bottom:20px;">
            <label style="font-size:11px; color:var(--text-muted); font-weight:bold; display:block; margin-bottom:5px;">STATION PRESETS</label>
            <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:8px;">
              <button onclick="setFmPreset(92.4)" class="neo-btn" style="padding:6px; font-family:monospace; font-size:11px; min-width:auto; text-transform:none;">📻 92.4 (Rap Cover)</button>
              <button onclick="setFmPreset(98.5)" class="neo-btn" style="padding:6px; font-family:monospace; font-size:11px; min-width:auto; text-transform:none;">📻 98.5 (Pop Cover)</button>
              <button onclick="setFmPreset(104.2)" class="neo-btn" style="padding:6px; font-family:monospace; font-size:11px; min-width:auto; text-transform:none;">📻 104.2 (Rock Cover)</button>
              <button onclick="setFmPreset(107.9)" class="neo-btn" style="padding:6px; font-family:monospace; font-size:11px; min-width:auto; text-transform:none;">📻 107.9 (Morse Station)</button>
            </div>
          </div>

          <!-- Volume and Audio Mute -->
          <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
            <button id="btn-fm-mute" onclick="toggleFmMute()" class="neo-btn" style="padding:8px 12px; font-size:12px; min-width:auto;">🔇 MUTE AUDIO</button>
            <div style="display:flex; align-items:center; gap:8px; flex:1;">
              <span style="font-size:11px; color:var(--text-muted);">VOL</span>
              <input type="range" id="fm-volume" min="0" max="1" step="0.05" value="0.5" oninput="setFmVolume(this.value)" style="flex:1;">
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ──────────────────────────────────────── CYBER CASINO TAB ──────────────────────────────────────── -->
  <section id="panel-casino" class="panel">
    <div class="panel-toolbar" style="justify-content: space-between;">
      <div class="panel-title-group">
        <h1 class="panel-heading">Cyber Casino Hub</h1>
        <span class="panel-sub">Offline Tactical Minigames</span>
      </div>
      <div style="text-align: right; margin-right: 20px;">
        <span style="font-size: 14px; color: var(--text-muted);">BALANCE</span><br>
        <strong class="cyber-credits-display" style="font-size: 24px; color: var(--cyan); text-shadow: 0 0 10px rgba(0,255,204,0.5);">-- CC</strong>
      </div>
    </div>
    
    <!-- Game Selection Tabs -->
    <div class="casino-tabs" style="display: flex; gap: 15px; margin-bottom: 20px; border-bottom: 3px solid #111; padding-bottom: 10px;">
      <button id="casino-tab-btn-crash" onclick="switchCasinoGame('crash')" class="casino-tab-btn" style="flex: 1; padding: 12px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; cursor: pointer; border: 3px solid #111; background: var(--bg-card); color: var(--text-primary); box-shadow: 4px 4px 0px #111; transition: 0.2s;">🚀 Crash</button>
      <button id="casino-tab-btn-gamba" onclick="switchCasinoGame('gamba')" class="casino-tab-btn" style="flex: 1; padding: 12px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; cursor: pointer; border: 3px solid #111; background: var(--bg-card); color: var(--text-primary); box-shadow: 4px 4px 0px #111; transition: 0.2s;">🎰 Gamba+</button>
      <button id="casino-tab-btn-blackjack" onclick="switchCasinoGame('blackjack')" class="casino-tab-btn" style="flex: 1; padding: 12px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; cursor: pointer; border: 3px solid #111; background: var(--bg-card); color: var(--text-primary); box-shadow: 4px 4px 0px #111; transition: 0.2s;">🃏 Blackjack</button>
      <button id="casino-tab-btn-tetris" onclick="switchCasinoGame('tetris')" class="casino-tab-btn" style="flex: 1; padding: 12px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; cursor: pointer; border: 3px solid #111; background: var(--bg-card); color: var(--text-primary); box-shadow: 4px 4px 0px #111; transition: 0.2s;">🧱 Tetris</button>
    </div>
    
    <div class="card" id="casino-card-crash" style="border-color: var(--cyan); margin-bottom:20px;">
      <div class="card-header" style="background:rgba(0,255,204,0.05);">
        <h2 class="card-title" style="color:var(--cyan);">Crash (Space Flight Mode)</h2>
      </div>
      <div class="card-body" style="padding: 20px; text-align: center;">
        <div id="crash-display-area" style="position: relative; background: #000; border: 3px solid var(--border); box-shadow: var(--shadow); margin-bottom: 20px; overflow: hidden; height: 55vh; min-height: 280px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <canvas id="crash-canvas" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1;"></canvas>
            <div id="crash-multiplier" style="position: relative; z-index: 2; font-size: 64px; font-weight: bold; font-family: monospace; color: var(--cyan); text-shadow: 0 0 15px currentColor; margin-top: -20px;">1.00x</div>
            <div id="crash-msg" style="position: relative; z-index: 2; color: var(--text-muted); margin-top: 10px; font-size: 18px; font-weight: bold;">Place your bet to launch rocket!</div>
        </div>
        <div style="display: flex; flex-direction: column; gap: 15px; align-items: center; justify-content: center; max-width: 500px; margin: 0 auto;">
            <!-- Quick Bet buttons -->
            <div style="display: flex; gap: 8px; width: 100%; justify-content: center;">
                <button onclick="setCrashBetMultiplier(0.1)" style="flex:1; padding: 8px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; font-size: 12px; background: rgba(0,255,204,0.05); color: var(--cyan); border: 2px solid var(--cyan); cursor: pointer; transition: 0.1s;">MIN</button>
                <button onclick="setCrashBetMultiplier(0.5)" style="flex:1; padding: 8px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; font-size: 12px; background: rgba(0,255,204,0.05); color: var(--cyan); border: 2px solid var(--cyan); cursor: pointer; transition: 0.1s;">1/2</button>
                <button onclick="setCrashBetMultiplier(2.0)" style="flex:1; padding: 8px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; font-size: 12px; background: rgba(0,255,204,0.05); color: var(--cyan); border: 2px solid var(--cyan); cursor: pointer; transition: 0.1s;">2x</button>
                <button onclick="setCrashBetMultiplier(999)" style="flex:1; padding: 8px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; font-size: 12px; background: rgba(0,255,204,0.05); color: var(--cyan); border: 2px solid var(--cyan); cursor: pointer; transition: 0.1s;">MAX</button>
            </div>
            
            <!-- Input & Launch buttons -->
            <div style="display: flex; gap: 12px; width: 100%; align-items: center;">
                <div style="position: relative; flex: 1; display: flex; align-items: center;">
                    <span style="position: absolute; left: 12px; color: var(--text-muted); font-weight: bold; font-size: 14px;">₡</span>
                    <input type="number" id="crash-bet" value="50" min="1" class="text-input" style="width: 100%; text-align: center; padding-left: 25px; padding-right: 10px; font-family: monospace; font-size: 16px; font-weight: bold; border: 3px solid #111; box-shadow: 2px 2px 0px #111; border-radius: 0px; height: 46px;" placeholder="Bet">
                </div>
                <button id="btn-crash-bet" class="btn-primary" onclick="startCrashGame()" style="flex: 1.2; padding: 12px; background: var(--cyan); color: #000; font-weight: 800; font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; border: 3px solid #111; box-shadow: 4px 4px 0px #111; cursor: pointer; transition: transform 0.1s; height: 46px;">🚀 Launch Bet</button>
                <button id="btn-crash-cashout" class="btn-primary" onclick="cashOutCrash()" style="display: none; flex: 1.2; padding: 12px; background: var(--green); color: #000; font-weight: 800; font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; border: 3px solid #111; box-shadow: 4px 4px 0px #111; cursor: pointer; transition: transform 0.1s; animation: pulse-green 1.5s infinite; height: 46px;">💰 Cash Out</button>
            </div>
        </div>
      </div>
    </div>
    
    <div class="card" id="casino-card-gamba" style="border-color: var(--orange); margin-bottom:20px; display: none;">
      <div class="card-header" style="background:rgba(255,102,0,0.05);">
        <h2 class="card-title" style="color:var(--orange);">Gamba+ Cyber Slots</h2>
      </div>
      <div class="card-body" style="padding: 20px; text-align: center;">
        <div style="background: #000; border: 3px solid var(--border); box-shadow: var(--shadow); margin-bottom: 20px; overflow: hidden; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 10px; position: relative;">
            <canvas id="gamba-canvas" style="max-width: 100%; height: auto; display: block; margin: 0 auto; filter: drop-shadow(0 0 15px var(--orange));"></canvas>
            <div id="gamba-msg" style="color: var(--text-muted); margin-top: 15px; min-height: 20px; font-weight: bold; font-size: 18px;">Spin to match symbols!</div>
        </div>
        <div style="display: flex; flex-direction: column; gap: 15px; align-items: center; justify-content: center; max-width: 500px; margin: 0 auto;">
            <!-- Quick Bet buttons -->
            <div style="display: flex; gap: 8px; width: 100%; justify-content: center;">
                <button onclick="setGambaBetMultiplier(0.1)" style="flex:1; padding: 8px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; font-size: 12px; background: rgba(255,102,0,0.05); color: var(--orange); border: 2px solid var(--orange); cursor: pointer; transition: 0.1s;">MIN</button>
                <button onclick="setGambaBetMultiplier(0.5)" style="flex:1; padding: 8px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; font-size: 12px; background: rgba(255,102,0,0.05); color: var(--orange); border: 2px solid var(--orange); cursor: pointer; transition: 0.1s;">1/2</button>
                <button onclick="setGambaBetMultiplier(2.0)" style="flex:1; padding: 8px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; font-size: 12px; background: rgba(255,102,0,0.05); color: var(--orange); border: 2px solid var(--orange); cursor: pointer; transition: 0.1s;">2x</button>
                <button onclick="setGambaBetMultiplier(999)" style="flex:1; padding: 8px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; font-size: 12px; background: rgba(255,102,0,0.05); color: var(--orange); border: 2px solid var(--orange); cursor: pointer; transition: 0.1s;">MAX</button>
            </div>
            
            <!-- Input & Spin buttons -->
            <div style="display: flex; gap: 12px; width: 100%; align-items: center;">
                <div style="position: relative; flex: 1; display: flex; align-items: center;">
                    <span style="position: absolute; left: 12px; color: var(--text-muted); font-weight: bold; font-size: 14px;">₡</span>
                    <input type="number" id="gamba-bet" value="50" min="1" class="text-input" style="width: 100%; text-align: center; padding-left: 25px; padding-right: 10px; font-family: monospace; font-size: 16px; font-weight: bold; border: 3px solid #111; box-shadow: 2px 2px 0px #111; border-radius: 0px; height: 46px;" placeholder="Bet">
                </div>
                <button id="btn-gamba-spin" class="btn-primary" onclick="spinGamba()" style="flex: 1.2; padding: 12px; background: var(--orange); color: #000; font-weight: 800; font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; border: 3px solid #111; box-shadow: 4px 4px 0px #111; cursor: pointer; transition: transform 0.1s; height: 46px;">🎰 Spin</button>
            </div>
        </div>
      </div>
    </div>
    
    <div class="card" id="casino-card-blackjack" style="border-color: var(--purple); margin-bottom:20px; display: none;">
      <div class="card-header" style="background:rgba(123,47,247,0.05);">
        <h2 class="card-title" style="color:var(--purple);">Table 1: Blackjack</h2>
      </div>
      <div class="card-body" style="padding: 20px; text-align: center;">
        
        <!-- Rules / Help Button -->
        <button class="casino-help-btn" onclick="document.getElementById('bj-rules').classList.add('open')">?</button>

        <!-- Rules Modal -->
        <div id="bj-rules" class="casino-modal">
          <h2>How to Play Blackjack</h2>
          <p><strong>Objective:</strong> Beat the dealer's hand without going over 21.</p>
          <p><strong>Values:</strong> Cards 2-10 are face value. Face cards (J, Q, K) are 10. Aces are 1 or 11.</p>
          <p><strong>Play:</strong> Press HIT to draw another card, STAND to lock your total.</p>
          <button class="casino-modal-close" onclick="document.getElementById('bj-rules').classList.remove('open')">GOT IT</button>
        </div>

        <div style="display:flex; justify-content:space-between; margin-bottom:20px; flex-wrap:wrap; gap:15px;">
          <!-- Dealer Hand -->
          <div style="flex:1; min-width:180px; background:#080d12; border:2px solid var(--border); padding:15px; border-radius:8px;">
            <h4 style="margin:0 0 10px 0; color:var(--text-muted); font-size:12px; text-transform:uppercase; font-weight:bold;">DEALER HAND (<span id="bj-dealer-score" style="font-weight:bold; color:#fff;">--</span>)</h4>
            <div id="bj-dealer-cards" style="display:flex; gap:10px; justify-content:center; min-height:100px; align-items:center;"></div>
          </div>
          <!-- Player Hand -->
          <div style="flex:1; min-width:180px; background:#080d12; border:2px solid var(--border); padding:15px; border-radius:8px;">
            <h4 style="margin:0 0 10px 0; color:var(--text-muted); font-size:12px; text-transform:uppercase; font-weight:bold;">YOUR HAND (<span id="bj-player-score" style="font-weight:bold; color:#fff;">--</span>)</h4>
            <div id="bj-player-cards" style="display:flex; gap:10px; justify-content:center; min-height:100px; align-items:center;"></div>
          </div>
        </div>

        <div style="display: flex; flex-direction: column; gap: 15px; align-items: center; justify-content: center; max-width: 500px; margin: 0 auto;">
          <!-- Betting controls inside card body -->
          <div id="bj-betting-controls" style="display: flex; flex-direction: column; gap: 10px; width: 100%; align-items: center;">
            <!-- Presets -->
            <div style="display: flex; gap: 8px; width: 100%; justify-content: center;">
              <button onclick="setBjBetMultiplier(0.1)" class="bj-preset-btn" style="flex: 1; padding: 6px; font-family: monospace; font-size: 11px; font-weight: bold; background: rgba(123,47,247,0.05); color: var(--purple); border: 2px solid var(--purple); cursor: pointer;">MIN</button>
              <button onclick="setBjBetMultiplier(0.5)" class="bj-preset-btn" style="flex: 1; padding: 6px; font-family: monospace; font-size: 11px; font-weight: bold; background: rgba(123,47,247,0.05); color: var(--purple); border: 2px solid var(--purple); cursor: pointer;">1/2</button>
              <button onclick="setBjBetMultiplier(2.0)" class="bj-preset-btn" style="flex: 1; padding: 6px; font-family: monospace; font-size: 11px; font-weight: bold; background: rgba(123,47,247,0.05); color: var(--purple); border: 2px solid var(--purple); cursor: pointer;">2x</button>
              <button onclick="setBjBetMultiplier(999)" class="bj-preset-btn" style="flex: 1; padding: 6px; font-family: monospace; font-size: 11px; font-weight: bold; background: rgba(123,47,247,0.05); color: var(--purple); border: 2px solid var(--purple); cursor: pointer;">MAX</button>
            </div>
            <!-- Input & Deal -->
            <div style="display: flex; gap: 10px; width: 100%; align-items: center;">
              <div style="position: relative; flex: 1; display: flex; align-items: center;">
                <span style="position: absolute; left: 12px; color: var(--text-muted); font-weight: bold; font-size: 14px;">₡</span>
                <input type="number" id="bj-bet-input" value="50" min="1" class="text-input" style="width: 100%; text-align: center; padding-left: 25px; padding-right: 10px; font-family: monospace; font-size: 16px; font-weight: bold; border: 3px solid #111; box-shadow: 2px 2px 0px #111; border-radius: 0px; height: 46px;" placeholder="Bet">
              </div>
              <button id="btn-bj-deal" class="btn-primary" onclick="startBlackjack()" style="flex: 1.2; padding: 12px; background: var(--purple); color: #fff; font-weight: 800; font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; border: 3px solid #111; box-shadow: 4px 4px 0px #111; cursor: pointer; transition: transform 0.1s; height: 46px;">🃏 Deal Hand</button>
            </div>
          </div>

          <!-- Gameplay buttons (Hit, Stand) -->
          <div id="bj-gameplay-controls" style="display:none; gap:12px; width: 100%;">
            <button id="btn-bj-hit" class="btn-primary" onclick="blackjackHit()" style="flex:1; padding: 12px; background: var(--green); color: #000; font-weight: 800; font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; border: 3px solid #111; box-shadow: 4px 4px 0px #111; cursor: pointer;">Hit</button>
            <button id="btn-bj-stand" class="btn-primary" onclick="blackjackStand()" style="flex:1; padding: 12px; background: var(--red); color: #fff; font-weight: 800; font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; border: 3px solid #111; box-shadow: 4px 4px 0px #111; cursor: pointer;">Stand</button>
          </div>
          
          <div id="bj-msg" style="color:var(--text-muted); font-weight:bold; min-height:22px; font-size:18px;">Place your bet to start round.</div>
        </div>
      </div>
    </div>

    <div class="card" id="casino-card-tetris" style="border-color: var(--yellow); margin-bottom:20px; display: none;">
      <div class="card-header" style="background:rgba(255,204,0,0.05);">
        <h2 class="card-title" style="color:var(--yellow);">Table 2: Cyber Tetris</h2>
      </div>
      <div class="card-body" style="padding: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #0a0f14; border: 2px solid var(--yellow); border-radius: 12px; box-shadow: inset 0 0 50px rgba(255,204,0,0.05), 0 0 20px rgba(255,204,0,0.1); min-height: 480px; position: relative;">
        
        <!-- Rules / Help Button -->
        <button class="casino-help-btn" onclick="document.getElementById('tetris-rules').classList.add('open')" style="border-color: var(--yellow); color: var(--yellow);">❓</button>

        <!-- Rules Modal -->
        <div id="tetris-rules" class="casino-modal" style="border-color: var(--yellow);">
          <h2 style="color: var(--yellow);">How to Play Tetris</h2>
          <p><strong>Objective:</strong> Fit falling tetrominoes together to clear horizontal lines.</p>
          <p><strong>Controls:</strong></p>
          <p style="margin-left: 20px; margin-bottom: 5px;">⌨️ <strong>Arrow Keys / WASD:</strong> Left/Right to move, Down to soft drop, Up/W to rotate</p>
          <p style="margin-left: 20px; margin-bottom: 5px;">⌨️ <strong>Spacebar:</strong> Hard drop (instant land)</p>
          <p style="margin-left: 20px; margin-bottom: 5px;">⌨️ <strong>C / Shift:</strong> Hold piece</p>
          <p><strong>Costs:</strong> 50 ₡ per game. Every line cleared refunds 10 ₡! Getting a Tetris (4 lines at once) pays a 100 ₡ bonus!</p>
          <button class="casino-modal-close" onclick="document.getElementById('tetris-rules').classList.remove('open')" style="background: var(--yellow); color: #000; border-color: #111;">GOT IT</button>
        </div>

        <!-- Entry Screen / Game Start -->
        <div id="tetris-start-screen" style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 20px; width: 100%; height: 100%; min-height: 400px; z-index: 2;">
          <h1 style="color: var(--yellow); font-family: 'Space Grotesk', sans-serif; font-weight: 900; letter-spacing: 2px; text-shadow: 0 0 10px var(--yellow); font-size: 36px;">CYBER TETRIS</h1>
          <p style="color: #aaa; text-align: center; max-width: 320px; font-size: 14px;">Deploy tetrominoes offline. Defend the matrix. Earn credits for every line cleared.</p>
          <button onclick="startTetrisGame()" class="bj-btn" style="background: var(--yellow); color: #000; box-shadow: 0 0 15px rgba(255,204,0,0.4); font-size: 18px; border: 3px solid #111; text-transform: uppercase;">Play (50 ₡)</button>
        </div>

        <!-- Game Active Container -->
        <div id="tetris-game-container" style="display: none; width: 100%; max-width: 480px; justify-content: center; gap: 15px; margin: 15px 0;">
          
          <!-- Left Sidebar (Hold Piece & Instructions) -->
          <div style="display: flex; flex-direction: column; gap: 12px; width: 80px; align-items: center;">
            <div style="border: 2px solid var(--yellow); padding: 8px; width: 100%; background: #111; text-align: center; border-radius: 6px;">
              <span style="font-size: 10px; color: var(--yellow); text-transform: uppercase; font-weight: bold; display: block; margin-bottom: 5px;">HOLD</span>
              <canvas id="tetris-hold-canvas" width="60" height="60" style="background: #000; display: block; border: 1px solid #222;"></canvas>
            </div>
            <div style="font-size: 10px; color: #666; text-align: center; line-height: 1.4; border: 1px solid #333; padding: 6px; border-radius: 4px; background: #080d12; width: 100%;">
              W: Rotate<br>A/D: Move<br>S: Soft<br>Space: Hard<br>C: Hold
            </div>
          </div>

          <!-- Main Game Board Canvas -->
          <div style="position: relative;">
            <canvas id="tetris-canvas" width="200" height="400" style="background: #050a0e; border: 3px solid var(--yellow); box-shadow: 0 0 15px rgba(255,204,0,0.15); display: block;"></canvas>
            <!-- Game Over overlay inside canvas -->
            <div id="tetris-gameover-overlay" style="display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); flex-direction: column; align-items: center; justify-content: center; gap: 15px; z-index: 10;">
              <h2 style="color: var(--red); text-shadow: 0 0 10px var(--red); font-size: 24px; font-weight: 900;">SYSTEM OVERLOAD</h2>
              <div style="text-align: center; color: #fff; font-size: 14px;">
                Score: <span id="tetris-final-score" style="color: var(--yellow); font-weight: bold;">0</span><br>
                Cleared: <span id="tetris-final-lines" style="color: var(--yellow); font-weight: bold;">0</span>
              </div>
              <button onclick="startTetrisGame()" class="bj-btn" style="background: var(--yellow); color: #000; font-size: 14px; padding: 8px 16px; border: 2px solid #111; text-transform: uppercase;">Try Again (50 ₡)</button>
            </div>
          </div>

          <!-- Right Sidebar (Next Piece & Score) -->
          <div style="display: flex; flex-direction: column; gap: 12px; width: 80px; align-items: center;">
            <div style="border: 2px solid var(--yellow); padding: 8px; width: 100%; background: #111; text-align: center; border-radius: 6px;">
              <span style="font-size: 10px; color: var(--yellow); text-transform: uppercase; font-weight: bold; display: block; margin-bottom: 5px;">NEXT</span>
              <canvas id="tetris-next-canvas" width="60" height="60" style="background: #000; display: block; border: 1px solid #222;"></canvas>
            </div>
            <div style="border: 2px solid var(--yellow); padding: 8px; width: 100%; background: #111; border-radius: 6px; text-align: center; width: 100%;">
              <span style="font-size: 8px; color: #aaa; text-transform: uppercase; font-weight: bold; display: block;">SCORE</span>
              <span id="tetris-score" style="font-size: 14px; font-weight: bold; color: var(--yellow); font-family: monospace;">0</span>
            </div>
            <div style="border: 2px solid var(--yellow); padding: 8px; width: 100%; background: #111; border-radius: 6px; text-align: center; width: 100%;">
              <span style="font-size: 8px; color: #aaa; text-transform: uppercase; font-weight: bold; display: block;">LINES</span>
              <span id="tetris-lines" style="font-size: 14px; font-weight: bold; color: var(--yellow); font-family: monospace;">0</span>
            </div>
          </div>

        </div>

        <!-- Controls toolbar under the board -->
        <div id="tetris-toolbar" style="display: none; width: 100%; max-width: 400px; justify-content: center; gap: 12px; margin-top: 10px; z-index: 2;">
          <button id="tetris-btn-pause" class="bj-btn" style="background: var(--bg-card); color: var(--text-primary); border: 2px solid #111; padding: 6px 12px; font-size: 12px; text-transform: uppercase;" onclick="toggleTetrisPause()">Pause</button>
          <button class="bj-btn" style="background: var(--red); color: #fff; border: 2px solid #111; padding: 6px 12px; font-size: 12px; text-transform: uppercase;" onclick="quitTetrisGame()">Quit</button>
        </div>

      </div>
    </div>
  </section>
"""

# 4. Inject scripts before app.js
script_tags = """  <script src="blackjack.js"></script>
  <script src="casino_engine.js"></script>
  <script src="crash.js"></script>
  <script src="gamba_plus.js"></script>
  <script src="tetris.js"></script>
  <script src="offline_tv.js"></script>
  <script src="offline_tv_games.js"></script>
  <script src="radio_comm.js"></script>
"""

# Find the end of panel-setup section
setup_idx = html.find('id="panel-setup"')
if setup_idx != -1:
    section_end_idx = html.find('</section>', setup_idx)
    if section_end_idx != -1:
        insert_pos = section_end_idx + len('</section>')
        if 'id="panel-casino"' not in html:
            html = html[:insert_pos] + "\n" + panels_html + html[insert_pos:]

# Inject script tags before app.js script tag
app_js_match = re.search(r'<script src="app\.js\?v=\d+"></script>', html)
if app_js_match:
    start_pos = app_js_match.start()
    if 'src="casino_engine.js"' not in html:
        html = html[:start_pos] + script_tags + "\n" + html[start_pos:]
else:
    # Fallback to general app.js search
    if '<script src="app.js' in html:
        pos = html.find('<script src="app.js')
        if 'src="casino_engine.js"' not in html:
            html = html[:pos] + script_tags + "\n" + html[pos:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("Casino UI successfully injected into index.html")
