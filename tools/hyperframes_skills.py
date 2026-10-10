"""HyperFrames core-skill install for Dragon bot profiles.

HyperFrames (https://github.com/heygen-com/hyperframes, Apache-2.0) turns HTML
into deterministic MP4. Agents use ``npx hyperframes skills update`` for the
core set (router ``/hyperframes`` plus domain skills). This module:

- recognizes the Skills Hub umbrella identifier
- probes Node >= 22, the ``hyperframes`` CLI, ffmpeg, and a Chrome/Chromium binary
- installs the core skill folders into the active profile's ``skills/`` directory
- prints a setup recipe when the renderer toolchain is missing (prefer the bot's
  Linux sandbox, which already ships Node + Chromium)

Not a model tool. Called from ``hermes_cli.skills_hub.do_install``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Sequence

HYPERFRAMES_REPO = "heygen-com/hyperframes"
HYPERFRAMES_REPO_URL = f"https://github.com/{HYPERFRAMES_REPO}"
HYPERFRAMES_LICENSE = "Apache-2.0"
HYPERFRAMES_IDENTIFIER = HYPERFRAMES_REPO
HYPERFRAMES_DISPLAY_NAME = "HyperFrames — make videos from HTML"
MIN_NODE_MAJOR = 22

# Umbrella ids the Skills Hub / team packs send. Per-skill GitHub paths are
# ``heygen-com/hyperframes/skills/<slug>`` and must NOT match this set.
HYPERFRAMES_IDENTIFIERS = frozenset({
    HYPERFRAMES_IDENTIFIER,
    "hyperframes",
    "hyperframes/hyperframes",
})

# Core set from HyperFrames docs: router + domain skills. Workflows install on demand.
HYPERFRAMES_CORE_SLUGS: tuple[str, ...] = (
    "hyperframes",
    "hyperframes-core",
    "hyperframes-animation",
    "hyperframes-keyframes",
    "hyperframes-creative",
    "hyperframes-cli",
    "hyperframes-audio",
    "hyperframes-registry",
    "media-use",
)

_NODE_MAJOR_RE = re.compile(r"v?(\d+)\.")


def is_hyperframes_identifier(identifier: str) -> bool:
    """True for the umbrella catalog id, not a single ``skills/<slug>`` path."""
    key = (identifier or "").strip().rstrip("/").lower()
    return key in HYPERFRAMES_IDENTIFIERS


def core_skill_identifiers() -> list[str]:
    """GitHub hub identifiers for each published core skill folder."""
    return [f"{HYPERFRAMES_REPO}/skills/{slug}" for slug in HYPERFRAMES_CORE_SLUGS]


def parse_node_major(version_text: str) -> Optional[int]:
    """``v22.14.0`` / ``22.14.0`` → 22; None when the string is not a version."""
    match = _NODE_MAJOR_RE.search(version_text or "")
    return int(match.group(1)) if match else None


@dataclass(frozen=True)
class HyperFramesProbe:
    node_major: Optional[int]
    node_ok: bool
    cli_ok: bool
    ffmpeg_ok: bool
    chrome_ok: bool

    @property
    def can_run_cli(self) -> bool:
        return self.node_ok

    @property
    def renderer_ready(self) -> bool:
        return self.node_ok and self.ffmpeg_ok and self.chrome_ok


def _run_text(argv: Sequence[str], timeout: float = 8) -> str:
    try:
        completed = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return ((completed.stdout or "") + (completed.stderr or "")).strip()


def probe_hyperframes(run: Callable[[Sequence[str], float], str] = _run_text) -> HyperFramesProbe:
    """Look at the current machine (or the sandbox PATH) for renderer prerequisites."""
    node_major = parse_node_major(run(("node", "-v"), 5))
    cli_text = run(("hyperframes", "--version"), 8)
    if not cli_text:
        # npx downloads on first use; a missing global binary is not a hard miss
        # when Node can run ``npx --yes hyperframes``.
        cli_text = run(("npx", "--yes", "hyperframes", "--version"), 20)
    ffmpeg_ok = bool(shutil.which("ffmpeg") or run(("ffmpeg", "-version"), 5))
    chrome_ok = any(
        shutil.which(name)
        for name in ("google-chrome", "chromium", "chromium-browser", "google-chrome-stable")
    )
    if not chrome_ok:
        chrome_ok = "chrome" in run(("agent-browser", "--version"), 5).lower()
    return HyperFramesProbe(
        node_major=node_major,
        node_ok=node_major is not None and node_major >= MIN_NODE_MAJOR,
        cli_ok=bool(cli_text) and "not found" not in cli_text.lower(),
        ffmpeg_ok=bool(ffmpeg_ok),
        chrome_ok=chrome_ok,
    )


def setup_steps(probe: Optional[HyperFramesProbe] = None) -> str:
    """User-facing setup copy. Dragon chrome only — no upstream product name."""
    probe = probe or HyperFramesProbe(
        node_major=None, node_ok=False, cli_ok=False, ffmpeg_ok=False, chrome_ok=False,
    )
    missing: list[str] = []
    if not probe.node_ok:
        found = f"found {probe.node_major}" if probe.node_major is not None else "not found"
        missing.append(f"Node.js >= {MIN_NODE_MAJOR} ({found})")
    if not probe.cli_ok:
        missing.append("hyperframes CLI (`npx hyperframes`)")
    if not probe.ffmpeg_ok:
        missing.append("ffmpeg")
    if not probe.chrome_ok:
        missing.append("headless Chrome/Chromium")

    lines = [
        f"{HYPERFRAMES_DISPLAY_NAME}",
        f"License: {HYPERFRAMES_LICENSE} — {HYPERFRAMES_REPO_URL}",
        "",
        "Prefer the bot's Linux sandbox (Computer). That image already has Node 22+",
        "and Chromium; ffmpeg is installed there for HyperFrames renders.",
        "",
    ]
    if missing:
        lines.append("Still needed on this machine:")
        lines.extend(f"  - {item}" for item in missing)
        lines.append("")
    lines.extend([
        "Sandbox / Computer (recommended):",
        "  1. Open this bot's Computer pane so the Linux desktop is running.",
        "  2. In that desktop, Node and Chromium are already present.",
        "  3. Click Add again — Dragon installs the core skill set into this bot.",
        "  4. Render with: npx hyperframes skills update && npx hyperframes render",
        "",
        "Windows host (only if you must render outside the sandbox):",
        f"  1. Install Node.js {MIN_NODE_MAJOR}+ from https://nodejs.org and reopen Dragon.",
        "  2. Install ffmpeg (https://ffmpeg.org) and add it to PATH.",
        "  3. Install Chrome or Edge. Then click Add again.",
        "",
        "Skills land in this bot's skills folder for the chosen profile.",
    ])
    return "\n".join(lines)


InstallOne = Callable[[str], bool]


def _default_install_one(identifier: str, *, force: bool, console) -> bool:
    """Install one GitHub skill folder through the hub quarantine/scan path."""
    from hermes_cli.skills_hub import _install_skill

    bundle, outcome = _install_skill(
        identifier, "", force, console, True, True, "", None,
    )
    # Already installed → (bundle, None). Fresh success → (bundle, "success").
    return bundle is not None and outcome in ("success", None)


def _run_skills_update(run: Callable[[Sequence[str], float], str] = _run_text) -> str:
    return run(("npx", "--yes", "hyperframes", "skills", "update"), 180)


def install_hyperframes_core(
    *,
    console,
    force: bool = False,
    probe: Optional[HyperFramesProbe] = None,
    install_one: Optional[InstallOne] = None,
    run_cli_update: Optional[Callable[[], str]] = None,
    slugs: Optional[Iterable[str]] = None,
) -> bool:
    """Install the core HyperFrames skill set into the active profile.

    Returns True when at least one core skill landed (or was already present).
    Prints setup steps when Node/CLI/ffmpeg/Chrome are missing. Does not raise
    for a missing renderer — skill text is still useful — but returns False when
    no skill could be installed.
    """
    probe = probe if probe is not None else probe_hyperframes()
    console.print(setup_steps(probe))

    installed: list[str] = []
    failed: list[str] = []
    installer = install_one or (lambda ident: _default_install_one(ident, force=force, console=console))

    for slug, identifier in zip(
        slugs or HYPERFRAMES_CORE_SLUGS,
        core_skill_identifiers() if slugs is None else [f"{HYPERFRAMES_REPO}/skills/{s}" for s in slugs],
    ):
        try:
            ok = installer(identifier)
        except Exception as exc:
            console.print(f"[yellow]HyperFrames skill '{slug}' failed:[/] {exc}")
            failed.append(slug)
            continue
        if ok:
            installed.append(slug)
            console.print(f"[green]Installed core skill:[/] {slug}")
        else:
            failed.append(slug)
            console.print(f"[yellow]Could not fetch[/] {identifier}")

    if probe.can_run_cli:
        updater = run_cli_update or (lambda: _run_skills_update())
        try:
            output = updater()
            if output:
                console.print(output)
            console.print("[dim]Ran `npx hyperframes skills update` (core set).[/]")
        except Exception as exc:
            console.print(f"[yellow]hyperframes CLI update skipped:[/] {exc}")
    else:
        console.print(
            "[yellow]Skipped `npx hyperframes skills update` — install Node.js "
            f"{MIN_NODE_MAJOR}+ in the sandbox, then click Add again.[/]"
        )

    if installed:
        console.print(
            f"[bold green]HyperFrames core skills ready:[/] {', '.join(installed)}"
        )
        return True

    console.print("[bold red]HyperFrames core skills were not installed.[/]")
    return False
