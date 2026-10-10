"""Where this profile's desktop lives: the gateway host or inside the configured terminal backend.

``bot_desktop.placement``:
  ``auto``      (default) follow the terminal backend when it is a sandbox that can host a stream
                (docker / ssh / singularity); the gateway host when ``terminal.backend`` is local AND
                this host can run Xvnc. On a non-Linux gateway with Docker available, ``auto`` +
                ``local`` resolves to a Linux guest (``terminal:docker``) instead of reporting
                "unsupported" — the Computer tab is a per-bot Linux VM, not the host display. A
                sandbox backend that CANNOT host one (modal, daytona, vercel) resolves to ``refused``:
                the user chose a sandbox for the agent's actions, so quietly running the screen, cua-driver
                and the browser on the host beside it would hand the agent a desktop outside that sandbox.
  ``terminal``  always the terminal backend; error when it cannot host one.
  ``gateway``   always the gateway host (the pre-#108914 behaviour for sandboxed users, now an explicit
                opt-in because it is the boundary-crossing shape). Never falls through to a guest.

``resolve()`` is pure config + backend-class + host-capability reasoning: it never starts a sandbox.
``terminal_environment()`` does acquire the environment (creating the container if needed) because a
screen cannot exist before the sandbox does. A Linux-guest fallback uses a dedicated, profile-scoped
task id so it does not replace the profile's local terminal and does not share one container across
bots on a multiplexed (``primary-shared``) backend.
"""
from __future__ import annotations

import hashlib
import logging
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

GATEWAY = "gateway"
TERMINAL = "terminal"
REFUSED = "refused"
_STREAM_BACKENDS = ("docker", "ssh", "singularity")
# Dedicated ``_active_environments`` prefix so a Windows/macOS Computer tab can
# bring up ``dragon-sandbox:desktop`` without flipping the profile's configured
# ``terminal.backend``. The live key MUST include the served profile — a
# multiplexed Desktop backend (``primary-shared``) handles every bot in one
# process, and a single unscoped ``bot-desktop-guest`` slot made Lead Scout
# adopt Researcher's container (and its :20), so ``ensure_sandbox_image`` never ran.
LINUX_GUEST_TASK_ID = "bot-desktop-guest"


def linux_guest_task_id() -> str:
    """``_active_environments`` key for THIS profile's Computer-tab Linux guest."""
    from hermes_cli.profiles import get_active_profile_name
    from hermes_constants import hermes_home_key

    profile = get_active_profile_name() or "default"
    digest = hashlib.sha256(hermes_home_key().encode("utf-8")).hexdigest()[:12]
    return f"{LINUX_GUEST_TASK_ID}:{profile}:{digest}"


def is_linux_guest_task_id(task_id: str) -> bool:
    """True for the unscoped legacy key or any per-profile ``bot-desktop-guest:…`` slot."""
    return task_id == LINUX_GUEST_TASK_ID or task_id.startswith(LINUX_GUEST_TASK_ID + ":")


@dataclass(frozen=True)
class Placement:
    where: str            # GATEWAY | TERMINAL | REFUSED
    backend: str          # terminal.backend as configured
    reason: str = ""      # human sentence when REFUSED (or why TERMINAL was not possible)


def _setting() -> str:
    from hermes_cli.config import load_config_readonly
    cfg = load_config_readonly().get("bot_desktop") or {}
    value = str(cfg.get("placement") or "auto").strip().lower()
    return value if value in ("auto", TERMINAL, GATEWAY) else "auto"


def _terminal_backend() -> str:
    from tools.terminal_tool import _get_env_config
    return str(_get_env_config().get("env_type") or "local")


def _host_can_run_xvnc() -> bool:
    """True when this process can exec Xvnc locally. Tests monkeypatch this; do not fake ``sys.platform``."""
    return sys.platform.startswith("linux")


def _docker_cli() -> Optional[str]:
    from tools.environments.docker import find_docker
    return find_docker()


def _uses_linux_guest(where: Optional[Placement] = None) -> bool:
    """True when resolve() picked a Docker Linux guest while the profile's terminal stays local."""
    chosen = where or resolve()
    return chosen.where == TERMINAL and chosen.backend == "docker" and _terminal_backend() == "local"


