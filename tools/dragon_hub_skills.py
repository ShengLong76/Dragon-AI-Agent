"""Dragon-branded Skills Hub installers for bundled research helpers.

YouTube, RSS, and Web Reader ship in ``optional-skills/research/``. One-click
hub add copies the local folder into the active profile and installs pinned
helper dependencies. Inspired by Agent-Reach (MIT) — we wrote our own helpers
and do not bundle that project.

Never fetches install steps from a live URL. Never reads cookies or browser
profiles. Not a model tool. Called from ``hermes_cli.skills_hub.do_install``.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

AGENT_REACH_CREDIT = (
    "Inspired by Agent-Reach (MIT) — https://github.com/Panniantong/Agent-Reach. "
    "Dragon wrote these helpers; Agent-Reach is not bundled."
)

YOUTUBE_IDENTIFIER = "dragon/youtube"
RSS_IDENTIFIER = "dragon/rss"
WEB_READER_IDENTIFIER = "dragon/web-reader"

YOUTUBE_REQUIREMENT = "yt-dlp>=2025.1.26,<2027"
RSS_REQUIREMENT = "feedparser>=6.0.11,<7"

HELPER_PYTHON_NAME = ".helper-python"


@dataclass(frozen=True)
class DragonHubSkill:
    identifier: str
    name: str
    display_name: str
    bundled_rel: str
    aliases: tuple[str, ...]
    requirements: tuple[str, ...]
    summary: str


DRAGON_HUB_SKILLS: tuple[DragonHubSkill, ...] = (
    DragonHubSkill(
        identifier=YOUTUBE_IDENTIFIER,
        name="dragon-youtube",
        display_name="YouTube — transcripts and search",
        bundled_rel="research/dragon-youtube",
        aliases=("dragon-youtube", "official/research/dragon-youtube"),
        requirements=(YOUTUBE_REQUIREMENT,),
        summary="Public YouTube search and captions via pinned yt-dlp. No login.",
    ),
    DragonHubSkill(
        identifier=RSS_IDENTIFIER,
        name="dragon-rss",
        display_name="RSS — read and summarize feeds",
        bundled_rel="research/dragon-rss",
        aliases=("dragon-rss", "official/research/dragon-rss"),
        requirements=(RSS_REQUIREMENT,),
        summary="Public RSS/Atom via pinned feedparser. No login.",
    ),
    DragonHubSkill(
        identifier=WEB_READER_IDENTIFIER,
        name="dragon-web-reader",
        display_name="Web Reader — clean page text",
        bundled_rel="research/dragon-web-reader",
        aliases=("dragon-web-reader", "official/research/dragon-web-reader"),
        requirements=(),
        summary="Jina Reader (r.jina.ai) with a plain-fetch fallback. No login.",
    ),
)

_BY_KEY: dict[str, DragonHubSkill] = {}
for _skill in DRAGON_HUB_SKILLS:
    _BY_KEY[_skill.identifier] = _skill
    _BY_KEY[_skill.name] = _skill
    for _alias in _skill.aliases:
        _BY_KEY[_alias] = _skill


def _norm_identifier(identifier: str) -> str:
    return (identifier or "").strip().rstrip("/").lower()


def is_dragon_hub_identifier(identifier: str) -> bool:
    """True for a bundled Dragon hub skill id or alias."""
    return _norm_identifier(identifier) in _BY_KEY


def resolve_dragon_hub_skill(identifier: str) -> Optional[DragonHubSkill]:
    return _BY_KEY.get(_norm_identifier(identifier))


def bundled_skill_dir(skill: DragonHubSkill, *, optional_root: Optional[Path] = None) -> Path:
    """Local optional-skills folder. Never a remote URL."""
    if optional_root is None:
        from hermes_constants import get_optional_skills_dir

        optional_root = get_optional_skills_dir(Path(__file__).resolve().parent.parent / "optional-skills")
    path = (optional_root / skill.bundled_rel).resolve()
    root = optional_root.resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Unsafe bundled skill path: {skill.bundled_rel}")
    return path


def read_pinned_requirements(skill_dir: Path) -> list[str]:
    """Pinned specs from the skill's requirements.txt (comments ignored)."""
    req = skill_dir / "requirements.txt"
    if not req.is_file():
        return []
    pins: list[str] = []
    for raw in req.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            pins.append(line)
    return pins


def setup_steps(skill: DragonHubSkill) -> str:
    """Local setup copy. No live URL to fetch install instructions."""
    reqs = ", ".join(skill.requirements) if skill.requirements else "none (stdlib)"
    return "\n".join(
        [
            skill.display_name,
            skill.summary,
            AGENT_REACH_CREDIT,
            "",
            f"Pinned helper packages: {reqs}",
            "Install copies the bundled skill into this bot's skills folder and",
            "creates an isolated helper interpreter. No cookies, no browser profile,",
            "no remote install script.",
            "",
            "Windows and POSIX use the same Python helpers (not bash).",
            "After install, run the interpreter path written to .helper-python.",
        ]
    )


