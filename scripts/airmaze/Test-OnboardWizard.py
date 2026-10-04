#!/usr/bin/env python3
"""Regression tests for Dragon AI Agent first-run wizard Continue + status strip.

Catches the UltraDragon crash:
  The property 'Text' cannot be found on this object.
which happens when Continue assigns .Text on $null / a PSCustomObject / a hashtable.

Also rejects the smashed status strip:
  Welcome: SUCCESS models: PENDING mail: PENDING CRM: PENDING ...
in favor of a short Welcome/Models line.

No secrets. Safe on Linux CI. Optionally runs pwsh -SelfTest when present.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
WIZARD = SCRIPTS / "Onboard-Wizard.ps1"
INSTALL = SCRIPTS / "install.ps1"
SETUP = ROOT / "installer" / "DragonAIAgentSetup.ps1"

MASHED_STATUS = (
    "Welcome: SUCCESS models: PENDING mail: PENDING CRM: PENDING "
    "Phone: PENDING property: PENDING ler: PENDING"
)

BANNED_STATUS_TOKENS = (
    "Email",
    "CRM",
    "Phone",
    "Dialer",
    "SUCCESS",
    "PENDING",
    "mail:",
    "ler:",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def extract_function(src: str, name: str) -> str:
    token = f"function {name}"
    start = src.find(token)
    if start < 0:
        fail(f"missing function {name}")
    rest = src[start:]
    nxt = rest.find("\nfunction ", 1)
    nested = rest.find("\n    function ", 1)
    cuts = [i for i in (nxt, nested) if i > 0]
    return rest if not cuts else rest[: min(cuts)]


def format_wizard_step_word(status: str | None) -> str:
    key = (status or "pending").strip().lower()
    return {
        "success": "OK",
        "failed": "failed",
        "skipped": "skipped",
        "in_app": "in-app",
    }.get(key, "pending")


def format_wizard_status_line(steps: dict | None) -> str:
    steps = steps or {}
    welcome = format_wizard_step_word(str(steps.get("welcome") or "pending"))
    models = format_wizard_step_word(str(steps.get("models") or "pending"))
    return f"Welcome: {welcome} / Models: {models}"


def wizard_can_set_text(target) -> bool:
    """Mirror Test-WizardCanSetText: refuse null, mappings, and objects without Text."""
    if target is None:
        return False
    if isinstance(target, dict):
        return False
    return hasattr(target, "Text")


def set_wizard_control_text(target, value: str) -> bool:
    """Mirror Set-WizardControlText: never assign .Text on a bad object."""
    if not wizard_can_set_text(target):
        return False
    target.Text = value
    return True


def test_status_formatting() -> None:
    smashed = format_wizard_status_line(
        {
            "welcome": "success",
            "models": "pending",
            "email": "pending",
            "crm": "pending",
            "telephony": "pending",
            "property_data": "pending",
            "dialer": "pending",
        }
    )
    if smashed != "Welcome: OK / Models: pending":
        fail(f"expected short Welcome/Models line, got {smashed!r}")
    if smashed == MASHED_STATUS:
        fail("status line reproduced the smashed PENDING mashup")
    for token in BANNED_STATUS_TOKENS:
        if token in smashed:
            fail(f"status line must not contain {token!r}: {smashed}")
    if format_wizard_status_line({"welcome": "failed", "models": "skipped"}) != "Welcome: failed / Models: skipped":
        fail("failed/skipped words are wrong")
    if format_wizard_status_line({"welcome": "success", "models": "in_app"}) != "Welcome: OK / Models: in-app":
        fail("in_app models must format as in-app")
    if format_wizard_status_line({}) != "Welcome: pending / Models: pending":
        fail("empty steps must default to pending")
    print("OK  status formatting is Welcome/Models only")


def test_text_guard() -> None:
    class NoText:
        pass

    class HasText:
        def __init__(self) -> None:
            self.Text = "old"

    bad = NoText()
    mapping = {"Text": "existing"}
    good = HasText()

    if wizard_can_set_text(None) or wizard_can_set_text(bad) or wizard_can_set_text(mapping):
        fail("wizard_can_set_text must refuse null / no-Text / hashtable")
    if not wizard_can_set_text(good):
        fail("wizard_can_set_text must allow an object that already has Text")

    try:
        if set_wizard_control_text(None, "x"):
            fail("set_wizard_control_text must refuse null")
        if set_wizard_control_text(bad, "hello"):
            fail("set_wizard_control_text must refuse an object without Text")
        if hasattr(bad, "Text"):
            fail("refusing a bad object must not add a Text attribute")
        if set_wizard_control_text(mapping, "overwrite"):
            fail("set_wizard_control_text must refuse a dict Text key")
        if mapping.get("Text") == "overwrite":
            fail("must not overwrite a hashtable Text key")
        if not set_wizard_control_text(good, "new") or good.Text != "new":
            fail("set_wizard_control_text must update a real Text property")
    except Exception as exc:  # noqa: BLE001 — the point of the regression
        fail(f"setting Text on a bad object must not throw: {exc}")
    print("OK  Text guard refuses bad objects without throwing")


def test_wizard_source() -> None:
    wizard = read(WIZARD)
    for name in (
        "Format-WizardStatusLine",
        "Format-WizardStepWord",
        "Test-WizardStepComplete",
        "Test-WizardCanSetText",
        "Set-WizardControlText",
        "Set-WizardMessage",
        "Invoke-WizardSelfTest",
    ):
        if f"function {name}" not in wizard:
            fail(f"Onboard-Wizard.ps1 missing {name}")

    status = extract_function(wizard, "Update-StatusStrip")
    if "Format-WizardStatusLine" not in status:
        fail("Update-StatusStrip must use Format-WizardStatusLine")
    for token in ("Email", "CRM", "Phone", "Property", "Dialer"):
        if token in status:
            fail(f"Update-StatusStrip still lists {token} (causes the PENDING mashup)")
    if "ToUpper()" in status:
        fail("Update-StatusStrip still uppercases SUCCESS/PENDING")

    if "$msgLabel.Text" in wizard:
        fail("wizard still assigns $msgLabel.Text (throws when the label is null / non-control)")
    if "The property 'Text' cannot be found" not in wizard:
        fail("Test-WizardCanSetText comment must name the WinForms Text error")

    models = extract_function(wizard, "Show-StepModels")
    if "Set-WizardMessage" not in models:
        fail("Models Continue must set the footer via Set-WizardMessage")
    if "$script:WizChatBox" not in models or "$script:WizImageBox" not in models:
        fail("Models Continue must read combos from $script: scope (GetNewClosure drops $msgLabel)")
    if "Invoke-ApplyGatewayModels -Chat $chat -Image $image" not in models:
        fail("Models Continue must still write the selected pair through Apply-GatewayModels")
    if "grok-4.7" not in models or "grok-imagine-image" not in models:
        fail("Grok / Grok Imagine defaults must stay on the Models step")
    if "SelectedIndex = 0" not in models:
        fail("Grok must remain the preselected chat/image default")
    catalog_fn = extract_function(wizard, "Get-WizardChatCatalog")
    for needle in ("OpenAI", "Anthropic", "Google Gemini", "Self-hosted / custom endpoint", "grok-4.7"):
        if needle not in catalog_fn:
            fail(f"Get-WizardChatCatalog must offer {needle}")
    if catalog_fn.find("grok-4.7") > catalog_fn.find("gpt-4o") and "gpt-4o" in catalog_fn:
        fail("Grok must stay first in Get-WizardChatCatalog")
    if "WizBaseUrlBox" not in models or "chat_api_key" not in models:
        fail("Self-hosted path must collect base URL / model id and store an optional key via DPAPI")
    if "[switch]$SelfTest" not in wizard:
        fail("wizard must expose -SelfTest for the Text/status regression")

    fmt = extract_function(wizard, "Format-WizardStatusLine")
    if 'return "Welcome: $welcome / Models: $models"' not in fmt:
        fail("Format-WizardStatusLine must return the short Welcome/Models template")
    word = extract_function(wizard, "Format-WizardStepWord")
    if "in_app" not in word or "in-app" not in word:
        fail("Format-WizardStepWord must map in_app to in-app")
    resume = extract_function(wizard, "Get-FirstIncompleteStep")
    if "Test-WizardStepComplete" not in resume:
        fail("Get-FirstIncompleteStep must treat in_app as a completed Models step")
    complete = extract_function(wizard, "Test-WizardStepComplete")
    if "in_app" not in complete:
        fail("Test-WizardStepComplete must include in_app")

    guard = extract_function(wizard, "Set-WizardControlText")
    if "Test-WizardCanSetText" not in guard:
        fail("Set-WizardControlText must check Test-WizardCanSetText before assigning .Text")

    selftest = extract_function(wizard, "Invoke-WizardSelfTest")
    if '$line -like "*$banned*"' in selftest:
        fail("SelfTest -like is case-insensitive and would reject lowercase pending")
    if "$line.Contains($banned)" not in selftest:
        fail("SelfTest must case-sensitively reject SUCCESS/PENDING mashups")
    if "in_app" not in selftest or "Get-FirstIncompleteStep" not in selftest:
        fail("SelfTest must prove in_app skips the WinForms Models step")

    print("OK  wizard source wired for Continue + short status")


def test_packaged() -> None:
    rel = "scripts\\airmaze\\Test-OnboardWizard.py"
    for path in (INSTALL, SETUP):
        text = read(path)
        if rel not in text:
            fail(f"{path.name} must install Test-OnboardWizard.py")
    install = read(INSTALL)
    if "& $wizard" in install or "Launching onboarding wizard" in install:
        fail("install.ps1 must not auto-launch WinForms Onboard-Wizard")
    if "Set-DragonAIInAppProviderOnboarding" not in install:
        fail("install.ps1 must mark first-run Models as the in-app provider UI")
    print("OK  installer copies Test-OnboardWizard.py")


def run_pwsh_selftest() -> None:
    host = shutil.which("pwsh") or shutil.which("powershell")
    if not host:
        print("SKIP host -SelfTest (pwsh/powershell not on PATH)")
        return
    cmd = [host, "-NoProfile", "-File", str(WIZARD), "-SelfTest"]
    print("RUN", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        fail(f"Onboard-Wizard -SelfTest exited {proc.returncode}")
    if "SELFTEST OK" not in proc.stdout:
        fail("Onboard-Wizard -SelfTest did not print SELFTEST OK")
    print("OK  host -SelfTest")


def main() -> int:
    test_status_formatting()
    test_text_guard()
    test_wizard_source()
    test_packaged()
    run_pwsh_selftest()
    print("SMOKE OK: wizard Continue no longer sets Text on a bad object; status is Welcome/Models only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
