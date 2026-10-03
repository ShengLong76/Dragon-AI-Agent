#!/usr/bin/env python3
"""Private Dragon AI Agent desktop — independent of a Hermes install.

Live contract:

- Dragon launches ``%LOCALAPPDATA%\\DragonAIAgent\\desktop\\win-unpacked\\DragonAIAgent.exe``
- That exe is copied from the Dragon package, never from a Hermes install
- User data stays under ``%LOCALAPPDATA%\\DragonAIAgent``
- Branding / launch refuse any path outside DragonAIAgent
- This installer does not search for, copy, require, or mention a Hermes install
- Standalone Hermes stays a separate product and is not mutated
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

USER_DATA_ENV = "HERMES_DESKTOP_USER_DATA_DIR"
INSTALL_DIR_NAME = "DragonAIAgent"
PRIVATE_EXE_NAME = "DragonAIAgent.exe"
PRIVATE_EXE_REL = Path("desktop") / "win-unpacked" / PRIVATE_EXE_NAME
USER_DATA_REL = Path("electron-userdata")
CONNECTIONS_NAME = "connections.json"
REFUSE_MESSAGE = (
    "Refuse branding outside DragonAIAgent "
    "(standalone Hermes tree is not mutated)"
)
REFUSE_HERMES_SOURCE = "Refuse copying from a Hermes install"


def _norm_parts(path: Path | str) -> tuple[str, ...]:
    return Path(path).expanduser().parts


def is_private_dragon_path(path: Path | str | None) -> bool:
    if not path:
        return False
    return INSTALL_DIR_NAME in _norm_parts(path)


def is_hermes_install_path(path: Path | str | None) -> bool:
    """True for a standalone Hermes tree. DragonAIAgent paths are never this."""
    if not path:
        return False
    if is_private_dragon_path(path):
        return False
    posix = Path(path).as_posix().replace("\\", "/").lower()
    name = Path(path).name.lower()
    if name == "hermes.exe":
        return True
    return "/hermes/" in posix or posix.endswith("/hermes")


def is_standalone_hermes_connections(path: Path | str | None) -> bool:
    if not path:
        return False
    p = Path(path)
    posix = p.as_posix().replace("\\", "/").lower()
    if INSTALL_DIR_NAME in p.parts:
        return False
    return posix.endswith("/hermes/connections.json")


def assert_private_dragon_path(path: Path | str | None, *, role: str = "branding") -> Path:
    if not path or not is_private_dragon_path(path):
        raise ValueError(f"{REFUSE_MESSAGE}: {path}")
    if role and role not in ("branding", "window-title", "launch", "copy-dest"):
        pass
    return Path(path)


def assert_not_hermes_source(path: Path | str | None) -> Path:
    if is_hermes_install_path(path):
        raise ValueError(f"{REFUSE_HERMES_SOURCE}: {path}")
    return Path(path)


def default_install_root() -> Path:
    local = os.environ.get("LOCALAPPDATA") or ""
    if local:
        return Path(local) / INSTALL_DIR_NAME
    return Path.home() / "AppData" / "Local" / INSTALL_DIR_NAME


def private_desktop_exe(install_root: Path | str | None = None) -> Path:
    root = Path(install_root) if install_root else default_install_root()
    return root / PRIVATE_EXE_REL


def electron_userdata_dir(install_root: Path | str | None = None) -> Path:
    env = os.environ.get(USER_DATA_ENV)
    if env:
        return Path(env)
    root = Path(install_root) if install_root else default_install_root()
    return root / USER_DATA_REL


def dragon_connections_path(install_root: Path | str | None = None) -> Path:
    return electron_userdata_dir(install_root) / CONNECTIONS_NAME


def standalone_hermes_connections_path() -> Path:
    appdata = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME")
    if appdata:
        return Path(appdata) / "Hermes" / CONNECTIONS_NAME
    return Path.home() / "AppData" / "Roaming" / "Hermes" / CONNECTIONS_NAME


def should_make_embedded_primary(path: Path | str | None) -> bool:
    """Embedded Linux is primary only for the private Dragon userdata file."""
    if is_standalone_hermes_connections(path):
        return False
    return is_private_dragon_path(path) or bool(os.environ.get(USER_DATA_ENV))


def package_desktop_candidates(payload_root: Path | str | None) -> list[Path]:
    if not payload_root:
        return []
    root = Path(payload_root)
    return [
        root / "desktop" / "win-unpacked" / PRIVATE_EXE_NAME,
        root / "vendor" / "desktop" / "win-unpacked" / PRIVATE_EXE_NAME,
        root / "vendor" / "desktop" / PRIVATE_EXE_NAME,
        root / PRIVATE_EXE_NAME,
    ]


def find_packaged_desktop_exe(payload_root: Path | str | None) -> Path | None:
    for cand in package_desktop_candidates(payload_root):
        if cand.is_file() and not is_hermes_install_path(cand):
            return cand
    return None


def copy_win_unpacked(source_exe: Path | str, dest_root: Path | str) -> Path:
    """Copy a Dragon package desktop tree into DragonAIAgent. Never read a Hermes install."""
    src_exe = assert_not_hermes_source(source_exe)
    dest_root_path = Path(dest_root)
    dest_exe = private_desktop_exe(dest_root_path)
    dest_dir = dest_exe.parent
    assert_private_dragon_path(dest_dir, role="copy-dest")
    if src_exe.name.lower() != PRIVATE_EXE_NAME.lower():
        raise FileNotFoundError(f"package desktop must be {PRIVATE_EXE_NAME}: {src_exe}")
    if not src_exe.is_file():
        raise FileNotFoundError(f"package DragonAIAgent.exe missing: {src_exe}")
    src_dir = src_exe.parent
    if is_private_dragon_path(src_dir) and src_dir.resolve() == dest_dir.resolve():
        return dest_exe
    if dest_exe.is_file():
        return dest_exe
    dest_dir.mkdir(parents=True, exist_ok=True)
    if dest_dir.resolve() == src_dir.resolve():
        return dest_exe
    shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)
    if not dest_exe.is_file():
        # Package may ship only the exe (UI is embedded).
        shutil.copy2(src_exe, dest_exe)
    if not dest_exe.is_file():
        raise FileNotFoundError(f"copy did not produce {dest_exe}")
    return dest_exe


def pointer_payload(exe_path: Path | str) -> dict[str, str]:
    exe = Path(exe_path)
    assert_private_dragon_path(exe, role="launch")
    return {
        "exe": str(exe),
        "workingDirectory": str(exe.parent),
        "notes": (
            "Dragon AI Agent desktop under DragonAIAgent\\desktop\\win-unpacked. "
            "Shipped with the Dragon package. Hermes is a separate product."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    copy_p = sub.add_parser("copy", help="Provision DragonAIAgent\\desktop\\win-unpacked")
    copy_p.add_argument("--source", required=True, help="Source DragonAIAgent.exe (Dragon package)")
    copy_p.add_argument("--dest-root", required=True, help="DragonAIAgent install root")

    refuse_p = sub.add_parser("refuse", help="Exit 2 if path is outside DragonAIAgent")
    refuse_p.add_argument("--path", required=True)

    paths_p = sub.add_parser("paths", help="Print private dest + userdata JSON")
    paths_p.add_argument("--install-root", default="")

    args = parser.parse_args(argv)
    if args.cmd == "copy":
        dest = copy_win_unpacked(args.source, args.dest_root)
        print(json.dumps({"exe": str(dest), USER_DATA_ENV: str(electron_userdata_dir(args.dest_root))}))
        return 0
    if args.cmd == "refuse":
        try:
            assert_private_dragon_path(args.path)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print("OK  private Dragon path")
        return 0
    if args.cmd == "paths":
        root = Path(args.install_root) if args.install_root else default_install_root()
        print(
            json.dumps(
                {
                    "exe": str(private_desktop_exe(root)),
                    "userData": str(electron_userdata_dir(root)),
                    "connections": str(dragon_connections_path(root)),
                    "env": USER_DATA_ENV,
                }
            )
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
