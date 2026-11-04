"""Start, stop and locate a per-profile voxl process bound to 127.0.0.1.

The password lives in ``<HERMES_HOME>/bot-desktop/voxl.secret`` (0600) and in the
child's ``VOXL_PASSWORD`` environment. It is never put on argv, in a URL, or in a
log line. voxl itself is told ``--enable-basic-auth=true`` and the gateway injects
``Authorization: Bearer`` when it proxies.
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from hermes_constants import get_hermes_home
from tools.bot_desktop import backend as _backend
from tools.bot_desktop import voxl_install

logger = logging.getLogger(__name__)

LISTEN_ADDR = "127.0.0.1"
HEALTH_TIMEOUT_S = 8.0
_TOKEN_IN_TEXT = re.compile(r"([?&]token=)[^&\s\"']+", re.IGNORECASE)


def state_dir() -> Path:
    return get_hermes_home() / "bot-desktop"


def secret_path() -> Path:
    return state_dir() / "voxl.secret"


def endpoint_path() -> Path:
    return state_dir() / "voxl.endpoint"


def pid_path() -> Path:
    return state_dir() / "voxl.pid"


def log_path() -> Path:
    return state_dir() / "voxl.log"


def redact(text: str, *secrets_in: str) -> str:
    """Strip voxl passwords and ``?token=`` values so a log line can never carry them."""
    out = text or ""
    out = _TOKEN_IN_TEXT.sub(r"\1[redacted]", out)
    for secret in secrets_in:
        if secret:
            out = out.replace(secret, "[redacted]")
    return out


def load_password() -> Optional[str]:
    try:
        raw = secret_path().read_text(encoding="ascii").strip()
    except OSError:
        return None
    return raw or None


def _write_secret(password: str) -> None:
    path = secret_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(password, encoding="ascii")
    os.chmod(path, 0o600)


def ensure_password() -> str:
    existing = load_password()
    if existing:
        return existing
    password = secrets.token_urlsafe(24)
    _write_secret(password)
    return password


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((LISTEN_ADDR, 0))
        return int(sock.getsockname()[1])


def _pid_alive(pid: int) -> bool:
    import psutil
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def _launcher_pid() -> Optional[int]:
    raw = ""
    try:
        raw = pid_path().read_text(encoding="utf-8-sig").strip()
    except OSError:
        return None
    pid_s, _, born_s = raw.partition(" ")
    if not pid_s.isdigit() or not born_s:
        return None
    try:
        pid, born = int(pid_s), float(born_s)
    except ValueError:
        return None
    import psutil
    try:
        proc = psutil.Process(pid)
        if abs(proc.create_time() - born) > 2.0:
            return None
        return pid if proc.status() != psutil.STATUS_ZOMBIE else None
    except (psutil.Error, OverflowError, ValueError):
        return None


def endpoint() -> Optional[Tuple[str, int]]:
    """``(addr, port)`` voxl is listening on, or None when down."""
    if _launcher_pid() is None:
        return None
    try:
        raw = endpoint_path().read_text(encoding="ascii").strip()
    except OSError:
        return None
    host, _, port_s = raw.partition(":")
    if not port_s.isdigit():
        return None
    return (host or LISTEN_ADDR, int(port_s))


def is_running() -> bool:
    return endpoint() is not None


def is_available() -> bool:
    return voxl_install.is_available()


def argv_for(
    port: int,
    *,
    audio: bool = False,
    microphone: bool = False,
    resize: bool = True,
) -> list[str]:
    """CLI for voxl. The password is NOT an argument; it rides in VOXL_PASSWORD."""
    binary = voxl_install.resolve_binary()
    if binary is None:
        raise FileNotFoundError("voxl binary not found")
    args = [
        str(binary),
        f"--addr={LISTEN_ADDR}",
        f"--port={port}",
        "--enable-basic-auth=true",
        "--title=Dragon AI Screen",
        "--file-transfers=none",
        "--framerate=60",
        "--enable-clipboard=true",
        f"--enable-resize={'true' if resize else 'false'}",
        f"--audio-enabled={'true' if audio else 'false'}",
        f"--microphone-enabled={'true' if microphone else 'false'}",
        "--allowed-origins=*",
    ]
    return args


def _child_env(password: str, display: Optional[str], xauth: Optional[str]) -> Dict[str, str]:
    from tools.environments.local import served_profile_child_env
    env = served_profile_child_env(inherit_credentials=False)
    env["VOXL_PASSWORD"] = password
    env.pop("SELKIES_BASIC_AUTH_PASSWORD", None)
    if display:
        env["DISPLAY"] = display
    if xauth:
        env["XAUTHORITY"] = xauth
    return env


def _healthz(port: int, timeout: float = HEALTH_TIMEOUT_S) -> bool:
    import urllib.error
    import urllib.request
    url = f"http://{LISTEN_ADDR}:{port}/healthz"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if 200 <= getattr(resp, "status", 200) < 300:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.1)
    return False


def start(
    *,
    display: Optional[str] = None,
    xauth: Optional[str] = None,
    wait_seconds: float = HEALTH_TIMEOUT_S,
) -> Tuple[str, int]:
    """Start voxl for this profile. Returns ``(addr, port)``. Raises on failure.

    Linux: ``display`` is the existing X display (Xvnc or Xvfb). Windows/macOS
    host mode omits it and voxl captures the session desktop.
    """
    if (running := endpoint()) is not None:
        return running
    binary = voxl_install.resolve_binary()
    if binary is None:
        raise RuntimeError("voxl is not installed")
    sd = state_dir()
    sd.mkdir(parents=True, exist_ok=True)
    os.chmod(sd, 0o700)
    password = ensure_password()
    port = _free_port()
    cfg = _backend._bot_desktop_cfg()
    args = argv_for(
        port,
        audio=_backend.audio_enabled(cfg),
        microphone=_backend.microphone_enabled(cfg),
        resize=True,
    )
    if any("password" in a.lower() and "enable-basic-auth" not in a.lower() for a in args):
        raise RuntimeError("voxl argv must not carry a password")
    env = _child_env(password, display, xauth)
    log = open(log_path(), "wb")  # noqa: SIM115 — handed to the child
    kwargs: Dict[str, object] = {
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,  # voxl prints a ?token= URL here
        "stderr": log,
        "close_fds": True,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(args, **kwargs)  # noqa: S603 — args from argv_for
    log.close()
    import psutil
    try:
        born = psutil.Process(proc.pid).create_time()
    except (psutil.Error, OverflowError, ValueError):
        born = time.time()
    pid_path().write_text(f"{proc.pid} {born}", encoding="ascii")
    os.chmod(pid_path(), 0o600)
    if not _healthz(port, timeout=wait_seconds):
        stop()
        tail = ""
        try:
            tail = log_path().read_text(encoding="utf-8", errors="replace")[-1500:]
        except OSError:
            pass
        raise RuntimeError("voxl did not become ready: " + redact(tail, password))
    endpoint_path().write_text(f"{LISTEN_ADDR}:{port}", encoding="ascii")
    os.chmod(endpoint_path(), 0o600)
    logger.info("voxl listening on %s:%s for profile home %s", LISTEN_ADDR, port, get_hermes_home())
    return LISTEN_ADDR, port


def stop() -> bool:
    pid = _launcher_pid()
    stopped = False
    if pid is not None:
        stopped = True
        try:
            if sys.platform == "win32":
                os.kill(pid, signal.SIGTERM)
            else:
                os.killpg(pid, signal.SIGTERM)
        except OSError:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and _pid_alive(pid):
            time.sleep(0.05)
        if _pid_alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    for path in (pid_path(), endpoint_path()):
        try:
            path.unlink()
        except OSError:
            pass
    return stopped


def start_for_desktop() -> Optional[Tuple[str, int]]:
    """Attach voxl to the running Bot Desktop X display, or Windows host desktop.

    Returns the endpoint, or None when voxl cannot start (caller falls back to VNC).
    """
    from tools.bot_desktop import runtime as _runtime
    env = _runtime.published_env()
    display = env.get("DISPLAY")
    xauth = env.get("XAUTHORITY")
    if display is None and sys.platform.startswith("linux"):
        logger.info("voxl: no DISPLAY published; skip")
        return None
    try:
        return start(display=display, xauth=xauth)
    except Exception as exc:
        logger.warning("voxl failed to start: %s", redact(str(exc), load_password() or ""))
        return None
