"""ECC workflow-pack installer for the active Dragon data folder.

Wraps the official ``ecc-universal`` Hermes-target installer so it writes into
the process's ``HERMES_HOME`` (the active profile / Dragon data folder), never a
hardcoded ``~/.hermes``. Memory Vault and Cursor hooks stay off.

User-facing copy says "Dragon data folder" — the framework name is never shown.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from hermes_constants import display_hermes_home, get_hermes_home

ECC_PACK_ID = "ecc-workflows"
ECC_PACK_TITLE = "ECC Workflows"
ECC_INSTALL_STATE_NAME = "ecc-install-state.json"
ECC_TARGET = "hermes"
ECC_PROFILE = "minimal"
ECC_PACKAGE = "ecc-universal"
DATA_FOLDER_LABEL = "Dragon data folder"

# Official installer always lands in <HOME>/.hermes. We point that path at the
# active Dragon data folder via a throwaway HOME so profile / suffix homes work.
_ECC_ADAPTER_HOME_SEGMENT = ".hermes"

_USER_VISIBLE_FORBIDDEN = ("hermes",)


class EccWorkflowError(RuntimeError):
    """Failed to install, update, or remove the ECC workflow pack."""


@dataclass(frozen=True)
class EccWorkflowStatus:
    installed: bool
    pack_id: str = ECC_PACK_ID
    title: str = ECC_PACK_TITLE
    profile: str = ECC_PROFILE
    target: str = ECC_TARGET
    version: str | None = None
    skill_count: int = 0
    home: str = ""
    home_display: str = ""
    install_state_path: str = ""
    memory_vault: bool = False
    cursor_hooks: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "installed": self.installed,
            "pack_id": self.pack_id,
            "title": self.title,
            "profile": self.profile,
            "target": self.target,
            "version": self.version,
            "skill_count": self.skill_count,
            "home": self.home,
            "home_display": self.home_display,
            "install_state_path": self.install_state_path,
            "memory_vault": self.memory_vault,
            "cursor_hooks": self.cursor_hooks,
        }


EccRunner = Callable[[list[str], Mapping[str, str]], subprocess.CompletedProcess[str]]

_ACTION_ALIASES = {
    "upgrade": "update",
    "uninstall": "remove",
}


def normalize_ecc_action(action: str | None) -> str:
    """Argparse alias dest is the literal typed (``uninstall``, ``upgrade``)."""
    raw = (action or "status").strip().lower()
    return _ACTION_ALIASES.get(raw, raw)


def install_state_path(home: Path | None = None) -> Path:
    return (home or get_hermes_home()) / ECC_INSTALL_STATE_NAME


def count_skill_files(home: Path | None = None) -> int:
    """Count ``SKILL.md`` trees under the data folder's ``skills/`` (not archives)."""
    skills_root = (home or get_hermes_home()) / "skills"
    if not skills_root.is_dir():
        return 0
    total = 0
    for path in skills_root.rglob("SKILL.md"):
        if not path.is_file():
            continue
        parts = {part.lower() for part in path.parts}
        if ".archive" in parts:
            continue
        total += 1
    return total


def read_install_state(home: Path | None = None) -> dict[str, Any] | None:
    path = install_state_path(home)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def read_status(home: Path | None = None) -> EccWorkflowStatus:
    resolved = Path(home) if home is not None else get_hermes_home()
    state = read_install_state(resolved)
    version = _state_version(state)
    return EccWorkflowStatus(
        installed=state is not None,
        version=version,
        skill_count=count_skill_files(resolved),
        home=str(resolved),
        home_display=display_hermes_home(resolved),
        install_state_path=str(install_state_path(resolved)),
    )


def npx_executable() -> str:
    return "npx.cmd" if os.name == "nt" else "npx"


def install_argv() -> list[str]:
    """Official ECC Hermes-target install: minimal profile, no hook runtime."""
    return [
        npx_executable(),
        "--yes",
        "--package",
        ECC_PACKAGE,
        "ecc",
        "install",
        "--target",
        ECC_TARGET,
        "--profile",
        ECC_PROFILE,
        "--no-hooks",
        "--json",
    ]


def uninstall_argv() -> list[str]:
    return [
        npx_executable(),
        "--yes",
        "--package",
        ECC_PACKAGE,
        "ecc",
        "uninstall",
        "--target",
        ECC_TARGET,
        "--json",
    ]


