#!/usr/bin/env python3
"""Dragon AI Agent ships its own Windows desktop.

James: Setup on a clean PC must not look for Hermes.exe or tell the user
to install standalone Hermes. The window that opens is Dragon AI Agent,
copied from the Dragon package into %LOCALAPPDATA%\\DragonAIAgent.

No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
PRIVATE = SCRIPTS / "private_desktop.py"
FINDER = SCRIPTS / "Find-HermesDesktop.ps1"
LAUNCHER = SCRIPTS / "start-embedded.ps1"
VBS = SCRIPTS / "Start-DragonAI.vbs"
INSTALLERS = (
    SCRIPTS / "install.ps1",
    ROOT / "installer" / "DragonAIAgentSetup.ps1",
)
DOCS = (
    ROOT / "docs" / "airmaze" / "PRIVATE_DESKTOP.md",
    ROOT / "PACKAGING.md",
    ROOT / "README.md",
)
DESKTOP_README = ROOT / "desktop" / "README.md"
VENDOR_README = ROOT / "vendor" / "desktop" / "README.md"

FORBIDDEN_USER = (
    "Install standalone Hermes",
    "install standalone Hermes",
    "win-unpacked Hermes.exe",
    "private win-unpacked Hermes.exe",
    "Find-HermesDesktopSourceExe",
    "Get-HermesDesktopExactCandidates",
    "Get-HermesDesktopSearchRoots",
)

REQUIRED_FINDER = (
    "DragonAIAgent.exe",
    "desktop\\win-unpacked",
    "Install-DragonAIPrivateDesktop",
    "Find-DragonDesktopExe",
    "Find-DragonAIPackagedDesktopExe",
    "Refuse copying from a Hermes install",
    "Test-DragonAIHermesInstallPath",
    "Start-DragonAIDesktopClient",
    "electron-userdata",
    "Refuse branding outside DragonAIAgent",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def test_package_has_desktop_source() -> None:
    if not (ROOT / "desktop" / "main.go").is_file():
        fail("desktop/main.go missing (Dragon AI Agent Windows host)")
    if not (ROOT / "desktop" / "ui" / "index.html").is_file():
        fail("desktop/ui/index.html missing")
    ui = read(ROOT / "desktop" / "ui" / "index.html")
    js = read(ROOT / "desktop" / "ui" / "app.js")
    if "<title>Dragon AI Agent</title>" not in ui:
        fail("desktop UI title must be Dragon AI Agent")
    if "Gateway ready" in ui or "Gateway ready" in js or "Starting gateway" in ui:
        fail("installed UI must not show the leftover Gateway ready status")
    if "Opening the desktop chat screen" not in ui:
        fail("desktop host loader must wait for the real desktop web UI")
    if 'id="screen-providers"' not in ui:
        fail("desktop UI must start with the expanded provider screen")
    if "xAI Grok" not in ui or "RECOMMENDED" not in ui:
        fail("desktop UI must recommend xAI Grok")
    if "grok-4.7" not in ui:
        fail("desktop UI default model must be grok-4.7")
    if 'id="vm-pane"' not in ui or 'data-rail="bots"' not in ui:
        fail("desktop home must include Bots + VM")
    if "Hermes" in ui:
        fail("desktop UI must not contain Hermes wording")
    go = read(ROOT / "desktop" / "main.go")
    if "DragonAIAgent.exe" not in go and "Dragon AI Agent" not in go:
        fail("desktop host must be Dragon AI Agent")
    if "isHeadlessPage" not in go or "web UI disabled" not in go:
        fail("desktop host must refuse the headless hermes serve page")
    if "first-run-models" not in go:
        fail("desktop host must inject the Air Maze first-run Models step")
    if "provider-setup" not in go:
        fail("desktop host must inject provider-setup on the live window")
    if "bot-workspace" not in go:
        fail("desktop host must inject bot-workspace on the live window")
    if not DESKTOP_README.is_file():
        fail("missing desktop/README.md")
    if not VENDOR_README.is_file():
        fail("missing vendor/desktop/README.md")
    print("OK  packaged Dragon desktop source")


def test_copy_from_package_not_hermes() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import private_desktop as pd  # noqa: E402

    with tempfile.TemporaryDirectory(prefix="dragon-desk-") as tmp:
        base = pathlib.Path(tmp)
        pkg = base / "payload" / "desktop" / "win-unpacked"
        pkg.mkdir(parents=True)
        src = pkg / "DragonAIAgent.exe"
        src.write_bytes(b"MZ-dragon")
        hermes = (
            base
            / "hermes"
            / "hermes-agent"
            / "apps"
            / "desktop"
            / "release"
            / "win-unpacked"
        )
        hermes.mkdir(parents=True)
        hermes_exe = hermes / "Hermes.exe"
        hermes_exe.write_bytes(b"MZ-hermes")
        dest_root = base / "DragonAIAgent"
        dest = pd.copy_win_unpacked(src, dest_root)
        if dest.name != "DragonAIAgent.exe":
            fail(f"private exe must be DragonAIAgent.exe, got {dest.name}")
        if dest.read_bytes() != b"MZ-dragon":
            fail("packaged DragonAIAgent.exe bytes were not copied")
        if pd.find_packaged_desktop_exe(base / "payload") != src:
            fail("find_packaged_desktop_exe must see payload/desktop/win-unpacked")
        try:
            pd.copy_win_unpacked(hermes_exe, dest_root)
            fail("copy must refuse a Hermes.exe source")
        except (ValueError, FileNotFoundError) as exc:
            if "Refuse copying from a Hermes install" not in str(exc) and "DragonAIAgent.exe" not in str(exc):
                fail(f"hermes source refuse unclear: {exc}")
        if dest.read_bytes() != b"MZ-dragon":
            fail("refused Hermes copy must not replace the Dragon exe")
        if pd.is_hermes_install_path(hermes_exe) is not True:
            fail("must detect standalone Hermes.exe")
        if pd.is_hermes_install_path(dest) is not False:
            fail("DragonAIAgent path must not be treated as a Hermes install")
    print("OK  copy uses Dragon package, refuses Hermes install")


def test_no_hermes_hunt() -> None:
    for path in (FINDER, LAUNCHER, *INSTALLERS, PRIVATE, VBS):
        text = read(path)
        for bad in FORBIDDEN_USER:
            if bad in text:
                fail(f"{path.name} still {bad!r}")
        if "Install standalone Hermes" in text or "install standalone Hermes" in text:
            fail(f"{path.name} still tells the user to install Hermes")
    finder = read(FINDER)
    for token in REQUIRED_FINDER:
        if token not in finder:
            fail(f"Find-HermesDesktop.ps1 missing {token}")
    if "LOCALAPPDATA" in finder and "hermes\\hermes-agent" in finder:
        fail("finder still searches %LOCALAPPDATA%\\hermes")
    py = read(PRIVATE)
    if "DragonAIAgent.exe" not in py:
        fail("private_desktop.py must name DragonAIAgent.exe")
    if py.split("PRIVATE_EXE_REL")[1].split("\n", 1)[0].count("Hermes.exe"):
        fail("PRIVATE_EXE_REL must not be Hermes.exe")
    print("OK  install/launch do not hunt for Hermes.exe")


def test_installers_copy_package() -> None:
    for path in INSTALLERS:
        text = read(path)
        if "Copied packaged Dragon AI Agent desktop" not in text:
            fail(f"{path.name} must copy desktop\\win-unpacked from the package")
        if "DragonAIAgent.exe" not in text:
            fail(f"{path.name} must name DragonAIAgent.exe")
        if "Install standalone Hermes" in text:
            fail(f"{path.name} still asks for a Hermes install")
        if "desktop\\win-unpacked\\Hermes.exe" in text:
            fail(f"{path.name} still expects Hermes.exe as the product")
    launcher = read(LAUNCHER)
    if "DragonAIAgent.exe" not in launcher:
        fail("start-embedded.ps1 must launch DragonAIAgent.exe")
    if "Install standalone Hermes" in launcher:
        fail("launcher still asks for a Hermes install")
    print("OK  installers ship/launch the Dragon package desktop")


def test_docs() -> None:
    docs = "\n".join(read(p) for p in DOCS)
    for needle in (
        "DragonAIAgent.exe",
        "desktop/win-unpacked",
        "does not search",
        "Hermes",
    ):
        if needle not in docs and needle.replace("/", "\\") not in docs:
            fail(f"docs must mention {needle}")
    if "Install standalone Hermes" in docs:
        fail("docs still tell the user to install Hermes")
    print("OK  docs describe a packaged Dragon desktop")


def test_self_test_cli() -> None:
    proc = subprocess.run(
        [sys.executable, str(PRIVATE), "paths", "--install-root", "/x/DragonAIAgent"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        fail(f"paths CLI failed: {proc.stderr}")
    if "DragonAIAgent.exe" not in proc.stdout:
        fail("paths CLI must print DragonAIAgent.exe")
    print("OK  private_desktop paths CLI")


def test_install_first_run_guardrails() -> None:
    guard = SCRIPTS / "Test-InstallFirstRun.py"
    if not guard.is_file():
        fail("missing Test-InstallFirstRun.py guardrails")
    proc = subprocess.run([sys.executable, str(guard)], cwd=str(ROOT))
    if proc.returncode != 0:
        fail("Test-InstallFirstRun.py failed")
    print("OK  install first-run guardrails")


def main() -> int:
    test_package_has_desktop_source()
    test_copy_from_package_not_hermes()
    test_no_hermes_hunt()
    test_installers_copy_package()
    test_docs()
    test_self_test_cli()
    test_install_first_run_guardrails()
    print("SMOKE OK: Dragon AI Agent desktop is packaged; install does not find Hermes.exe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
