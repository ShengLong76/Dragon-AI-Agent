#!/usr/bin/env python3
"""Hermes and Dragon AI stay separate programs.

Proves the live UltraDragon contract in-repo:

- Private client is DragonAIAgent\\desktop\\win-unpacked
- HERMES_DESKTOP_USER_DATA_DIR is DragonAIAgent\\electron-userdata
- Copy/provision never writes back to the standalone Hermes tree
- Branding is refused outside DragonAIAgent
- Standalone connections.json primary stays local

No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
PRIVATE = SCRIPTS / "private_desktop.py"
FINDER = SCRIPTS / "Find-HermesDesktop.ps1"
APPLY = SCRIPTS / "Apply-DesktopBranding.ps1"
BRAND_PY = SCRIPTS / "desktop_branding.py"
LAUNCHER = SCRIPTS / "start-embedded.ps1"
VBS = SCRIPTS / "Start-DragonAI.vbs"
CONN_PY = SCRIPTS / "embedded_desktop_connection.py"
CONN_PS1 = SCRIPTS / "Set-EmbeddedDesktopConnection.ps1"
INSTALLERS = (
    SCRIPTS / "install.ps1",
    ROOT / "installer" / "DragonAIAgentSetup.ps1",
)
DOCS = (
    ROOT / "docs" / "airmaze" / "PRIVATE_DESKTOP.md",
    ROOT / "docs" / "airmaze" / "BRANDING.md",
    ROOT / "README.md",
)

REQUIRED_FINDER = (
    "DragonAIAgent\\desktop\\win-unpacked",
    "HERMES_DESKTOP_USER_DATA_DIR",
    "electron-userdata",
    "Install-DragonAIPrivateDesktop",
    "Test-DragonAIPrivateDesktopPath",
    "Refuse branding outside DragonAIAgent",
    "Set-DragonAIDesktopUserDataEnv",
)

REQUIRED_APPLY = (
    "Refuse branding outside DragonAIAgent",
    "Test-DragonAIPrivateDesktopPath",
    "DragonAIAgent",
)

REQUIRED_LAUNCHER = (
    "HERMES_DESKTOP_USER_DATA_DIR",
    "Install-DragonAIPrivateDesktop",
    "electron-userdata",
    "desktop\\win-unpacked",
)

REQUIRED_VBS = (
    "HERMES_DESKTOP_USER_DATA_DIR",
    "electron-userdata",
    "desktop\\win-unpacked",
)

REQUIRED_INSTALLER = (
    "private_desktop.py",
    "Install-DragonAIPrivateDesktop",
    "HERMES_DESKTOP_USER_DATA_DIR",
    "desktop\\win-unpacked",
)

REQUIRED_CONN = (
    "HERMES_DESKTOP_USER_DATA_DIR",
    "electron-userdata",
    "NoPrimary",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def require_tokens(path: pathlib.Path, tokens: tuple[str, ...], label: str) -> None:
    text = read(path)
    for token in tokens:
        if token not in text:
            fail(f"{path.name} missing {label} token: {token}")
    print(f"OK  {label}: {path.relative_to(ROOT)}")


def test_copy_does_not_mutate_source() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import private_desktop as pd  # noqa: E402

    with tempfile.TemporaryDirectory(prefix="dragon-private-desk-") as tmp:
        base = pathlib.Path(tmp)
        src_dir = base / "hermes" / "hermes-agent" / "apps" / "desktop" / "release" / "win-unpacked"
        src_dir.mkdir(parents=True)
        src_exe = src_dir / "Hermes.exe"
        src_exe.write_bytes(b"MZ-source")
        marker = src_dir / "resources" / "app.asar.unpacked" / "dist" / "renderer.js"
        marker.parent.mkdir(parents=True)
        marker.write_text("HERMES AGENT\n", encoding="utf-8")
        dest_root = base / "DragonAIAgent"
        dest_exe = pd.copy_win_unpacked(src_exe, dest_root)
        if not dest_exe.is_file():
            fail(f"private copy missing: {dest_exe}")
        if dest_exe.read_bytes() != b"MZ-source":
            fail("private Hermes.exe bytes do not match source")
        dest_marker = dest_exe.parent / "resources" / "app.asar.unpacked" / "dist" / "renderer.js"
        if not dest_marker.is_file():
            fail("win-unpacked resources were not copied")
        dest_marker.write_text("DRAGON AI AGENT\n", encoding="utf-8")
        if marker.read_text(encoding="utf-8") != "HERMES AGENT\n":
            fail("copy/provision mutated the standalone Hermes tree")
        if "DragonAIAgent" not in dest_exe.parts:
            fail("private exe is not under DragonAIAgent")
        again = pd.copy_win_unpacked(src_exe, dest_root)
        if again != dest_exe:
            fail("second provision must reuse the existing private exe")
        if dest_marker.read_text(encoding="utf-8") != "DRAGON AI AGENT\n":
            fail("re-provision must not clobber an existing private tree")
        try:
            pd.copy_win_unpacked(src_exe, base / "hermes-dest")
            fail("copy must refuse a destination outside DragonAIAgent")
        except ValueError as exc:
            if "Refuse branding outside DragonAIAgent" not in str(exc) and "DragonAIAgent" not in str(exc):
                fail(f"refuse message unclear: {exc}")
        print("OK  copy provisions private tree and leaves standalone Hermes alone")


def test_refuse_branding_and_paths() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import private_desktop as pd  # noqa: E402

    standalone = pathlib.Path("/tmp/hermes/hermes-agent/apps/desktop/release/win-unpacked/Hermes.exe")
    try:
        pd.assert_private_dragon_path(standalone)
        fail("standalone Hermes path must be refused")
    except ValueError as exc:
        if "Refuse branding outside DragonAIAgent" not in str(exc):
            fail(f"refuse message missing: {exc}")
    private = pathlib.Path("/tmp/DragonAIAgent/desktop/win-unpacked/Hermes.exe")
    pd.assert_private_dragon_path(private)
    if pd.private_desktop_exe("/x/DragonAIAgent").as_posix() != "/x/DragonAIAgent/desktop/win-unpacked/Hermes.exe":
        fail("private exe relative path drifted")
    if pd.electron_userdata_dir("/x/DragonAIAgent").name != "electron-userdata":
        fail("userdata dir must be electron-userdata")
    proc = subprocess.run(
        [sys.executable, str(PRIVATE), "refuse", "--path", str(standalone)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 2:
        fail(f"refuse CLI must exit 2 for standalone Hermes, got {proc.returncode}")
    print("OK  refuse branding outside DragonAIAgent")


def test_standalone_connections_stay_local() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import embedded_desktop_connection as edc  # noqa: E402
    import private_desktop as pd  # noqa: E402

    standalone = pathlib.Path("/tmp/AppData/Roaming/Hermes/connections.json")
    if not pd.is_standalone_hermes_connections(standalone):
        fail("must detect standalone Hermes connections.json")
    if pd.should_make_embedded_primary(standalone):
        fail("standalone connections must not take Embedded Linux as primary")
    dragon = pathlib.Path("/tmp/DragonAIAgent/electron-userdata/connections.json")
    if not pd.should_make_embedded_primary(dragon):
        fail("Dragon userdata connections should make Embedded Linux primary")

    existing = {
        "version": 2,
        "primary": "local",
        "lastUsed": "local",
        "connections": [
            {"id": "local", "kind": "local", "label": "This device"},
        ],
    }
    kept = edc.merge_registry(existing, make_primary=False)
    if kept["primary"] != "local":
        fail(f"standalone primary drifted to {kept['primary']}")
    ids = [c["id"] for c in kept["connections"]]
    if "embedded-linux" not in ids or "local" not in ids:
        fail(f"standalone should still list both connections: {ids}")

    with tempfile.TemporaryDirectory(prefix="dragon-conn-") as tmp:
        dest = pathlib.Path(tmp) / "Hermes" / "connections.json"
        dest.parent.mkdir(parents=True)
        dest.write_text(json.dumps(existing), encoding="utf-8")
        updated = edc.apply(dest, make_primary=pd.should_make_embedded_primary(dest))
        doc = json.loads(dest.read_text(encoding="utf-8"))
        if doc["primary"] != "local":
            fail(f"apply() stole standalone primary: {doc['primary']} ({updated})")
        remote = next(c for c in doc["connections"] if c["id"] == "embedded-linux")
        if remote["url"] != "http://127.0.0.1:8650":
            fail("standalone may list Embedded Linux but must not become primary")
    print("OK  standalone connections primary stays local")


def test_scripts_and_docs() -> None:
    require_tokens(FINDER, REQUIRED_FINDER, "finder")
    require_tokens(APPLY, REQUIRED_APPLY, "apply")
    require_tokens(BRAND_PY, ("Refuse branding outside DragonAIAgent", "assert_private_dragon_path"), "brand-py")
    require_tokens(LAUNCHER, REQUIRED_LAUNCHER, "launcher")
    require_tokens(VBS, REQUIRED_VBS, "vbs")
    require_tokens(CONN_PY, REQUIRED_CONN, "conn-py")
    require_tokens(CONN_PS1, REQUIRED_CONN, "conn-ps1")
    for path in INSTALLERS:
        require_tokens(path, REQUIRED_INSTALLER, "installer")
        text = read(path)
        if "Start-HermesDesktopClient" not in text:
            fail(f"{path.name} must still launch via Start-HermesDesktopClient")
    brand_py = read(BRAND_PY)
    if "assert_private_dragon_path" not in brand_py:
        fail("desktop_branding.py must refuse branding outside DragonAIAgent")
    finder = read(FINDER)
    if "Find-HermesDesktopSourceExe" not in finder:
        fail("finder must keep a source-only discovery path for the standalone tree")
    if "Set-DragonAIMainWindowTitle" not in finder or "DragonAIAgent" not in finder.split("function Set-DragonAIMainWindowTitle", 1)[-1][:1200]:
        fail("window title wrap must only touch DragonAIAgent process paths")
    launcher = read(LAUNCHER)
    if "APPDATA\\Hermes\\connections.json" in launcher and "electron-userdata" not in launcher:
        fail("launcher must wire Dragon electron-userdata, not steal standalone Hermes connections")
    vbs = read(VBS)
    if "Environment" not in vbs and "HERMES_DESKTOP_USER_DATA_DIR" not in vbs:
        fail("Start-DragonAI.vbs must set HERMES_DESKTOP_USER_DATA_DIR")
    docs = "\n".join(read(p) for p in DOCS)
    for needle in (
        "desktop\\win-unpacked",
        "HERMES_DESKTOP_USER_DATA_DIR",
        "electron-userdata",
        "standalone",
        "primary",
        "local",
    ):
        if needle not in docs and needle.replace("\\", "/") not in docs:
            fail(f"docs must mention {needle}")
    if "%APPDATA%\\Hermes\\connections.json" in read(ROOT / "docs" / "airmaze" / "EMBEDDED_GATEWAY.md"):
        gw = read(ROOT / "docs" / "airmaze" / "EMBEDDED_GATEWAY.md")
        if "electron-userdata" not in gw or "stays local" not in gw.lower() and "primary stays local" not in gw.lower():
            fail("EMBEDDED_GATEWAY.md must say Dragon userdata is primary and standalone stays local")
    print("OK  scripts + docs keep Hermes and Dragon separate")


def main() -> int:
    if not PRIVATE.is_file():
        fail(f"missing {PRIVATE}")
    test_copy_does_not_mutate_source()
    test_refuse_branding_and_paths()
    test_standalone_connections_stay_local()
    test_scripts_and_docs()
    print("SMOKE OK: Dragon AI is a private desktop; standalone Hermes is not mutated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
