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

// ──────────────────────────────────────────────────────
// AUTO-UPDATE SYSTEM
// Polls /api/version every 30s. When the server restarts
// (you made changes + ran start.bat), the version hash
// changes and every connected device auto-reloads.
// ──────────────────────────────────────────────────────
let _knownVersion = null;
let _updateBannerShown = false;

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
  document.getElementById(`tab-${tab}`)?.classList.add('active');
  document.getElementById(`panel-${tab}`)?.classList.add('active');
  if (tab === 'network')   loadDevices();
  if (tab === 'ports')     loadPorts();
  if (tab === 'alerts')    loadAlerts();
  if (tab === 'eventlog')  loadEventLog();
  if (tab === 'dns')       loadDNS();
  if (tab === 'processes') loadProcesses();
  if (tab === 'setup')     loadSetupConfig();
  if (tab === 'connect')   loadConnect();
}

// ──────────────────────────────────────────────────────
// CONNECT DEVICES — QR Code + Agents
// ──────────────────────────────────────────────────────
let _qrGenerated = false;

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

    // Show URL text
    const urlEl = document.getElementById('net-url');
    if (urlEl) urlEl.textContent = url;

    // Pre-fill agent download steps
    const agentUrl = `${url}/agent.py`;
    const androidEl = document.getElementById('android-agent-url');
    if (androidEl) androidEl.textContent = `curl -O ${agentUrl}`;
    const winEl = document.getElementById('win-agent-url');
    if (winEl) winEl.textContent = `(open in browser) ${agentUrl}`;

    // Generate QR code (once)
    const qrEl = document.getElementById('qr-code');
    if (qrEl && !_qrGenerated && typeof QRCode !== 'undefined') {
      qrEl.innerHTML = '';
      new QRCode(qrEl, {
        text: url,
        width: 160,
        height: 160,
        colorDark: '#000000',
        colorLight: '#ffffff',
        correctLevel: QRCode.CorrectLevel.M
      });
      _qrGenerated = true;
    } else if (qrEl && !_qrGenerated) {
      qrEl.innerHTML = `<div style="color:#666;font-size:11px;padding:16px">${url}</div>`;
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
                ${d.doh_enabled ? 'DoH Enabled' : 'DoH Not Enabled'}
              </div>
              <div class="vpn-sub">${d.doh_enabled ? 'DNS queries are encrypted' : 'Your ISP can see every domain you visit'}</div>
            </div>
          </div>
          ${!d.doh_enabled ? `<div class="rec-box">Enable: Settings → Network & Internet → DNS → Custom (1.1.1.1) → Enable DoH</div>` : ''}
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
  const maxDash = 251.2;
  const offset = maxDash - (score / 100) * maxDash;
  const fill = document.getElementById('gauge-fill');
  if (fill) fill.style.strokeDashoffset = offset;
  const scoreEl = document.getElementById('gauge-score');
  if (scoreEl) scoreEl.textContent = score;
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
    fetchAgents(),
    fetchAlerts(),
    fetchBluetoothData()
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

    // Score gauge + header
    updateGauge(s.security_score);
    document.getElementById('score-status-label').textContent = scoreInfo.label;
    document.getElementById('score-status-label').style.color = scoreInfo.color;

    // Stat cards
    setStatCard('stat-score', s.security_score, '/100', `${scoreInfo.label}`,
      s.security_score >= 75 ? 'good' : (s.security_score >= 50 ? 'warn' : 'bad'));
    setStatCard('stat-devices', s.unknown_devices === 0 ? '✓' : s.unknown_devices,
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
    document.getElementById('sys-grid').innerHTML = `
      <div class="sys-row"><span class="sys-key">Hostname</span><span class="sys-val">${sys.hostname}</span></div>
      <div class="sys-row"><span class="sys-key">Uptime</span><span class="sys-val">${sys.uptime_hours}h</span></div>
      <div class="sys-row"><span class="sys-key">Memory</span><span class="sys-val">${sys.memory_used_gb}/${sys.memory_total_gb} GB</span></div>
      <div class="sys-row"><span class="sys-key">Pending Updates</span><span class="sys-val ${s.pending_updates > 5 ? 'text-orange' : ''}">${s.pending_updates < 0 ? 'Unknown' : s.pending_updates}</span></div>
    `;
    document.getElementById('cpu-val').textContent = `${sys.cpu_percent}%`;
    document.getElementById('cpu-bar').style.width = `${sys.cpu_percent}%`;
    document.getElementById('mem-val').textContent = `${sys.memory_percent}%`;
    document.getElementById('mem-bar').style.width = `${sys.memory_percent}%`;

    // Deductions
    const dl = document.getElementById('deductions-list');
    if (s.deductions && s.deductions.length > 0) {
      dl.innerHTML = s.deductions.map(d => `<div class="deduction-item">⚠ ${d}</div>`).join('');
    } else {
      dl.innerHTML = `<div class="deduction-item none">✓ No security issues found!</div>`;
    }

    // Alert for unknown devices
    if (s.unknown_devices > 0) {
      document.getElementById('alert-text').textContent =
        `⚠ ${s.unknown_devices} unknown device(s) detected on your network! Check the Network tab.`;
      document.getElementById('alerts-bar').style.display = 'block';
    }

    // Connection indicator
    document.getElementById('connection-pill').style.opacity = '1';

  } catch (e) {
    console.error('Status fetch failed:', e);
    document.getElementById('connection-pill').style.opacity = '0.4';
    showApiError();
  }
}

