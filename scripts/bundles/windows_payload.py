"""Windows payload hygiene: MAX_PATH budget, cache stripping, robust deletes.

NSIS upgrades move the previous install into ``%TEMP%\\<nst…>`` and then delete
it. Files under ``resources\\agent-payload`` whose *full* path in that temp
tree exceeds MAX_PATH (~260, and NSIS fails closer to 250) abort the upgrade
with ``Failed to uninstall old application files: 2``.

uv-cache trees and ``__pycache__\\*.pyc`` (especially vendored packages such as
elevenlabs) are the usual offenders. They are build/runtime caches, not the
product: strip them from anything we ship, and refuse a payload that would
still overflow a realistic NSIS temp prefix.
"""
from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

# 20-char username + ~40-char NSIS nst* temp dir, matching the upgrade abort.
NSIS_UPGRADE_PREFIX = (
    "C:\\Users\\"
    + ("U" * 20)
    + "\\AppData\\Local\\Temp\\"
    + ("N" * 40)
    + "\\"
)
# NSIS FileLog fails before the classic 260-char MAX_PATH.
WINDOWS_PACKAGED_PATH_LIMIT = 250
# electron-builder extraResources land here relative to the install root.
PAYLOAD_INSTALL_PREFIX = r"resources\agent-payload"

CACHE_DIR_NAMES = frozenset({"uv-cache", "__pycache__"})
BYTECODE_SUFFIXES = frozenset({".pyc", ".pyo"})


def nsis_upgrade_path(relative: str) -> str:
    """Absolute path NSIS would use while parking an old install in %TEMP%."""
    rel = relative.replace("/", "\\").lstrip("\\")
    return NSIS_UPGRADE_PREFIX + PAYLOAD_INSTALL_PREFIX + "\\" + rel


def iter_overlong_payload_paths(root: Path) -> list[tuple[str, int]]:
    """``(relative_posix, nsis_path_len)`` for every file that would overflow."""
    root = Path(root)
    overlong: list[tuple[str, int]] = []
    if not root.is_dir():
        return overlong
    for path in root.rglob("*"):
        if not path.is_file() and not path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        length = len(nsis_upgrade_path(relative))
        if length > WINDOWS_PACKAGED_PATH_LIMIT:
            overlong.append((relative, length))
    return overlong


def assert_payload_windows_paths(root: Path) -> None:
    """Fail closed if any packaged path would exceed the NSIS upgrade budget."""
    overlong = iter_overlong_payload_paths(root)
    if not overlong:
        return
    sample = ", ".join(f"{rel} ({n})" for rel, n in overlong[:8])
    raise ValueError(
        f"{len(overlong)} packaged path(s) exceed {WINDOWS_PACKAGED_PATH_LIMIT} chars "
        f"under a realistic NSIS upgrade temp root ({sample})"
    )


def strip_payload_caches(root: Path) -> dict[str, int]:
    """Remove uv-cache trees, ``__pycache__`` dirs, and ``*.pyc``/``*.pyo``.

    Returns counts so callers can log what left the payload.
    """
    root = Path(root)
    removed_dirs = 0
    removed_files = 0
    if not root.is_dir():
        return {"dirs": 0, "files": 0}
    # Deepest-first so a cache dir is gone before we try its parent.
    for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        name = path.name
        if path.is_dir() and name in CACHE_DIR_NAMES:
            robust_rmtree(path)
            removed_dirs += 1
        elif path.is_file() and path.suffix in BYTECODE_SUFFIXES:
            _clear_readonly(path)
            path.unlink(missing_ok=True)
            removed_files += 1
    return {"dirs": removed_dirs, "files": removed_files}


def finalize_windows_payload(root: Path) -> dict[str, int]:
    """Strip caches then enforce the NSIS path budget. Call after staging."""
    stripped = strip_payload_caches(root)
    assert_payload_windows_paths(root)
    return stripped


def _win_long(path: Path) -> str:
    """``\\\\?\\`` prefix so Win32 APIs accept paths past MAX_PATH."""
    text = os.fspath(path)
    if os.name == "nt" and not text.startswith("\\\\?\\"):
        text = "\\\\?\\" + os.path.abspath(text)
    return text


def _clear_readonly(path: Path) -> None:
    try:
        os.chmod(path, stat.S_IRWXU)
    except OSError:
        pass
    if os.name == "nt":
        try:
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        except OSError:
            pass


def robust_rmtree(path: Path | str) -> None:
    """``shutil.rmtree`` that clears read-only bits and uses long-path prefixes.

    Payload staging chmod's baked ``.pyc`` files 0444 and uv-cache trees can
    sit past MAX_PATH. A plain rmtree then raises Access Denied on Windows
    mid-rebuild. Walk, unlock, then delete; ``onerror`` retries the same way.
    """
    target = Path(path)
    if not target.exists() and not os.path.lexists(target):
        return

    def _onerror(func, fpath, _exc):
        victim = Path(fpath)
        _clear_readonly(victim)
        if func is os.rmdir or func is os.listdir:
            _clear_readonly(victim.parent)
        retry = _win_long(victim) if os.name == "nt" else fpath
        try:
            func(retry)
        except OSError:
            pass

    for dirpath, dirnames, filenames in os.walk(target, topdown=False):
        current = Path(dirpath)
        _clear_readonly(current)
        for name in filenames + dirnames:
            _clear_readonly(current / name)

    shutil.rmtree(_win_long(target) if os.name == "nt" else target, onerror=_onerror)
