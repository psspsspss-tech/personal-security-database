"""
terminal_service.py — Web Terminal Shell Manager
Spawns and manages interactive shell sessions (PowerShell, CMD, WSL Kali)
over WebSocket for the Security Suite dashboard terminal panel.
"""

import subprocess
import threading
import os
import signal
import sys
import time
import queue

# Active terminal sessions: { session_id: TerminalSession }
_sessions = {}
_sessions_lock = threading.Lock()


class TerminalSession:
    """Manages a single interactive shell process with non-blocking I/O."""

    SHELL_COMMANDS = {
        'powershell': ['powershell.exe', '-NoLogo', '-NoProfile'],
        'cmd': ['cmd.exe'],
        'kali': ['wsl.exe', '-d', 'kali-linux'],
        'wsl': ['wsl.exe'],
    }

    def __init__(self, session_id, shell='powershell', emit_fn=None):
        self.session_id = session_id
        self.shell = shell
        self.emit_fn = emit_fn  # callback: emit_fn(session_id, data_str)
        self.process = None
        self._reader_thread = None
        self._alive = False
        self._output_queue = queue.Queue()

    def start(self):
        """Spawn the shell process."""
        cmd = self.SHELL_COMMANDS.get(self.shell, self.SHELL_COMMANDS['powershell'])
        
        try:
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = subprocess.CREATE_NO_WINDOW

            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                creationflags=creationflags,
                env=os.environ.copy(),
            )
            self._alive = True
            self._reader_thread = threading.Thread(
                target=self._read_loop, daemon=True
            )
            self._reader_thread.start()
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"[Terminal] Failed to start {self.shell}: {e}")
            return False

    def _read_loop(self):
        """Background thread: continuously read stdout and emit to client."""
        try:
            while self._alive and self.process and self.process.poll() is None:
                chunk = self.process.stdout.read(4096)
                if chunk:
                    try:
                        text = chunk.decode('utf-8', errors='replace')
                    except Exception:
                        text = chunk.decode('latin-1', errors='replace')
                    if self.emit_fn:
                        self.emit_fn(self.session_id, text)
                else:
                    time.sleep(0.02)
        except Exception as e:
            if self._alive:
                if self.emit_fn:
                    self.emit_fn(self.session_id, f'\r\n[Session ended: {e}]\r\n')
        finally:
            self._alive = False
            if self.emit_fn:
                self.emit_fn(self.session_id, '\r\n[Shell process exited]\r\n')

    def write(self, data: str):
        """Send keystrokes to the shell stdin."""
        if self.process and self._alive:
            try:
                self.process.stdin.write(data.encode('utf-8'))
                self.process.stdin.flush()
            except Exception as e:
                print(f"[Terminal] Write error: {e}")

    def kill(self):
        """Terminate the shell process."""
        self._alive = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

    @property
    def is_alive(self):
        return self._alive and self.process and self.process.poll() is None


def create_session(session_id, shell='powershell', emit_fn=None):
    """Create and start a new terminal session. Returns True on success."""
    with _sessions_lock:
        # Kill existing session for this ID if any
        if session_id in _sessions:
            _sessions[session_id].kill()

        sess = TerminalSession(session_id, shell=shell, emit_fn=emit_fn)
        ok = sess.start()
        if ok:
            _sessions[session_id] = sess
        return ok


def write_to_session(session_id, data):
    """Send input to an existing terminal session."""
    with _sessions_lock:
        sess = _sessions.get(session_id)
    if sess:
        sess.write(data)


def kill_session(session_id):
    """Kill and remove a terminal session."""
    with _sessions_lock:
        sess = _sessions.pop(session_id, None)
    if sess:
        sess.kill()


def is_kali_available():
    """Check if Kali WSL distro is installed and available."""
    try:
        result = subprocess.run(
            ['wsl.exe', '-d', 'kali-linux', '--', 'echo', 'ok'],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        return result.returncode == 0
    except Exception:
        return False


def is_wsl_available():
    """Check if WSL is installed at all."""
    try:
        result = subprocess.run(
            ['wsl.exe', '--list'],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        return result.returncode == 0
    except Exception:
        return False