function showApiError() {
  const dl = document.getElementById('deductions-list');
  if (dl) dl.innerHTML = `<div class="deduction-item">
    ⚠ Cannot connect to backend server.<br>
    <small>Make sure <code>python backend/server.py</code> is running.</small>
  </div>`;
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
  showToast(`Deep scanning ${ip}... this takes a moment.`, 'info', 5000);
  try {
    const res = await fetch(`${API}/device/deep-scan`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ip })
    });
    const data = await res.json();
    if (data.ok) {
      showVulnerabilityModal(ip, data.open_ports);
    } else throw new Error(data.error);
  } catch(e) { showToast(`Deep scan failed: ${e.message}`, 'error'); }
}

function showVulnerabilityModal(ip, ports) {
  let html = `<p>Vulnerability Assessment for <strong>${ip}</strong></p>`;
  
  if (ports.length === 0) {
    html += `<div style="padding:15px;background:rgba(0,255,0,0.1);border:1px solid var(--success);border-radius:6px;margin-top:10px;">
      ✅ No highly common vulnerable ports exposed.
    </div>`;
  } else {
    html += `<div style="display:flex;flex-direction:column;gap:10px;margin-top:10px;">`;
    ports.forEach(p => {
      let color = 'var(--text-secondary)';
      let bg = 'var(--card-bg)';
      if (p.risk === 'high') { color = 'var(--danger)'; bg = 'rgba(255,0,0,0.1)'; }
      else if (p.risk === 'medium') { color = 'var(--warning)'; bg = 'rgba(255,165,0,0.1)'; }
      
      html += `
        <div style="padding:12px; border-left: 4px solid ${color}; background: ${bg}; border-radius: 4px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
            <strong style="color:${color}">Port ${p.port} - ${p.service}</strong>
            <span style="font-size:11px; text-transform:uppercase; padding:2px 6px; background:var(--bg); border-radius:10px;">${p.risk} risk</span>
          </div>
          <div style="font-family:monospace; font-size:12px; color:var(--text-secondary); background:rgba(0,0,0,0.2); padding:6px; border-radius:4px; overflow-x:auto;">
            ${p.banner}
          </div>
        </div>
      `;
    });
    html += `</div>`;
  }

  document.getElementById('modal-title').innerText = 'Vulnerability Report';
  document.getElementById('modal-body').innerHTML = html;
  document.getElementById('modal-footer').innerHTML = `<button class="btn" onclick="closeModal()">Close</button>`;
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
    el.innerHTML = `<div class="empty-state">No unknown devices — network looks clean ✓</div>`;
    return;
  }
  el.innerHTML = unknowns.map(d => `
    <div class="alert-item-small severity-high">
      <div>
        <div class="alert-title">⚠ Unknown Device</div>
        <div class="alert-msg">${d.ip} · ${d.mac} · ${d.vendor || 'Unknown Vendor'}</div>
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
const RISKY_PORTS = [21, 23, 135, 137, 138, 139, 445, 1433, 3306, 3389, 5900, 8080];
const MEDIUM_PORTS = [80, 443, 8443, 5432];

function portRisk(port) {
  if (RISKY_PORTS.includes(port)) return 'high';
  if (MEDIUM_PORTS.includes(port)) return 'medium';
  return 'low';
}

async function loadPorts() {
  const tbody = document.getElementById('ports-tbody');
  tbody.innerHTML = `<tr><td colspan="5" class="table-loading"><div class="spinner" style="margin:12px auto"></div></td></tr>`;

  try {
    const res = await fetch(`${API}/ports`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);

    const ports = data.data;
    if (ports.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="table-loading">No listening ports found.</td></tr>`;
      return;
    }

    tbody.innerHTML = ports.map(p => {
      const risk = portRisk(p.port);
      const riskBadge = `<span class="risk-badge risk-${risk}">${risk.toUpperCase()}</span>`;
      return `<tr>
        <td style="font-weight:700; color: ${risk === 'high' ? 'var(--red)' : risk === 'medium' ? 'var(--orange)' : 'var(--text-primary)'}">:${p.port}</td>
        <td>${p.address || '*'}</td>
        <td>${p.process || '—'}</td>
        <td>${p.pid || '—'}</td>
        <td>${riskBadge}</td>
      </tr>`;
    }).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5" class="table-loading" style="color:var(--red)">Error: ${e.message}</td></tr>`;
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
  return `<div class="alert-full severity-${a.severity} ${a.acknowledged ? 'acknowledged' : ''}" id="alert-${a.id}">
    <div class="alert-full-icon">${icon}</div>
    <div class="alert-full-body">
      <div class="alert-full-title">${a.title}</div>
      <div class="alert-full-msg">${a.message}</div>
      <div class="alert-full-meta">
        <span>🕒 ${time}</span>
        <span>Severity: ${a.severity.toUpperCase()}</span>
        ${a.acknowledged ? '<span style="color:var(--green)">✓ Acknowledged</span>' : ''}
      </div>
      ${!a.acknowledged ? `<div class="alert-full-actions">
        <button class="btn-sm" onclick="acknowledgeAlert('${a.id}')">✓ Acknowledge</button>
        ${a.type === 'unknown_device' ? `<button class="btn-approve" onclick="openApproveModal('${a.device?.mac}','${a.device?.ip}','${a.device?.vendor}')">✓ Approve Device</button>` : ''}
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
    showToast('Alert acknowledged', 'success');
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
    }
  } catch (e) {
    showToast('Failed to approve device', 'error');
  }
}

