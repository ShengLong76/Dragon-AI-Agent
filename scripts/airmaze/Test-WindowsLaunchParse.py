#!/usr/bin/env python3
"""Smoke/parse check: Windows launch scripts must parse on PowerShell 5.1.

James/Cos: Dragon AI Agent.lnk did nothing because start-embedded.ps1
aborted on a duplicate tray-settings key and a $HOME shadow.
No secrets. Safe on Linux CI (static). Optionally AST-parses with pwsh.
"""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
INSTALLER = ROOT / "installer"
DESIGN = ROOT / "docs" / "airmaze" / "WINDOWS_LAUNCH_PARSE.md"
PLAN = ROOT / "docs" / "airmaze" / "WINDOWS_LAUNCH_PARSE_PLAN.md"
LAUNCHER = SCRIPTS / "start-embedded.ps1"
APPLY_MODELS = SCRIPTS / "Apply-GatewayModels.ps1"
APPLY_VOICE = SCRIPTS / "Apply-VoiceChat.ps1"
WIZARD = SCRIPTS / "Onboard-Wizard.ps1"

PS1_ROOTS = (SCRIPTS, INSTALLER)

# PowerShell hashtables are case-insensitive. Both spellings in one @{ } is a parse error.
OPENUI_CAMEL = "openUIOnStartupDisabled"
OPENUI_PASCAL = "OpenUIOnStartupDisabled"

# Automatic $HOME is read-only. param $Home / assignment $home= shadows it.
HOME_PARAM_RE = re.compile(r"\[string\]\s*\$Home\b", re.IGNORECASE)
HOME_ASSIGN_RE = re.compile(r"\$Home\s*=", re.IGNORECASE)
HERMES_HOME_PARAM_RE = re.compile(r"\[string\]\s*\$HermesHome\b")

# @{ ... } blocks (non-greedy enough for the tray patches in this repo)
HASHTABLE_RE = re.compile(r"@\{(.*?)}", re.DOTALL)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def iter_ps1() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for root in PS1_ROOTS:
        if not root.is_dir():
            continue
        files.extend(sorted(root.rglob("*.ps1")))
    if not files:
        fail("no PowerShell scripts found")
    return files


def strip_line_comment(line: str) -> str:
    in_s = False
    in_d = False
    out: list[str] = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "'" and not in_d:
            in_s = not in_s
            out.append(ch)
        elif ch == '"' and not in_s:
            in_d = not in_d
            out.append(ch)
        elif ch == "#" and not in_s and not in_d:
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def test_design_recorded() -> None:
    design = read(DESIGN)
    for needle in (
        "openUIOnStartupDisabled",
        "Duplicate keys",
        "HOME",
        "HermesHome",
        "embeddedHome",
        "start-embedded.ps1",
        "Apply-GatewayModels.ps1",
    ):
        if needle not in design:
            fail(f"WINDOWS_LAUNCH_PARSE.md must document {needle!r}")
    if OPENUI_PASCAL in design and "Do not add PascalCase" not in design:
        # Design may mention the bad key as the bug; require the rule.
        pass
    plan = read(PLAN)
    if "Tests first" not in plan or "HermesHome" not in plan:
        fail("WINDOWS_LAUNCH_PARSE_PLAN.md must name HermesHome and tests-first order")
    print("OK  design + plan recorded")


def test_single_openui_key() -> None:
    for path in iter_ps1():
        text = read(path)
        for block in HASHTABLE_RE.findall(text):
            has_camel = OPENUI_CAMEL in block
            has_pascal = OPENUI_PASCAL in block
            if has_camel and has_pascal:
                fail(
                    f"{path.relative_to(ROOT)} tray hashtable lists both "
                    f"{OPENUI_CAMEL!r} and {OPENUI_PASCAL!r} "
                    "(PowerShell hashtables are case-insensitive)"
                )
        # Belt: the two spellings must not sit as sibling hash keys in one file's patch.
        if re.search(
            rf"{re.escape(OPENUI_CAMEL)}\s*=\s*\$true[\s\S]{{0,200}}{re.escape(OPENUI_PASCAL)}\s*=",
            text,
        ) or re.search(
            rf"{re.escape(OPENUI_PASCAL)}\s*=\s*\$true[\s\S]{{0,200}}{re.escape(OPENUI_CAMEL)}\s*=",
            text,
        ):
            fail(f"{path.relative_to(ROOT)} still pairs both OpenUIOnStartupDisabled spellings")
    print("OK  single openUIOnStartupDisabled key per hashtable")


