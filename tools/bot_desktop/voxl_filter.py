"""Lease-gated filter for voxl's client\to server WebSocket.

voxl's ``--read-only`` is process-wide, so the gateway applies the Bot Desktop lease per
viewer the same way :mod:`tools.bot_desktop.rfb_filter` does for RFB. Watch-only commands
(acks, video/audio on/off, keyframe, ping reply) always pass; input, clipboard, microphone
and resize are dropped unless this viewer currently holds the lease.

Text commands are ``cmd`` or ``cmd,args`` (see voxl ``src/server.rs``). Every binary frame
from a viewer acts on the desktop (clipboard image, microphone) and is dropped for watchers.
"""

from __future__ import annotations

from typing import Callable, Optional

# Commands a watcher may send. Matches voxl's READ_ONLY_COMMANDS.
WATCH_ONLY_COMMANDS = frozenset({"a", "v", "au", "kf", "po"})


def text_command(message: str) -> str:
    return message.split(",", 1)[0].strip()


def allow_client_text(message: str, may_send_input: bool) -> bool:
    if may_send_input:
        return True
    return text_command(message) in WATCH_ONLY_COMMANDS


def allow_client_binary(data: bytes, may_send_input: bool) -> bool:
    if not data:
        return False
    return bool(may_send_input)


class VoxlClientFilter:
    """Stateful only in that it re-reads the lease through ``may_send_input``."""

    def __init__(self, may_send_input: Callable[[], bool]):
        self._may_send_input = may_send_input

    def text(self, message: str) -> Optional[str]:
        if allow_client_text(message, self._may_send_input()):
            return message
        return None

    def binary(self, data: bytes) -> Optional[bytes]:
        if allow_client_binary(data, self._may_send_input()):
            return data
        return None
