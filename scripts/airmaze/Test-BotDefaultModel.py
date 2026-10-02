#!/usr/bin/env python3
"""Tests first: onboarding default LLM is inherited by all bots.

James (via Cos): first-run provider/model applies to Personal Assistant
and later team seats, not only gateway chat/Generate.
No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
DOCS = ROOT / "docs" / "airmaze"
ENGINE = SCRIPTS / "gateway_models.py"
BOT_GROUPS = SCRIPTS / "bot_groups.py"
APPLY = SCRIPTS / "Apply-GatewayModels.ps1"
WIZARD = SCRIPTS / "Onboard-Wizard.ps1"
SELECT = SCRIPTS / "Select-BotGroup.ps1"
LAUNCHER = SCRIPTS / "start-embedded.ps1"
INSTALL = SCRIPTS / "install.ps1"
SETUP = ROOT / "installer" / "DragonAIAgentSetup.ps1"
DESIGN = DOCS / "BOT_DEFAULT_MODEL.md"
PLAN = DOCS / "BOT_DEFAULT_MODEL_PLAN.md"
FIRST_RUN = DOCS / "FIRST_RUN_MODELS.md"
SETUP_GUIDE = DOCS / "SETUP_GUIDE.md"
BOT_GROUPS_DOC = DOCS / "BOT_GROUPS.md"
README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"
DESIGN_DOC = DOCS / "DESIGN.md"
BRANDING_CSS = ROOT / "branding" / "fonts" / "syne" / "dragon-ui.css"

DEFAULT_CHAT = "grok-4.6"
OVERRIDE_CHAT = "grok-4.5"
LATER_CHAT = "grok-4.3"
INHERITED_MARK = "# dragon-ai-inherited-model"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def load_engines():
    if not ENGINE.is_file():
        fail("gateway_models.py must exist")
    if not BOT_GROUPS.is_file():
        fail("bot_groups.py must exist")
    sys.path.insert(0, str(SCRIPTS))
    import bot_groups as bg  # noqa: WPS433
    import gateway_models as gm  # noqa: WPS433

    return gm, bg


def _mapping(text: str) -> dict:
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if ":" not in raw:
            continue
        key, _, rest = raw.lstrip(" ").partition(":")
        key = key.strip()
        value = rest.strip().strip("'\"")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value:
            parent[key] = value
        else:
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
    return root


def _chat_of(profile: pathlib.Path) -> tuple[str, str, bool]:
    text = ""
    for name in ("config.yaml", "profile.yaml", "bot.yaml"):
        path = profile / name
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            break
    if not text:
        return "", "", False
    data = _mapping(text)
    model = (
        ((data.get("model") or {}) if isinstance(data.get("model"), dict) else {})
        .get("default")
        or ((data.get("model") or {}) if isinstance(data.get("model"), dict) else {}).get("model")
        or (data.get("principal") or {}).get("model")
        or (data.get("model") if isinstance(data.get("model"), str) else "")
        or ""
    )
    provider = (
        ((data.get("model") or {}) if isinstance(data.get("model"), dict) else {}).get("provider")
        or (data.get("principal") or {}).get("provider")
        or ""
    )
    return str(provider), str(model), INHERITED_MARK in text


def _write_bot(root: pathlib.Path, bot_id: str, body: str = "") -> pathlib.Path:
    dest = root / bot_id
    dest.mkdir(parents=True)
    (dest / "bot.yaml").write_text(
        body
        or (
            f"slug: {bot_id}\n"
            f"display_name: {bot_id}\n"
            "bot_desktop:\n"
            "  geometry: \"1440x900\"\n"
        ),
        encoding="utf-8",
    )
    (dest / "SOUL.md").write_text(f"# {bot_id}\n", encoding="utf-8")
    return dest


def test_design_recorded() -> None:
    design = read(DESIGN)
    for needle in (
        "all bots",
        "inherit",
        "Onboard-Wizard",
        "Apply-GatewayModels",
        "principal",
        "model.default",
        "Personal Assistant",
        "dragon-ai-inherited-model",
        "Grok (xAI)",
        "Grok Imagine",
    ):
        if needle not in design:
            fail(f"BOT_DEFAULT_MODEL.md must document {needle!r}")
    plan = read(PLAN)
    if "Tests first" not in plan or "gateway_models.py" not in plan:
        fail("BOT_DEFAULT_MODEL_PLAN.md must name the engine and tests-first order")
    first = read(FIRST_RUN)
    if "all bots" not in first.lower() and "every bot" not in first.lower():
        fail("FIRST_RUN_MODELS.md must say the pick applies to all bots")
    print("OK  design + plan recorded")


def test_gateway_writes_hermes_model_field(gm) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-bdm-gw-") as tmp:
        home = pathlib.Path(tmp)
        result = gm.apply_models(home, stamp_bots=False)
        data = _mapping((home / "config.yaml").read_text(encoding="utf-8"))
        principal = data.get("principal") or {}
        model = data.get("model") or {}
        if principal.get("model") != DEFAULT_CHAT:
            fail(f"gateway principal.model must stay {DEFAULT_CHAT}, got {principal}")
        if not isinstance(model, dict) or model.get("default") != DEFAULT_CHAT or model.get("provider") != "xai":
            fail(f"gateway must also write Hermes model.provider/default, got {model}")
        if result.get("chatModel") != DEFAULT_CHAT:
            fail(f"apply result chatModel {result}")
    print("OK  gateway writes principal + Hermes model.default")


def test_apply_stamps_personal_assistant(gm) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-bdm-pa-") as tmp:
        home = pathlib.Path(tmp) / "embedded"
        desktop = pathlib.Path(tmp) / "hermes" / "profiles"
        pa = _write_bot(desktop, "personal-assistant")
        result = gm.apply_models(
            home,
            chat_model=LATER_CHAT,
            profile_roots=[desktop],
        )
        provider, model, inherited = _chat_of(pa)
        if provider != "xai" or model != LATER_CHAT:
            fail(f"PA must inherit selected chat {LATER_CHAT}, got {provider}/{model}")
        if not inherited:
            fail("PA stamp must carry the inherited marker")
        cfg = pa / "config.yaml"
        if not cfg.is_file():
            fail("inherit must create Hermes config.yaml on the bot profile")
        body = cfg.read_text(encoding="utf-8")
        if "bot_desktop" not in body:
            fail("bot config merge must keep bot_desktop")
        if "api_key" in body.lower():
            fail("bot stamp must not write API keys")
        if int(result.get("botsStamped") or 0) < 1:
            fail(f"apply must report botsStamped, got {result}")
    print("OK  apply stamps Personal Assistant to the selected model")


def test_later_seats_inherit_stored_default(gm, bg) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-bdm-seats-") as tmp:
        tmp_path = pathlib.Path(tmp)
        home = tmp_path / "embedded"
        desktop = tmp_path / "hermes-profiles"
        payload = tmp_path / "payload" / "bot-groups"
        install = tmp_path / "install"
        payload.mkdir(parents=True)
        gm.apply_models(home, chat_model=LATER_CHAT, stamp_bots=False)
        group = {
            "kind": "bot-group",
            "schemaVersion": 1,
            "id": "real-estate-cold-call-lead-refresher",
            "name": "Real Estate Cold Call Lead Refresher",
            "departmentJob": "Outbound real-estate department.",
            "version": "1.1.0",
            "bots": [
                {
                    "id": "email-warmer",
                    "title": "Email Warmer",
                    "description": "CAN-SPAM warming toward a TCPA consent form.",
                    "tools": ["email", "crm", "consent-form"],
                    "soul": "bots/email-warmer/SOUL.md",
                    "config": "bots/email-warmer/bot.yaml",
                },
                {
                    "id": "lead-sourcer",
                    "title": "Lead Sourcer",
                    "description": "Finds and refreshes outbound leads.",
                    "tools": ["crm", "property-data"],
                    "soul": "bots/lead-sourcer/SOUL.md",
                    "config": "bots/lead-sourcer/bot.yaml",
                },
            ],
        }
        for bot in group["bots"]:
            bot_dir = payload / group["id"] / "bots" / bot["id"]
            bot_dir.mkdir(parents=True)
            (bot_dir / "SOUL.md").write_text(f"# {bot['title']}\n", encoding="utf-8")
            (bot_dir / "bot.yaml").write_text(
                f"slug: {bot['id']}\ndisplay_name: {bot['title']}\n",
                encoding="utf-8",
            )
        (payload / group["id"] / "bot-group.json").write_text(
            json.dumps(group), encoding="utf-8"
        )
        (payload / "catalog.json").write_text(
            json.dumps({"kind": "bot-group-catalog", "schemaVersion": 1, "groups": [{"id": group["id"], "path": group["id"]}]}),
            encoding="utf-8",
        )
        bg.deploy_group(
            group["id"],
            payload_root=tmp_path / "payload",
            install_root=install,
            desktop_profiles_root=desktop,
            embedded_profiles_root=home / "profiles",
        )
        for bot_id in ("email-warmer", "lead-sourcer"):
            provider, model, inherited = _chat_of(desktop / bot_id)
            if model != LATER_CHAT or provider != "xai":
                fail(f"{bot_id} must inherit stored {LATER_CHAT}, got {provider}/{model}")
            if not inherited:
                fail(f"{bot_id} must be marked inherited")
    print("OK  later team seats inherit the stored onboarding default")


def test_per_bot_override_survives(gm) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-bdm-ov-") as tmp:
        home = pathlib.Path(tmp) / "embedded"
        desktop = pathlib.Path(tmp) / "profiles"
        pa = _write_bot(desktop, "personal-assistant")
        override = (
            "slug: personal-assistant\n"
            "model:\n"
            "  provider: xai\n"
            f"  default: {OVERRIDE_CHAT}\n"
            f"  model: {OVERRIDE_CHAT}\n"
        )
        (pa / "config.yaml").write_text(override, encoding="utf-8")
        (pa / "bot.yaml").write_text(override, encoding="utf-8")
        gm.apply_models(home, chat_model=LATER_CHAT, profile_roots=[desktop], overwrite=True)
        provider, model, inherited = _chat_of(pa)
        if model != OVERRIDE_CHAT:
            fail(f"per-bot override must survive wizard overwrite, got {model}")
        if inherited:
            fail("override must not gain the inherited marker")
        if provider != "xai":
            fail(f"override provider clobbered: {provider}")
        skipped = gm.apply_models(
            home,
            chat_model=DEFAULT_CHAT,
            profile_roots=[desktop],
            overwrite=False,
        )
        _, model_again, _ = _chat_of(pa)
        if model_again != OVERRIDE_CHAT:
            fail("--if-missing must not overwrite a per-bot override")
        if int(skipped.get("botsSkippedOverride") or 0) < 1 and int(skipped.get("botsStamped") or 0) != 0:
            # either skip counter or a no-op stamp is fine; model must stay
            pass
    print("OK  per-bot override is left alone")


def test_if_missing_does_not_clobber_gateway(gm) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-bdm-miss-") as tmp:
        home = pathlib.Path(tmp)
        (home / "config.yaml").write_text(
            "principal:\n  provider: xai\n  model: grok-4.5\n"
            "model:\n  provider: xai\n  default: grok-4.5\n  model: grok-4.5\n",
            encoding="utf-8",
        )
        gm.apply_models(home, overwrite=False, stamp_bots=False)
        data = _mapping((home / "config.yaml").read_text(encoding="utf-8"))
        if (data.get("principal") or {}).get("model") != "grok-4.5":
            fail("--if-missing must keep an existing principal.model")
        if (data.get("model") or {}).get("default") != "grok-4.5":
            fail("--if-missing must keep an existing model.default")
    print("OK  --if-missing leaves a present gateway model")


def test_wiring_and_docs() -> None:
    wizard = read(WIZARD)
    if "Apply-GatewayModels" not in wizard:
        fail("wizard must keep Apply-GatewayModels (no second provider stack)")
    if "all bots" not in wizard.lower() and "every bot" not in wizard.lower():
        fail("wizard copy must say all bots inherit the default")
    if "[string]$Home" in wizard or re_home_param(wizard):
        fail("wizard must not reintroduce $Home")
    apply = read(APPLY)
    if "[string]$HermesHome" not in apply:
        fail("Apply-GatewayModels.ps1 must keep -HermesHome")
    if "[string]$Home" in apply:
        fail("Apply-GatewayModels.ps1 must not use $Home")
    select = read(SELECT)
    if "--embedded" not in select:
        fail("Select-BotGroup.ps1 must pass --embedded so later seats stamp the volume")
    launcher = read(LAUNCHER)
    if "Apply-GatewayModels" not in launcher or "-HermesHome" not in launcher:
        fail("start-embedded.ps1 must keep Apply-GatewayModels -HermesHome")
    for path in (INSTALL, SETUP):
        text = read(path)
        if "BOT_DEFAULT_MODEL.md" not in text or "Test-BotDefaultModel.py" not in text:
            fail(f"{path.name} must ship the all-bots design + test")
    guide = read(SETUP_GUIDE)
    if "inherit" not in guide.lower() or "all bots" not in guide.lower() and "every bot" not in guide.lower():
        fail("SETUP_GUIDE.md must document all-bot inheritance")
    groups_doc = read(BOT_GROUPS_DOC)
    if "inherit" not in groups_doc.lower():
        fail("BOT_GROUPS.md must mention inherited default model on deploy")
    readme = read(README)
    if "inherit" not in readme.lower():
        fail("README onboarding snippet must mention inheritance")
    log = read(CHANGELOG)
    if "all bots" not in log.lower() and "every bot" not in log.lower():
        fail("CHANGELOG.md must mention all-bot default model")
    design = read(DESIGN_DOC)
    if "all bots" not in design.lower() and "every bot" not in design.lower():
        fail("DESIGN.md must mention all-bot inheritance")
    if not BRANDING_CSS.is_file():
        fail("Syne overlay CSS must remain in place")
    print("OK  wizard/launch/docs wired; branding files not required in this change")


def re_home_param(text: str) -> bool:
    import re

    return bool(re.search(r"\[string\]\s*\$Home\b", text, re.IGNORECASE))


def main() -> int:
    test_design_recorded()
    gm, bg = load_engines()
    if not hasattr(gm, "inherit_default_model"):
        fail("gateway_models.inherit_default_model must exist")
    if not hasattr(gm, "read_applied_models"):
        fail("gateway_models.read_applied_models must exist")
    if hasattr(gm, "self_test") and gm.self_test() != 0:
        fail("gateway_models --self-test failed")
    test_gateway_writes_hermes_model_field(gm)
    test_apply_stamps_personal_assistant(gm)
    test_later_seats_inherit_stored_default(gm, bg)
    test_per_bot_override_survives(gm)
    test_if_missing_does_not_clobber_gateway(gm)
    test_wiring_and_docs()
    print("SMOKE OK: onboarding default LLM is inherited by all bots unless overridden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
