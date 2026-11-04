"""Which streamer the Bot Screen pane should use: voxl (H.264) or the TigerVNC RFB path.

``bot_desktop.screen_backend`` is ``voxl`` (default) or ``vnc``. voxl is preferred for latency;
when it cannot start, the runtime falls back to VNC on its own and the pane shows a short notice.
A user who pins ``vnc`` never starts voxl. The password for voxl is never part of this choice.
"""

from __future__ import annotations

from typing import Optional, Tuple

VOXL = "voxl"
VNC = "vnc"
_ALLOWED = (VOXL, VNC)

FALLBACK_NOTICE = "Streaming with VNC \u2014 voxl was unavailable."
VOXL_MISSING_NOTICE = "Streaming with VNC \u2014 voxl is not installed on this host."
VOXL_FAILED_NOTICE = "Streaming with VNC \u2014 voxl failed to start."
VNC_UNAVAILABLE_NOTICE = "VNC fallback is not available on this host."


def configured_backend(cfg: Optional[dict] = None) -> str:
    """Return the configured streamer, defaulting to voxl. Unknown values fall through to voxl."""
    if cfg is None:
        cfg = _bot_desktop_cfg()
    raw = str((cfg or {}).get("screen_backend") or VOXL).strip().lower()
    return raw if raw in _ALLOWED else VOXL


def audio_enabled(cfg: Optional[dict] = None) -> bool:
    if cfg is None:
        cfg = _bot_desktop_cfg()
    return bool((cfg or {}).get("audio_enabled"))


def microphone_enabled(cfg: Optional[dict] = None) -> bool:
    if cfg is None:
        cfg = _bot_desktop_cfg()
    return bool((cfg or {}).get("microphone_enabled"))


def select_stream_backend(
    wanted: str,
    *,
    voxl_available: bool,
    voxl_running: bool,
    vnc_available: bool,
    voxl_failed: bool = False,
) -> Tuple[str, Optional[str]]:
    """Pick the live streamer and an optional fallback notice.

    ``wanted`` is the configured choice. voxl is used when it is up (or can be);
    otherwise VNC is used when that path exists. The notice is set only on an
    automatic fallback, never when the user asked for VNC.
    """
    choice = wanted if wanted in _ALLOWED else VOXL
    if choice == VNC:
        if vnc_available:
            return VNC, None
        if voxl_running or voxl_available:
            return VOXL, None
        return VNC, VNC_UNAVAILABLE_NOTICE
    if voxl_running:
        return VOXL, None
    if voxl_available and not voxl_failed:
        return VOXL, None
    if vnc_available:
        return VNC, fallback_notice_for("failed" if voxl_failed else "missing")
    return VOXL, None


def attach_preferred(*, vnc_available: bool, sandbox: bool = False) -> Tuple[str, Optional[str]]:
    """Start voxl when configured, or fall back to VNC. Sandbox placement stays on VNC
    (the guest has no pinned voxl binary); the pane shows the missing-install notice."""
    from tools.bot_desktop import voxl

    wanted = configured_backend()
    if wanted == VNC:
        if voxl.is_running():
            voxl.stop()
        return (VNC, None) if vnc_available else (VNC, VNC_UNAVAILABLE_NOTICE)
    if sandbox:
        if voxl.is_running():
            voxl.stop()
        return (VNC, VOXL_MISSING_NOTICE) if vnc_available else (VOXL, VOXL_MISSING_NOTICE)
    if voxl.is_running():
        return VOXL, None
    if voxl.start_for_desktop() is not None:
        return VOXL, None
    notice = fallback_notice_for("missing" if not voxl.is_available() else "failed")
    if vnc_available:
        return VNC, notice
    return VOXL, notice


def fallback_notice_for(reason: str) -> str:
    if reason == "missing":
        return VOXL_MISSING_NOTICE
    if reason == "failed":
        return VOXL_FAILED_NOTICE
    return FALLBACK_NOTICE


def _bot_desktop_cfg() -> dict:
    try:
        from hermes_cli.config import load_config_readonly
        return load_config_readonly().get("bot_desktop") or {}
    except Exception:
        return {}