def resolve() -> Placement:
    # Backend first (env only): a local terminal IS the gateway host when this host can run Xvnc,
    # and that is the common Linux case — it must not cost a config load (this runs on every
    # browser / cua-driver spawn). On a host that cannot run Xvnc, ``auto`` (not an explicit
    # ``gateway``) falls through to a Docker Linux guest when the CLI is present.
    backend = _terminal_backend()
    if backend == "local":
        if _host_can_run_xvnc():
            return Placement(GATEWAY, backend, "terminal.backend is local, so the terminal IS the gateway host")
        if _setting() != GATEWAY and _docker_cli():
            return Placement(
                TERMINAL, "docker",
                "this host cannot run Xvnc; the screen runs in a Linux guest via Docker",
            )
        return Placement(GATEWAY, backend, "terminal.backend is local, so the terminal IS the gateway host")
    setting = _setting()
    if setting == GATEWAY:
        return Placement(GATEWAY, backend)
    if backend in _STREAM_BACKENDS:
        return Placement(TERMINAL, backend)
    reason = (f"terminal.backend is {backend}, which cannot host a screen yet, and running the desktop on the "
              f"gateway host would put the agent's screen, browser and computer_use outside the sandbox you chose "
              f"for it. Set bot_desktop.placement: gateway to allow that explicitly.")
    return Placement(REFUSED, backend, reason)


def _linux_guest_paths(config: dict) -> tuple[str, Optional[str]]:
    """``(container_cwd, host_cwd)`` for a Docker Linux guest.

    The profile's local terminal cwd is the Windows/macOS host home and must
    never become ``docker run -w``. Guest workdir is ``/root``; ``host_cwd``
    is only whatever the docker config already chose to bind.
    """
    from tools.terminal_tool_config import _is_unusable_container_cwd

    raw = str(config.get("cwd") or "/root")
    host = config.get("host_cwd")
    host_cwd = host.strip() if isinstance(host, str) and host.strip() else None
    if _is_unusable_container_cwd(raw):
        return "/root", host_cwd
    return raw, host_cwd


def _linux_guest_environment(*, create: bool) -> Optional[Any]:
    """A Docker ``dragon-sandbox:desktop`` guest for Computer tab on a non-Linux host.

    Registered under :func:`linux_guest_task_id` so it never replaces the profile's
    local terminal and never shares another bot's guest on a multiplexed host.
    ``create=False`` is a cache/status probe and must not pull or start a container.
    ``create=True`` with no cached guest calls ``_create_configured_env``, which is
    the path that runs ``ensure_sandbox_image`` (inspect → GHCR → upstream + retag).
    """
    from hermes_cli.config_defaults import DEFAULT_SANDBOX_IMAGE
    from tools import terminal_tool as tt
    from tools.terminal_tool_lifecycle import _create_configured_env

    task_id = linux_guest_task_id()
    with tt._env_lock:
        env = tt._active_environments.get(task_id)
    if env is not None or not create:
        return env
    with tt._creation_locks_lock:
        task_lock = tt._creation_locks.setdefault(task_id, threading.Lock())
    with task_lock:
        with tt._env_lock:
            env = tt._active_environments.get(task_id)
        if env is not None:
            return env
        config = dict(tt._get_env_config())
        cwd, host_cwd = _linux_guest_paths(config)
        env = _create_configured_env(
            config, "docker",
            image=DEFAULT_SANDBOX_IMAGE,
            cwd=cwd,
            timeout=int(config.get("timeout") or 180),
            task_id=task_id,
            host_cwd=host_cwd,
        )
        with tt._env_lock:
            tt._active_environments[task_id] = env
            tt._last_activity[task_id] = time.time()
        logger.info("Linux guest environment ready for bot desktop (%s)", task_id)
        return env


def terminal_environment(*, create: bool = True) -> Optional[Any]:
    """This profile's terminal environment object (the one ``terminal`` runs commands in). ``create=False``
    only returns an already-running one. A Linux-guest fallback creates a dedicated Docker
    environment instead of warming the configured local backend."""
    if _uses_linux_guest():
        return _linux_guest_environment(create=create)
    from tools import terminal_tool as tt
    task_id = tt._resolve_container_task_id(None)
    with tt._env_lock:
        env = tt._lookup_active_env(task_id, None)
    if env is not None or not create:
        return env
    # Acquire through the same planner the terminal tool uses so the container carries the same mounts,
    # limits and identity label; a trivial command warms it.
    tt.terminal_tool("true", task_id=None)
    with tt._env_lock:
        return tt._lookup_active_env(task_id, None)
