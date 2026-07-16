/* ═══════════════════════════════════════════════════════
   Security Command Center — Dashboard JavaScript
   Polls the local Flask API and renders live data.
   Auto-updates across ALL devices when server restarts.
   ═══════════════════════════════════════════════════════ */

// Detect the server's origin dynamically so the dashboard
// works whether opened as localhost or via LAN IP on another device
const _origin = window.location.origin;       // e.g. http://192.168.1.4:8765
const API = `${_origin}/api`;
const POLL_INTERVAL = 10000;
let _currentTab = 'overview';
let _pollingTimer = null;
let _drawerOpen = false;
let _isAuthenticated = false;
let _lastSecurityScore = 100;
let _highlightRiskyPorts = false;

// ──────────────────────────────────────────────────────
// AUTO-UPDATE SYSTEM
// Polls /api/version every 30s. When the server restarts
// (you made changes + ran start.bat), the version hash
// changes and every connected device auto-reloads.
// ──────────────────────────────────────────────────────
let _knownVersion = null;
let _updateBannerShown = false;
let _lastDevices = [];

async function checkForUpdates() {
  try {
    const res = await fetch(`${API}/version`, { cache: 'no-store' });
    const data = await res.json();
    if (!data.ok) return;

    if (_knownVersion === null) {
      // First load — record current version
      _knownVersion = data.version;
      console.log(`[Security Suite] Dashboard version: ${_knownVersion}`);
      return;
    }

    if (data.version !== _knownVersion && !_updateBannerShown) {
      _updateBannerShown = true;
      showUpdateBanner();
    }
  } catch (_) {
    // Server temporarily unreachable — skip
  }
}

function showUpdateBanner() {
  // Remove any existing banner
  document.getElementById('update-banner')?.remove();

  const banner = document.createElement('div');
  banner.id = 'update-banner';
  banner.style.cssText = `
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
    background: linear-gradient(90deg, #00d4ff22, #7b2ff722);
    border-bottom: 1px solid #00d4ff55;
    backdrop-filter: blur(16px);
    padding: 12px 24px;
    display: flex; align-items: center; gap: 14px;
    font-family: 'Inter', sans-serif; font-size: 14px; color: #fff;
    animation: slideDown 0.4s ease;
  `;
  banner.innerHTML = `
    <span style="font-size:20px">🔄</span>
    <div style="flex:1">
      <strong>Dashboard Updated!</strong>
      <span style="color:#aaa;margin-left:8px">New version detected — refreshing in <span id="update-countdown">5</span>s</span>
    </div>
    <button onclick="reloadNow()" style="background:var(--cyan,#00d4ff);color:#000;border:none;padding:6px 16px;border-radius:6px;cursor:pointer;font-weight:700">Refresh Now</button>
    <button onclick="dismissUpdate()" style="background:none;border:1px solid #444;color:#aaa;padding:6px 12px;border-radius:6px;cursor:pointer">Skip</button>
  `;
  document.body.prepend(banner);

  // Add slide-down animation if not already in CSS
  if (!document.getElementById('update-style')) {
    const style = document.createElement('style');
    style.id = 'update-style';
    style.textContent = `@keyframes slideDown { from { transform: translateY(-100%); } to { transform: translateY(0); } }`;
    document.head.appendChild(style);
  }

  // Countdown timer
  let secs = 5;
  const countdown = setInterval(() => {
    secs--;
    const el = document.getElementById('update-countdown');
    if (el) el.textContent = secs;
    if (secs <= 0) { clearInterval(countdown); reloadNow(); }
  }, 1000);
  banner._countdown = countdown;
}

function reloadNow() {
  // Tell service worker to skip waiting so new SW activates immediately
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage('SKIP_WAITING');
  }
  // Clear all caches then reload
  if ('caches' in window) {
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k)))).then(() => location.reload(true));
  } else {
    location.reload(true);
  }
}

function dismissUpdate() {
  const banner = document.getElementById('update-banner');
  if (banner) {
    clearInterval(banner._countdown);
    banner.remove();
  }
  _updateBannerShown = false;
}

// Poll for updates every 30 seconds
checkForUpdates();
setInterval(checkForUpdates, 30000);

// ──────────────────────────────────────────────────────
// AUTHENTICATION (LOCK SCREEN)
// ──────────────────────────────────────────────────────
let currentPin = '';

function initLockScreen() {
  // Clear any existing pin state
  currentPin = '';
  updatePinDots();
  document.getElementById('login-error').textContent = '';
}

function addPin(num) {
  if (currentPin.length < 4) {
    currentPin += num;
    updatePinDots();
    if (currentPin.length === 4) {
      attemptLogin(currentPin);
    }
  }
}

function removePin() {
  if (currentPin.length > 0) {
    currentPin = currentPin.slice(0, -1);
    updatePinDots();
    document.getElementById('login-error').textContent = '';
  }
}

function updatePinDots() {
  for (let i = 1; i <= 4; i++) {
    const dot = document.getElementById(`dot-${i}`);
    if (dot) {
      if (i <= currentPin.length) {
        dot.classList.add('filled');
      } else {
        dot.classList.remove('filled');
      }
    }
  }
}

async function attemptLogin(pin) {
  const errorEl = document.getElementById('login-error');
  const overlay = document.getElementById('login-overlay');
  const card = document.querySelector('.login-card');
  
  errorEl.textContent = 'Authenticating...';
  
  try {
    const res = await fetch(`${API}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin })
    });
    const data = await res.json();
    
    if (data.ok) {
      // Success! Hide lock screen and start app
      _isAuthenticated = true;
      errorEl.textContent = '';
      overlay.style.opacity = '0';
      setTimeout(() => {
        overlay.style.display = 'none';
        startApp(); // Now load the real data
      }, 500);
    } else {
      // Failed!
      errorEl.textContent = data.error || 'Invalid PIN';
      currentPin = '';
      updatePinDots();
      card.classList.add('shake');
      setTimeout(() => card.classList.remove('shake'), 400);
    }
  } catch (err) {
    errorEl.textContent = 'Server unreachable';
  }
}


// ──────────────────────────────────────────────────────
// SERVICE WORKER REGISTRATION
// Enables PWA install on iOS/Android + offline fallback
// ──────────────────────────────────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => {
        console.log('[Security Suite] Service Worker registered:', reg.scope);
        // Listen for a new SW waiting to activate
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing;
          newWorker?.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New SW ready — let our version poller handle the reload notification
              console.log('[Security Suite] New service worker installed.');
            }
          });
        });
      })
      .catch(err => console.warn('[Security Suite] SW registration failed:', err));

    // When SW controller changes (new SW activated) — reload page
    let refreshing = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (!refreshing) { refreshing = true; location.reload(true); }
    });
  });
}

// ──────────────────────────────────────────────────────
// Clock
// ──────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  document.getElementById('time-display').textContent =
    now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
setInterval(updateClock, 1000);
updateClock();

// ──────────────────────────────────────────────────────
// Tab Navigation
// ──────────────────────────────────────────────────────
function showTab(tab) {
  _currentTab = tab;
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.drawer-item').forEach(d => d.classList.remove('active'));
  document.getElementById(`tab-${tab}`)?.classList.add('active');
  document.getElementById(`panel-${tab}`)?.classList.add('active');
  document.getElementById(`drawer-tab-${tab}`)?.classList.add('active');
  if (tab === 'network')   loadDevices();
  if (tab === 'ports')     loadPorts();
  if (tab === 'alerts')    loadAlerts();
  if (tab === 'eventlog')  loadEventLog();
  if (tab === 'dns')       loadDNS();
  if (tab === 'processes') loadProcesses();
  if (tab === 'setup')     loadSetupConfig();
  if (tab === 'connect')   loadConnect();
  if (tab === 'terminal') {
    // Slight delay so the panel is visible before xterm measures size
    setTimeout(initTerminal, 80);
  }
}

// ──────────────────────────────────────────────────────
// CONNECT DEVICES — QR Code + Agents
// ──────────────────────────────────────────────────────
let _qrGenerated = false;
let _localQrGenerated = false;
let _tunnelQrGenerated = false;
let _lastTunnelUrl = "";

async function loadConnect() {
  await loadNetworkInfo();
  await loadAgents();
}

async function loadNetworkInfo() {
  try {
    const res = await fetch(`${API.replace('/api', '')}/api/network-info`);
    const data = await res.json();
    if (!data.ok) return;

    const url = data.dashboard_url;
    const localUrl = `https://${data.local_ip}:8768`;
    const tunnelUrl = data.tunnel_url;

    // Show URL text
    const urlEl = document.getElementById('net-url');
    if (urlEl) urlEl.textContent = url;

    const localUrlEl = document.getElementById('net-url-local');
    if (localUrlEl) localUrlEl.textContent = localUrl;

    // Pre-fill agent download steps
    const agentUrl = `${url}/agent.py`;
    const androidEl = document.getElementById('android-agent-url');
    if (androidEl) androidEl.textContent = `curl -O ${agentUrl}`;
    const winEl = document.getElementById('win-agent-url');
    if (winEl) winEl.textContent = `(open in browser) ${agentUrl}`;
    const nethunterEl = document.getElementById('agent-download-url');
    if (nethunterEl) nethunterEl.textContent = agentUrl;

    // Generate Local Offline QR code (once)
    const localQrEl = document.getElementById('qr-code-local');
    if (localQrEl && !_localQrGenerated && typeof QRCode !== 'undefined') {
      localQrEl.innerHTML = '';
      new QRCode(localQrEl, {
        text: localUrl,
        width: 140,
        height: 140,
        colorDark: '#000000',
        colorLight: '#ffffff',
        correctLevel: QRCode.CorrectLevel.M
      });
      _localQrGenerated = true;
    } else if (localQrEl && !_localQrGenerated) {
      localQrEl.innerHTML = `<div style="color:#666;font-size:11px;padding:16px">${localUrl}</div>`;
    }

    // Generate Tailscale Secure QR code (once)
    const qrEl = document.getElementById('qr-code');
    if (qrEl && !_qrGenerated && typeof QRCode !== 'undefined') {
      qrEl.innerHTML = '';
      new QRCode(qrEl, {
        text: url,
        width: 140,
        height: 140,
        colorDark: '#000000',
        colorLight: '#ffffff',
        correctLevel: QRCode.CorrectLevel.M
      });
      _qrGenerated = true;
    } else if (qrEl && !_qrGenerated) {
      qrEl.innerHTML = `<div style="color:#666;font-size:11px;padding:16px">${url}</div>`;
    }

    // Generate Tunnel QR code if tunnelUrl exists
    const tunnelUrlEl = document.getElementById('tunnel-url');
    const tunnelQrEl = document.getElementById('qr-code-tunnel');
    if (tunnelUrl) {
      if (tunnelUrlEl) tunnelUrlEl.innerHTML = `<a href="${tunnelUrl}" target="_blank" style="color:var(--primary);text-decoration:underline;">${tunnelUrl}</a>`;
      
      if (tunnelQrEl && (!_tunnelQrGenerated || _lastTunnelUrl !== tunnelUrl) && typeof QRCode !== 'undefined') {
        tunnelQrEl.innerHTML = '';
        new QRCode(tunnelQrEl, {
          text: tunnelUrl,
          width: 140,
          height: 140,
          colorDark: '#000000',
          colorLight: '#ffffff',
          correctLevel: QRCode.CorrectLevel.M
        });
        _tunnelQrGenerated = true;
        _lastTunnelUrl = tunnelUrl;
      }
    } else {
      if (tunnelUrlEl) tunnelUrlEl.textContent = "Awaiting Cloudflare activation...";
      if (tunnelQrEl) tunnelQrEl.innerHTML = '<div style="color:#666;font-size:11px;padding:40px 10px;">Waiting for backend...</div>';
      _tunnelQrGenerated = false;
      _lastTunnelUrl = "";
    }
  } catch (e) {
    console.warn('Network info fetch failed:', e);
  }
}

async function loadAgents() {
  const tbody = document.getElementById('agents-tbody');
  if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="table-loading"><div class="spinner" style="margin:12px auto"></div></td></tr>`;

  try {
    const res = await fetch(`${API}/agents`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'Failed');
    const d = data.data;

    // Update counts
    document.getElementById('agents-online-count').textContent = d.online;
    document.getElementById('agents-offline-count').textContent = d.offline;
    document.getElementById('agents-total-count').textContent = d.total;

    // Update badge
    const badge = document.getElementById('agents-badge');
    if (badge) {
      if (d.online > 0) {
        badge.textContent = d.online;
        badge.style.display = 'inline';
        badge.style.background = 'var(--green)';
      } else {
        badge.style.display = 'none';
      }
    }

    if (!d.agents || d.agents.length === 0) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="table-loading">No agents connected yet. Follow the setup steps above to connect a device.</td></tr>`;
      return;
    }

    if (tbody) tbody.innerHTML = d.agents.map(a => {
      const online = a.status === 'online';
      const platform = a.platform || '?';
      const platformIcon = platform === 'Windows' ? '🖥️' : platform === 'Linux' ? '🐧' : platform === 'Darwin' ? '🍎' : '📱';
      const battery = a.battery ? `${a.battery.percent}%${a.battery.plugged ? ' ⚡' : ''}` : '—';
      const lastSec = a.last_seen_seconds_ago ?? 9999;
      const lastStr = lastSec < 60 ? `${lastSec}s ago` : lastSec < 3600 ? `${Math.floor(lastSec/60)}m ago` : `${Math.floor(lastSec/3600)}h ago`;

      return `<tr>
        <td style="font-weight:600">${platformIcon} ${a.hostname || a.device_id}</td>
        <td>${platform} ${a.platform_version ? '<span style="color:var(--text-muted);font-size:10px">' + a.platform_version.substring(0,20) + '</span>' : ''}</td>
        <td style="font-family:var(--font-mono)">${a.ip || '—'}</td>
        <td><span class="risk-badge ${online ? 'risk-low' : 'risk-medium'}">${online ? '● ONLINE' : '○ OFFLINE'}</span></td>
        <td style="font-family:var(--font-mono)">${a.cpu_percent ?? '—'}%</td>
        <td style="font-family:var(--font-mono)">${a.memory_percent ?? '—'}%</td>
        <td>${battery}</td>
        <td style="font-size:11px;color:var(--text-muted)">${lastStr}</td>
        <td><button class="btn-sm" style="color:var(--red)" onclick="removeAgent('${a.device_id}')">✕</button></td>
      </tr>`;
    }).join('');
  } catch (e) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="table-loading" style="color:var(--red)">${e.message}</td></tr>`;
  }
}

async function removeAgent(deviceId) {
  if (!confirm('Remove this agent from the dashboard?')) return;
  try {
    const res = await fetch(`${API}/agents/${encodeURIComponent(deviceId)}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.ok) { showToast('Agent removed', 'info'); loadAgents(); }
    else showToast(data.error || 'Failed', 'error');
  } catch (e) { showToast(e.message, 'error'); }
}

// ──────────────────────────────────────────────────────
// EVENT LOG
// ──────────────────────────────────────────────────────
async function loadEventLog() {
  const hours = document.getElementById('evtlog-hours')?.value || 24;
  const tbody = document.getElementById('evtlog-tbody');
  const summaryEl = document.getElementById('evtlog-summary');
  if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="table-loading"><div class="spinner" style="margin:12px auto"></div></td></tr>`;

  try {
    const res = await fetch(`${API}/eventlog?hours=${hours}`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);
    const d = data.data;

    // Summary cards
    const bf = d.brute_force_risk;
    if (summaryEl) {
      summaryEl.innerHTML = `
        <div class="stat-card"><div class="stat-card-icon icon-blue"><svg viewBox="0 0 24 24" fill="none"><path d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></div><div class="stat-card-body"><div class="stat-value" style="color:${d.failed_logins>20?'var(--red)':d.failed_logins>5?'var(--orange)':'var(--green)'}">${d.failed_logins}</div><div class="stat-label">Failed Logins</div><div class="stat-sub">Last ${hours}h</div></div></div>
        <div class="stat-card"><div class="stat-card-icon icon-purple"><svg viewBox="0 0 24 24" fill="none"><path d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></div><div class="stat-card-body"><div class="stat-value" style="color:${d.account_lockouts>0?'var(--red)':'var(--green)'}">${d.account_lockouts}</div><div class="stat-label">Account Lockouts</div><div class="stat-sub">Last ${hours}h</div></div></div>
        <div class="stat-card"><div class="stat-card-icon icon-green"><svg viewBox="0 0 24 24" fill="none"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="stat-card-body"><div class="stat-value">${d.successful_logins}</div><div class="stat-label">Successful Logins</div><div class="stat-sub">Last ${hours}h</div></div></div>
        <div class="stat-card"><div class="stat-card-icon ${bf==='HIGH'?'icon-purple':'icon-cyan'}"><svg viewBox="0 0 24 24" fill="none"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="stat-card-body"><div class="stat-value" style="color:${bf==='HIGH'?'var(--red)':bf==='MEDIUM'?'var(--orange)':'var(--green)'}">${bf}</div><div class="stat-label">Brute Force Risk</div><div class="stat-sub">${d.failed_logins} attempts</div></div></div>
      `;
    }

    // Badge
    const badge = document.getElementById('evtlog-badge');
    if (badge) { badge.style.display = d.failed_logins > 10 || d.account_lockouts > 0 ? 'inline' : 'none'; }

    // Events table
    if (!d.recent_events || d.recent_events.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="table-loading" style="color:var(--green)">No security events in the last ${hours} hours.</td></tr>`;
      return;
    }

    tbody.innerHTML = d.recent_events.map(e => {
      const t = new Date(e.time).toLocaleString('en-IN');
      return `<tr>
        <td style="font-family:var(--font-mono);font-size:11px">${t}</td>
        <td>${e.icon || ''} ${e.name}</td>
        <td><span class="risk-badge risk-${e.severity === 'high' ? 'high' : e.severity === 'medium' ? 'medium' : 'low'} sev-${e.severity}">${e.severity?.toUpperCase()}</span></td>
        <td style="font-family:var(--font-mono);font-size:12px">${e.username || '—'}</td>
        <td style="font-size:11px;color:var(--text-muted)">${(e.message || '').substring(0, 80)}</td>
      </tr>`;
    }).join('');
  } catch (e) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="table-loading" style="color:var(--red)">${e.message}</td></tr>`;
  }
}

// ──────────────────────────────────────────────────────
// DNS & VPN
// ──────────────────────────────────────────────────────
async function loadDNS() {
  const el = document.getElementById('dns-content');
  if (!el) return;
  el.innerHTML = `<div class="device-loading"><div class="spinner"></div><p>Checking DNS & VPN...</p></div>`;

  try {
    const res = await fetch(`${API}/dns`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);
    const d = data.data;

    const vpn = d.vpn;
    const leak = d.leak_test;

    el.innerHTML = `
      <div class="dns-grid">
        <!-- VPN Status -->
        <div class="card">
          <div class="card-header"><h2 class="card-title">VPN Status</h2></div>
          <div class="vpn-status ${vpn.vpn_active ? 'active' : 'inactive'}">
            <div class="vpn-icon">${vpn.vpn_active ? '🔐' : '⚠️'}</div>
            <div>
              <div class="vpn-label" style="color:${vpn.vpn_active ? 'var(--green)' : 'var(--orange)'}">
                ${vpn.vpn_active ? 'VPN Active' : 'No VPN Detected'}
              </div>
              <div class="vpn-sub">${vpn.vpn_active ? vpn.connections.map(c => c.name).join(', ') : 'You are unprotected on public networks'}</div>
            </div>
          </div>
          ${!vpn.vpn_active ? `<div class="rec-box">Use ProtonVPN (free) or Mullvad for traffic encryption on public WiFi.</div>` : ''}
        </div>

        <!-- DNS-over-HTTPS -->
        <div class="card">
          <div class="card-header"><h2 class="card-title">DNS-over-HTTPS</h2></div>
          <div class="vpn-status ${d.doh_enabled ? 'active' : 'inactive'}">
            <div class="vpn-icon">${d.doh_enabled ? '✅' : '⚠️'}</div>
            <div>
              <div class="vpn-label" style="color:${d.doh_enabled ? 'var(--green)' : 'var(--orange)'}">
                ${d.doh_enabled ? 'DoH Enabled' : 'DoH Not Enabled (System)'}
              </div>
              <div class="vpn-sub">${d.doh_enabled ? 'DNS queries are encrypted' : 'System DNS is unencrypted. Note: If you enabled DoH inside your web browser settings, your browser traffic is protected, but other PC apps are not.'}</div>
            </div>
          </div>
          ${!d.doh_enabled ? `<div class="rec-box">To enable system-wide DoH: Windows Settings → Network & Internet → WiFi/Ethernet properties → DNS settings edit → choose Encrypted (DNS-over-HTTPS).</div>` : ''}
        </div>

        <!-- DNS Leak Test -->
        <div class="card">
          <div class="card-header"><h2 class="card-title">DNS Resolution Test</h2></div>
          ${(leak.test_results || []).map(r => `
            <div class="dns-server-row">
              <div class="dns-dot ${r.resolved !== 'FAILED' ? 'safe' : 'unsafe'}"></div>
              <div><div class="dns-addr">${r.host}</div><div class="dns-provider">${r.resolved !== 'FAILED' ? r.resolved + ' · ' + r.ms + 'ms' : 'FAILED to resolve'}</div></div>
            </div>`).join('')}
          <div style="margin-top:10px;font-size:12px;color:var(--text-muted)">Avg response: ${leak.avg_response_ms || '--'}ms</div>
        </div>
      </div>

      <!-- DNS Servers -->
      <div class="card">
        <div class="card-header"><h2 class="card-title">Current DNS Servers</h2></div>
        ${d.dns_servers && d.dns_servers.length > 0 ? d.dns_servers.map(s => `
          <div class="dns-server-row">
            <div class="dns-dot ${s.is_safe ? 'safe' : 'unsafe'}"></div>
            <div>
              <div class="dns-addr">${s.address}</div>
              <div class="dns-provider">${s.provider} · ${s.interface}</div>
            </div>
            ${!s.is_safe ? `<span class="risk-badge risk-medium" style="margin-left:auto">ISP DNS</span>` : `<span class="risk-badge risk-low" style="margin-left:auto">Private</span>`}
          </div>`).join('') : '<p style="color:var(--text-muted);font-size:13px">Could not detect DNS servers.</p>'}

        ${d.recommendations && d.recommendations.length > 0 ? `<div style="margin-top:16px">${d.recommendations.map(r => `<div class="rec-box">${r}</div>`).join('')}</div>` : ''}
      </div>`;
  } catch (e) {
    el.innerHTML = `<div class="device-loading"><p style="color:var(--red)">Error: ${e.message}</p></div>`;
  }
}

// ──────────────────────────────────────────────────────
// PROCESS MONITOR
// ──────────────────────────────────────────────────────
async function loadProcesses() {
  const tbody = document.getElementById('proc-tbody');
  const showSafe = document.getElementById('show-safe-procs')?.checked;
  if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="table-loading"><div class="spinner" style="margin:12px auto"></div></td></tr>`;

  try {
    const res = await fetch(`${API}/processes`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);
    const d = data.data;

    // Badge
    const badge = document.getElementById('proc-badge');
    if (badge) { badge.style.display = d.high_risk_count > 0 ? 'inline' : 'none'; if (d.high_risk_count > 0) badge.textContent = d.high_risk_count; }

    let procs = d.processes || [];
    if (!showSafe) procs = procs.filter(p => !p.is_safe || p.risk !== 'low');

    if (procs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="table-loading" style="color:var(--green)">All networked processes look clean.</td></tr>`;
      return;
    }

    tbody.innerHTML = procs.map(p => `<tr>
      <td style="font-weight:600">${p.name}</td>
      <td style="font-family:var(--font-mono);font-size:11px">${p.pid}</td>
      <td><span class="risk-badge risk-${p.risk}">${p.risk.toUpperCase()}</span></td>
      <td style="font-family:var(--font-mono)">${p.cpu_percent || 0}%</td>
      <td style="font-family:var(--font-mono)">${p.memory_mb || 0}</td>
      <td style="font-family:var(--font-mono)">${p.outbound_count || 0}</td>
      <td style="font-size:11px;color:${p.risk === 'high' ? 'var(--red)' : p.risk === 'medium' ? 'var(--orange)' : 'var(--text-muted)'}">${(p.suspicion_reasons || []).join(', ') || '—'}</td>
    </tr>`).join('');
  } catch (e) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="table-loading" style="color:var(--red)">${e.message}</td></tr>`;
  }
}