def _iter_skill_files(src: Path) -> Iterable[Path]:
    from tools.skills_hub_github import _skip_bundle_file

    for path in src.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(src).as_posix()
        if _skip_bundle_file(rel) or path.name == HELPER_PYTHON_NAME:
            continue
        yield path


def copy_bundled_skill(src: Path, dest: Path) -> list[str]:
    """Copy helper files into the profile skills dir. Overwrites dest."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    for path in _iter_skill_files(src):
        rel = path.relative_to(src).as_posix()
        target = dest.joinpath(*rel.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        files.append(rel)
    if not (dest / "SKILL.md").is_file():
        raise FileNotFoundError(f"Bundled skill is missing SKILL.md: {src}")
    return files


def _content_hash(dest: Path, files: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for rel in sorted(files):
        digest.update(rel.encode("utf-8"))
        digest.update((dest / rel).read_bytes())
    return digest.hexdigest()


def _write_helper_python(dest: Path, python: Path) -> None:
    (dest / HELPER_PYTHON_NAME).write_text(str(python), encoding="utf-8", newline="\n")


def _default_install_deps(name: str, requirements: Sequence[str], root: Path) -> Path:
    """Isolated helper env. Prefer PM; fall back to stdlib venv + pip."""
    if not requirements:
        return Path(sys.executable)
    try:
        from pm import ensure_environment

        return Path(ensure_environment(name, list(requirements), root=root, explicit=True))
    except Exception:
        return _venv_pip_install(name, requirements, root)


def _venv_pip_install(name: str, requirements: Sequence[str], root: Path) -> Path:
    import subprocess
    import venv

    dest = root / name
    dest.mkdir(parents=True, exist_ok=True)
    venv.create(dest, with_pip=True)
    python = dest / "Scripts" / "python.exe" if sys.platform == "win32" else dest / "bin" / "python"
    cmd = [str(python), "-m", "pip", "install", "--disable-pip-version-check", *requirements]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "pip install failed").strip())
    return python


InstallDeps = Callable[[str, Sequence[str], Path], Path]
CopySkill = Callable[[Path, Path], list[str]]


def install_dragon_hub_skill(
    identifier: str,
    *,
    console,
    force: bool = False,
    optional_root: Optional[Path] = None,
    dest_root: Optional[Path] = None,
    helper_root: Optional[Path] = None,
    copy_skill: Optional[CopySkill] = None,
    install_deps: Optional[InstallDeps] = None,
    record_lock: bool = True,
) -> bool:
    """Copy one bundled Dragon hub skill into the active profile and pin deps.

    Returns True when SKILL.md landed. Missing renderer deps still copy the
    skill text; a failed copy returns False.
    """
    skill = resolve_dragon_hub_skill(identifier)
    if skill is None:
        console.print(f"[bold red]Unknown Dragon hub skill:[/] {identifier}")
        return False

    console.print(setup_steps(skill))
    src = bundled_skill_dir(skill, optional_root=optional_root)
    if not src.is_dir():
        console.print(f"[bold red]Bundled skill folder missing:[/] {src}")
        return False

    if dest_root is None:
        from tools.skills_hub import _skills_dir

        dest_root = _skills_dir()
    dest = dest_root / skill.name
    if dest.exists() and not force:
        existing = dest / "SKILL.md"
        if existing.is_file():
            console.print(f"[yellow]Already installed:[/] {skill.name} at {dest}")
            _ensure_helper(skill, src, dest, helper_root, install_deps, console)
            return True

    copier = copy_skill or copy_bundled_skill
    try:
        files = copier(src, dest)
    except Exception as exc:
        console.print(f"[bold red]Could not copy {skill.name}:[/] {exc}")
        return False

    _ensure_helper(skill, src, dest, helper_root, install_deps, console)

    if record_lock:
        try:
            from tools.skills_hub import HubLockFile

            HubLockFile().record_install(
                name=skill.name,
                source="official",
                identifier=skill.identifier,
                trust_level="builtin",
                scan_verdict="safe",
                skill_hash=_content_hash(dest, files),
                install_path=skill.name,
                files=list(files),
                metadata={"dragon_hub": True, "pinned_requirements": list(skill.requirements)},
            )
        except Exception as exc:
            console.print(f"[yellow]Lock file not updated:[/] {exc}")

    console.print(f"[bold green]Installed:[/] {skill.display_name}")
    return True


def _ensure_helper(
    skill: DragonHubSkill,
    src: Path,
    dest: Path,
    helper_root: Optional[Path],
    install_deps: Optional[InstallDeps],
    console,
) -> None:
    pins = list(skill.requirements) or read_pinned_requirements(src)
    if helper_root is None:
        from hermes_constants import get_hermes_home

        helper_root = get_hermes_home() / "skill-helpers"
    installer = install_deps or _default_install_deps
    try:
        python = installer(skill.name, pins, helper_root)
        _write_helper_python(dest, Path(python))
        console.print(f"[dim]Helper interpreter:[/] {python}")
        if pins:
            console.print(f"[dim]Pinned:[/] {', '.join(pins)}")
    except Exception as exc:
        console.print(f"[yellow]Helper packages not installed:[/] {exc}")
        console.print(f"[yellow]Install locally:[/] python -m pip install {' '.join(pins)}")