def bind_ecc_hermes_home(hermes_home: Path, staging_home: Path) -> Path:
    """Make ECC's ``<HOME>/.hermes`` resolve to ``hermes_home``.

    The official adapter ignores ``HERMES_HOME`` and always uses ``HOME/.hermes``.
    A directory link lets named profiles and ``HERMES_DATA_DIR_SUFFIX`` homes
    receive the pack without writing the platform default.
    """
    staging_home.mkdir(parents=True, exist_ok=True)
    hermes_home.mkdir(parents=True, exist_ok=True)
    link = staging_home / _ECC_ADAPTER_HOME_SEGMENT
    if link.exists() or link.is_symlink():
        if link.is_dir() and not link.is_symlink():
            raise EccWorkflowError(f"Refusing to replace staging directory {link}")
        link.unlink()
    _link_directory(hermes_home.resolve(), link)
    return staging_home


def ecc_child_env(staging_home: Path, hermes_home: Path) -> dict[str, str]:
    """Env for ``npx ecc-universal``: HOME is the staging dir, data home is real."""
    env = dict(os.environ)
    env["HOME"] = str(staging_home)
    env["HERMES_HOME"] = str(hermes_home)
    return env


def run_ecc_subprocess(argv: list[str], env: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            argv,
            env=dict(env),
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise EccWorkflowError(
            "Node.js (npx) is required to install ECC Workflows. Install Node.js and try again."
        ) from exc


def invalidate_skill_caches() -> None:
    """Best-effort: pick up new SKILL.md trees on the next session / skills list."""
    try:
        from agent.prompt_builder import clear_skills_system_prompt_cache

        clear_skills_system_prompt_cache(clear_snapshot=True)
    except Exception:
        pass
    try:
        from agent.skill_commands import reload_skills

        reload_skills()
    except Exception:
        pass


def apply_ecc_action(
    action: str,
    *,
    home: Path | None = None,
    runner: EccRunner | None = None,
) -> EccWorkflowStatus:
    """install / update / remove / status against the active Dragon data folder."""
    resolved = Path(home) if home is not None else get_hermes_home()
    action = normalize_ecc_action(action)
    if action == "status":
        return read_status(resolved)
    if action not in {"install", "update", "remove"}:
        raise EccWorkflowError(f"Unknown ECC workflow action: {action}")

    argv = uninstall_argv() if action == "remove" else install_argv()
    with tempfile.TemporaryDirectory(prefix="dragon-ecc-") as tmp:
        staging = bind_ecc_hermes_home(resolved, Path(tmp))
        result = (runner or run_ecc_subprocess)(argv, ecc_child_env(staging, resolved))
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() or f"exit {result.returncode}"
        raise EccWorkflowError(_friendly_failure(action, detail))
    invalidate_skill_caches()
    return read_status(resolved)


def format_human_status(status: EccWorkflowStatus, action: str = "status") -> str:
    folder = DATA_FOLDER_LABEL
    if action == "remove" and not status.installed:
        return f"{ECC_PACK_TITLE} removed from the {folder}."
    if action in {"install", "update"} and status.installed:
        verb = "updated" if action == "update" else "installed"
        return (
            f"{ECC_PACK_TITLE} {verb} into the {folder}. "
            f"{status.skill_count} skill(s) available under Capabilities → Skills."
        )
    if status.installed:
        version = f" version {status.version}" if status.version else ""
        return (
            f"{ECC_PACK_TITLE}{version} is installed in the {folder} "
            f"({status.skill_count} skill(s))."
        )
    return f"{ECC_PACK_TITLE} is not installed in the {folder}."


def cmd_ecc(args: Any) -> None:
    action = normalize_ecc_action(getattr(args, "ecc_action", None))
    try:
        status = apply_ecc_action(action)
    except EccWorkflowError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    if getattr(args, "json", False):
        print(json.dumps(status.to_dict(), indent=2))
        return
    print(format_human_status(status, action))


def assert_no_framework_branding(text: str) -> None:
    """Test helper: user-visible copy must not name the underlying framework."""
    import re

    for word in _USER_VISIBLE_FORBIDDEN:
        if re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9-])", text, re.IGNORECASE):
            raise AssertionError(f"User-visible copy names the framework: {text!r}")


def _link_directory(target: Path, link: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except OSError:
        if os.name != "nt":
            raise
    _win_junction(target, link)


def _win_junction(target: Path, link: Path) -> None:
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise EccWorkflowError(f"Could not link the Dragon data folder for ECC: {detail}")


def _state_version(state: dict[str, Any] | None) -> str | None:
    if not state:
        return None
    package = state.get("package")
    candidates = [
        state.get("version"),
        state.get("eccVersion"),
        package.get("version") if isinstance(package, dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, dict):
            candidate = candidate.get("version")
        if candidate:
            return str(candidate)
    return None


def _friendly_failure(action: str, detail: str) -> str:
    verbs = {"install": "install", "update": "update", "remove": "remove"}
    verb = verbs.get(action, action)
    return f"Couldn't {verb} {ECC_PACK_TITLE}. {detail}"