// ──────────────────────────────────────────────────────
// TELEGRAM SETUP
// ──────────────────────────────────────────────────────
async function loadSetupConfig() {
  try {
    const res = await fetch(`${API}/config`);
    const data = await res.json();
    if (!data.ok) return;
    const cfg = data.data;
    const tg = cfg.telegram || {};
    if (tg.chat_id) document.getElementById('tg-chatid').value = tg.chat_id;
    if (tg.bot_token_set) document.getElementById('tg-token').placeholder = '(token saved — paste to update)';
    const alerts = cfg.alerts || {};
    if (alerts.unknown_device !== undefined) document.getElementById('alert-unknown').checked = alerts.unknown_device;
    if (alerts.high_risk_process !== undefined) document.getElementById('alert-process').checked = alerts.high_risk_process;
    if (alerts.firewall_down !== undefined) document.getElementById('alert-firewall').checked = alerts.firewall_down;

    // Load SauceNAO config
    const saucenaoInput = document.getElementById('saucenao-key');
    if (saucenaoInput) {
      if (cfg.saucenao_api_key_set) {
        saucenaoInput.value = '';
        saucenaoInput.placeholder = '(key saved — paste to update)';
      } else {
        saucenaoInput.value = '';
        saucenaoInput.placeholder = 'Enter SauceNAO API Key...';
      }
    }
  } catch (_) {}
}

async function autoDetectChatId() {
  const token = document.getElementById('tg-token')?.value.trim();
  if (!token) { showToast('Paste your bot token first', 'error'); return; }
  showToast('Detecting chat ID...', 'info');
  try {
    const res = await fetch(`${API}/telegram/get-chatid`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bot_token: token })
    });
    const data = await res.json();
    if (data.ok && data.chat_id) {
      document.getElementById('tg-chatid').value = data.chat_id;
      showToast(`Chat ID found: ${data.chat_id}`, 'success');
    } else {
      showToast(data.error || 'Could not detect. Send a message to your bot first.', 'error', 5000);
    }
  } catch (e) { showToast(e.message, 'error'); }
}

async function saveTelegramConfig() {
  const token = document.getElementById('tg-token')?.value.trim();
  const chatId = document.getElementById('tg-chatid')?.value.trim();
  const msg = document.getElementById('tg-status');
  try {
    const res = await fetch(`${API}/config`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ telegram: { bot_token: token, chat_id: chatId, enabled: !!(token && chatId) } })
    });
    const data = await res.json();
    if (data.ok) {
      if (msg) { msg.textContent = '✓ Settings saved!'; msg.className = 'form-message success'; }
      showToast('Telegram config saved', 'success');
    } else throw new Error(data.error);
  } catch (e) {
    if (msg) { msg.textContent = `Error: ${e.message}`; msg.className = 'form-message error'; }
  }
}

async function sendTestTelegram() {
  const msg = document.getElementById('tg-status');
  if (msg) { msg.textContent = 'Sending test message...'; msg.className = 'form-message'; msg.style.display = 'block'; msg.style.color = 'var(--text-muted)'; }
  try {
    const res = await fetch(`${API}/telegram/test`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      if (msg) { msg.textContent = '✓ Test message sent! Check your Telegram.'; msg.className = 'form-message success'; }
      showToast('Test message sent to Telegram!', 'success');
    } else {
      if (msg) { msg.textContent = `Failed: ${data.error}`; msg.className = 'form-message error'; }
    }
  } catch (e) {
    if (msg) { msg.textContent = `Error: ${e.message}`; msg.className = 'form-message error'; }
  }
}

async function saveAlertSettings() {
  const alerts = {
    unknown_device:            document.getElementById('alert-unknown')?.checked ?? true,
    failed_logins_threshold:   5,
    high_risk_process:         document.getElementById('alert-process')?.checked ?? true,
    firewall_down:             document.getElementById('alert-firewall')?.checked ?? true,
  };
  try {
    await fetch(`${API}/config`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ alerts })
    });
    showToast('Alert settings saved', 'success');
  } catch (e) { showToast('Failed to save settings', 'error'); }
}

async function saveSauceNAOConfig() {
  const key = document.getElementById('saucenao-key')?.value.trim();
  const msg = document.getElementById('saucenao-status');
  if (msg) { msg.textContent = 'Saving key...'; msg.className = 'form-message'; }
  try {
    const res = await fetch(`${API}/config`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ saucenao_api_key: key })
    });
    const data = await res.json();
    if (data.ok) {
      if (msg) { msg.textContent = '✓ API Key saved successfully!'; msg.className = 'form-message success'; }
      showToast('SauceNAO API Key saved', 'success');
      if (key) {
        document.getElementById('saucenao-key').value = '';
        document.getElementById('saucenao-key').placeholder = '(key saved — paste to update)';
      } else {
        document.getElementById('saucenao-key').placeholder = 'Enter SauceNAO API Key...';
      }
    } else throw new Error(data.error);
  } catch (e) {
    if (msg) { msg.textContent = `Error: ${e.message}`; msg.className = 'form-message error'; }
    showToast('Failed to save SauceNAO API Key', 'error');
  }
}

// ──────────────────────────────────────────────────────
// Toasts
// ──────────────────────────────────────────────────────
function showToast(msg, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'toastOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ──────────────────────────────────────────────────────
// Security Score Gauge
// ──────────────────────────────────────────────────────
function updateGauge(score) {
  // Use percentage offset directly since pathLength="100" is set in SVG
  const offset = 100 - score;
  const fill = document.getElementById('gauge-fill');
  if (fill) {
    fill.setAttribute('stroke-dashoffset', offset);
    fill.setAttribute('stroke', 'url(#gauge-grad)');
  }

  // Score number
  const scoreEl = document.getElementById('gauge-score');
  if (scoreEl) scoreEl.textContent = score;

  // Score status pill badge
  const { label, color } = getScoreLabel(score);
  const labelBar = document.getElementById('gauge-score-label-bar');
  if (labelBar) {
    const palettes = {
      '#00e699': { bg: '#e6fff5', border: '#00e699', text: '#006644', dot: '#00e699' },
      '#88ff44': { bg: '#f0ffe6', border: '#88ff44', text: '#3a6600', dot: '#88ff44' },
      '#ffcc00': { bg: '#fff9e0', border: '#ffcc00', text: '#7a5700', dot: '#ffcc00' },
      '#ff9944': { bg: '#fff3e6', border: '#ff9944', text: '#8a3d00', dot: '#ff9944' },
      '#ff4455': { bg: '#fff0f2', border: '#ff4455', text: '#8a0010', dot: '#ff4455' },
    };
    const p = palettes[color] || palettes['#ff4455'];
    labelBar.style.background = p.bg;
    labelBar.style.borderColor = p.border;
    labelBar.style.color = p.text;
    const dot = document.getElementById('gauge-status-dot');
    if (dot) dot.style.background = p.dot;
    const textEl = document.getElementById('gauge-status-text');
    if (textEl) textEl.textContent = label.toUpperCase();
  }

  document.getElementById('gauge-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();

  // Update mini ring
  const maxMini = 150.8;
  const miniOffset = maxMini - (score / 100) * maxMini;
  const miniRing = document.getElementById('score-ring-path');
  if (miniRing) miniRing.style.strokeDashoffset = miniOffset;
  const miniVal = document.getElementById('score-value-mini');
  if (miniVal) miniVal.textContent = score;
}

function getScoreLabel(score) {
  if (score >= 90) return { label: 'Excellent', color: '#00ff88' };
  if (score >= 75) return { label: 'Good', color: '#88ff44' };
  if (score >= 55) return { label: 'Fair', color: '#ffcc00' };
  if (score >= 35) return { label: 'At Risk', color: '#ff9944' };
  return { label: 'Critical', color: '#ff4455' };
}

// ──────────────────────────────────────────────────────
// Main Status Fetch (polls every 10s)
// ──────────────────────────────────────────────────────
async function fetchAll() {
  await Promise.all([
    fetchSystemStatus(),
    fetchPorts(),
    loadAgents(),
    fetchAlerts(),
    fetchBluetoothData(),
    refreshUsbStatus()
  ]);
}

async function fetchStatus() {
  try {
    const res = await fetch(`${API}/status`);
    if (!res.ok) throw new Error('API error');
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'Unknown error');

    const s = data;
    const scoreInfo = getScoreLabel(s.security_score);
    _lastSecurityScore = s.security_score;

    // Score gauge + header
    updateGauge(s.security_score);
    document.getElementById('score-status-label').textContent = scoreInfo.label;
    document.getElementById('score-status-label').style.color = scoreInfo.color;

    // Stat cards
    setStatCard('stat-score', s.security_score, '/100', `${scoreInfo.label}`,
      s.security_score >= 75 ? 'good' : (s.security_score >= 50 ? 'warn' : 'bad'));
    setStatCard('stat-devices', s.unknown_devices === 0 ? '?' : s.unknown_devices,
      '', s.unknown_devices === 0 ? 'No unknowns' : `${s.unknown_devices} unknown device(s)!`,
      s.unknown_devices === 0 ? 'good' : 'bad');
    setStatCard('stat-firewall', s.firewall_ok ? 'ON' : 'OFF', '',
      s.firewall_ok ? 'All profiles active' : 'Firewall is partially/fully off!',
      s.firewall_ok ? 'good' : 'bad');
    setStatCard('stat-av', s.antivirus_ok ? 'ON' : 'OFF', '',
      s.antivirus_ok ? (s.realtime_ok ? 'Real-time protection active' : 'Real-time protection off!') : 'Antivirus disabled!',
      s.antivirus_ok && s.realtime_ok ? 'good' : 'bad');

    // System info
    const sys = s.system;
    const sysGrid = document.getElementById('sys-grid');
    if (sysGrid) {
      sysGrid.innerHTML = `
        <div class="sys-row"><span class="sys-key">Hostname</span><span class="sys-val">${sys.hostname}</span></div>
        <div class="sys-row"><span class="sys-key">Uptime</span><span class="sys-val">${sys.uptime_hours}h</span></div>
        <div class="sys-row"><span class="sys-key">Memory</span><span class="sys-val">${sys.memory_used_gb}/${sys.memory_total_gb} GB</span></div>
        <div class="sys-row"><span class="sys-key">Pending Updates</span><span class="sys-val ${s.pending_updates > 5 ? 'text-orange' : ''}">${s.pending_updates < 0 ? 'Unknown' : s.pending_updates}</span></div>
      `;
    }
    const cpuVal = document.getElementById('cpu-val');
    if (cpuVal) cpuVal.textContent = `${sys.cpu_percent}%`;
    const cpuBar = document.getElementById('cpu-bar');
    if (cpuBar) cpuBar.style.width = `${sys.cpu_percent}%`;
    const memVal = document.getElementById('mem-val');
    if (memVal) memVal.textContent = `${sys.memory_percent}%`;
    const memBar = document.getElementById('mem-bar');
    if (memBar) memBar.style.width = `${sys.memory_percent}%`;

    if (window.resourceHistory) {
      if (window.resourceHistory.length === 0) {
        for (let i = 0; i < 40; i++) {
          window.resourceHistory.push({ cpu: sys.cpu_percent, mem: sys.memory_percent });
        }
      } else if (window.updateResourceChartData) {
        window.updateResourceChartData(sys.cpu_percent, sys.memory_percent);
      }
    }
    
    // Update the SVG Neo-Brutalist live resource widget
    if (typeof updateResourceWidget === 'function') {
      updateResourceWidget(sys.cpu_percent, sys.memory_percent);
    }

    // Deductions
    const dl = document.getElementById('deductions-list');
    if (s.deductions && s.deductions.length > 0) {
      dl.innerHTML = s.deductions.map(d => renderInteractiveDeduction(d)).join('');
    } else {
      dl.innerHTML = `<div class="deduction-item none">✓ No security issues found!</div>`;
    }

    // Alert for unknown devices
    if (s.unknown_devices > 0) {
      document.getElementById('alert-text').textContent =
        `⚠️ ${s.unknown_devices} unknown device(s) detected on your network! Check the Network tab.`;
      document.getElementById('alerts-bar').style.display = 'block';
    }

    // Connection indicator
    const connInd = document.getElementById('status-indicator');
    if (connInd) connInd.style.opacity = '1';

  } catch (e) {
    console.error('Status fetch failed:', e);
    const connInd = document.getElementById('status-indicator');
    if (connInd) connInd.style.opacity = '0.4';
    showApiError();
  }
}

function showApiError() {
  // Silently mark as offline - don't corrupt the deductions panel with error messages
  const dl = document.getElementById('deductions-list');
  if (dl && dl.querySelector('.loading')) {
    // Only show offline message if still in initial loading state
    dl.innerHTML = `<div class="deduction-item" style="color:var(--text-secondary); font-size:12px; padding: 8px 0;">
      ⏳ Waiting for server connection...
    </div>`;
  }
}

function renderInteractiveDeduction(d) {
  let title = d;
  let description = '';
  let actionHtml = '';

  if (d.includes('Firewall') && d.includes('OFF')) {
    title = '🔥 Firewall Profile Disabled';
    description = 'One or more Windows Firewall profiles are turned off, exposing your computer to network intrusions.';
    actionHtml = `<button class="btn-sm" onclick="fixFirewall(this)" style="background:var(--cyan); color:#000; border:none; margin-top:6px; font-weight:700;">Enable Firewall</button>`;
  } else if (d.includes('Antivirus is disabled')) {
    title = '🛡️ Defender Antivirus Disabled';
    description = 'Your system has no active antivirus protection enabled.';
    actionHtml = `<button class="btn-sm" onclick="openDefenderSettings()" style="background:var(--cyan); color:#000; border:none; margin-top:6px; font-weight:700;">Open Defender Settings</button>`;
  } else if (d.includes('Real-time protection is OFF')) {
    title = '⚡ Real-time Protection Off';
    description = 'Active scanning of newly created files and processes is disabled, making it easy for malware to execute.';
    actionHtml = `<button class="btn-sm" onclick="openDefenderSettings()" style="background:var(--cyan); color:#000; border:none; margin-top:6px; font-weight:700;">Open Defender Settings</button>`;
  } else if (d.includes('signatures') && d.includes('old')) {
    title = '🔄 Antivirus Signatures Outdated';
    description = 'Defender signatures are more than 7 days old. New threats may not be detected.';
    actionHtml = `<button class="btn-sm" onclick="updateDefenderSignatures(this)" style="background:var(--cyan); color:#000; border:none; margin-top:6px; font-weight:700;">Update Antivirus</button>`;
  } else if (d.includes('risky port')) {
    const countMatch = d.match(/(\d+) risky port/);
    const count = countMatch ? countMatch[1] : 'Some';
    title = `⚠️ ${count} Dangerous Ports Open`;
    description = 'Services like RDP, SMB, or Telnet are currently open, which attackers can use to access or breach your PC.';
    actionHtml = `<button class="btn-sm" onclick="goToPortsFromSecScore()" style="background:var(--cyan); color:#000; border:none; margin-top:6px; font-weight:700;">Go to Ports Tab</button>`;
  } else if (d.includes('pending updates')) {
    const countMatch = d.match(/(\d+) pending update/);
    const count = countMatch ? countMatch[1] : 'Several';
    title = `⚙️ ${count} Windows Updates Pending`;
    description = 'Security updates are waiting to be installed. Leaving them uninstalled leaves your PC vulnerable to known exploits.';
    actionHtml = `<button class="btn-sm" onclick="openWindowsUpdates(this)" style="background:var(--cyan); color:#000; border:none; margin-top:6px; font-weight:700;">Open Windows Update</button>`;
  } else if (d.includes('Could not verify')) {
    title = '❓ Verification Service Warning';
    description = 'The system monitor was unable to verify firewall or antivirus status due to permission limits.';
    actionHtml = `<span style="font-size:11px; color:#aaa;">Run Security Suite as Administrator to fix this.</span>`;
  }

  // Generate expandable accordion-like deduction item
  return `
    <div class="deduction-card" style="margin-bottom: 8px; background: rgba(255, 68, 85, 0.04); border-left: 3px solid #ff4455; border-radius: 4px; border: 1px solid rgba(255, 68, 85, 0.1); border-left-width: 3px; font-family:'Inter', sans-serif;">
      <div onclick="this.parentElement.querySelector('.deduction-card-details').style.display = this.parentElement.querySelector('.deduction-card-details').style.display === 'none' ? 'block' : 'none';" 
           style="padding: 10px 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; user-select: none;">
        <span style="font-size: 13px; font-weight: 700; color: #ff8899;">${title}</span>
        <span style="font-size: 10px; color: #ff8899; opacity: 0.8; font-weight:800;">[CLICK FOR STEPS]</span>
      </div>
      <div class="deduction-card-details" style="display: none; padding: 0 12px 12px 12px; font-size: 12px; color: #ccc; border-top: 1px solid rgba(255, 68, 85, 0.05); padding-top: 8px;">
        <p style="margin: 0 0 8px 0; line-height: 1.4;">${description}</p>
        ${actionHtml}
      </div>
    </div>
  `;
}

async function fixFirewall(btn) {
  btn.disabled = true;
  btn.textContent = 'Enabling...';
  try {
    const res = await fetch(`${API}/firewall/enable`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      showToast('✓ Windows Firewall enabled!', 'success');
      fetchStatus();
    } else throw new Error(data.error);
  } catch(e) {
    showToast(`Failed: ${e.message}`, 'error');
    btn.disabled = false;
    btn.textContent = 'Enable Firewall';
  }
}

async function openDefenderSettings() {
  try {
    const res = await fetch(`${API}/defender/open`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      showToast('Opening Windows Security Settings on your PC...', 'info');
    } else throw new Error(data.error);
  } catch(e) {
    showToast(`Failed: ${e.message}`, 'error');
  }
}

async function updateDefenderSignatures(btn) {
  btn.disabled = true;
  btn.textContent = 'Updating...';
  try {
    const res = await fetch(`${API}/defender/update`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      showToast('Triggered antivirus signature updates in background.', 'success');
      setTimeout(fetchStatus, 5000);
    } else throw new Error(data.error);
  } catch(e) {
    showToast(`Failed: ${e.message}`, 'error');
    btn.disabled = false;
    btn.textContent = 'Update Antivirus';
  }
}

async function openWindowsUpdates(btn) {
  try {
    const res = await fetch(`${API}/system/open-update`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      showToast('Opening Windows Update settings on your PC...', 'info');
    } else throw new Error(data.error);
  } catch(e) {
    showToast(`Failed: ${e.message}`, 'error');
  }
}

function goToPortsFromSecScore() {
  _highlightRiskyPorts = true;
  
  // Inject the pulse animation styling dynamically if not present
  if (!document.getElementById('pulse-glow-style')) {
    const style = document.createElement('style');
    style.id = 'pulse-glow-style';
    style.textContent = `
      @keyframes pulseGlow {
        0% { background-color: rgba(255, 68, 85, 0.08); }
        50% { background-color: rgba(255, 68, 85, 0.25); }
        100% { background-color: rgba(255, 68, 85, 0.08); }
      }
    `;
    document.head.appendChild(style);
  }
  
  showTab('ports');
}

function setStatCard(id, value, suffix, sub, state) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value + suffix;

  const subId = id.replace('stat-', 'stat-') + '-sub';
  const subEl = document.getElementById(subId);
  if (subEl) {
    subEl.textContent = sub;
    subEl.style.color = state === 'good' ? '#00ff88' : (state === 'bad' ? '#ff4455' : '#ff9944');
  }
}

