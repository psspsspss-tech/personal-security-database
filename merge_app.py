import os
import re

desktop_app = r"C:\Users\acer\Desktop\Security Suite\dashboard\app.js"

with open(desktop_app, 'r', encoding='utf-8') as f:
    d_content = f.read()

# 1. Replace the old Kali logic with new Matrix WebSSH logic
old_logic_pattern = re.compile(r"// .*? KALI TERMINAL LOGIC .*?\nlet kaliTermInterval = null;.*?kaliTermInterval = setInterval\(pollKaliOutput, 2000\);", re.DOTALL)

new_logic = """/* ------------------------------------------- KALI TERMINAL --- */
let term = null;
let fitAddon = null;
let socket = null;
let isConnected = false;

function initTerminal() {
  if (term) return;
  term = new Terminal({
    cursorBlink: true,
    fontFamily: '"JetBrains Mono", monospace',
    fontSize: 14,
    theme: {
      background: '#000000',
      foreground: '#00ff00',
      cursor: '#00ff00'
    }
  });
  fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(document.getElementById('terminal-container'));
  fitAddon.fit();

  window.addEventListener('resize', () => {
    if (fitAddon) {
      fitAddon.fit();
      if (socket && isConnected) {
        socket.emit('ssh_resize', { cols: term.cols, rows: term.rows });
      }
    }
  });

  term.onData(data => {
    if (socket && isConnected) {
      socket.emit('ssh_input', { input: data });
    }
  });
}

function connectKali() {
  const ip = document.getElementById('kali-ip').value.trim();
  const pass = document.getElementById('kali-pass').value.trim();
  const user = document.getElementById('kali-user')?.value.trim() || 'kali';
  if (!ip) { showToast('Please enter the phone IP address', 'error'); return; }

  document.getElementById('terminal-overlay').innerHTML = '<div class="matrix-text" style="color:#0f0;font-family:monospace;text-align:center;">Establishing encrypted SSH tunnel to ' + ip + '...</div>';
  document.getElementById('btn-kali-connect').disabled = true;

  if (!socket) {
    socket = io();
    socket.on('ssh_status', data => {
      if (data.status === 'connected') {
        isConnected = true;
        document.getElementById('terminal-overlay').style.display = 'none';
        showToast('SSH Tunnel Established', 'success');
        if (!term) initTerminal();
        setTimeout(() => {
          fitAddon.fit();
          socket.emit('ssh_resize', { cols: term.cols, rows: term.rows });
        }, 500);
      } else {
        document.getElementById('terminal-overlay').innerHTML = '<div class="matrix-text" style="color:red;font-family:monospace;text-align:center;">Connection Failed: ' + (data.message || 'Unknown error') + '</div>';
        document.getElementById('btn-kali-connect').disabled = false;
        showToast('Connection failed', 'error');
      }
    });
    socket.on('ssh_output', data => {
      if (term) term.write(data.data);
    });
    socket.on('disconnect', () => {
      isConnected = false;
      document.getElementById('terminal-overlay').style.display = 'flex';
      document.getElementById('terminal-overlay').innerHTML = '<div class="matrix-text" style="color:red;font-family:monospace;text-align:center;">SSH Tunnel Disconnected</div>';
      document.getElementById('btn-kali-connect').disabled = false;
    });
  }

  socket.emit('ssh_connect', { ip: ip, password: pass || 'kali', username: user });
}

// Make sure terminal resizes when tab is shown
const originalShowTab = window.showTab;
window.showTab = function(tabId) {
  originalShowTab(tabId);
  if (tabId === 'kaliterminal') {
    setTimeout(() => {
      if (!term) initTerminal();
      if (fitAddon) fitAddon.fit();
    }, 100);
  }
};
"""

d_content = old_logic_pattern.sub(new_logic, d_content)

with open(desktop_app, 'w', encoding='utf-8') as f:
    f.write(d_content)

print("Merged app.js")
