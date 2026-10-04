#!/usr/bin/env python3
"""Cross-compile DragonAIAgent.exe with the current sidebar ICO embedded."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "desktop"
BRAND_ICO = ROOT / "branding" / "dragon-ai-agent-logo.ico"
WINRES_ICO = DESKTOP / "winres" / "icon.ico"
OUT = DESKTOP / "win-unpacked" / "DragonAIAgent.exe"


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd or DESKTOP, env=env, check=True)


def main() -> int:
    if not BRAND_ICO.is_file():
        print("missing branding/dragon-ai-agent-logo.ico", file=sys.stderr)
        return 1
    WINRES_ICO.parent.mkdir(parents=True, exist_ok=True)
    WINRES_ICO.write_bytes(BRAND_ICO.read_bytes())
    brand_dest = DESKTOP / "ui" / "branding"
    brand_dest.mkdir(parents=True, exist_ok=True)
    for src in (
        ROOT / "branding" / "fonts" / "syne" / "first-run-models.js",
        ROOT / "branding" / "fonts" / "syne" / "provider-setup.js",
        ROOT / "branding" / "fonts" / "syne" / "bot-workspace.js",
        ROOT / "branding" / "fonts" / "syne" / "sidebar-header.js",
        ROOT / "branding" / "fonts" / "syne" / "teams-picker.js",
        ROOT / "branding" / "fonts" / "syne" / "dragon-ui.css",
        ROOT / "branding" / "voice" / "dragon-voice-selector.js",
        ROOT / "branding" / "voice" / "dragon-voice-settings.js",
    ):
        if src.is_file():
            (brand_dest / src.name).write_bytes(src.read_bytes())
    go = shutil.which("go")
    if not go:
        print("go is required to rebuild DragonAIAgent.exe", file=sys.stderr)
        return 1
    winres = shutil.which("go-winres")
    if not winres:
        run([go, "install", "github.com/tc-hib/go-winres@v0.3.3"])
        gobin = Path(os.environ.get("GOBIN") or Path(os.environ.get("GOPATH") or (Path.home() / "go")) / "bin")
        winres = str(gobin / "go-winres")
    if not Path(winres).is_file():
        print("go-winres is not on PATH", file=sys.stderr)
        return 1
    # Pillow ICO frames are PNG-in-ICO; go-winres wants a PNG/BMP source.
    png = ROOT / "branding" / "dragon-ai-agent-logo.png"
    run(
        [
            winres,
            "simply",
            "--arch",
            "amd64",
            "--icon",
            str(png),
            "--manifest",
            "gui",
            "--product-name",
            "Dragon AI Agent",
            "--file-description",
            "Dragon AI Agent",
            "--original-filename",
            "DragonAIAgent.exe",
            "--product-version",
            "0.1.0.0",
            "--file-version",
            "0.1.0.0",
        ]
    )
    env = os.environ.copy()
    env["GOOS"] = "windows"
    env["GOARCH"] = "amd64"
    env["CGO_ENABLED"] = "0"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    run(
        [go, "build", "-ldflags=-H windowsgui -s -w", "-o", str(OUT), "."],
        env=env,
    )
    packed = OUT.read_bytes()
    if BRAND_ICO.read_bytes() not in packed and packed.find(b"\x00\x00\x01\x00") < 0:
        print("rebuild did not embed a Windows icon resource", file=sys.stderr)
        return 1
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