// ──────────────────────────────────────────────────────
// Network Devices
// ──────────────────────────────────────────────────────
async function loadDevices() {
  const grid = document.getElementById('device-grid');
  grid.innerHTML = `<div class="device-loading"><div class="spinner"></div><p>Scanning your network...</p></div>`;

  try {
    const res = await fetch(`${API}/devices`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);

    const { devices, summary, local_ip, gateway, subnet } = data.data;
    _lastDevices = devices || [];

    // Update sub-header
    document.getElementById('network-sub').textContent =
      `${summary.total_devices} devices · ${summary.approved} approved · ${summary.unknown} unknown · Gateway: ${gateway || 'n/a'} · Subnet: ${subnet}`;

    if (!devices || devices.length === 0) {
      grid.innerHTML = `<div class="device-loading"><p>No devices found. Try clicking "Rescan".</p></div>`;
      return;
    }

    // Sort: unknown first, then self, then approved
    const sorted = [...devices].sort((a, b) => {
      const order = { unknown: 0, self: 1, approved: 2 };
      return (order[a.status] ?? 3) - (order[b.status] ?? 3);
    });

    grid.innerHTML = sorted.map(d => deviceCardHTML(d)).join('');

    // Update overview alerts for unknown devices
    renderOverviewAlerts(devices.filter(d => d.status === 'unknown'));

  } catch (e) {
    grid.innerHTML = `<div class="device-loading"><p style="color:#ff4455">Error: ${e.message}<br><small>Is the backend server running?</small></p></div>`;
  }
}

function deviceIcon(vendor, status, os) {
  if (status === 'self') return '🖥️';
  if (os === 'Apple (iOS/macOS)') return '🍎';
  if (os === 'Android') return '🤖';
  if (os === 'Windows/PC') return '🪟';
  if (os === 'Router/Gateway') return '🌐';
  if (os === 'Google Cast / Nest') return '📺';
  
  const v = (vendor || '').toLowerCase();
  if (v.includes('apple')) return '🍎';
  if (v.includes('samsung') || v.includes('xiaomi')) return '📱';
  if (v.includes('google') || v.includes('nest')) return '🔵';
  if (v.includes('raspberry')) return '🍓';
  if (v.includes('vmware') || v.includes('virtual')) return '💻';
  return '📡';
}

function deviceCardHTML(d) {
  const statusLabel = { approved: 'Approved', unknown: 'Unknown', self: 'This Device' };
  const badgeClass = { approved: 'badge-approved', unknown: 'badge-unknown', self: 'badge-self' };

  let mainActions = '';
  if (d.status === 'unknown') {
    mainActions = `<button class="btn-approve" onclick="event.stopPropagation(); openApproveModal('${d.mac}','${d.ip}','${d.vendor}')">✓ Approve</button>`;
  } else if (d.status === 'approved') {
    mainActions = `<button class="btn-sm" onclick="event.stopPropagation(); removeWhitelist('${d.mac}')">✕ Revoke</button>`;
  }

  // Active Control Actions
  const activeControls = d.status !== 'self' ? `
    <div class="active-controls" onclick="event.stopPropagation()">
      <button class="btn-action" onclick="actionDeepScan('${d.ip}')" title="Scan for open ports">🔍 Scan</button>
      <button class="btn-action btn-danger-action" onclick="actionBlockIp('${d.ip}')" title="Block from PC">🚫 Block</button>
      <button class="btn-action" onclick="actionWol('${d.mac}')" title="Wake up device">⚡ Wake</button>
    </div>
  ` : '';

  const randBadge = d.is_randomized_mac ? `<span class="badge-private-mac" title="Device is hiding its true hardware vendor">🛡️ Private MAC</span>` : '';
  const osBadge = d.os_guess && d.os_guess !== 'Unknown' ? `<span class="badge-os">${d.os_guess}</span>` : '';

  return `
    <div class="device-card status-${d.status}" onclick="showDeviceDetail('${d.mac}')">
      <div class="device-header">
        <span class="device-icon">${deviceIcon(d.vendor, d.status, d.os_guess)}</span>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
          <span class="device-status-badge ${badgeClass[d.status] || 'badge-unknown'}">${statusLabel[d.status] || 'Unknown'}</span>
          ${randBadge}
          ${osBadge}
        </div>
      </div>
      <div class="device-name">${d.approved_name || d.hostname || 'Unknown Device'}</div>
      <div class="device-vendor">${d.vendor || 'Unknown Vendor'}</div>
      <div class="device-ip">${d.ip}</div>
      <div class="device-mac">${d.mac}</div>
      <div class="device-actions" onclick="event.stopPropagation()">
        ${mainActions}
        ${activeControls}
      </div>
    </div>`;
}

// ─── ACTIVE CONTROLS JS ───

async function actionDeepScan(ip) {
  showToast(`Scanning ports on ${ip}... hang tight.`, 'info', 6000);
  try {
    const res = await fetch(`${API}/device/offensive-scan`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ip })
    });
    const data = await res.json();
    if (data.ok) {
      showVulnerabilityModal(ip, data.open_ports, data.os_guess);
    } else throw new Error(data.error);
  } catch(e) { showToast(`Scan failed: ${e.message}`, 'error'); }
}

function showVulnerabilityModal(ip, ports, osGuess) {
  // Risk classification based on port number
  const HIGH_RISK = [21,23,135,139,445,3389,5900,1723];
  const MED_RISK  = [22,25,53,80,110,143,3306,8080,8000,8443,993,995];

  let html = `
    <div style="margin-bottom:12px; padding:10px; background:var(--card-bg); border-radius:6px; border-left:4px solid var(--cyan);">
      <span style="font-size:12px; color:var(--text-secondary);">Target</span>
      <div style="font-weight:bold; font-family:monospace;">${ip}</div>
      <span style="font-size:12px; color:var(--text-secondary);">OS Guess: <strong style="color:var(--cyan)">${osGuess || 'Unknown'}</strong></span>
    </div>`;

  if (!ports || ports.length === 0) {
    html += `<div style="padding:15px;background:rgba(0,255,0,0.1);border:1px solid var(--success);border-radius:6px;margin-top:10px;">
      ✅ No common vulnerable ports found open on this device.
    </div>`;
  } else {
    html += `<div style="display:flex;flex-direction:column;gap:8px;margin-top:10px;">`;
    ports.forEach(p => {
      const isHigh = HIGH_RISK.includes(p.port);
      const isMed  = MED_RISK.includes(p.port);
      const risk   = isHigh ? 'HIGH' : isMed ? 'MEDIUM' : 'LOW';
      const color  = isHigh ? 'var(--danger)' : isMed ? 'var(--warning)' : 'var(--success)';
      const bg     = isHigh ? 'rgba(255,0,0,0.08)' : isMed ? 'rgba(255,165,0,0.08)' : 'rgba(0,255,0,0.05)';
      html += `
        <div style="padding:10px 12px; border-left:4px solid ${color}; background:${bg}; border-radius:4px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <strong style="color:${color}; font-family:monospace;">:${p.port}</strong>
            <span style="color:var(--text-secondary); margin-left:8px; font-size:13px;">${p.service}</span>
          </div>
          <span style="font-size:11px; text-transform:uppercase; padding:2px 8px; background:${color}22; color:${color}; border-radius:10px; border:1px solid ${color}44;">${risk}</span>
        </div>`;
    });
    html += `</div>`;
  }

  document.getElementById('modal-title').innerText = `Port Scan — ${ip}`;
  document.getElementById('modal-body').innerHTML = html;
  document.getElementById('modal-footer').innerHTML = `<button class="btn-sm" onclick="closeModal()">Close</button>`;
  document.getElementById('modal-overlay').style.display = 'flex';
}

async function actionBlockIp(ip) {
  if(!confirm(`Instantly drop all traffic from ${ip} to this PC?`)) return;
  try {
    const res = await fetch(`${API}/device/block`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ip })
    });
    const data = await res.json();
    if (data.ok) showToast(`Blocked ${ip} in Windows Firewall!`, 'success');
    else throw new Error("Could not add firewall rule");
  } catch(e) { showToast(`Block failed: ${e.message}`, 'error'); }
}

async function actionWol(mac) {
  try {
    const res = await fetch(`${API}/device/wol`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mac })
    });
    const data = await res.json();
    if (data.ok) showToast(`Sent Wake-on-LAN magic packet to ${mac}`, 'success');
    else throw new Error("Could not send WOL packet");
  } catch(e) { showToast(`Wake failed: ${e.message}`, 'error'); }
}


function renderOverviewAlerts(unknowns) {
  const el = document.getElementById('overview-alerts');
  if (!el) return;
  if (unknowns.length === 0) {
    el.innerHTML = `<div class="empty-state">No unknown devices - network looks clean ?</div>`;
    return;
  }
  el.innerHTML = unknowns.map(d => `
    <div class="alert-item-small severity-high">
      <div>
        <div class="alert-title">?? Unknown Device</div>
        <div class="alert-msg">${d.ip} - ${d.mac} - ${d.vendor || 'Unknown Vendor'}</div>
      </div>
    </div>`).join('');
}

async function triggerScan() {
  const btn = document.getElementById('btn-scan');
  const icon = btn?.querySelector('svg');
  if (icon) icon.style.animation = 'spin 0.8s linear infinite';
  btn.disabled = true;
  showToast('Network scan started...', 'info');

  try {
    const res = await fetch(`${API}/scan`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      showToast(`Scan complete — ${data.data.summary.total_devices} devices found`, 'success');
      if (_currentTab === 'network') loadDevices();
      fetchStatus();
    }
  } catch (e) {
    showToast('Scan failed — is the server running?', 'error');
  } finally {
    if (icon) icon.style.animation = '';
    btn.disabled = false;
  }
}

// ──────────────────────────────────────────────────────
// Open Ports
// ──────────────────────────────────────────────────────
const RISKY_PORTS  = [21, 23, 135, 137, 138, 139, 445, 1433, 3306, 3389, 5900, 8080];
const MEDIUM_PORTS = [80, 443, 8443, 5432];

let _blockedPortsSet = new Set();

function portRisk(port) {
  if (RISKY_PORTS.includes(port)) return 'high';
  if (MEDIUM_PORTS.includes(port)) return 'medium';
  return 'low';
}

function _updateStealthBtn(active) {
  // Update new overview switch if it exists
  const overviewSwitch = document.getElementById('overview-stealth-switch');
  if (overviewSwitch) {
    overviewSwitch.checked = active;
    const statusText = document.getElementById('overview-stealth-status');
    if (statusText) {
      statusText.textContent = active ? 'ACTIVE' : 'INACTIVE';
      statusText.style.color = active ? 'var(--success)' : 'var(--text-muted)';
    }
  }

  const btn   = document.getElementById('stealth-btn');
  const icon  = document.getElementById('stealth-icon');
  const label = document.getElementById('stealth-label');
  if (!btn) return;
  if (active) {
    btn.style.background   = 'rgba(0,255,136,0.15)';
    btn.style.border       = '1px solid var(--success)';
    btn.style.color        = 'var(--success)';
    if (icon) icon.textContent       = '\uD83D\uDD12';
    if (label) label.textContent      = 'Stealth: ON';
  } else {
    btn.style.background   = '';
    btn.style.border       = '';
    btn.style.color        = '';
    if (icon) icon.textContent       = '\uD83D\uDD10';
    if (label) label.textContent      = 'Stealth Mode';
  }
}

async function toggleStealth() {
  const btn = document.getElementById('stealth-btn');
  const isOn = btn.dataset.active === 'true';
  btn.disabled = true;

  if (!isOn) {
    // Enable stealth
    if (!confirm('Enable Stealth Mode?\n\nThis will:\n• Turn on Windows Firewall (all profiles)\n• Block ALL inbound connections\n• +10 to security score\n\nYour dashboard will still work.')) {
      btn.disabled = false; return;
    }
    try {
      const res  = await fetch(`${API}/firewall/stealth`, { method: 'POST' });
      const data = await res.json();
      if (data.ok) {
        btn.dataset.active = 'true';
        _updateStealthBtn(true);
        showToast(`\uD83D\uDD12 Stealth Mode ON \u2014 Score: ${data.new_score}`, 'success', 4000);
      } else throw new Error(data.error);
    } catch(e) { showToast(`Stealth failed: ${e.message}`, 'error'); }
  } else {
    // Disable stealth
    if (!confirm('Disable Stealth Mode?\n\nInbound connections will be allowed again.')) {
      btn.disabled = false; return;
    }
    try {
      const res  = await fetch(`${API}/firewall/stealth-off`, { method: 'POST' });
      const data = await res.json();
      if (data.ok) {
        btn.dataset.active = 'false';
        _updateStealthBtn(false);
        showToast('\uD83D\uDD10 Stealth Mode OFF', 'info', 3000);
      } else throw new Error(data.error);
    } catch(e) { showToast(`Failed: ${e.message}`, 'error'); }
  }
  btn.disabled = false;
}

async function loadPorts() {
  const tbody = document.getElementById('ports-tbody');
  tbody.innerHTML = `<tr><td colspan="6" class="table-loading"><div class="spinner" style="margin:12px auto"></div></td></tr>`;

  try {
    const res = await fetch(`${API}/ports`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);

    // Fetch already-blocked ports + stealth state
    try {
      const bRes = await fetch(`${API}/firewall/blocked-ports`);
      const bData = await bRes.json();
      if (bData.ok) _blockedPortsSet = new Set(bData.ports || []);
    } catch (_) {}
    try {
      const sRes = await fetch(`${API}/status`);
      const sData = await sRes.json();
      const stealthOn = sData.stealth_active || false;
      const btn = document.getElementById('stealth-btn');
      if (btn) { btn.dataset.active = String(stealthOn); _updateStealthBtn(stealthOn); }
    } catch (_) {}

    const ports = data.data;
    if (!ports || ports.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="table-loading">No listening ports found.</td></tr>`;
      return;
    }

    tbody.innerHTML = ports.map(p => {
      const risk      = portRisk(p.port);
      const riskColor = risk === 'high' ? 'var(--danger)' : risk === 'medium' ? 'var(--warning)' : 'var(--success)';
      const riskBadge = `<span class="risk-badge risk-${risk}">${risk.toUpperCase()}</span>`;
      const isBlocked = _blockedPortsSet.has(p.port);
      const actionBtn = isBlocked
        ? `<button class="btn-sm" style="background:rgba(0,255,0,0.1);color:var(--success);border:1px solid var(--success);font-size:11px;" onclick="unblockPort(${p.port},this)">\u2713 Unblock</button>`
        : `<button class="btn-sm" style="background:rgba(255,0,0,0.1);color:var(--danger);border:1px solid var(--danger);font-size:11px;" onclick="blockPort(${p.port},this)">\uD83D\uDEAB Block</button>`;
      
      const isRisky = [21, 23, 135, 139, 445, 3389, 5900].includes(p.port);
      const rowStyle = (_highlightRiskyPorts && isRisky)
        ? `animation: pulseGlow 1.5s infinite; border: 1px solid #ff4455;`
        : '';
      const helperLabel = (_highlightRiskyPorts && isRisky)
        ? `<span style="color:#ff8899; font-size:10px; font-weight:800; display:block; margin-top:2px; font-family:'Inter', sans-serif;">⚠️ ACTION REQUIRED</span>`
        : '';

      return `<tr style="${rowStyle}">
        <td style="font-weight:700;color:${riskColor};font-family:monospace;">:${p.port}${helperLabel}</td>
        <td style="font-family:monospace;font-size:12px;">${p.address || '*'}</td>
        <td>${p.process || '\u2014'}</td>
        <td style="font-family:monospace;">${p.pid || '\u2014'}</td>
        <td>${riskBadge}</td>
        <td>${actionBtn}</td>
      </tr>`;
    }).join('');

    // Clear flag after rendering
    _highlightRiskyPorts = false;
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="table-loading" style="color:var(--danger)">Error: ${e.message}</td></tr>`;
  }
}

async function blockPort(port, btn) {
  if (!confirm(`Block ALL inbound traffic on port ${port}?\nThis adds a Windows Firewall rule.`)) return;
  btn.disabled = true; btn.textContent = 'Blocking...';
  try {
    const res  = await fetch(`${API}/firewall/block-port`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ port })
    });
    const data = await res.json();
    if (data.ok) {
      _blockedPortsSet.add(port);
      showToast(`Port ${port} blocked! Score: ${data.new_score}`, 'success');
      btn.outerHTML = `<button class="btn-sm" style="background:rgba(0,255,0,0.1);color:var(--success);border:1px solid var(--success);font-size:11px;" onclick="unblockPort(${port},this)">\u2713 Unblock</button>`;
    } else throw new Error(data.error);
  } catch (e) {
    showToast(`Block failed: ${e.message}`, 'error');
    btn.disabled = false; btn.textContent = '\uD83D\uDEAB Block';
  }
}

async function unblockPort(port, btn) {
  if (!confirm(`Remove firewall block on port ${port}?`)) return;
  btn.disabled = true; btn.textContent = 'Unblocking...';
  try {
    const res  = await fetch(`${API}/firewall/unblock-port`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ port })
    });
    const data = await res.json();
    if (data.ok) {
      _blockedPortsSet.delete(port);
      showToast(`Port ${port} unblocked.`, 'info');
      btn.outerHTML = `<button class="btn-sm" style="background:rgba(255,0,0,0.1);color:var(--danger);border:1px solid var(--danger);font-size:11px;" onclick="blockPort(${port},this)">\uD83D\uDEAB Block</button>`;
    } else throw new Error(data.error);
  } catch (e) {
    showToast(`Unblock failed: ${e.message}`, 'error');
    btn.disabled = false; btn.textContent = '\u2713 Unblock';
  }
}


// ──────────────────────────────────────────────────────
// Alerts
// ──────────────────────────────────────────────────────
async function loadAlerts() {
  try {
    const res = await fetch(`${API}/alerts`);
    const data = await res.json();
    const container = document.getElementById('alerts-container');
    const badge = document.getElementById('alert-badge');

    const unacked = (data.data || []).filter(a => !a.acknowledged);
    if (unacked.length > 0) {
      badge.textContent = unacked.length;
      badge.style.display = 'inline';
    } else {
      badge.style.display = 'none';
    }

    if (!data.data || data.data.length === 0) {
      container.innerHTML = `<div class="empty-state-large">
        <div class="empty-icon">🛡️</div>
        <h3>All Clear!</h3>
        <p>No security alerts recorded. Your system looks clean.</p>
      </div>`;
      return;
    }

    container.innerHTML = data.data.map(a => alertCardHTML(a)).join('');
  } catch (e) {
    document.getElementById('alerts-container').innerHTML =
      `<div class="empty-state-large"><p style="color:var(--red)">Could not load alerts: ${e.message}</p></div>`;
  }
}

function alertCardHTML(a) {
  const icons = { unknown_device: '📡', firewall: '🔥', process: '⚙️' };
  const icon = icons[a.type] || '⚠️';
  const time = new Date(a.timestamp).toLocaleString('en-IN');
  
  let deviceDetailsHtml = '';
  if (a.type === 'unknown_device' && a.device) {
    const d = a.device;
    const osBadge = d.os_guess && d.os_guess !== 'Unknown' ? `<span class="badge-os" style="font-size:10px; background:rgba(0,212,255,0.15); color:#00d4ff; border:1px solid #00d4ff33; padding:2px 6px; border-radius:4px; font-weight:600; margin-left:6px; display:inline-block; vertical-align:middle;">${d.os_guess}</span>` : '';
    const privateMacBadge = d.is_randomized_mac ? `<span class="badge-private-mac" style="font-size:10px; background:rgba(123,47,247,0.15); color:#7b2ff7; border:1px solid #7b2ff733; padding:2px 6px; border-radius:4px; font-weight:600; margin-left:6px; display:inline-block; vertical-align:middle;">🛡️ Private MAC</span>` : '';
    
    deviceDetailsHtml = `
      <div style="margin: 10px 0; padding: 12px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; font-size: 13px; font-family:'Inter', sans-serif;">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
          <span style="font-size:18px;">${deviceIcon(d.vendor, d.status || 'unknown', d.os_guess)}</span>
          <strong style="color:#fff; font-size:14px;">${d.hostname || 'Unknown Hostname'}</strong>
          ${osBadge}
          ${privateMacBadge}
        </div>
        <div style="color:var(--text-muted); font-size:12px; line-height:1.5; display:flex; flex-wrap:wrap; gap:12px;">
          <span>Vendor: <strong style="color:#ddd;">${d.vendor || 'Unknown'}</strong></span>
          <span>IP: <strong style="color:#ddd; font-family:var(--font-mono);">${d.ip}</strong></span>
          <span>MAC: <strong style="color:#ddd; font-family:var(--font-mono);">${d.mac}</strong></span>
        </div>
      </div>
    `;
  }

  return `<div class="alert-full severity-${a.severity} ${a.acknowledged ? 'acknowledged' : ''}" id="alert-${a.id}">
    <div class="alert-full-icon">${icon}</div>
    <div class="alert-full-body">
      <div class="alert-full-title">${a.title}</div>
      <div class="alert-full-msg">${a.message}</div>
      ${deviceDetailsHtml}
      <div class="alert-full-meta">
        <span>🕒 ${time}</span>
        <span>Severity: ${a.severity.toUpperCase()}</span>
        ${a.acknowledged ? '<span style="color:var(--green)">✓ Acknowledged</span>' : ''}
      </div>
      ${!a.acknowledged ? `<div class="alert-full-actions">
        <button class="btn-sm" onclick="acknowledgeAlert('${a.id}')" title="Dismiss this alert notification">&#x2713; Dismiss</button>
        ${a.type === 'unknown_device' ? `<button class="btn-approve" onclick="openApproveModal('${a.device?.mac}','${a.device?.ip}','${a.device?.vendor}')" title="Add this device to your trusted whitelist permanently">&#x2714; Approve &amp; Trust Device</button>` : ''}
      </div>` : ''}
    </div>
  </div>`;
}

async function acknowledgeAlert(id) {
  try {
    await fetch(`${API}/alerts/acknowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    showToast('Alert acknowledged (+100 CC)', 'success');
    if (typeof addCredits === 'function') {
        addCredits(100);
    }
    loadAlerts();
  } catch (e) {
    showToast('Failed to acknowledge', 'error');
  }
}

// ──────────────────────────────────────────────────────
// Whitelist Management
// ──────────────────────────────────────────────────────
async function addToWhitelist() {
  const mac = document.getElementById('wl-mac').value.trim();
  const name = document.getElementById('wl-name').value.trim();
  const notes = document.getElementById('wl-notes').value.trim();
  const msg = document.getElementById('wl-message');

  if (!mac) {
    msg.textContent = 'Please enter a MAC address.';
    msg.className = 'form-message error';
    return;
  }

  try {
    const res = await fetch(`${API}/whitelist/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mac, name, notes })
    });
    const data = await res.json();
    if (data.ok) {
      msg.textContent = `✓ Device ${name || mac} approved and added to whitelist.`;
      msg.className = 'form-message success';
      document.getElementById('wl-mac').value = '';
      document.getElementById('wl-name').value = '';
      document.getElementById('wl-notes').value = '';
      showToast(`Device approved: ${name || mac}`, 'success');
      loadDevices();
      fetchStatus();
      loadAlerts();
    } else {
      throw new Error(data.error);
    }
  } catch (e) {
    msg.textContent = `Error: ${e.message}`;
    msg.className = 'form-message error';
  }
}