function showDeviceDetail(mac) {
  // Find device from last scan — quick info modal
  document.getElementById('modal-title').textContent = 'Device Info';
  document.getElementById('modal-body').innerHTML = `
    <div class="modal-detail-row"><span class="modal-detail-key">MAC</span><span class="modal-detail-val">${mac}</span></div>
    <p style="margin-top:12px; font-size:13px; color:var(--text-muted)">Click a device's Approve or Revoke button to manage its access.</p>`;
  document.getElementById('modal-footer').innerHTML = `<button class="btn-sm" onclick="closeModal()">Close</button>`;
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
  showTab('overview');
  startPolling();
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
});

// ─── BLUETOOTH RADAR LOGIC ───

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

// --- TOOLKIT LOGIC ---
async function runToolkitCommand(cmd) {
  const target = document.getElementById('toolkit-target').value.trim();
  const out = document.getElementById('toolkit-output');
  if (!target) {
    out.textContent = 'Please enter a target IP or domain.';
    return;
  }
  out.textContent = 'Running ' + cmd + ' on ' + target + '... Please wait.';
  try {
    const res = await fetch(API + '/toolkit/' + cmd, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ip: target})
    });
    const data = await res.json();
    if (data.ok) {
      out.textContent = data.output;
    } else {
      out.textContent = 'Error: ' + data.error;
    }
  } catch (e) {
    out.textContent = 'Network Error: ' + e.message;
  }
}


// --- UPDATE NETHUNTER URL ---
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    const el = document.getElementById('nethunter-agent-url');
    if(el) el.textContent = window.location.protocol + '//' + window.location.hostname + ':8080/nethunter_bt_agent.py';
  }, 2000);
});