def test_no_home_shadow() -> None:
    for path in iter_ps1():
        text = read(path)
        for lineno, raw in enumerate(text.splitlines(), 1):
            line = strip_line_comment(raw)
            if HOME_PARAM_RE.search(line):
                fail(
                    f"{path.relative_to(ROOT)}:{lineno} param $Home shadows automatic $HOME"
                )
            if HOME_ASSIGN_RE.search(line):
                fail(
                    f"{path.relative_to(ROOT)}:{lineno} assignment $Home/$home shadows automatic $HOME"
                )
    print("OK  no $Home / $home param or assignment")


def test_hotfix_symbols() -> None:
    launcher = read(LAUNCHER)
    if "$embeddedHome" not in launcher:
        fail("start-embedded.ps1 Start-DragonAIVoiceChat must use $embeddedHome")
    if "-HermesHome" not in launcher:
        fail("start-embedded.ps1 must call Apply-GatewayModels.ps1 -HermesHome")
    if re.search(r"-Home\s+\$data", launcher):
        fail("start-embedded.ps1 still passes -Home to Apply-GatewayModels.ps1")
    if OPENUI_CAMEL not in launcher:
        fail("start-embedded.ps1 must keep camelCase openUIOnStartupDisabled")

    apply = read(APPLY_MODELS)
    if not HERMES_HOME_PARAM_RE.search(apply):
        fail("Apply-GatewayModels.ps1 must declare [string]$HermesHome")
    if "$HermesHome" not in apply:
        fail("Apply-GatewayModels.ps1 must use $HermesHome")
    if "--home" not in apply:
        fail("Apply-GatewayModels.ps1 must still pass Python --home")

    wizard = read(WIZARD)
    if "-HermesHome" not in wizard:
        fail("Onboard-Wizard.ps1 must pass -HermesHome to Apply-GatewayModels.ps1")
    if re.search(r'"-Home"', wizard) or re.search(r"'-Home'", wizard):
        fail("Onboard-Wizard.ps1 still passes -Home")

    voice = read(APPLY_VOICE)
    if not HERMES_HOME_PARAM_RE.search(voice):
        fail("Apply-VoiceChat.ps1 must declare [string]$HermesHome")
    print("OK  hotfix symbols (embeddedHome / HermesHome)")


def test_host_parse() -> None:
    host = shutil.which("pwsh") or shutil.which("powershell")
    if not host:
        print("SKIP host AST parse (pwsh/powershell not on PATH)")
        return
    targets = [LAUNCHER, APPLY_MODELS, APPLY_VOICE, WIZARD]
    targets.extend(sorted(INSTALLER.glob("*.ps1")))
    for path in targets:
        if not path.is_file():
            continue
        # Parser::ParseFile reports duplicate hashtable keys and other parse errors
        # without executing the script (no Docker, no $HOME assignment).
        cmd = [
            host,
            "-NoProfile",
            "-Command",
            (
                "$e=$null; $t=$null; "
                "[void][System.Management.Automation.Language.Parser]::ParseFile("
                f"'{path}', [ref]$t, [ref]$e); "
                "if ($e) { $e | ForEach-Object { $_.ToString() }; exit 1 }"
            ),
        ]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        if proc.returncode != 0:
            sys.stdout.write(proc.stdout)
            sys.stderr.write(proc.stderr)
            fail(f"PowerShell parse failed: {path.relative_to(ROOT)}")
    print("OK  host AST parse")


def main() -> int:
    test_design_recorded()
    test_single_openui_key()
    test_no_home_shadow()
    test_hotfix_symbols()
    test_host_parse()
    print("SMOKE OK: Windows launch scripts do not shadow $HOME or duplicate OpenUI keys.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