async function removeWhitelist(mac) {
  if (!confirm(`Remove ${mac} from whitelist? It will be marked as unknown.`)) return;
  try {
    const res = await fetch(`${API}/whitelist/remove`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mac })
    });
    const data = await res.json();
    if (data.ok) {
      showToast('Device removed from whitelist', 'info');
      loadDevices();
      fetchStatus();
      loadAlerts();
    }
  } catch (e) {
    showToast('Failed to remove device', 'error');
  }
}

// ──────────────────────────────────────────────────────
// Modal
// ──────────────────────────────────────────────────────
let _currentDevice = null;

function openApproveModal(mac, ip, vendor) {
  _currentDevice = { mac, ip, vendor };
  document.getElementById('modal-title').textContent = 'Approve Device';
  document.getElementById('modal-body').innerHTML = `
    <div class="modal-detail-row"><span class="modal-detail-key">MAC Address</span><span class="modal-detail-val">${mac}</span></div>
    <div class="modal-detail-row"><span class="modal-detail-key">IP Address</span><span class="modal-detail-val">${ip}</span></div>
    <div class="modal-detail-row"><span class="modal-detail-key">Vendor</span><span class="modal-detail-val">${vendor || 'Unknown'}</span></div>
    <div style="margin-top:16px">
      <input type="text" id="modal-device-name" placeholder="Give this device a name..." class="form-input" style="width:100%" />
    </div>`;
  document.getElementById('modal-footer').innerHTML = `
    <button class="btn-sm" onclick="closeModal()">Cancel</button>
    <button class="btn-approve" onclick="confirmApprove()">✓ Approve & Whitelist</button>`;
  document.getElementById('modal-overlay').style.display = 'flex';
}

async function confirmApprove() {
  if (!_currentDevice) return;
  const name = document.getElementById('modal-device-name').value.trim() || 'My Device';
  await addDeviceDirectly(_currentDevice.mac, name, _currentDevice.vendor || '');
  closeModal();
}

async function addDeviceDirectly(mac, name, notes) {
  try {
    const res = await fetch(`${API}/whitelist/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mac, name, notes })
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`✓ ${name} approved!`, 'success');
      loadDevices();
      fetchStatus();
      loadAlerts();
    }
  } catch (e) {
    showToast('Failed to approve device', 'error');
  }
}

function showDeviceDetail(mac) {
  // Find device from last scan - quick info modal
  const d = _lastDevices.find(dev => dev.mac === mac);
  if (!d) {
    document.getElementById('modal-title').textContent = 'Device Info';
    document.getElementById('modal-body').innerHTML = `
      <div class="modal-detail-row"><span class="modal-detail-key">MAC</span><span class="modal-detail-val">${mac}</span></div>
      <p style="margin-top:12px; font-size:13px; color:var(--text-muted)">Click a device's Approve or Revoke button to manage its access.</p>`;
    document.getElementById('modal-footer').innerHTML = `<button class="btn-sm" onclick="closeModal()">Close</button>`;
    document.getElementById('modal-overlay').style.display = 'flex';
    return;
  }

  const statusLabel = { approved: 'Approved', unknown: 'Unknown', self: 'This Device' };
  const badgeClass = { approved: 'badge-approved', unknown: 'badge-unknown', self: 'badge-self' };
  const name = d.approved_name || d.hostname || 'Unknown Device';

  document.getElementById('modal-title').textContent = 'Device Connection Details';
  document.getElementById('modal-body').innerHTML = `
    <div style="display:flex; flex-direction:column; gap:12px; font-family:'Inter', sans-serif;">
      <div style="display:flex; align-items:center; gap:12px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:12px;">
        <span style="font-size:32px;">${deviceIcon(d.vendor, d.status, d.os_guess)}</span>
        <div>
          <h4 style="margin:0; font-size:18px; color:#fff;">${name}</h4>
          <span style="font-size:12px; color:#888;">${d.vendor || 'Unknown Vendor'}</span>
        </div>
      </div>
      <div class="modal-detail-row"><span class="modal-detail-key">IP Address</span><span class="modal-detail-val" style="color:#eee; font-family:var(--font-mono);">${d.ip}</span></div>
      <div class="modal-detail-row"><span class="modal-detail-key">MAC Address</span><span class="modal-detail-val" style="color:#eee; font-family:var(--font-mono);">${d.mac}</span></div>
      <div class="modal-detail-row"><span class="modal-detail-key">Status</span><span class="device-status-badge ${badgeClass[d.status]}">${statusLabel[d.status]}</span></div>
      <div class="modal-detail-row"><span class="modal-detail-key">OS Fingerprint</span><span class="modal-detail-val" style="color:#eee;">${d.os_guess || 'Unknown'}</span></div>
      <div class="modal-detail-row"><span class="modal-detail-key">Private MAC?</span><span class="modal-detail-val" style="color:#eee;">${d.is_randomized_mac ? '🛡️ Yes (Randomized)' : 'No (Hardware MAC)'}</span></div>
      <div class="modal-detail-row"><span class="modal-detail-key">Last Seen</span><span class="modal-detail-val" style="color:#eee;">${d.last_seen ? new Date(d.last_seen).toLocaleString('en-IN') : 'Just now'}</span></div>
      ${d.label ? `<div class="modal-detail-row"><span class="modal-detail-key">Label</span><span class="modal-detail-val" style="color:#eee;">${d.label}</span></div>` : ''}
    </div>
    <p style="margin-top:16px; font-size:13px; color:var(--text-muted); border-top:1px solid rgba(255,255,255,0.05); padding-top:12px; line-height:1.4;">
      <strong>How do I identify this device?</strong><br>
      • Compare this device's MAC/IP address with your phone or laptop's Wi-Fi Settings.<br>
      • If it shows "Private MAC", this device is using MAC Randomization (e.g. Apple's "Private Wi-Fi Address" or Android's "Use Randomized MAC" option).
    </p>`;
  
  let footerBtns = '';
  if (d.status === 'unknown') {
    footerBtns = `
      <button class="btn-approve" onclick="closeModal(); openApproveModal('${d.mac}','${d.ip}','${d.vendor}')">✓ Approve & Trust</button>
      <button class="btn-sm" onclick="closeModal(); actionDeepScan('${d.ip}')">🔍 Deep Scan</button>
      <button class="btn-sm" style="background:rgba(255, 68, 85, 0.1); color:#ff4455; border:1px solid #ff4455; font-size:11px;" onclick="closeModal(); actionBlockIp('${d.ip}')">🚫 Block IP</button>
    `;
  } else if (d.status === 'approved') {
    footerBtns = `
      <button class="btn-sm" onclick="closeModal(); removeWhitelist('${d.mac}')">✕ Revoke Trust</button>
    `;
  }
  document.getElementById('modal-footer').innerHTML = `
    <div style="display:flex; justify-content:space-between; width:100%; gap:8px; align-items:center;">
      <div style="display:flex; gap:8px;">${footerBtns}</div>
      <button class="btn-sm" onclick="closeModal()">Close</button>
    </div>
  `;
  document.getElementById('modal-overlay').style.display = 'flex';
}

function flagDevice(mac) {
  showToast(`Device ${mac} flagged for review`, 'error');
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
  _currentDevice = null;
}

// ──────────────────────────────────────────────────────
// Breach Check
// ──────────────────────────────────────────────────────
async function checkBreach() {
  const email = document.getElementById('breach-email').value.trim();
  const resultEl = document.getElementById('breach-result');
  const btn = document.getElementById('btn-breach');

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showToast('Please enter a valid email address', 'error');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Checking...';
  resultEl.innerHTML = `<div style="text-align:center;padding:32px"><div class="spinner" style="margin:0 auto"></div></div>`;

  try {
    const res = await fetch(`${API}/breach-check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    const data = await res.json();

    if (!data.ok) {
      resultEl.innerHTML = `<div class="breach-result-card">
        <div class="breach-result-header">
          <div class="breach-result-icon">⚠️</div>
          <div class="breach-result-title">Check Unavailable</div>
          <div class="breach-result-count">${data.error}</div>
        </div>
      </div>`;
      return;
    }

    if (!data.found) {
      resultEl.innerHTML = `<div class="breach-result-card safe">
        <div class="breach-result-header">
          <div class="breach-result-icon">✅</div>
          <div class="breach-result-title" style="color:var(--green)">Good news — No breaches found!</div>
          <div class="breach-result-count">This email was not found in any known data breaches.</div>
        </div>
        <p style="text-align:center;font-size:13px;color:var(--text-muted);margin-top:16px">
          Stay safe: still use a strong, unique password and enable 2FA.
        </p>
      </div>`;
    } else {
      resultEl.innerHTML = `<div class="breach-result-card danger">
        <div class="breach-result-header">
          <div class="breach-result-icon">⚠️</div>
          <div class="breach-result-title" style="color:var(--red)">Breaches Detected!</div>
          <div class="breach-result-count">Found in ${data.breach_count} known data breach(es)</div>
        </div>
        <div class="breach-list">
          ${data.breaches.map(b => `<div class="breach-item">
            <div class="breach-item-name">🔴 ${b.name}</div>
            <div class="breach-item-date">Date: ${b.date || 'Unknown'}</div>
            <div class="breach-item-desc">${b.description?.replace(/<[^>]*>/g, '') || ''}</div>
          </div>`).join('')}
        </div>
        <div style="margin-top:20px;padding:16px;background:rgba(255,68,85,0.06);border-radius:10px;font-size:13px;color:var(--text-secondary)">
          <strong style="color:var(--red)">Action required:</strong> Change your password for any affected services immediately and enable 2FA.
        </div>
      </div>`;
    }
  } catch (e) {
    resultEl.innerHTML = `<div class="breach-result-card">
      <div class="breach-result-header">
        <div class="breach-result-icon">❌</div>
        <div class="breach-result-title">Error</div>
        <div class="breach-result-count">${e.message}</div>
      </div>
    </div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Check Now';
  }
}

// Allow Enter key in breach input
document.getElementById('breach-email')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') checkBreach();
});

// ──────────────────────────────────────────────────────
// Alert Bar Dismiss
// ──────────────────────────────────────────────────────
function dismissAlertBar() {
  document.getElementById('alerts-bar').style.display = 'none';
}

// ──────────────────────────────────────────────────────
// Polling
// ──────────────────────────────────────────────────────
function startPolling() {
  fetchStatus();
  _pollingTimer = setInterval(() => {
    fetchStatus();
    if (_currentTab === 'alerts') loadAlerts();
  }, POLL_INTERVAL);
}

// ──────────────────────────────────────────────────────
// Init
// ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Restore sidebar collapsed preference on desktop
  if (window.innerWidth >= 801 && localStorage.getItem('sidebarCollapsed') === 'true') {
    const drawer = document.getElementById('more-drawer');
    if (drawer) drawer.classList.add('sidebar-collapsed');
    document.body.classList.add('sidebar-collapsed');
  }

  initLockScreen();
  // Synchronous login bypass for headless screenshots/testing
  if (window.location.search.includes('bypass_auth=1')) {
    _isAuthenticated = true;
    const overlay = document.getElementById('login-overlay');
    if (overlay) overlay.style.display = 'none';
    startApp();
  }
});

function initMobileBattery() {
  const badge = document.getElementById('mobile-battery-indicator');
  const icon = document.getElementById('mobile-battery-icon');
  const text = document.getElementById('mobile-battery-text');
  
  if (navigator.getBattery && badge && icon && text) {
    navigator.getBattery().then(battery => {
      badge.style.display = 'flex';
      
      function update() {
        const pct = Math.round(battery.level * 100);
        text.textContent = `${pct}%`;
        
        if (battery.charging) {
          icon.textContent = '🔌';
        } else {
          if (pct > 80) icon.textContent = '🔋';
          else if (pct > 30) icon.textContent = '🪫';
          else icon.textContent = '⚠️';
        }
      }
      
      update();
      battery.addEventListener('levelchange', update);
      battery.addEventListener('chargingchange', update);
    });
  }
}

function startApp() {
  const urlParams = new URLSearchParams(window.location.search);
  const targetTab = urlParams.get('tab') || 'overview';
  showTab(targetTab);
  loadAlertSettings();
  startPolling();
  startResourceChartLoop();
  initMobileBattery();
  
  // Start scrolling IDS log feed
  if (typeof startIdsFeed === 'function') {
    startIdsFeed();
  }
  
  // Load alerts badge on start
  setTimeout(async () => {
    try {
      const res = await fetch(`${API}/alerts`);
      const data = await res.json();
      const unacked = (data.data || []).filter(a => !a.acknowledged).length;
      if (unacked > 0) {
        const badge = document.getElementById('alert-badge');
        badge.textContent = unacked;
        badge.style.display = 'inline';
      }
    } catch (_) {}
  }, 3000);

  // Initial credits fetch
  fetchCredits();
  
  // Security Economy: Passive Income Loop (every 30s)
  setInterval(() => {
    let delta = 0;
    if (_lastSecurityScore === 100) delta = 25;
    else if (_lastSecurityScore >= 80) delta = 10;
    else if (_lastSecurityScore < 50) delta = -5;
    
    if (delta !== 0) {
      if (window.addCredits) {
        window.addCredits(delta);
      } else {
        updateCredits(delta);
      }
    }
  }, 30000);
}

// ───?? BLUETOOTH RADAR LOGIC ??───

async function fetchBluetoothData() {
  try {
    const res = await fetch(`${API}/bluetooth`);
    const json = await res.json();
    if (!json.ok) return;

    const data = json.data;
    const tbody = document.getElementById('bt-tbody');
    const badge = document.getElementById('bt-sensor-status');
    if(!tbody || !badge) return;

    if (!data.last_updated) {
      tbody.innerHTML = `<tr><td colspan="2" class="table-loading">No NetHunter node detected yet...</td></tr>`;
      return;
    }

    // Check if stale (older than 2 minutes)
    const lastUpdateMs = new Date(data.last_updated).getTime();
    const nowMs = Date.now();
    if (nowMs - lastUpdateMs > 120000) {
      badge.textContent = "Sensor Offline";
      badge.style.background = "var(--danger-color)";
    } else {
      badge.textContent = `Sensor: ${data.reporter}`;
      badge.style.background = "var(--success-color)";
    }

    if (!data.devices || data.devices.length === 0) {
      tbody.innerHTML = `<tr><td colspan="2" class="table-loading">Scanning... No devices found.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.devices.map(d => `
      <tr>
        <td><strong>${d.name || "Unknown Device"}</strong></td>
        <td style="font-family:monospace; color:var(--text-secondary)">${d.mac}</td>
      </tr>
    `).join('');

  } catch(e) {
    console.warn("BT fetch failed", e);
  }
}

let toolkitTypingInterval = null;

function typeMatrixEffect(element, text) {
  if (toolkitTypingInterval) clearInterval(toolkitTypingInterval);
  element.innerHTML = '';
  element.style.position = 'relative';
  element.style.fontFamily = '"JetBrains Mono", monospace';
  
  let i = 0;
  // create cursor span
  const cursor = document.createElement('span');
  cursor.className = 'matrix-cursor';
  cursor.textContent = '█';
  cursor.style.animation = 'blink 1s step-end infinite';
  
  element.appendChild(cursor);
  
  // Clean up text slightly for HTML
  const lines = text.split('\n');
  let cleanText = text;
  
  toolkitTypingInterval = setInterval(() => {
    if (i < cleanText.length) {
      const char = cleanText.charAt(i);
      if (char === '\n') {
        const br = document.createElement('br');
        element.insertBefore(br, cursor);
      } else {
        const textNode = document.createTextNode(char);
        element.insertBefore(textNode, cursor);
      }
      i++;
      // Auto scroll to bottom
      element.scrollTop = element.scrollHeight;
    } else {
      clearInterval(toolkitTypingInterval);
    }
  }, 10); // Super fast typing
}

async function runToolkitCommand(cmd) {
  const target = document.getElementById('toolkit-target').value.trim();
  const out = document.getElementById('toolkit-output');
  if (!target) {
    typeMatrixEffect(out, 'ERROR: Please enter a target IP or domain.\n');
    return;
  }
  
  typeMatrixEffect(out, `Initiating [${cmd.toUpperCase()}] sequence on target: ${target}\nBypassing mainframe... Standby for output...\n`);
  
  try {
    const res = await fetch(API + '/toolkit/' + cmd, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ip: target})
    });
    const data = await res.json();
    if (data.ok) {
      typeMatrixEffect(out, data.output);
    } else {
      typeMatrixEffect(out, 'CRITICAL ERROR:\n' + data.error);
    }
  } catch (e) {
    typeMatrixEffect(out, 'NETWORK FAILURE:\n' + e.message);
  }
}


// --- UPDATE NETHUNTER URL ---
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    const el = document.getElementById('nethunter-agent-url');
    if(el) el.textContent = window.location.protocol + '//' + window.location.hostname + ':8080/nethunter_bt_agent.py';
  }, 2000);
});

// --- BREACH CHECK LOGIC ---
async function checkBreach() {
  const pwdInput = document.getElementById('breach-pwd');
  const resultDiv = document.getElementById('breach-result');
  const btn = document.getElementById('btn-breach');
  const pwd = pwdInput.value;
  
  if (!pwd) {
    showToast('Please enter a password', 'error');
    return;
  }
  
  btn.disabled = true;
  btn.innerHTML = 'Checking...';
  resultDiv.style.display = 'none';
  resultDiv.className = 'breach-result';
  
  try {
    const res = await fetch(`${API}/breach/password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pwd })
    });
    
    const data = await res.json();
    
    if (!data.ok) {
      throw new Error(data.error);
    }
    
    resultDiv.style.display = 'block';
    if (data.pwned) {
      resultDiv.classList.add('breach-danger');
      resultDiv.innerHTML = `
        <div style="font-size: 24px; margin-bottom: 8px;">🚨</div>
        <h3 style="margin-bottom: 4px; color: var(--red);">DANGER! Password Leaked</h3>
        <p>${data.message}</p>
        <p style="font-size: 11px; margin-top: 8px; color: var(--text-muted);">You should immediately change this password anywhere you use it.</p>
      `;
    } else {
      resultDiv.classList.add('breach-safe');
      resultDiv.innerHTML = `
        <div style="font-size: 24px; margin-bottom: 8px;">✅</div>
        <h3 style="margin-bottom: 4px; color: var(--green);">Safe Password</h3>
        <p>${data.message}</p>
        <p style="font-size: 11px; margin-top: 8px; color: var(--text-muted);">This password hasn't been found in any known public database breaches.</p>
      `;
    }
  } catch (err) {
    showToast('Error checking password: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Check Dark Web Databases';
  }
}

// --- DRAWER NAVIGATION ---
function toggleDrawer() {
  if (window.innerWidth >= 801) {
    // Desktop: collapse/expand sidebar
    const drawer = document.getElementById('more-drawer');
    const isCollapsed = drawer.classList.contains('sidebar-collapsed');
    if (isCollapsed) {
      drawer.classList.remove('sidebar-collapsed');
      document.body.classList.remove('sidebar-collapsed');
      localStorage.setItem('sidebarCollapsed', 'false');
    } else {
      drawer.classList.add('sidebar-collapsed');
      document.body.classList.add('sidebar-collapsed');
      localStorage.setItem('sidebarCollapsed', 'true');
    }
  } else {
    // Mobile: open/close bottom drawer
    const drawer = document.getElementById('more-drawer');
    const backdrop = document.getElementById('drawer-backdrop');
    _drawerOpen = !_drawerOpen;
    
    if (_drawerOpen) {
      drawer.classList.add('open');
      backdrop.classList.add('open');
      document.body.style.overflow = 'hidden';
    } else {
      drawer.classList.remove('open');
      backdrop.classList.remove('open');
      document.body.style.overflow = '';
    }
  }
}

function closeDrawer() {
  if (_drawerOpen) toggleDrawer();
}



// --- INJECTED BY RECOVERY SCRIPT ---


function openRadarModal() {
    document.getElementById('radar-modal').style.display = 'flex';
}

