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
import select

if sys.platform != 'win32':
    import pty
    import fcntl

# Active terminal sessions: { session_id: TerminalSession }
_sessions = {}
_sessions_lock = threading.Lock()


class TerminalSession:
    """Manages a single interactive shell process with non-blocking I/O (PTY on Linux/macOS)."""

    import shutil
    if sys.platform == 'win32':
        SHELL_COMMANDS = {
            'powershell': ['powershell.exe', '-NoLogo', '-NoProfile'],
            'cmd': ['cmd.exe'],
            'kali': ['wsl.exe', '-d', 'kali-linux'],
            'wsl': ['wsl.exe'],
        }
    else:
        # Determine default Linux shells (Zsh is default on modern Kali)
        default_shell = '/bin/bash'
        if os.path.exists('/bin/zsh'):
            default_shell = '/bin/zsh'
            
        SHELL_COMMANDS = {
            'powershell': ['pwsh'] if shutil.which('pwsh') else [default_shell],
            'cmd': ['/bin/sh'],
            'kali': [default_shell],
            'wsl': [default_shell],
        }

    def __init__(self, session_id, shell='powershell', emit_fn=None):
        self.session_id = session_id
        self.shell = shell
        self.emit_fn = emit_fn  # callback: emit_fn(session_id, data_str)
        self.process = None
        self.master_fd = None
        self.slave_fd = None
        self._reader_thread = None
        self._alive = False
        self._output_queue = queue.Queue()

    def start(self):
        """Spawn the shell process."""
        cmd = self.SHELL_COMMANDS.get(self.shell, self.SHELL_COMMANDS['powershell'])
        
        try:
            if sys.platform == 'win32':
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=0,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    env=os.environ.copy(),
                )
            else:
                # Spawn a pseudo-terminal (PTY) on Unix to support interactive shells natively
                self.master_fd, self.slave_fd = pty.openpty()
                
                # Make master_fd non-blocking
                fl = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
                fcntl.fcntl(self.master_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
                
                # Set terminal window size (30 rows, 100 cols) to prevent BufferWidth/Height errors
                import struct
                import termios
                winsize = struct.pack("HHHH", 30, 100, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
                
                # Set environment variables like TERM to ensure rich color support
                env = os.environ.copy()
                env['TERM'] = 'xterm-256color'
                env['COLUMNS'] = '100'
                env['LINES'] = '30'
                
                self.process = subprocess.Popen(
                    cmd,
                    stdin=self.slave_fd,
                    stdout=self.slave_fd,
                    stderr=self.slave_fd,
                    preexec_fn=os.setsid, # Put in its own session to kill all sub-processes
                    env=env,
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
            if sys.platform == 'win32':
                while self._alive and self.process and self.process.poll() is None:
                    chunk = self.process.stdout.read(4096)
                    if chunk:
                        text = chunk.decode('utf-8', errors='replace')
                        if self.emit_fn:
                            self.emit_fn(self.session_id, text)
                    else:
                        time.sleep(0.02)
            else:
                # Unix select-based non-blocking PTY read loop
                while self._alive and self.process and self.process.poll() is None:
                    r, _, _ = select.select([self.master_fd], [], [], 0.05)
                    if self.master_fd in r:
                        try:
                            chunk = os.read(self.master_fd, 4096)
                            if chunk:
                                text = chunk.decode('utf-8', errors='replace')
                                if self.emit_fn:
                                    self.emit_fn(self.session_id, text)
                            else:
                                break
                        except BlockingIOError:
                            pass
                        except OSError:
                            break
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
        if self._alive:
            try:
                if sys.platform == 'win32':
                    if self.process:
                        self.process.stdin.write(data.encode('utf-8'))
                        self.process.stdin.flush()
                else:
                    if self.master_fd is not None:
                        os.write(self.master_fd, data.encode('utf-8'))
            except Exception as e:
                print(f"[Terminal] Write error: {e}")

    def resize(self, rows: int, cols: int):
        """Resize the PTY window to match the browser terminal dimensions."""
        if sys.platform == 'win32' or self.master_fd is None:
            return
        try:
            import struct, termios
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
            # Also send SIGWINCH to notify the shell process of the resize
            if self.process and self.process.poll() is None:
                os.killpg(os.getpgid(self.process.pid), signal.SIGWINCH)
        except Exception as e:
            print(f"[Terminal] Resize error: {e}")

    def kill(self):
        """Terminate the shell process and close file descriptors."""
        self._alive = False
        if self.process:
            try:
                if sys.platform != 'win32':
                    # Kill the entire process group
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                else:
                    self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    if sys.platform != 'win32':
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    else:
                        self.process.kill()
                except Exception:
                    pass
                    
        # Close Unix PTY file descriptors
        if sys.platform != 'win32':
            try:
                if self.master_fd is not None:
                    os.close(self.master_fd)
                if self.slave_fd is not None:
                    os.close(self.slave_fd)
            except Exception:
                pass
            self.master_fd = None
            self.slave_fd = None

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


def resize_session(session_id, rows: int, cols: int):
    """Resize the PTY for an existing terminal session."""
    with _sessions_lock:
        sess = _sessions.get(session_id)
    if sess:
        sess.resize(rows, cols)


def kill_session(session_id):
    """Kill and remove a terminal session."""
    with _sessions_lock:
        sess = _sessions.pop(session_id, None)
    if sess:
        sess.kill()


def is_kali_available():
    """Check if Kali is available (either natively or via WSL)."""
    if sys.platform != 'win32':
        # Check if the host OS is Kali Linux
        try:
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release') as f:
                    if 'kali' in f.read().lower():
                        return True
        except Exception:
            pass
        return False

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
    if sys.platform != 'win32':
        return False
    try:
        result = subprocess.run(
            ['wsl.exe', '--list'],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        return result.returncode == 0
    except Exception:
        return False