async function runRadarScan() {
    const resDiv = document.getElementById('radar-results');
    resDiv.innerHTML = "<span style='color:var(--cyan);'>Initiating ARP sweep... Please wait.</span>";
    try {
        const res = await fetch('/api/scan', { method: 'POST' });
        const data = await res.json();
        if(data.ok) {
            let html = "<table style='width:100%; text-align:left; border-collapse:collapse;'>";
            html += "<tr style='color:var(--cyan); border-bottom:1px solid #333;'><th>IP Address</th><th>MAC Address</th><th>Vendor/OS</th></tr>";
            data.data.devices.forEach(d => {
                let devType = d.vendor || d.os_guess || "Unknown";
                html += `<tr><td style='padding:5px 0;'>${d.ip}</td><td>${d.mac}</td><td>${devType}</td></tr>`;
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



let cacheInterval = null;

function openCacheModal() {
    document.getElementById('cache-modal').style.display = 'flex';
    loadCachePathPref();
    fetchCacheList();
    if (cacheInterval) clearInterval(cacheInterval);
    cacheInterval = setInterval(fetchCacheList, 2000);
}

// Ensure interval is cleared when closed
document.addEventListener('DOMContentLoaded', () => {
    const cacheModal = document.getElementById('cache-modal');
    if (cacheModal) {
        const closeBtn = cacheModal.querySelector('button[onclick*="none"]');
        if (closeBtn) {
            closeBtn.onclick = function() {
                if (cacheInterval) clearInterval(cacheInterval);
                cacheModal.style.display = 'none';
            };
        }
    }
});

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function fetchCacheList() {
    try {
        const res = await fetch('http://127.0.0.1:8766/cache/list');
        const data = await res.json();
        const resDiv = document.getElementById('cache-results');
        
        if (data.ok) {
            if (data.cache.length === 0) {
                resDiv.innerHTML = "<div style='color:#888; text-align:center; margin-top:20px;'>Vault is empty.</div>";
                return;
            }
            
            let html = "";
            data.cache.forEach(t => {
                const percent = Math.round(t.progress * 100);
                const speed = formatBytes(t.downloadSpeed) + '/s';
                const downloaded = formatBytes(t.downloaded);
                const total = formatBytes(t.length);
                const isDone = percent === 100;
                
                html += `
                <div style="background:#111; border:1px solid #333; padding:15px; margin-bottom:10px; border-radius:4px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                        <strong style="color:var(--cyan); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:70%;">${t.name || 'Fetching Metadata...'}</strong>
                        <span style="color:#888; font-size:12px;">${isDone ? 'Completed' : speed}</span>
                    </div>
                    
                    <div style="background:#222; height:10px; border-radius:5px; overflow:hidden; margin-bottom:10px;">
                        <div style="background:${isDone ? 'var(--green)' : 'var(--cyan)'}; height:100%; width:${percent}%;"></div>
                    </div>
                    
                    <div style="display:flex; justify-content:space-between; font-size:12px; color:#aaa; align-items:center;">
                        <span>${percent}% (${downloaded} / ${total})</span>
                        <div>
                            ${isDone ? `<button onclick="playCached('${t.infoHash}')" style="background:var(--green); color:#000; border:none; padding:4px 10px; cursor:pointer; border-radius:2px; margin-right:5px; font-weight:bold;">PLAY</button>` : ''}
                            <button onclick="deleteCache('${t.magnet}')" style="background:#ff4444; color:#fff; border:none; padding:4px 10px; cursor:pointer; border-radius:2px;">TRASH</button>
                        </div>
                    </div>
                </div>`;
            });
            resDiv.innerHTML = html;
        }
    } catch(e) {
        console.error("Cache fetch error:", e);
        const resDiv = document.getElementById('cache-results');
        if (resDiv) {
            resDiv.innerHTML = `
            <div style="color:#ff8800; text-align:center; padding:20px; font-family:'Space Grotesk',sans-serif;">
                <div style="font-size:24px; margin-bottom:8px;">⚠️</div>
                <div style="font-weight:bold; margin-bottom:4px;">Cache Engine Offline</div>
                <div style="font-size:12px; color:#888;">The P2P background process is offline or initializing...</div>
            </div>`;
        }
    }
}

function saveCachePathPref() {
    const path = document.getElementById('cache-path-input').value.trim();
    if (path) localStorage.setItem('cache_vault_path', path);
    else localStorage.removeItem('cache_vault_path');
}

function loadCachePathPref() {
    const saved = localStorage.getItem('cache_vault_path');
    const el = document.getElementById('cache-path-input');
    if (saved && el) el.value = saved;
}

async function addCacheTask() {
    const magnet = document.getElementById('cache-magnet-input').value.trim();
    if (!magnet) return;
    const pathEl = document.getElementById('cache-path-input');
    const savePath = pathEl ? pathEl.value.trim() : '';
    if (savePath) localStorage.setItem('cache_vault_path', savePath);
    document.getElementById('cache-magnet-input').value = '';
    
    const url = new URL('http://127.0.0.1:8766/cache/add');
    url.searchParams.set('magnet', magnet);
    if (savePath) url.searchParams.set('path', savePath);
    
    try {
        showToast('📥 Download started — seeding to ' + (savePath || 'default folder'), 'info');
        await fetch(url.toString());
        fetchCacheList();
    } catch(e) {
        showToast('❌ Failed to start download: ' + e.message, 'error');
    }
}

async function deleteCache(magnet) {
    if (!confirm("Delete this file permanently from disk?")) return;
    try {
        await fetch(`http://127.0.0.1:8766/cache/delete?magnet=${encodeURIComponent(magnet)}`);
        fetchCacheList();
    } catch(e) {}
}

function playCached(infoHash) {
    document.getElementById('cache-modal').style.display = 'none';
    if (cacheInterval) clearInterval(cacheInterval);
    
    // Play directly using the stream endpoint
    document.getElementById('video-player').src = `http://127.0.0.1:8766/play/${infoHash}`;
    document.getElementById('video-player').play();
}




// --- DOOMSCROLL LOGIC ---
async function loadDoomScroll() {
    const container = document.getElementById('doomscroll-container');
    container.innerHTML = '<div style="text-align:center; padding:50px; color:#aa00ff; font-weight:bold; grid-column: 1 / -1;">Connecting to The Hive...</div>';
    
    try {
        const res = await fetch(`${API}/doomscroll`);
        const data = await res.json();
        if(data.ok && data.posts) {
            container.innerHTML = '';
            data.posts.forEach(post => {
                const card = document.createElement('div');
                card.className = 'doom-card';
                
                let mediaHtml = '';
                if(post.type === 'image') {
                    mediaHtml = `<img src="${post.media_url}" class="doom-media" loading="lazy" onclick="window.open('${post.permalink}', '_blank')" style="cursor:pointer;" />`;
                } else if (post.type === 'video') {
                    mediaHtml = `<video src="${post.media_url}" class="doom-media" controls preload="none" poster="${post.thumbnail || ''}" loop></video>`;
                }
                
                card.innerHTML = `
                    ${mediaHtml}
                    <div class="doom-content">
                        <div class="doom-title">${post.title}</div>
                        <div class="doom-meta">
                            <span>${post.subreddit}</span>
                            <span>?? ${post.score}</span>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
        } else {
            container.innerHTML = `<div style="color:red; padding:20px; grid-column: 1 / -1;">Failed to load The Hive: ${data.error || 'Unknown error'}</div>`;
        }
    } catch(err) {
        container.innerHTML = `<div style="color:red; padding:20px; grid-column: 1 / -1;">Connection Error to The Hive</div>`;
    }
}


async function loadAlertSettings() {
    try {
        const res = await fetch(`${API}/config`);
        const data = await res.json();
        if(data.ok && data.data && data.data.alerts) {
            const alerts = data.data.alerts;
            const unknownEl = document.getElementById('alert-unknown');
            const bruteEl = document.getElementById('alert-bruteforce');
            const processEl = document.getElementById('alert-process');
            const firewallEl = document.getElementById('alert-firewall');
            
            if(unknownEl) unknownEl.checked = alerts.unknown_device ?? true;
            if(bruteEl) bruteEl.checked = alerts.brute_force ?? true;
            if(processEl) processEl.checked = alerts.high_risk_process ?? true;
            if(firewallEl) firewallEl.checked = alerts.firewall_down ?? true;
        }
    } catch(e) {
        console.error('Failed to load alert settings', e);
    }
}

// -------------------------------------------------------------------------------------------------------------------
// Streamlink Integration
// -------------------------------------------------------------------------------------------------------------------
async function launchStreamlink() {
  const urlInput = document.getElementById('media-url-input');
  if (!urlInput || !urlInput.value) {
    alert("Please enter a media URL to stream!");
    return;
  }
  const url = urlInput.value.trim();
  try {
    const res = await fetch(API + '/media/streamlink', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url: url})
    });
    const data = await res.json();
    if (data.ok) {
      alert(data.message);
    } else {
      alert("Error: " + data.error);
    }
  } catch (err) {
    alert("Network error calling streamlink API.");
  }
}

// -------------------------------------------------------------------------------------------------------------------
// NetHunter / Remote Agent C2 Logic
// -------------------------------------------------------------------------------------------------------------------
let currentActionTarget = null;
let actionPollInterval = null;

function openActionPanel(deviceId) {
  currentActionTarget = deviceId;
  document.getElementById('action-target-id').textContent = deviceId;
  document.getElementById('action-panel').style.display = 'block';
  document.getElementById('action-terminal-output').textContent = `[+] Connected to agent: ${deviceId}\n[*] Awaiting commands...\n`;
  
  // Start polling for results
  if (actionPollInterval) clearInterval(actionPollInterval);
  actionPollInterval = setInterval(pollActionResults, 2000);
}

function closeActionPanel() {
  document.getElementById('action-panel').style.display = 'none';
  if (actionPollInterval) clearInterval(actionPollInterval);
  currentActionTarget = null;
}

function sendPredefCommand(cmd) {
  document.getElementById('action-cmd-input').value = cmd;
  sendRemoteCommand();
}

async function sendRemoteCommand() {
  if (!currentActionTarget) return;
  const input = document.getElementById('action-cmd-input');
  const cmd = input.value.trim();
  if (!cmd) return;
  
  const term = document.getElementById('action-terminal-output');
  term.textContent += `\n[User@Dashboard]~# ${cmd}\n[*] Queuing command...\n`;
  input.value = '';
  
  try {
    const res = await fetch(`${API}/agents/${currentActionTarget}/command`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({command: cmd})
    });
    const data = await res.json();
    if (data.ok) {
      term.textContent += `[+] Command queued. Waiting for agent execution...\n`;
      term.scrollTop = term.scrollHeight;
    } else {
      term.textContent += `[-] Failed to queue: ${data.error}\n`;
    }
  } catch (err) {
    term.textContent += `[-] Network error queueing command.\n`;
  }
}

let lastResultCount = 0;
async function pollActionResults() {
  if (!currentActionTarget) return;
  try {
    const res = await fetch(`${API}/agents/${currentActionTarget}/results`);
    const data = await res.json();
    if (data.ok && data.results) {
      if (data.results.length > lastResultCount) {
        const newResults = data.results.slice(lastResultCount);
        lastResultCount = data.results.length;
        
        const term = document.getElementById('action-terminal-output');
        newResults.forEach(r => {
           term.textContent += `\n--- Result: ${r.command} ---\n${r.output}\n`;
        });
        term.scrollTop = term.scrollHeight;
      }
    }
  } catch (err) {
    // silently fail polling
  }
}


// ---------------------------------------------------------------------------------------------------
// Packet Matrix Logic
// ---------------------------------------------------------------------------------------------------
let snifferInterval = null;

async function toggleSniffer() {
  const btn = document.getElementById("btn-sniffer-start");
  const statusEl = document.getElementById("sniffer-status");
  
  if (btn.innerText === "START SNIFFER") {
    // Start it
    btn.innerText = "STOP SNIFFER";
    btn.style.background = "var(--red)";
    statusEl.innerText = "ONLINE";
    statusEl.style.color = "var(--green)";
    
    await fetch("/api/network/sniffer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "start" })
    });
    
    document.getElementById("matrix-terminal").innerText = "Sniffer initialized. Awaiting packets...\n";
    
    // Poll every 1 second
    snifferInterval = setInterval(pollSniffer, 1000);
  } else {
    // Stop it
    btn.innerText = "START SNIFFER";
    btn.style.background = "var(--cyan)";
    statusEl.innerText = "OFFLINE";
    statusEl.style.color = "var(--red)";
    
    clearInterval(snifferInterval);
    snifferInterval = null;
    
    await fetch("/api/network/sniffer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "stop" })
    });
    
    const term = document.getElementById("matrix-terminal");
    term.innerText += "\n[SYSTEM] Sniffer Offline.";
  }
}

async function pollSniffer() {
  try {
    const res = await fetch("/api/network/sniffer");
    const data = await res.json();
    
    if (data.ok && data.packets && data.packets.length > 0) {
      const term = document.getElementById("matrix-terminal");
      
      data.packets.forEach(p => {
        let color = "#0f0"; // default TCP
        if (p.protocol === "UDP") color = "#00ffff";
        if (p.protocol === "ICMP") color = "#ff00ff";
        if (p.protocol === "SYS") color = "#ff0000";
        
        let line = "";
        if (p.protocol === "SYS") {
          line = `<span style="color:${color}">[${p.timestamp}] ${p.info || p.error}</span>\n`;
        } else {
          line = `<span style="color:#555">[${p.timestamp}]</span> <span style="color:${color};font-weight:bold;">${p.protocol}</span> <span style="color:#aaa">${p.src}</span> &rarr; <span style="color:#fff">${p.dst}</span> <span style="color:#555">(${p.size} bytes)</span>\n`;
        }
        term.innerHTML += line;
      });
      
      // Auto-scroll
      term.scrollTop = term.scrollHeight;
      
      // Prevent unbounded growth
      if (term.innerHTML.length > 50000) {
        term.innerHTML = term.innerHTML.substring(term.innerHTML.length - 25000);
      }
    }
    
    // Safety check if backend stopped
    if (data.ok && !data.running && document.getElementById("btn-sniffer-start").innerText === "STOP SNIFFER") {
        toggleSniffer(); // Reset UI
    }
  } catch (e) {
    console.error("Sniffer poll error", e);
  }
}

// ---------------------------------------------------------------------------------------------------
// USB Trap Logic
// ---------------------------------------------------------------------------------------------------
async function toggleUsbTrap() {
  const btn = document.getElementById("btn-usb-trap");
  const statusEl = document.getElementById("usb-status-text");
  
  if (btn.innerText === "ARM TRIPWIRE") {
    // Arm it
    btn.innerText = "DISARM TRIPWIRE";
    btn.style.background = "var(--red)";
    statusEl.innerText = "ARMED & WATCHING";
    statusEl.style.color = "var(--red)";
    
    await fetch("/api/usb/arm", { method: "POST" });
    refreshUsbStatus();
    
  } else {
    // Disarm it
    btn.innerText = "ARM TRIPWIRE";
    btn.style.background = "#555";
    statusEl.innerText = "DISARMED";
    statusEl.style.color = "var(--text-muted)";
    
    await fetch("/api/usb/disarm", { method: "POST" });
    refreshUsbStatus();
  }
}

async function refreshUsbStatus() {
  try {
    const res = await fetch("/api/usb/status");
    const data = await res.json();
    if (data.ok) {
        document.getElementById("usb-trap-count").innerText = `Baselines: ${data.data.baseline_count} devices`;
        
        // Sync UI if changed via backend restart
        const btn = document.getElementById("btn-usb-trap");
        const statusEl = document.getElementById("usb-status-text");
        if (data.data.armed && btn.innerText === "ARM TRIPWIRE") {
            btn.innerText = "DISARM TRIPWIRE";
            btn.style.background = "var(--red)";
            statusEl.innerText = "ARMED & WATCHING";
            statusEl.style.color = "var(--red)";
        } else if (!data.data.armed && btn.innerText === "DISARM TRIPWIRE") {
            btn.innerText = "ARM TRIPWIRE";
            btn.style.background = "#555";
            statusEl.innerText = "DISARMED";
            statusEl.style.color = "var(--text-muted)";
        }
    }
  } catch(e) {}
}

// Check USB status on boot
setTimeout(refreshUsbStatus, 2000);



// ------------------------------------------------------
// KALI TERMINAL LOGIC
// ------------------------------------------------------
let kaliTerm = null;
let kaliFitAddon = null;
let activeKaliAgent = null;
let terminalPollInterval = null;

let termBuffer = '';
document.addEventListener('DOMContentLoaded', () => {
    // Override the init for full line buffering
    setTimeout(() => {
        if(kaliTerm) {
            kaliTerm.dispose();
            kaliTerm = null;
        }
        
        const container = document.getElementById('kali-terminal');
        if (!container) return;
        
        kaliTerm = new Terminal({
          cursorBlink: true,
          theme: { background: '#000000', foreground: '#00ffcc', cursor: '#00ffcc' },
          fontFamily: 'JetBrains Mono, monospace', fontSize: 14
        });
        
        kaliFitAddon = new FitAddon.FitAddon();
        kaliTerm.loadAddon(kaliFitAddon);
        kaliTerm.open(container);
        kaliFitAddon.fit();
        
        kaliTerm.writeln('root@nethunter:~# Ready.');
        
        kaliTerm.onData(async (data) => {
            if (!activeKaliAgent) return;
            
            if (data === '\r') {
                kaliTerm.write('\r\n');
                if (termBuffer.trim().length > 0) {
                    try {
                        const res = await fetch(`${API}/agents/${activeKaliAgent}/command`, {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ cmd: termBuffer })
                        });
                        termBuffer = '';
                    } catch(e) {
                        kaliTerm.writeln(`\r\n[Error sending command: ${e.message}]`);
                    }
                } else {
                    kaliTerm.write('root@nethunter:~# ');
                }
            } else if (data === '\u007F') {
                if (termBuffer.length > 0) {
                    termBuffer = termBuffer.slice(0, -1);
                    kaliTerm.write('\b \b');
                }
            } else {
                termBuffer += data;
                kaliTerm.write(data);
            }
        });
        
        window.addEventListener('resize', () => {
            if (kaliFitAddon) kaliFitAddon.fit();
        });
    }, 1000);
});

// ------------------------------------------------------
// LOCAL SECURITY TOOLKIT LOGIC
// ------------------------------------------------------
let selectedAuditTool = 'ping';

window.selectAuditTool = function(tool) {
  selectedAuditTool = tool;
  
  // Update button background styling (yellow active, white inactive)
  const tools = ['ping', 'traceroute', 'nmap', 'nikto', 'sqlmap', 'wayback', 'archive', 'sandbox', 'duckduckgo'];
  tools.forEach(t => {
    const btn = document.getElementById(`btn-tool-${t}`);
    if (btn) {
      if (t === tool) {
        btn.style.background = '#ffcc00';
      } else {
        btn.style.background = '#fff';
      }
    }
  });

  // Update input placeholder text
  const input = document.getElementById('audit-target-input');
  if (input) {
    const placeholders = {
      ping: 'Enter IP or domain to ping (e.g. 8.8.8.8)',
      traceroute: 'Enter target IP or domain for traceroute (e.g. google.com)',
      nmap: 'Enter IP or domain for fast port scan (e.g. 192.168.1.1)',
      nikto: 'Enter target web server IP/URL for Nikto scan (e.g. 192.168.1.10)',
      sqlmap: 'Enter target HTTP URL to test for SQLi (e.g. http://192.168.1.15/page.php?id=1)',
      wayback: 'Enter URL/domain to retrieve archive history (e.g. example.com)',
      archive: 'Enter target URL to save a local HTML copy (e.g. http://example.com)',
      sandbox: 'Enter suspicious URL to safely analyze in sandbox (e.g. http://malicious.com)',
      duckduckgo: 'DuckDuckGo Browser (Target not required)'
    };
    input.placeholder = placeholders[tool] || 'Enter target...';
    if (tool === 'duckduckgo') {
      input.value = '';
      input.disabled = true;
    } else {
      input.disabled = false;
    }
  }
};

window.executeAuditTool = async function() {
  const targetInput = document.getElementById('audit-target-input');
  const consoleElem = document.getElementById('audit-console');
  const runBtn = document.getElementById('btn-run-audit');
  
  if (!targetInput || !consoleElem || !runBtn) return;
  
  const target = targetInput.value.trim();
  if (!target && selectedAuditTool !== 'duckduckgo') {
    showToast('⚠️ Target IP/Domain/URL is required.', 'warning');
    return;
  }
  
  // Set loading state
  runBtn.disabled = true;
  runBtn.textContent = 'RUNNING...';
  runBtn.style.background = '#e8e6df';
  
  consoleElem.innerHTML = `<div style="color: #ffcc00;">[~] Starting ${selectedAuditTool.toUpperCase()} diagnostics on target: ${target || 'Local Session'}...\n[~] Execution initiated. Please wait (scans may take up to 30 seconds)...</div>`;
  
  try {
    let url = `${API}/toolkit/${selectedAuditTool}`;
    if (selectedAuditTool === 'archive') {
      url = `${API}/toolkit/archive_local`;
    }
    
    const body = {};
    if (selectedAuditTool === 'sandbox') {
      body.url = target;
    } else {
      body.ip = target;
    }
    
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    
    const data = await res.json();
    if (data.ok) {
      if (selectedAuditTool === 'sandbox') {
        const r = data.data;
        let out = `URL SANDBOX ANALYSIS REPORT\n`;
        out += `===========================\n`;
        out += `Target URL: ${r.original_url}\n`;
        out += `Final URL: ${r.final_url || 'N/A'}\n`;
        out += `Page Title: ${r.title || 'N/A'}\n`;
        out += `Risk Level: ${r.risk_level.toUpperCase()}\n`;
        out += `Risk Factors:\n`;
        if (!r.risk_factors || r.risk_factors.length === 0) {
          out += `  - None detected\n`;
        } else {
          r.risk_factors.forEach(f => {
            out += `  - [!] ${f}\n`;
          });
        }
        out += `Scripts Found: ${r.scripts_found}\n`;
        if (r.redirect_chain && r.redirect_chain.length > 0) {
          out += `Redirect Chain:\n`;
          r.redirect_chain.forEach((c, idx) => {
            out += `  [${idx+1}] ${c.url} (Status: ${c.status_code})\n`;
          });
        }
        if (r.error) {
          out += `Error Details: ${r.error}\n`;
        }
        consoleElem.innerHTML = `<pre style="font-family: inherit; color: ${r.risk_level === 'high' ? '#ff3366' : r.risk_level === 'medium' ? '#ffcc00' : '#00ffcc'}; white-space: pre-wrap; margin: 0; text-align: left;">${out}</pre>`;
        showToast('✅ URL Sandbox analysis completed.', 'success');
      } else {
        const escapedOutput = (data.output || '')
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;');
        consoleElem.innerHTML = `<pre style="font-family: inherit; color: #00ffcc; white-space: pre-wrap; margin: 0; text-align: left;">${escapedOutput}</pre>`;
        showToast(`✅ ${selectedAuditTool.toUpperCase()} audit completed.`, 'success');
      }
    } else {
      consoleElem.innerHTML = `<div style="color: #ff3366; text-align: left;">[x] Scan failed: ${data.error || 'Unknown error occurred'}</div>`;
      showToast(`❌ ${selectedAuditTool.toUpperCase()} audit failed.`, 'error');
    }
  } catch (error) {
    consoleElem.innerHTML = `<div style="color: #ff3366; text-align: left;">[x] Network error connecting to toolkit daemon: ${error.message}</div>`;
    showToast('❌ Audit request failed due to connection error.', 'error');
  } finally {
    // Reset state
    runBtn.disabled = false;
    runBtn.textContent = 'RUN AUDIT';
    runBtn.style.background = '#33ccff';
    consoleElem.scrollTop = consoleElem.scrollHeight;
  }
};

function clearTerminal() {
    if (kaliTerm) {
        kaliTerm.clear();
        kaliTerm.writeln('root@nethunter:~# ');
    }
}

async function pollKaliResults() {
    if (!activeKaliAgent || !kaliTerm) return;
    try {
        const res = await fetch(`${API}/agents/${activeKaliAgent}/results`);
        const json = await res.json();
        if (json.ok && json.data && json.data.length > 0) {
            json.data.forEach(result => {
                const out = result.output || result.error || 'No output';
                kaliTerm.write(out.replace(/\n/g, '\r\n') + '\r\n');
                kaliTerm.write('root@nethunter:~# ');
            });
        }
    } catch(e) {}
}

const originalLoadAgents = loadAgents;
loadAgents = async function() {
    await originalLoadAgents();
    
    const select = document.getElementById('terminal-agent-select');
    if (!select) return;
    
    try {
        const res = await fetch(`${API}/agents`);
        const json = await res.json();
        if (json.ok && json.data && json.data.agents && json.data.agents.length > 0) {
            const currentVal = select.value;
            select.innerHTML = '<option value="">Select Target Drone...</option>';
            
            for (const agent of json.data.agents) {
                const statusIcon = agent.status === 'online' ? '🟢' : '🔴';
                select.innerHTML += `<option value="${agent.device_id}">${statusIcon} ${agent.platform} (${agent.ip})</option>`;
            }
            
            if (currentVal && select.querySelector(`option[value="${currentVal}"]`)) {
                select.value = currentVal;
            }
            
            select.onchange = function() {
                activeKaliAgent = this.value;
                if (activeKaliAgent) {
                    kaliTerm.writeln(`\r\n[*] Connected to ${this.options[this.selectedIndex].text}`);
                    kaliTerm.write('root@nethunter:~# ');
                    if (!terminalPollInterval) {
                        terminalPollInterval = setInterval(pollKaliResults, 1500);
                    }
                } else {
                    kaliTerm.writeln('\r\n[*] Disconnected.');
                    if (terminalPollInterval) {
                        clearInterval(terminalPollInterval);
                        terminalPollInterval = null;
                    }
                }
            };
        } else {
            select.innerHTML = '<option value="">No Active Drones</option>';
        }
    } catch(e) {}
};

const origShowTab = showTab;
showTab = function(tabId) {
    origShowTab(tabId);
    if (tabId === 'toolkit' && kaliFitAddon) {
        setTimeout(() => kaliFitAddon.fit(), 100);
    }
    if (tabId === 'casino' && typeof window.resizeCanvas === 'function') {
        setTimeout(window.resizeCanvas, 100);
    }
    if (tabId === 'overview') {
        setTimeout(resizeResourceChart, 100);
    }
};

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

// ══════════════════════════════════════════════════════
// CINEMA MODE — Lights-out immersive player experience
// ══════════════════════════════════════════════════════
let cinemaModeActive = false;

function toggleCinemaMode(forceOn) {
    const overlay = document.getElementById('cinema-overlay');
    const container = document.getElementById('media-player-container');
    const btn = document.getElementById('btn-cinema');
    const bsContainer = document.getElementById('bs-container');
    const toolbar = document.querySelector('#panel-media .panel-toolbar');

    if (forceOn === true) cinemaModeActive = false; // force enable path
    cinemaModeActive = !cinemaModeActive;

    if (cinemaModeActive) {
        // Lights out! Blur + darken everything
        overlay.style.display = 'block';
        requestAnimationFrame(() => { overlay.style.opacity = '1'; });

        // Elevate player above overlay
        if (container) {
            container.style.display = 'block';
            container.style.position = 'fixed';
            container.style.zIndex = '10000';
            container.style.top = '50%';
            container.style.left = '50%';
            container.style.transform = 'translate(-50%, -50%)';
            container.style.width = 'min(95vw, 1400px)';
            container.style.maxWidth = 'unset';
            container.style.borderRadius = '8px';
            container.style.boxShadow = '0 0 120px rgba(255, 0, 0, 0.35), 0 0 250px rgba(0,0,0,0.9)';
            container.style.transition = 'box-shadow 0.4s';
        }

        // Blur & dim the rest of the player card content
        if (bsContainer) {
            bsContainer.style.filter = 'blur(8px)';
            bsContainer.style.pointerEvents = 'none';
            bsContainer.style.transition = 'filter 0.4s';
        }
        if (toolbar) {
            toolbar.style.filter = 'blur(6px) opacity(0.3)';
            toolbar.style.transition = 'filter 0.4s';
        }

        // Cinema exit hint
        if (!document.getElementById('cinema-exit-hint')) {
            const hint = document.createElement('div');
            hint.id = 'cinema-exit-hint';
            hint.innerHTML = '🎬 Cinema Mode &nbsp;|&nbsp; Press <kbd>C</kbd> or click to exit';
            hint.style.cssText = `
                position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
                z-index: 10001; background: rgba(0,0,0,0.75); color: #ffcccc;
                padding: 10px 22px; border-radius: 30px; font-size: 13px;
                border: 1px solid rgba(255,50,50,0.4); pointer-events: none;
                opacity: 1; transition: opacity 2s; font-family: 'Space Grotesk', sans-serif;
                backdrop-filter: blur(10px); letter-spacing: 0.5px;
            `;
            document.body.appendChild(hint);
            setTimeout(() => { hint.style.opacity = '0'; }, 3000);
            setTimeout(() => { if(hint.parentNode) hint.remove(); }, 5200);
        }

        if (btn) { btn.classList.add('active'); btn.textContent = '✕ Exit Cinema'; }

    } else {
        // Exit cinema mode
        overlay.style.opacity = '0';
        setTimeout(() => { overlay.style.display = 'none'; }, 400);

        if (container) {
            container.style.position = '';
            container.style.zIndex = '';
            container.style.top = '';
            container.style.left = '';
            container.style.transform = '';
            container.style.width = '';
            container.style.maxWidth = '';
            container.style.boxShadow = '';
        }
        if (bsContainer) { bsContainer.style.filter = ''; bsContainer.style.pointerEvents = ''; }
        if (toolbar) { toolbar.style.filter = ''; }
        if (btn) { btn.classList.remove('active'); btn.textContent = '🎬 Cinema Mode'; }
    }
}

// Click overlay to exit cinema mode
document.getElementById('cinema-overlay')?.addEventListener('click', () => {
    if (cinemaModeActive) toggleCinemaMode();
});

// C key shortcut
document.addEventListener('keydown', (e) => {
    if (e.code === 'KeyC' && !e.ctrlKey && !e.altKey &&
        document.activeElement.tagName !== 'INPUT' &&
        document.activeElement.tagName !== 'TEXTAREA') {
        if (document.getElementById('panel-media').style.display !== 'none') {
            toggleCinemaMode();
        }
    }
});

window.toggleCinemaMode = toggleCinemaMode;

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
        const res = await fetch(API + '/media/extract', {
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

// ──────────────────────────────────────────────────────
// CYBER CREDITS ECONOMY
// ──────────────────────────────────────────────────────
async function fetchCredits() {
  try {
    const res = await fetch(`${API}/credits`);
    const data = await res.json();
    if (data.ok) {
      document.getElementById('cyber-credits-display').textContent = data.credits;
    }
  } catch (err) {}
}

async function updateCredits(delta) {
  try {
    const res = await fetch(`${API}/credits/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delta })
    });
    const data = await res.json();
    if (data.ok) {
      const el = document.getElementById('cyber-credits-display');
      if (el) {
          el.textContent = data.credits;
          
          // Visual flair
          el.style.color = delta > 0 ? '#0f0' : '#f00';
          el.style.transform = 'scale(1.2)';
          setTimeout(() => {
            el.style.color = '';
            el.style.transform = '';
          }, 500);
      }
    }
    return data;
  } catch (err) {
    return { ok: false };
  }
}


// Sidebar toggle is now handled inline in index.html to prevent caching collisions

// --- GHOSTTRACK OSINT SCANNER & REVERSE SEARCH ---
async function startGhostTrackHunt() {
    const targetInput = document.getElementById('gt-target');
    if (!targetInput) return;
    const query = targetInput.value.trim();
    if (!query) {
        showToast("Please enter a username, email, or phone number", "error");
        return;
    }
    
    const progressContainer = document.getElementById('gt-progress-container');
    const progressBar = document.getElementById('gt-progress-bar');
    const statusText = document.getElementById('gt-status-text');
    const resultsCard = document.getElementById('gt-results-card');
    const resultsDiv = document.getElementById('gt-results');
    
    if (progressContainer) progressContainer.style.display = 'block';
    if (resultsCard) resultsCard.style.display = 'none';
    if (progressBar) progressBar.style.width = '0%';
    
    const statuses = [
        "Initializing deep web crawlers...",
        "Querying public intelligence repositories...",
        "Resolving social media accounts...",
        "Checking database leak records...",
        "Analyzing footprint reports..."
    ];
    
    let progress = 0;
    const interval = setInterval(() => {
        progress += 10;
        if (progressBar) progressBar.style.width = `${progress}%`;
        const statusIdx = Math.floor((progress / 100) * statuses.length);
        if (statusText && statusIdx < statuses.length) {
            statusText.textContent = statuses[statusIdx];
        }
        if (progress >= 100) {
            clearInterval(interval);
        }
    }, 200);
    
    try {
        const response = await fetch('/api/osint/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const result = await response.json();
        
        await new Promise(r => setTimeout(r, 2200));
        
        if (progressContainer) progressContainer.style.display = 'none';
        
        if (response.ok && result.ok) {
            if (resultsCard) resultsCard.style.display = 'block';
            if (resultsDiv) {
                renderGtResults(result, resultsDiv);
            }
        } else {
            showToast(result.error || "OSINT scan failed", "error");
        }
    } catch (e) {
        if (progressContainer) progressContainer.style.display = 'none';
        showToast("Error connecting to OSINT API", "error");
    }
}

async function uploadGtExif(input) {
    const file = input.files[0];
    if (!file) return;
    
    const progressContainer = document.getElementById('gt-progress-container');
    const progressBar = document.getElementById('gt-progress-bar');
    const statusText = document.getElementById('gt-status-text');
    const resultsCard = document.getElementById('gt-results-card');
    const resultsDiv = document.getElementById('gt-results');
    
    if (progressContainer) progressContainer.style.display = 'block';
    if (resultsCard) resultsCard.style.display = 'none';
    if (progressBar) progressBar.style.width = '0%';
    if (statusText) statusText.textContent = "Extracting EXIF Image Metadata...";
    
    let progress = 0;
    const interval = setInterval(() => {
        progress += 15;
        if (progress > 90) progress = 90;
        if (progressBar) progressBar.style.width = `${progress}%`;
    }, 150);
    
    const formData = new FormData();
    formData.append('image', file);
    
    try {
        const response = await fetch('/api/osint/exif', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        
        clearInterval(interval);
        if (progressBar) progressBar.style.width = '100%';
        await new Promise(r => setTimeout(r, 400));
        if (progressContainer) progressContainer.style.display = 'none';
        
        if (response.ok && result.ok) {
            if (resultsCard) resultsCard.style.display = 'block';
            if (resultsDiv) {
                renderGtResults(result, resultsDiv);
            }
        } else {
            showToast(result.error || "EXIF parsing failed", "error");
        }
    } catch (e) {
        clearInterval(interval);
        if (progressContainer) progressContainer.style.display = 'none';
        showToast("Error connecting to EXIF API", "error");
    } finally {
        input.value = ''; // Reset file input
    }
}

async function uploadGtReverse(input) {
    const file = input.files[0];
    if (!file) return;
    
    const progressContainer = document.getElementById('gt-progress-container');
    const progressBar = document.getElementById('gt-progress-bar');
    const statusText = document.getElementById('gt-status-text');
    const resultsCard = document.getElementById('gt-results-card');
    const resultsDiv = document.getElementById('gt-results');
    
    if (progressContainer) progressContainer.style.display = 'block';
    if (resultsCard) resultsCard.style.display = 'none';
    if (progressBar) progressBar.style.width = '0%';
    
    const isVideo = file.type.startsWith('video/') || file.name.toLowerCase().endsWith('.mp4') || file.name.toLowerCase().endsWith('.webm') || file.name.toLowerCase().endsWith('.mov');
    if (statusText) {
        statusText.textContent = isVideo ? "Extracting frame and searching sources..." : "Uploading image for reverse search...";
    }
    
    let progress = 0;
    const interval = setInterval(() => {
        progress += 5;
        if (progress > 95) progress = 95;
        if (progressBar) progressBar.style.width = `${progress}%`;
    }, 200);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/reverse-image', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        
        clearInterval(interval);
        if (progressBar) progressBar.style.width = '100%';
        await new Promise(r => setTimeout(r, 400));
        if (progressContainer) progressContainer.style.display = 'none';
        
        if (response.ok && result.ok) {
            if (resultsCard) resultsCard.style.display = 'block';
            if (resultsDiv) {
                renderGtResults({ type: 'REVERSE_SEARCH', data: result }, resultsDiv);
            }
        } else {
            showToast(result.error || "Reverse search failed", "error");
        }
    } catch (e) {
        clearInterval(interval);
        if (progressContainer) progressContainer.style.display = 'none';
        showToast("Error connecting to Reverse Search API", "error");
    } finally {
        input.value = ''; // Reset file input
    }
}

function renderGtResults(res, targetDiv) {
    let html = '';
    const type = res.type;
    
    if (type === 'IP') {
        const d = res.data;
        html += createGtCard('fa-location-dot', 'Location', d.location || 'Unknown');
        const coords = d.coordinates || d.loc || '';
        html += createGtCard('fa-map', 'Coordinates', coords
            ? `${coords} <a href="https://maps.google.com/?q=${encodeURIComponent(coords)}" target="_blank" style="color:var(--cyan); font-size:11px; margin-left:6px;">🗺 View on Map</a>`
            : 'N/A');
        html += createGtCard('fa-network-wired', 'ISP', d.isp || d.org || 'Unknown');
        html += createGtCard('fa-building', 'Organization', d.organization || d.org || 'Unknown');
        html += createGtCard('fa-clock', 'Timezone', d.timezone || 'Unknown');
        if (d.country_code) html += createGtCard('fa-flag', 'Country', `${d.country_code} — ${d.country || ''}`);
        if (d.asn) html += createGtCard('fa-server', 'ASN', d.asn);
    }
    else if (type === 'PHONE') {
        const d = res.data;
        // Radar canvas id unique to avoid collisions
        const radarId = 'phone-radar-' + Date.now();
        const coordsText = d.coordinates && d.coordinates !== 'Unknown' ? `<div id="radar-gps-text" style="font-size:11px; color:#00d4ff; font-family:monospace; margin-top:4px;">GPS: ${d.coordinates}</div>` : '';
        html += `
        <div class="intel-card" style="grid-column: 1 / -1; background: #0a0a0f; border-color: #00d4ff; padding: 0; overflow: hidden; min-height: 200px; position: relative;">
            <canvas id="${radarId}" width="600" height="200" style="width:100%; display:block;"></canvas>
            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); text-align:center; pointer-events:none;">
                <div style="font-size:11px; color:#00d4ff; font-weight:900; letter-spacing:2px; text-transform:uppercase; font-family:monospace;">SIGNAL TRACE</div>
                <div style="font-size:22px; font-weight:900; color:#fff; margin:4px 0; font-family:monospace;">${d.number || 'Unknown'}</div>
                <div style="font-size:12px; color:#aaa; font-family:monospace;">${d.carrier || 'Carrier Unknown'} • ${d.location || 'Location Unknown'}</div>
                ${coordsText}
            </div>
        </div>`;
        html += createGtCard('fa-phone', 'International Format', d.number || 'N/A');
        html += createGtCard('fa-earth-americas', 'Country Code', d.country_code ? `+${d.country_code}` : 'N/A');
        html += createGtCard('fa-location-dot', 'Region', d.location || 'N/A');
        const coordsVal = (d.coordinates && d.coordinates !== 'Unknown') ? d.coordinates : 'Unknown';
        const mapLinkHtml = coordsVal !== 'Unknown' 
          ? `<a id="osint-gps-maplink" href="https://maps.google.com/?q=${encodeURIComponent(coordsVal)}" target="_blank" style="color:var(--cyan); font-size:11px; margin-left:6px; font-weight: bold;">🗺 View on Map</a>`
          : `<a id="osint-gps-maplink" href="#" target="_blank" style="color:var(--cyan); font-size:11px; margin-left:6px; font-weight: bold; display: none;">🗺 View on Map</a>`;
          
        html += createGtCard('fa-map-location-dot', 'GPS Coordinates', `
            <span id="osint-gps-coords">${coordsVal}</span>
            ${mapLinkHtml}
            <div style="margin-top: 8px;">
                <button class="btn-sm" style="padding: 6px 12px; font-size: 11px; background: var(--green); color: #000; cursor: pointer; border: 2px solid var(--border); box-shadow: 2px 2px 0px var(--border); font-family: var(--font);" onclick="refineWithBrowserGps()">📍 Recalibrate with Device GPS</button>
            </div>
            <div style="font-size: 10px; color: var(--text-muted); margin-top: 4px;">*OSINT retrieves carrier registry center. Click Recalibrate to query active browser GPS.</div>
        `);
        html += createGtCard('fa-sim-card', 'Network Carrier', d.carrier || 'Unknown');
        if (d.line_type) html += createGtCard('fa-mobile-screen', 'Line Type', d.line_type);
        if (d.timezones && d.timezones.length) html += createGtCard('fa-clock', 'Timezones', Array.isArray(d.timezones) ? d.timezones.join(', ') : d.timezones);
        if (d.number_type) html += createGtCard('fa-hashtag', 'Number Type', d.number_type);
        // Schedule radar animation after DOM paint
        setTimeout(() => startPhoneRadar(radarId), 80);
    }
    else if (type === 'EMAIL') {
        const d = res.data;
        html += createGtCard('fa-at', 'Domain', d.domain_info.domain);
        html += createGtCard(d.domain_info.is_disposable ? 'fa-trash' : 'fa-server', 'Provider Type', d.domain_info.is_disposable ? 'Disposable / Burner' : d.domain_info.provider);
        if (d.gravatar && d.gravatar.has_profile) {
            html += `
            <div class="intel-card" style="border-color: var(--cyan);">
                <h3><i class="fa-solid fa-image"></i> Gravatar Profile</h3>
                <div style="display:flex; justify-content:center; align-items:center;">
                    <img src="${d.gravatar.url}" style="border-radius: 4px; width: 80px; height: 80px; border: 2px solid var(--cyan);" alt="Gravatar">
                </div>
            </div>`;
        }
        if (d.social_profiles && d.social_profiles.length > 0) {
            let profilesHtml = '<div class="profile-grid">';
            d.social_profiles.forEach(p => {
                const icon = p.found ? 'fa-check' : 'fa-xmark';
                const statusClass = p.found ? 'found' : 'not-found';
                const link = p.found ? `<a href="${p.url}" target="_blank">${p.platform} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 0.7rem;"></i></a>` : p.platform;
                profilesHtml += `
                <div class="profile-item ${statusClass}">
                    <i class="fa-solid ${icon}"></i>
                    ${link}
                </div>`;
            });
            profilesHtml += '</div>';
            html += `
            <div class="intel-card" style="grid-column: 1 / -1;">
                <h3><i class="fa-solid fa-users-viewfinder"></i> Username Correlation (@${d.username})</h3>
                ${profilesHtml}
            </div>`;
        }
    }
    else if (type === 'USERNAME') {
        const profiles = res.data.profiles || [];
        let profilesHtml = '<div class="profile-grid">';
        profiles.forEach(p => {
            const icon = p.found ? 'fa-check' : 'fa-xmark';
            const statusClass = p.found ? 'found' : 'not-found';
            const link = p.found ? `<a href="${p.url}" target="_blank">${p.platform} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 0.7rem;"></i></a>` : p.platform;
            profilesHtml += `
            <div class="profile-item ${statusClass}">
                <i class="fa-solid ${icon}"></i>
                ${link}
            </div>`;
        });
        profilesHtml += '</div>';
        html += `
        <div class="intel-card" style="grid-column: 1 / -1;">
            <h3><i class="fa-solid fa-users-viewfinder"></i> Cross-Platform Presence</h3>
            ${profilesHtml}
        </div>`;
    }
    else if (type === 'EXIF') {
        const d = res.data;
        if (d.Make) html += createGtCard('fa-camera', 'Make', d.Make);
        if (d.Model) html += createGtCard('fa-mobile-screen', 'Model', d.Model);
        if (d.OriginalTime) html += createGtCard('fa-clock', 'Taken On', d.OriginalTime);
        if (d.Software) html += createGtCard('fa-code', 'Software', d.Software);
        if (d.GPS) {
            html += `
            <div class="intel-card" style="grid-column: 1 / -1; border-color: var(--cyan);">
                <h3><i class="fa-solid fa-map-location-dot" style="color: var(--cyan);"></i> Exact GPS Location</h3>
                <div class="intel-value" style="font-size: 15px; color: var(--cyan);">
                    Lat: ${d.GPS.Latitude}, Lon: ${d.GPS.Longitude}
                    <a href="${d.GPS.MapLink}" target="_blank" style="margin-left: 10px; color: #fff; text-decoration: underline; font-weight: bold;">Open in Maps <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                </div>
            </div>`;
        }
        if (Object.keys(d).length === 0 || (Object.keys(d).length === 1 && d.hasOwnProperty('GPS') && Object.keys(d.GPS).length === 0)) {
            html += createGtCard('fa-triangle-exclamation', 'No EXIF Data', 'No camera metadata or location data found in this image.');
        }
    }
    else if (type === 'REVERSE_SEARCH') {
        const d = res.data;
        if (d.results && d.results.length > 0) {
            d.results.forEach(r => {
                let urlsHtml = '';
                if (r.urls && r.urls.length > 0) {
                    urlsHtml = '<div style="margin-top: 8px; display:flex; gap:10px; flex-wrap:wrap;">';
                    r.urls.forEach(url => {
                        let domain = new URL(url).hostname.replace('www.', '');
                        urlsHtml += `<a href="${url}" target="_blank" style="background:#222; border:1px solid #333; padding:4px 8px; border-radius:4px; font-size:11px; color:var(--cyan); text-decoration:none; font-weight:bold;">${domain} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 9px;"></i></a>`;
                    });
                    urlsHtml += '</div>';
                }
                
                html += `
                <div class="intel-card" style="display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap;">
                    ${r.thumbnail ? `
                    <div style="flex-shrink: 0; width: 100px; height: 100px; border: 1px solid #333; background: #000; display:flex; justify-content:center; align-items:center; overflow:hidden;">
                        <img src="${r.thumbnail}" style="max-width:100%; max-height:100%; object-fit:contain;" alt="Thumbnail">
                    </div>` : ''}
                    <div style="flex: 1; min-width: 200px;">
                        <h3 style="margin-bottom:4px;"><i class="fa-solid fa-circle-check"></i> ${r.similarity}% Match</h3>
                        <div class="intel-value" style="font-size: 15px; margin-bottom: 4px;">${r.title}</div>
                        ${r.author ? `<div style="font-size:12px; color:var(--text-secondary); margin-bottom:6px;">Author: <strong>${r.author}</strong></div>` : ''}
                        <div style="font-size:10px; color:#555; font-family:monospace;">Source Database: ${r.index_name}</div>
                        ${urlsHtml}
                    </div>
                </div>`;
            });
        } else {
            html += createGtCard('fa-magnifying-glass', 'No Matches Found', 'SauceNAO database returned no matches with high similarity (>40%).');
        }
    }
    
    targetDiv.innerHTML = `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px,1fr)); gap: 15px;">${html}</div>`;
}

function startPhoneRadar(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    // Scale for High DPI / Retina Displays
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    
    const W = rect.width;
    const H = rect.height;
    const cx = W / 2;
    const cy = H / 2;
    const maxR = Math.min(cx, cy) - 10;
    let angle = 0;
    let blips = [];
    
    // Generate 5 random signal blips
    for (let i = 0; i < 5; i++) {
        blips.push({
            a: Math.random() * Math.PI * 2,
            r: (0.3 + Math.random() * 0.6) * maxR,
            life: 0,
            maxLife: 120 + Math.random() * 60
        });
    }
    
    function drawFrame() {
        if (!document.getElementById(canvasId)) return; // stop if removed
        ctx.clearRect(0, 0, W, H);
        
        // Background
        ctx.fillStyle = '#0a0a0f';
        ctx.fillRect(0, 0, W, H);
        
        // Tech Grid Dots Background
        ctx.fillStyle = 'rgba(0, 212, 255, 0.05)';
        for (let x = 10; x < W; x += 20) {
            for (let y = 10; y < H; y += 20) {
                ctx.fillRect(x, y, 1.5, 1.5);
            }
        }
        
        // Draw concentric rings
        for (let ring = 1; ring <= 4; ring++) {
            ctx.beginPath();
            ctx.arc(cx, cy, maxR * ring / 4, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(0, 212, 255, 0.15)';
            ctx.lineWidth = 1;
            ctx.stroke();
        }
        
        // Cross hairs
        ctx.strokeStyle = 'rgba(0, 212, 255, 0.1)';
        ctx.beginPath(); ctx.moveTo(cx - maxR, cy); ctx.lineTo(cx + maxR, cy); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(cx, cy - maxR); ctx.lineTo(cx, cy + maxR); ctx.stroke();
        
        // Sweep
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(angle);
        const grad = ctx.createLinearGradient(0, 0, maxR, 0);
        grad.addColorStop(0, 'rgba(0, 212, 255, 0.4)');
        grad.addColorStop(1, 'rgba(0, 212, 255, 0)');
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.arc(0, 0, maxR, -0.5, 0);
        ctx.closePath();
        ctx.fillStyle = grad;
        ctx.fill();
        
        // Sweep line
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(maxR, 0);
        ctx.strokeStyle = '#00d4ff';
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.restore();
        
        // Blips
        blips.forEach(b => {
            const diff = ((b.a - angle) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
            if (diff < 0.2) { b.life = b.maxLife; }
            if (b.life > 0) {
                const alpha = b.life / b.maxLife;
                const bx = cx + Math.cos(b.a) * b.r;
                const by = cy + Math.sin(b.a) * b.r;
                
                ctx.beginPath();
                ctx.arc(bx, by, 5 * alpha, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(0, 255, 136, ${alpha})`;
                ctx.fill();
                
                ctx.beginPath();
                ctx.arc(bx, by, 10 * alpha, 0, Math.PI * 2);
                ctx.strokeStyle = `rgba(0, 255, 136, ${alpha * 0.5})`;
                ctx.lineWidth = 1;
                ctx.stroke();
                
                b.life--;
            }
        });
        
        // Center dot
        ctx.beginPath();
        ctx.arc(cx, cy, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#00d4ff';
        ctx.fill();
        
        angle += 0.025;
        requestAnimationFrame(drawFrame);
    }
    drawFrame();
}

function createGtCard(icon, title, value) {
    return `
    <div class="intel-card">
        <h3><i class="fa-solid ${icon}"></i> ${title}</h3>
        <div class="intel-value">${value}</div>
    </div>`;
}

window.startGhostTrackHunt = startGhostTrackHunt;
window.uploadGtExif = uploadGtExif;
window.uploadGtReverse = uploadGtReverse;

// --- LIVE SYSTEM RESOURCES CANVAS CHART ---
window.resourceHistory = [];
const MAX_HISTORY = 40;

window.updateResourceChartData = function(cpu, mem) {
  window.resourceHistory.push({ cpu: cpu, mem: mem });
  if (window.resourceHistory.length > MAX_HISTORY) {
    window.resourceHistory.shift();
  }
};

// ══════════════════════════════════════════════════════
// LIVE SYSTEM RESOURCES — CSS + SVG (bulletproof, no canvas sizing issues)
// ══════════════════════════════════════════════════════
function buildResourceWidget() {
  const wrapper = document.getElementById('resource-widget-inner');
  if (!wrapper) return;
  wrapper.innerHTML = `
  <style>
    @keyframes pulse-glow {
      from { opacity: 0.3; transform: scale(0.9); }
      to { opacity: 1; transform: scale(1.1); }
    }
  </style>
  <div id="res-widget" style="display: flex; flex-direction: column; gap: 16px;">
    <!-- Indicator Row -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px;">
      <!-- CPU Indicator -->
      <div style="background: #ffcc00; border: 2px solid #111111; padding: 14px; display: flex; flex-direction: column; gap: 6px; box-shadow: 3px 3px 0px #111111;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 13px; color: #111111; letter-spacing: 1px;">CPU LOAD</span>
          <span id="res-cpu-pct" style="font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 16px; color: #111111;">0%</span>
        </div>
        <!-- Track -->
        <div style="height: 10px; background: #ffffff; border: 2px solid #111111; overflow: hidden; position: relative;">
          <div id="res-cpu-bar" style="height: 100%; background: #111111; border-right: 2px solid #111111; width: 0%; transition: width 0.25s cubic-bezier(0.4,0,0.2,1);"></div>
        </div>
      </div>
      
      <!-- Memory Indicator -->
      <div style="background: #33ccff; border: 2px solid #111111; padding: 14px; display: flex; flex-direction: column; gap: 6px; box-shadow: 3px 3px 0px #111111;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 13px; color: #111111; letter-spacing: 1px;">RAM USAGE</span>
          <span id="res-mem-pct" style="font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 16px; color: #111111;">0%</span>
        </div>
        <!-- Track -->
        <div style="height: 10px; background: #ffffff; border: 2px solid #111111; overflow: hidden; position: relative;">
          <div id="res-mem-bar" style="height: 100%; background: #111111; border-right: 2px solid #111111; width: 0%; transition: width 0.25s cubic-bezier(0.4,0,0.2,1);"></div>
        </div>
      </div>
    </div>
    
    <!-- Oscilloscope Container -->
    <div style="background: #000000; border: 2px solid #111111; padding: 10px; position: relative; box-shadow: 3px 3px 0px #111111; display: flex; flex-direction: column;">
      <!-- Live Indicator Overlay -->
      <div style="position: absolute; top: 10px; right: 12px; display: flex; align-items: center; gap: 6px; font-size: 9px; font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #00ffcc; z-index: 10;">
        <span style="display: inline-block; width: 6px; height: 6px; background: #00ffcc; border-radius: 50%; animation: pulse-glow 1.5s infinite alternate;"></span>
        LIVE FEED
      </div>
      
      <svg class="res-sparkline" id="res-sparkline" viewBox="0 0 400 80" preserveAspectRatio="none" style="width: 100%; height: 90px; display: block; background: #000000;">
        <defs>
          <linearGradient id="g-cpu" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#ffcc00" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="#ffcc00" stop-opacity="0"/>
          </linearGradient>
          <linearGradient id="g-mem" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#33ccff" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="#33ccff" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <!-- Grid lines -->
        <line x1="0" y1="20" x2="400" y2="20" stroke="rgba(255,255,255,0.06)" stroke-width="1" stroke-dasharray="2,2"/>
        <line x1="0" y1="40" x2="400" y2="40" stroke="rgba(255,255,255,0.06)" stroke-width="1" stroke-dasharray="2,2"/>
        <line x1="0" y1="60" x2="400" y2="60" stroke="rgba(255,255,255,0.06)" stroke-width="1" stroke-dasharray="2,2"/>
        <!-- CPU area fill -->
        <path id="res-cpu-area" fill="url(#g-cpu)" d="M0,80 L400,80 Z"/>
        <!-- MEM area fill -->
        <path id="res-mem-area" fill="url(#g-mem)" d="M0,80 L400,80 Z"/>
        <!-- CPU line -->
        <polyline id="res-cpu-line" fill="none" stroke="#ffcc00" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" points="0,80"/>
        <!-- MEM line -->
        <polyline id="res-mem-line" fill="none" stroke="#33ccff" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" points="0,80"/>
        <!-- Scan line -->
        <line id="res-scanline" x1="0" y1="0" x2="0" y2="80" stroke="rgba(0,212,255,0.25)" stroke-width="1.5"/>
        <!-- Live dots -->
        <circle id="res-cpu-dot" cx="0" cy="80" r="4.5" fill="#ffcc00" stroke="#000000" stroke-width="1"/>
        <circle id="res-mem-dot" cx="0" cy="80" r="4.5" fill="#33ccff" stroke="#000000" stroke-width="1"/>
      </svg>
      <div style="display: flex; gap: 14px; margin-top: 8px; justify-content: flex-start;">
        <div style="display: flex; align-items: center; gap: 6px; font-size: 10px; font-family: 'JetBrains Mono', monospace; color: rgba(255,255,255,0.5);"><span style="width: 8px; height: 8px; background: #ffcc00; display: inline-block;"></span>CPU</div>
        <div style="display: flex; align-items: center; gap: 6px; font-size: 10px; font-family: 'JetBrains Mono', monospace; color: rgba(255,255,255,0.5);"><span style="width: 8px; height: 8px; background: #33ccff; display: inline-block;"></span>Memory</div>
      </div>
    </div>
  </div>
  `;
}

const RES_HISTORY_MAX = 60;
const resHistory = [];

function updateResourceWidget(cpu, mem) {
  resHistory.push({ cpu, mem });
  if (resHistory.length > RES_HISTORY_MAX) resHistory.shift();

  // Update bars
  const cpuBar = document.getElementById('res-cpu-bar');
  const memBar = document.getElementById('res-mem-bar');
  const cpuPct = document.getElementById('res-cpu-pct');
  const memPct = document.getElementById('res-mem-pct');
  if (!cpuBar) return;

  cpuBar.style.width = cpu + '%';
  memBar.style.width = mem + '%';
  cpuPct.textContent = Math.round(cpu) + '%';
  memPct.textContent = Math.round(mem) + '%';

  // Color cpu bar by load level
  if (cpu > 80) cpuBar.style.background = 'linear-gradient(90deg,#ff2200,#ff4400)';
  else if (cpu > 50) cpuBar.style.background = 'linear-gradient(90deg,#ff6600,#ff8800)';
  else cpuBar.style.background = 'linear-gradient(90deg,#ff8800,#ffaa00)';

  // Update sparklines
  const W = 400, H = 80;
  const n = resHistory.length;
  const step = W / (RES_HISTORY_MAX - 1);

  function buildPoints(key) {
    return resHistory.map((p, i) => {
      const x = i * step;
      const y = H - (p[key] / 100) * (H - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
  }

  function buildArea(key) {
    const pts = resHistory.map((p, i) => {
      const x = i * step;
      const y = H - (p[key] / 100) * (H - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    if (!pts.length) return '';
    return `M${pts[0]} L${pts.join(' L')} L${((n-1)*step).toFixed(1)},${H} L0,${H} Z`;
  }

  const cpuPts = buildPoints('cpu');
  const memPts = buildPoints('mem');
  document.getElementById('res-cpu-line').setAttribute('points', cpuPts);
  document.getElementById('res-mem-line').setAttribute('points', memPts);
  document.getElementById('res-cpu-area').setAttribute('d', buildArea('cpu'));
  document.getElementById('res-mem-area').setAttribute('d', buildArea('mem'));

  // Live end dots
  const last = resHistory[resHistory.length - 1];
  const lastX = ((n - 1) * step).toFixed(1);
  const cpuY = (H - (last.cpu / 100) * (H - 4) - 2).toFixed(1);
  const memY = (H - (last.mem / 100) * (H - 4) - 2).toFixed(1);
  document.getElementById('res-cpu-dot').setAttribute('cx', lastX);
  document.getElementById('res-cpu-dot').setAttribute('cy', cpuY);
  document.getElementById('res-mem-dot').setAttribute('cx', lastX);
  document.getElementById('res-mem-dot').setAttribute('cy', memY);

  // Animated scan line
  const scanX = ((Date.now() / 30) % W).toFixed(1);
  const scanEl = document.getElementById('res-scanline');
  if (scanEl) { scanEl.setAttribute('x1', scanX); scanEl.setAttribute('x2', scanX); }
}

function resizeScanlineLoop() {
  const scanEl = document.getElementById('res-scanline');
  if (!scanEl) return;
  const scanX = ((Date.now() / 30) % 400).toFixed(1);
  scanEl.setAttribute('x1', scanX);
  scanEl.setAttribute('x2', scanX);
  requestAnimationFrame(resizeScanlineLoop);
}

function resizeResourceChart() { /* kept for compat — no-op; SVG widget is used now */ }


function drawResourceChart() {
  const canvas = document.getElementById('resourceChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  
  const w = canvas.width;
  const h = canvas.height;
  
  // Neo-Brutalist clean dark chart background
  ctx.fillStyle = "#0c1015";
  ctx.fillRect(0, 0, w, h);
  
  const chartX = 35;
  const chartW = w - 45;
  
  // Grid lines
  ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
  ctx.lineWidth = 1;
  
  // 6 vertical grid sections
  const gridSpacing = chartW / 6;
  for (let i = 0; i <= 6; i++) {
    const x = chartX + i * gridSpacing;
    ctx.beginPath();
    ctx.moveTo(x, 5);
    ctx.lineTo(x, h - 10);
    ctx.stroke();
  }
  
  // 4 horizontal grid sections
  const horizSpacing = (h - 15) / 4;
  for (let i = 0; i <= 4; i++) {
    const y = 5 + i * horizSpacing;
    ctx.beginPath();
    ctx.moveTo(chartX, y);
    ctx.lineTo(chartX + chartW, y);
    ctx.stroke();
  }
  
  // Percentage markers
  ctx.fillStyle = "rgba(255, 255, 255, 0.35)";
  ctx.font = "9px 'JetBrains Mono', monospace";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  ctx.fillText("100%", 28, 5);
  ctx.fillText("75%", 28, 5 + horizSpacing);
  ctx.fillText("50%", 28, 5 + 2 * horizSpacing);
  ctx.fillText("25%", 28, 5 + 3 * horizSpacing);
  ctx.fillText("0%", 28, h - 10);
  
  // Dynamic scanning radar sweeping line
  const scanX = chartX + ((Date.now() / 20) % chartW);
  ctx.strokeStyle = "rgba(0, 212, 255, 0.08)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(scanX, 5);
  ctx.lineTo(scanX, h - 10);
  ctx.stroke();
  
  if (window.resourceHistory.length < 2) {
    ctx.fillStyle = "#8892b0";
    ctx.font = "12px 'Space Grotesk', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Awaiting telemetry updates...", chartX + chartW / 2, h / 2 + 4);
    return;
  }
  
  const points = window.resourceHistory.length;
  const step = chartW / (MAX_HISTORY - 1);
  
  function drawMetric(key, strokeColor, fillColor, labelText, labelY) {
    ctx.beginPath();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = strokeColor;
    
    // Smooth quadratic curve plotting
    const getX = (idx) => chartX + idx * step;
    const getY = (idx) => h - 10 - (window.resourceHistory[idx][key] / 100) * (h - 15);
    
    ctx.moveTo(getX(0), getY(0));
    if (points > 2) {
      for (let i = 0; i < points - 1; i++) {
        const xc = (getX(i) + getX(i + 1)) / 2;
        const yc = (getY(i) + getY(i + 1)) / 2;
        ctx.quadraticCurveTo(getX(i), getY(i), xc, yc);
      }
      ctx.lineTo(getX(points - 1), getY(points - 1));
    } else {
      ctx.lineTo(getX(points - 1), getY(points - 1));
    }
    ctx.stroke();
    
    // Fill Area under curve
    const lastX = getX(points - 1);
    ctx.lineTo(lastX, h - 10);
    ctx.lineTo(chartX, h - 10);
    ctx.closePath();
    
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, fillColor);
    grad.addColorStop(1, "rgba(12, 16, 21, 0)");
    ctx.fillStyle = grad;
    ctx.fill();
    
    // Draw current value label
    const lastVal = window.resourceHistory[points - 1][key];
    ctx.fillStyle = strokeColor;
    ctx.font = "bold 11px 'Space Grotesk', sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(`${labelText}: ${Math.round(lastVal)}%`, w - 12, labelY);
    
    // Draw glowing dot at the tail
    const lastY = getY(points - 1);
    ctx.beginPath();
    ctx.arc(lastX, lastY, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = strokeColor;
    ctx.fill();
    
    const pulseRadius = 4.5 + (Date.now() % 1000) / 200;
    ctx.beginPath();
    ctx.arc(lastX, lastY, pulseRadius, 0, Math.PI * 2);
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 1;
    ctx.stroke();
  }
  
  drawMetric('cpu', '#ff8800', 'rgba(255, 136, 0, 0.15)', 'CPU', 18);
  drawMetric('mem', '#00ffcc', 'rgba(0, 255, 204, 0.15)', 'MEM', 34);
}

window.startResourceChartLoop = function() {
  // Build the new SVG neo-brutalist widget in the DOM
  buildResourceWidget();
  
  // Pre-fill the sparkline history with initial zero values so it starts rendering lines immediately
  if (resHistory.length === 0) {
    for (let i = 0; i < RES_HISTORY_MAX; i++) {
      resHistory.push({ cpu: 0, mem: 0 });
    }
  }
  
  // Do an initial render of the sparklines/bars
  updateResourceWidget(0, 0);

  // Start the scanline animation loop
  resizeScanlineLoop();
};

window.runSandboxTest = async function(module) {
  const labels = { tarpit: 'Infinite Tarpit', tripwire: 'Ransomware Tripwire' };
  const label = labels[module] || module;
  const container = document.getElementById('overview-ids-feed');

  // Helper: inject a line into the feed
  function feedLine(level, cat, msg) {
    if (!container) return;
    const el = _idsBuildLine(new Date().toLocaleTimeString(), level, cat, msg);
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
  }

  // Show "running" line in feed
  feedLine('SYS', 'TEST', `Running sandbox test for ${label}...`);

  try {
    const res = await fetch('/api/system/sandbox-test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ module })
    });
    const data = await res.json();

    if (data.ok) {
      // Build a full alert card for the result
      const cat = module === 'tripwire' ? 'TRIPWIRE' : 'HONEYPOT';
      const solutions = _solutions[cat] || _solutions.INTRUSION;
      const card = document.createElement('div');
      card.style.cssText = `border:2px solid #00e699; background:rgba(0,230,153,0.06); margin-bottom:6px; overflow:hidden;`;

      const header = document.createElement('div');
      header.style.cssText = `display:flex; align-items:center; justify-content:space-between; padding:6px 10px; background:rgba(0,230,153,0.1); border-bottom:1px solid rgba(0,230,153,0.2);`;
      header.innerHTML = `
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="font-size:14px;">${module === 'tripwire' ? '⚡' : '🍯'}</span>
          <span style="font-family:'Space Grotesk',sans-serif; font-weight:900; font-size:11px; color:#00e699; letter-spacing:1px;">TEST PASSED — ${label.toUpperCase()}</span>
        </div>
        <span style="font-family:'JetBrains Mono',monospace; font-size:9px; color:#888;">${new Date().toLocaleTimeString()}</span>
      `;

      const msgEl = document.createElement('div');
      msgEl.style.cssText = `padding:6px 10px; font-family:'JetBrains Mono',monospace; font-size:11px; color:#aaa; border-bottom:1px solid #1a2a1a;`;
      msgEl.textContent = data.message;

      const solEl = document.createElement('div');
      solEl.style.cssText = `padding:6px 10px;`;
      solEl.innerHTML = `<div style="font-family:'Space Grotesk',sans-serif; font-size:10px; font-weight:800; color:#ffcc00; letter-spacing:1px; margin-bottom:4px;">▶ WHAT THIS MEANS IF REAL</div>`;
      solutions.slice(0, 3).forEach(s => {
        const item = document.createElement('div');
        item.style.cssText = `font-family:'JetBrains Mono',monospace; font-size:10px; color:#888; padding:1px 0 1px 8px;`;
        item.textContent = s;
        solEl.appendChild(item);
      });

      card.appendChild(header);
      card.appendChild(msgEl);
      card.appendChild(solEl);

      if (container) {
        container.appendChild(card);
        container.scrollTop = container.scrollHeight;
      }
    } else {
      feedLine('WARN', 'TEST', `Test failed: ${data.error || 'Sandbox returned error'}`);
    }
  } catch(e) {
    feedLine('WARN', 'TEST', `Test request failed: ${e.message}`);
  }
};

window.refineWithBrowserGps = function() {
  if (!navigator.geolocation) {
    showToast('⚠️ Geolocation is not supported by your browser.', 'error');
    return;
  }
  
  showToast('⏳ Requesting device GPS access...', 'info');
  
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;
      const coords = `${lat}, ${lon}`;
      
      // Update the UI elements
      const coordsSpan = document.getElementById('osint-gps-coords');
      const mapLink = document.getElementById('osint-gps-maplink');
      
      if (coordsSpan) coordsSpan.textContent = coords;
      if (mapLink) {
        mapLink.href = `https://maps.google.com/?q=${encodeURIComponent(coords)}`;
        mapLink.style.display = 'inline-block';
      }
      
      // Also update any radar text overlay if active
      const radarCoords = document.getElementById('radar-gps-text');
      if (radarCoords) {
        radarCoords.textContent = `GPS: ${coords}`;
      }
      
      showToast('✅ Location recalibrated successfully!', 'success');
    },
    (error) => {
      console.warn("Hardware GPS failed, falling back to IP Geolocation:", error);
      showToast('⚠️ Hardware GPS unavailable. Attempting IP-based geolocation...', 'info');
      
      // Fallback: Fetch location from ip-api.com
      fetch('https://ip-api.com/json/')
        .then(res => res.json())
        .then(ipData => {
          if (ipData && ipData.lat && ipData.lon) {
            const coords = `${ipData.lat}, ${ipData.lon}`;
            
            const coordsSpan = document.getElementById('osint-gps-coords');
            const mapLink = document.getElementById('osint-gps-maplink');
            
            if (coordsSpan) coordsSpan.textContent = coords + ' (IP Estimated)';
            if (mapLink) {
              mapLink.href = `https://maps.google.com/?q=${encodeURIComponent(coords)}`;
              mapLink.style.display = 'inline-block';
            }
            
            const radarCoords = document.getElementById('radar-gps-text');
            if (radarCoords) {
              radarCoords.textContent = `GPS: ${coords} (IP)`;
            }
            
            showToast('✅ Coarse IP-based location resolved!', 'success');
          } else {
            showToast('❌ Location unavailable (IP lookup failed).', 'error');
          }
        })
        .catch(err => {
          showToast('❌ Location unavailable (Network error on IP lookup).', 'error');
        });
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
  );
};

// ══════════════════════════════════════════════════════
// LIVE IDS SENSOR FEED — Real events + simulated ambient
// ══════════════════════════════════════════════════════
let _idsTimer = null;
let _idsLastEventCount = 0;
let _idsSeenIds = new Set();

const _mockIPs = [
  '185.220.101.4','45.143.203.14','92.118.160.17',
  '141.98.80.32','185.244.25.178','80.82.77.240'
];

// Ambient noise events (simulated network chatter)
const _ambientEvents = [
  { level: 'INFO',  cat: 'NET',     msg: 'TCP SYN probe on port {port} — dropped by firewall' },
  { level: 'INFO',  cat: 'NET',     msg: 'Stealth ping sweep from {ip} — ignored' },
  { level: 'INFO',  cat: 'SYS',     msg: 'Windows Defender real-time protection: active' },
  { level: 'INFO',  cat: 'SYS',     msg: 'Firewall rule set loaded — {port} rules active' },
  { level: 'WARN',  cat: 'NET',     msg: 'Port scan detected from {ip} — ports 22,80,443 probed' },
  { level: 'WARN',  cat: 'NET',     msg: 'Blocked outbound connection sweep from {ip}' },
  { level: 'INFO',  cat: 'SYS',     msg: 'DNS query for {ip} resolved successfully' },
  { level: 'INFO',  cat: 'NET',     msg: 'ICMP echo to {ip} — TTL expired in transit' },
  { level: 'INFO',  cat: 'SYS',     msg: 'TLS handshake with remote host — certificate valid' },
  { level: 'WARN',  cat: 'NET',     msg: 'Brute-force attempt on port {port} from {ip} — rate limited' },
];

// Solution playbooks for critical events
const _solutions = {
  TRIPWIRE: [
    '🚨 IMMEDIATELY disconnect from the internet',
    '🔍 Run full AV scan: Windows Defender > Full Scan',
    '💾 Check C:\\Users for any encrypted files (.locked, .enc)',
    '📋 Open Event Viewer → Security logs for the accessing process',
    '🔒 Change all passwords from a CLEAN device',
    '📞 Report to: security@cert.in or call 1800-11-4949'
  ],
  HONEYPOT: [
    '🛡️ Block attacker IP in Windows Firewall immediately',
    '🔍 Check if port {port} is exposed via: netstat -an',
    '📋 Review network logs for other connections from this IP',
    '🌐 Look up IP reputation: https://www.abuseipdb.com',
    '🔔 Enable alerts if IP connects again',
    '📝 Document the incident with timestamp and IP'
  ],
  INTRUSION: [
    '🚫 Block the source IP in your router/firewall',
    '📊 Check active connections: netstat -b in cmd',
    '🔍 Verify no new user accounts were created',
    '🔒 Rotate passwords for any exposed services',
    '📋 Check Windows Event Viewer for login attempts'
  ]
};

function _idsLevelStyle(level) {
  switch(level) {
    case 'CRITICAL': return { color: '#ff1a2e', border: '#ff1a2e', bg: 'rgba(255,26,46,0.08)', label: '💀 CRITICAL' };
    case 'ALERT':    return { color: '#ff4455', border: '#ff4455', bg: 'rgba(255,68,85,0.06)',  label: '🚨 ALERT' };
    case 'WARN':     return { color: '#ff9944', border: '#ff9944', bg: 'rgba(255,153,68,0.05)', label: '⚠️ WARN' };
    case 'INFO':     return { color: '#33ccff', border: '#333',    bg: 'transparent',           label: 'ℹ️ INFO' };
    case 'SYS':      return { color: '#888',    border: '#333',    bg: 'transparent',           label: '⚙️ SYS' };
    default:         return { color: '#aaa',    border: '#333',    bg: 'transparent',           label: level };
  }
}

function _idsBuildLine(timeStr, level, cat, msg) {
  const s = _idsLevelStyle(level);
  const el = document.createElement('div');
  el.style.cssText = `padding:4px 8px; border-left:3px solid ${s.border}; background:${s.bg}; margin-bottom:2px; line-height:1.5;`;
  const t = timeStr ? `<span style="color:#555; font-size:10px;">[${timeStr}]</span> ` : '';
  const c = cat ? `<span style="color:#666; font-size:9px; background:#222; padding:1px 4px; margin-right:4px; border-radius:2px;">${cat}</span>` : '';
  el.innerHTML = `${t}${c}<span style="color:${s.color}; font-size:10px; font-weight:700;">${s.label}</span> <span style="color:#ccc; font-size:11px;">${msg}</span>`;
  return el;
}

function _idsBuildAlertCard(event) {
  const s = _idsLevelStyle(event.level);
  const cat = event.category || 'EVENT';
  const solutions = _solutions[cat] || _solutions.INTRUSION;
  const ip = event.data && event.data.ip ? event.data.ip : '';
  const port = event.data && event.data.port ? event.data.port : '22';

  const card = document.createElement('div');
  card.style.cssText = `border:2px solid ${s.border}; background:${s.bg || 'rgba(255,68,85,0.05)'}; margin-bottom:6px; overflow:hidden;`;

  // Header
  const header = document.createElement('div');
  header.style.cssText = `display:flex; align-items:center; justify-content:space-between; padding:6px 10px; background:${s.border}22; border-bottom:1px solid ${s.border}44;`;
  header.innerHTML = `
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="font-size:14px;">${event.level === 'CRITICAL' ? '💀' : event.category === 'HONEYPOT' ? '🍯' : '🚨'}</span>
      <span style="font-family:'Space Grotesk',sans-serif; font-weight:900; font-size:11px; color:${s.color}; letter-spacing:1px;">${event.level} — ${cat}</span>
    </div>
    <span style="font-family:'JetBrains Mono',monospace; font-size:9px; color:#888;">${event.time || new Date().toLocaleTimeString()}</span>
  `;

  // Message
  const msgEl = document.createElement('div');
  msgEl.style.cssText = `padding:6px 10px; font-family:'JetBrains Mono',monospace; font-size:11px; color:#ddd; border-bottom:1px solid #222;`;
  msgEl.textContent = event.msg;

  // Solutions section
  const solEl = document.createElement('div');
  solEl.style.cssText = `padding:6px 10px;`;
  solEl.innerHTML = `<div style="font-family:'Space Grotesk',sans-serif; font-size:10px; font-weight:800; color:#ffcc00; letter-spacing:1px; margin-bottom:4px;">▶ RECOMMENDED ACTIONS</div>`;
  solutions.slice(0, 4).forEach(sol => {
    const s2 = sol.replace('{port}', port).replace('{ip}', ip);
    const item = document.createElement('div');
    item.style.cssText = `font-family:'JetBrains Mono',monospace; font-size:10px; color:#aaa; padding:1px 0; padding-left:8px;`;
    item.textContent = s2;
    solEl.appendChild(item);
  });

  // Dismiss button
  const footer = document.createElement('div');
  footer.style.cssText = `padding:4px 10px; display:flex; justify-content:flex-end; border-top:1px solid #222;`;
  const btn = document.createElement('button');
  btn.textContent = 'ACKNOWLEDGE';
  btn.style.cssText = `font-family:'Space Grotesk',sans-serif; font-size:9px; font-weight:800; padding:2px 8px; background:transparent; border:1px solid #444; color:#888; cursor:pointer; letter-spacing:1px;`;
  btn.onclick = () => { card.style.opacity = '0.3'; btn.textContent = 'ACK\'D'; btn.disabled = true; };
  footer.appendChild(btn);

  card.appendChild(header);
  card.appendChild(msgEl);
  card.appendChild(solEl);
  card.appendChild(footer);
  return card;
}

// Poll /api/events for real data
async function _idsPollReal(container) {
  try {
    const r = await fetch('/api/events');
    if (!r.ok) return;
    const data = await r.json();
    if (!data.ok || !data.events) return;

    let added = 0;
    for (const ev of data.events) {
      // Create a unique key for deduplication
      const key = ev.category + '|' + ev.level + '|' + ev.msg + '|' + ev.time;
      if (_idsSeenIds.has(key)) continue;
      _idsSeenIds.add(key);

      let el;
      const isCritical = ev.level === 'CRITICAL' || ev.level === 'ALERT' || ev.category === 'TRIPWIRE' || ev.category === 'HONEYPOT';
      if (isCritical && !ev.acknowledged) {
        el = _idsBuildAlertCard(ev);
      } else {
        el = _idsBuildLine(ev.time, ev.level, ev.category, ev.msg);
      }
      container.appendChild(el);
      added++;
    }

    if (added > 0) {
      container.scrollTop = container.scrollHeight;
    }
    // Prune old simple lines (keep cards)
    while (container.childNodes.length > 60) {
      const first = container.firstChild;
      if (first) container.removeChild(first);
    }
  } catch(e) { /* offline */ }
}

// Inject ambient simulated network noise
function _idsInjectAmbient(container) {
  const t = _ambientEvents[Math.floor(Math.random() * _ambientEvents.length)];
  const ip = _mockIPs[Math.floor(Math.random() * _mockIPs.length)];
  const port = [22, 80, 443, 445, 3389, 8080][Math.floor(Math.random() * 6)];
  const msg = t.msg.replace('{ip}', ip).replace('{port}', port);
  const time = new Date().toLocaleTimeString();
  const el = _idsBuildLine(time, t.level, t.cat, msg);
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  while (container.childNodes.length > 80) container.removeChild(container.firstChild);
}

window.startIdsFeed = function() {
  const container = document.getElementById('overview-ids-feed');
  if (!container) return;

  container.innerHTML = '';
  // Boot message
  const boot = _idsBuildLine(new Date().toLocaleTimeString(), 'SYS', 'BOOT', 'IDS daemon online — all interfaces monitored');
  container.appendChild(boot);

  if (_idsTimer) clearInterval(_idsTimer);
  _idsSeenIds.clear();

  // Poll real events immediately, then every 5s
  _idsPollReal(container);
  const realTimer = setInterval(() => _idsPollReal(container), 5000);

  // Inject ambient noise every 3-6s
  let ambientDelay = 3000;
  function scheduleAmbient() {
    setTimeout(() => {
      _idsInjectAmbient(container);
      ambientDelay = 3000 + Math.random() * 3000;
      scheduleAmbient();
    }, ambientDelay);
  }
  scheduleAmbient();

  _idsTimer = realTimer;
};

// Aegis Shield (Antivirus / System Protection)
// ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
async function aegisRefresh() {
  document.getElementById('aegis-status-indicator').innerHTML = `<div class="spinner" style="width:16px;height:16px;display:inline-block;"></div> <span style="margin-left:8px;">Scanning...</span>`;
  try {
    const res = await fetch(`${API}/aegis/scan`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);

    const aegis = data.data;

    // Render Processes
    let phtml = '';
    if (aegis.processes && aegis.processes.length > 0) {
        const sorted = [...aegis.processes].sort((a,b) => (a.suspicious === b.suspicious) ? 0 : a.suspicious ? -1 : 1);
        phtml = sorted.map(p => `
          <tr style="${p.suspicious ? 'background: rgba(255,51,102,0.1); border-left: 2px solid var(--danger);' : ''}">
            <td>${p.pid}</td>
            <td><strong>${p.name}</strong></td>
            <td><span style="font-family: monospace; font-size: 11px;">${p.path}</span></td>
            <td>${p.suspicious ? '<span style="color:var(--danger)">Suspicious</span>' : '<span style="color:var(--success)">OK</span>'}</td>
            <td>
              <button class="btn btn-danger" style="padding:4px 8px; font-size:12px;" onclick="aegisKillProcess(${p.pid})">Kill</button>
            </td>
          </tr>
        `).join('');
    } else {
        phtml = `<tr><td colspan="5" style="text-align:center;">No processes found.</td></tr>`;
    }
    document.getElementById('aegis-processes-table').innerHTML = phtml;

    // Render Startup
    let shtml = '';
    if (aegis.startup && aegis.startup.length > 0) {
        shtml = aegis.startup.map(s => `
          <tr>
            <td><strong>${s.name}</strong></td>
            <td><span style="font-family: monospace; font-size: 11px; word-break: break-all;">${s.path}</span></td>
            <td>
              <button class="btn" style="padding:4px 8px; font-size:12px;" onclick="aegisDisableStartup('${s.name}')">Disable</button>
            </td>
          </tr>
        `).join('');
    } else {
        shtml = `<tr><td colspan="3" style="text-align:center;">No startup items found.</td></tr>`;
    }
    document.getElementById('aegis-startup-table').innerHTML = shtml;

    // Render Status Indicator
    document.getElementById('aegis-status-indicator').innerHTML = `
      <span style="color: ${aegis.hosts_ok ? 'var(--success)' : 'var(--danger)'}; font-weight: bold;">
        Hosts File: ${aegis.hosts_ok ? 'OK' : 'Hijacked!'}
      </span>
    `;

  } catch (e) {
    console.error('Aegis fetch failed:', e);
    showToast('Failed to load Aegis data.', 'error');
    document.getElementById('aegis-status-indicator').innerHTML = `<span style="color:var(--danger)">Error</span>`;
  }
}

async function aegisKillProcess(pid) {
  if (!confirm(`Are you sure you want to terminate process ${pid}?`)) return;
  try {
    const res = await fetch(`${API}/aegis/kill`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pid })
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);
    showToast(data.message, 'success');
    aegisRefresh();
  } catch (e) {
    showToast(`Error killing process: ${e.message}`, 'error');
  }
}

async function aegisDisableStartup(name) {
  if (!confirm(`Disable startup item '${name}'?`)) return;
  try {
    const res = await fetch(`${API}/aegis/disable_startup`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);
    showToast(data.message, 'success');
    aegisRefresh();
  } catch (e) {
    showToast(`Error disabling startup item: ${e.message}`, 'error');
  }
}

async function aegisCleanTemp() {
  if (!confirm(`Wipe all temporary files?`)) return;
  try {
    const res = await fetch(`${API}/aegis/clean_temp`, { method: 'POST' });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);
    showToast(data.message, 'success');
  } catch (e) {
    showToast(`Error cleaning temp files: ${e.message}`, 'error');
  }
}

async function aegisResetHosts() {
  if (!confirm(`Reset Windows Hosts file to default?`)) return;
  try {
    const res = await fetch(`${API}/aegis/reset_hosts`, { method: 'POST' });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);
    showToast(data.message, 'success');
    aegisRefresh();
  } catch (e) {
    showToast(`Error resetting hosts file: ${e.message}`, 'error');
  }
}

async function aegisTriggerScan() {
  showToast('Triggering Defender Scan...', 'info');
  try {
    const res = await fetch(`${API}/aegis/defender_scan`, { method: 'POST' });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);
    showToast(data.message, 'success');
  } catch (e) {
    showToast(`Error triggering scan: ${e.message}`, 'error');
  }
}

// ══════════════════════════════════════════════════════
//  ⚡ KALI TERMINAL CONTROLLER
//  xterm.js + polling loop → Flask /api/terminal/*
// ══════════════════════════════════════════════════════

const _term = {
  xterm: null,
  fitAddon: null,
  sessionId: 'main-' + Math.random().toString(36).slice(2, 8),
  shell: 'powershell',
  pollTimer: null,
  pollInterval: 120,   // ms — fast polling for snappy feel
  started: false,
  kaliAvailable: false,
};

// ── Init (called when terminal tab opens) ──────────────
async function initTerminal() {
  if (_term.started) {
    if (_term.fitAddon) _term.fitAddon.fit();
    return;
  }

  const container = document.getElementById('terminal-xterm');
  if (!container || typeof Terminal === 'undefined') return;

  // Build xterm instance
  _term.xterm = new Terminal({
    theme: {
      background:   '#0a0a0a',
      foreground:   '#00ff41',
      cursor:       '#00ff41',
      cursorAccent: '#000',
      black:        '#0a0a0a',
      green:        '#00ff41',
      brightGreen:  '#39ff14',
      cyan:         '#00e5cc',
      blue:         '#268bd2',
      yellow:       '#f7b731',
      red:          '#ff4757',
      white:        '#cccccc',
      brightWhite:  '#ffffff',
    },
    fontFamily: '"Cascadia Code", "Fira Code", "Consolas", monospace',
    fontSize: 13,
    lineHeight: 1.25,
    cursorBlink: true,
    cursorStyle: 'block',
    allowTransparency: true,
    scrollback: 5000,
  });

  _term.fitAddon = new FitAddon.FitAddon();
  _term.xterm.loadAddon(_term.fitAddon);
  _term.xterm.open(container);
  _term.fitAddon.fit();

  // Resize observer — keep terminal fitting the container
  const ro = new ResizeObserver(() => {
    if (_term.fitAddon) _term.fitAddon.fit();
  });
  ro.observe(container);

  // Keyboard input → POST to /api/terminal/input
  _term.xterm.onData(async (data) => {
    await fetch(`${API}/terminal/input`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: _term.sessionId, data }),
    });
  });

  _term.started = true;

  // Check Kali availability
  await termCheckKaliStatus();

  // Start the shell
  await termStartShell();

  // Start output polling
  _termStartPolling();

  _term.xterm.writeln('\x1b[1;32m⚡ Terminal ready. Type a command and press Enter.\x1b[0m');
}

// ── Check if Kali WSL2 is available ───────────────────
async function termCheckKaliStatus() {
  try {
    const res  = await fetch(`${API}/terminal/status`);
    const data = await res.json();
    _term.kaliAvailable = data.kali_available || false;

    const statusEl = document.getElementById('term-kali-status');
    const kaliBtn  = document.getElementById('term-btn-kali');
    const banner   = document.getElementById('term-kali-install-banner');

    if (_term.kaliAvailable) {
      if (statusEl) { statusEl.textContent = '🟢 Kali: Online'; statusEl.className = 'kali-online'; }
      if (kaliBtn)  kaliBtn.disabled = false;
      if (banner)   banner.style.display = 'none';
    } else {
      if (statusEl) { statusEl.textContent = '🔴 Kali: Not installed'; statusEl.className = 'kali-offline'; }
      if (kaliBtn)  kaliBtn.disabled = true;
      if (banner)   banner.style.display = 'block';
    }
  } catch (e) {
    console.warn('[Terminal] Status check failed:', e);
  }
}

// ── Start / restart a shell session ───────────────────
async function termStartShell(shell) {
  if (shell) _term.shell = shell;
  try {
    const res  = await fetch(`${API}/terminal/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: _term.sessionId, shell: _term.shell }),
    });
    const data = await res.json();
    if (!data.ok) {
      _term.xterm.writeln(`\x1b[1;31m✗ Failed to start ${_term.shell}: ${data.error}\x1b[0m`);
    } else {
      _term.xterm.writeln(`\x1b[2;32m[Shell: ${_term.shell} | Session: ${_term.sessionId}]\x1b[0m`);
    }
  } catch (e) {
    _term.xterm.writeln(`\x1b[1;31m✗ Cannot reach terminal backend: ${e.message}\x1b[0m`);
  }
}

// ── Poll for output ────────────────────────────────────
function _termStartPolling() {
  if (_term.pollTimer) clearInterval(_term.pollTimer);
  _term.pollTimer = setInterval(async () => {
    try {
      const res  = await fetch(`${API}/terminal/output?session_id=${_term.sessionId}`);
      const data = await res.json();
      if (data.data && data.data.length > 0) {
        _term.xterm.write(data.data);
      }
    } catch (_) { /* ignore network blips */ }
  }, _term.pollInterval);
}

// ── Shell selector UI ─────────────────────────────────
async function termSelectShell(shell) {
  if (shell === _term.shell) return;

  // Kill existing session
  await fetch(`${API}/terminal/kill`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: _term.sessionId }),
  });

  // Update UI buttons
  document.querySelectorAll('.term-shell-btn').forEach(b => b.classList.remove('active-shell'));
  const btn = document.getElementById(`term-btn-${shell}`);
  if (btn) btn.classList.add('active-shell');

  _term.xterm.writeln(`\x1b[2;33m\r\n[Switching to ${shell}...]\x1b[0m`);
  await termStartShell(shell);
}

// ── Restart current shell ─────────────────────────────
async function termRestart() {
  _term.xterm.writeln('\x1b[2;33m\r\n[Restarting shell...]\x1b[0m');
  await fetch(`${API}/terminal/kill`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: _term.sessionId }),
  });
  await termStartShell();
}

// ── Clear screen ──────────────────────────────────────
function termClear() {
  if (_term.xterm) _term.xterm.clear();
}

// Terminal initialization hook is now merged directly into the main showTab function to prevent recursion crashes

