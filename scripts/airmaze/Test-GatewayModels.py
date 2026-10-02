#!/usr/bin/env python3
"""Tests first: first-run default chat LLM + image LLM.

James: wizard pickers write Hermes gateway config so chat and
profile Generate work without hand-editing YAML.
No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
ENGINE = SCRIPTS / "gateway_models.py"
APPLY = SCRIPTS / "Apply-GatewayModels.ps1"
WIZARD = SCRIPTS / "Onboard-Wizard.ps1"
ONBOARD_WIZARD_TEST = SCRIPTS / "Test-OnboardWizard.py"
LAUNCHER = SCRIPTS / "start-embedded.ps1"
INSTALL = SCRIPTS / "install.ps1"
SETUP = ROOT / "installer" / "DragonAIAgentSetup.ps1"
DESIGN = ROOT / "docs" / "airmaze" / "FIRST_RUN_MODELS.md"
PLAN = ROOT / "docs" / "airmaze" / "FIRST_RUN_MODELS_PLAN.md"
SETUP_GUIDE = ROOT / "docs" / "airmaze" / "SETUP_GUIDE.md"
README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"

DEFAULT_CHAT = "grok-4.6"
DEFAULT_IMAGE = "grok-imagine-image"
CHAT_CHOICES = ("grok-4.6", "grok-4.5", "grok-4.3")
CLOUD_CHAT_IDS = ("gpt-4o", "claude-sonnet-4-6", "gemini-2.5-pro", "openrouter-gpt-4o")
CLOUD_PROVIDERS = ("xai", "openai-api", "anthropic", "gemini", "openrouter")
IMAGE_CHOICES = ("grok-imagine-image", "grok-imagine-image-quality", "grok-imagine-image-2.0")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def load_engine():
    if not ENGINE.is_file():
        fail("gateway_models.py must exist")
    sys.path.insert(0, str(SCRIPTS))
    import gateway_models as gm  # noqa: WPS433

    return gm


def _mapping(text: str) -> dict:
    """Tiny indent parser for the keys this feature writes."""
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


def test_design_recorded() -> None:
    design = read(DESIGN)
    for needle in (
        "principal.provider",
        "image_gen.provider",
        "grok-imagine-image",
        "grok-4.6",
        "Onboard-Wizard",
        "XAI_API_KEY",
        "Dragon AI Agent",
        "self-hosted",
        "openai-api",
        "anthropic",
        "gemini",
    ):
        if needle not in design:
            fail(f"FIRST_RUN_MODELS.md must document {needle!r}")
    plan = read(PLAN)
    if "gateway_models.py" not in plan or "Tests first" not in plan:
        fail("FIRST_RUN_MODELS_PLAN.md must name the engine and tests-first order")
    print("OK  design + plan recorded")


def test_defaults_and_apply(gm) -> None:
    if gm.DEFAULT_CHAT_MODEL != DEFAULT_CHAT:
        fail(f"product chat default must be {DEFAULT_CHAT}, got {gm.DEFAULT_CHAT_MODEL}")
    if gm.DEFAULT_IMAGE_MODEL != DEFAULT_IMAGE:
        fail(f"product image default must be {DEFAULT_IMAGE}, got {gm.DEFAULT_IMAGE_MODEL}")
    chat_ids = [c["id"] for c in gm.chat_catalog()]
    image_ids = [c["id"] for c in gm.image_catalog()]
    for mid in CHAT_CHOICES:
        if mid not in chat_ids:
            fail(f"chat catalog missing {mid}")
    for mid in IMAGE_CHOICES:
        if mid not in image_ids:
            fail(f"image catalog missing {mid}")
    for mid in CLOUD_CHAT_IDS:
        if mid not in chat_ids:
            fail(f"chat catalog missing popular cloud option {mid}")
    if "self-hosted" not in chat_ids:
        fail("chat catalog must include a self-hosted / custom endpoint option")
    if chat_ids[0] != DEFAULT_CHAT:
        fail(f"Grok {DEFAULT_CHAT} must stay the first/suggested chat catalog entry")
    providers = {c["provider"] for c in gm.chat_catalog()}
    for pid in CLOUD_PROVIDERS:
        if pid not in providers:
            fail(f"chat catalog missing provider {pid}")
    if "custom" not in providers:
        fail("chat catalog must include Hermes provider custom for self-hosted")
    if hasattr(gm, "popular_cloud_providers"):
        got = set(gm.popular_cloud_providers())
        if not set(CLOUD_PROVIDERS).issubset(got):
            fail(f"popular_cloud_providers missing {set(CLOUD_PROVIDERS) - got}")
    with tempfile.TemporaryDirectory(prefix="dragon-models-") as tmp:
        home = pathlib.Path(tmp) / "embedded"
        home.mkdir()
        result = gm.apply_models(home)
        cfg = home / "config.yaml"
        if not cfg.is_file():
            fail("apply must write config.yaml")
        data = _mapping(cfg.read_text(encoding="utf-8"))
        principal = data.get("principal") or {}
        image = data.get("image_gen") or {}
        if principal.get("provider") != "xai" or principal.get("model") != DEFAULT_CHAT:
            fail(f"defaults must write principal xai/{DEFAULT_CHAT}, got {principal}")
        if image.get("provider") != "xai":
            fail(f"image_gen.provider must be xai, got {image}")
        if image.get("model") != DEFAULT_IMAGE:
            fail(f"image_gen.model must be {DEFAULT_IMAGE}, got {image}")
        nested = image.get("xai") or {}
        if nested.get("model") != DEFAULT_IMAGE:
            fail(f"image_gen.xai.model must be {DEFAULT_IMAGE}, got {nested}")
        written = cfg.read_text(encoding="utf-8").lower()
        if "api_key" in written or "xai_api_key" in written:
            fail("apply must not write API keys into config.yaml")
        if result.get("chatModel") != DEFAULT_CHAT or result.get("imageModel") != DEFAULT_IMAGE:
            fail(f"apply result must report selected models, got {result}")
    print("OK  defaults write principal + image_gen Grok Imagine shape")


def json_ish(value) -> str:
    return str(value).lower()


def test_quality_variant_and_merge(gm) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-models-merge-") as tmp:
        home = pathlib.Path(tmp)
        existing = home / "config.yaml"
        existing.write_text(
            "bot_desktop:\n  geometry: \"1440x900\"\n  auto_start: true\n\nprincipal:\n  provider: openai\n  model: gpt-4o\n",
            encoding="utf-8",
        )
        skipped = gm.apply_models(home, overwrite=False)
        kept = _mapping(existing.read_text(encoding="utf-8"))
        if (kept.get("principal") or {}).get("model") != "gpt-4o":
            fail("--if-missing must not overwrite an existing principal.model")
        if (kept.get("image_gen") or {}).get("provider") != "xai":
            fail("--if-missing must still fill a missing image_gen block")
        if skipped.get("wrote") is not True:
            fail("if-missing should write when image_gen is absent")
        noop = gm.apply_models(home, overwrite=False)
        if noop.get("wrote") is True:
            fail("if-missing on a complete config must not write again")
        gm.apply_models(
            home,
            chat_model="grok-4.3",
            image_model="grok-imagine-image-quality",
            overwrite=True,
        )
        data = _mapping(existing.read_text(encoding="utf-8"))
        if (data.get("bot_desktop") or {}).get("geometry") != "1440x900":
            fail("merge must keep bot_desktop")
        if (data.get("principal") or {}).get("model") != "grok-4.3":
            fail("overwrite must set selected chat model")
        image = data.get("image_gen") or {}
        if image.get("model") != "grok-imagine-image-quality":
            fail("overwrite must set Grok Imagine quality variant")
        if (image.get("xai") or {}).get("model") != "grok-imagine-image-quality":
            fail("image_gen.xai.model must match the selected Imagine variant")
        gm.apply_models(home, image_model="grok-imagine-image-2.0", overwrite=True)
        again = _mapping(existing.read_text(encoding="utf-8"))
        if (again.get("image_gen") or {}).get("model") != "grok-imagine-image-2.0":
            fail("must persist grok-imagine-image-2.0")
    print("OK  quality variants + merge preserve unrelated keys")


def test_cloud_and_self_hosted(gm) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-models-cloud-") as tmp:
        home = pathlib.Path(tmp)
        gm.apply_models(home, chat_model="gpt-4o", overwrite=True)
        data = _mapping((home / "config.yaml").read_text(encoding="utf-8"))
        principal = data.get("principal") or {}
        hermes_model = data.get("model") or {}
        if principal.get("provider") != "openai-api" or principal.get("model") != "gpt-4o":
            fail(f"OpenAI pick must write principal openai-api/gpt-4o, got {principal}")
        if hermes_model.get("provider") != "openai-api" or hermes_model.get("default") != "gpt-4o":
            fail(f"OpenAI pick must also write Hermes model.provider openai-api, got {hermes_model}")
        gm.apply_models(
            home,
            chat_model="self-hosted",
            custom_model="llama3.1",
            base_url="http://127.0.0.1:11434/v1",
            overwrite=True,
        )
        text = (home / "config.yaml").read_text(encoding="utf-8")
        again = _mapping(text)
        principal = again.get("principal") or {}
        if principal.get("provider") != "custom" or principal.get("model") != "llama3.1":
            fail(f"self-hosted must write principal custom/llama3.1, got {principal}")
        if "11434" not in str(principal.get("base_url") or ""):
            fail(f"self-hosted must persist base_url, got {principal}")
        if re_search_key(text):
            fail("self-hosted apply must not write api_key into config.yaml")
        image = again.get("image_gen") or {}
        if image.get("model") != DEFAULT_IMAGE:
            fail("self-hosted chat must keep Grok Imagine as the image default")
    print("OK  cloud + self-hosted catalog writes (no secrets in YAML)")


def re_search_key(text: str) -> bool:
    low = text.lower()
    return "api_key:" in low or "xai_api_key:" in low or "openai_api_key:" in low


def test_wizard_and_launch_wired() -> None:
    wizard = read(WIZARD)
    if '"models"' not in wizard and "'models'" not in wizard:
        fail("wizard resume order must include a models step")
    if "welcome" not in wizard or "email" not in wizard:
        fail("existing onboarding steps must stay")
    if "Default chat LLM" not in wizard or "Default image LLM" not in wizard:
        fail("wizard must show both model pickers")
    if "Grok Imagine" not in wizard or "grok-imagine-image" not in wizard:
        fail("wizard must surface Grok Imagine")
    if "Grok (xAI)" not in wizard and "xAI Grok" not in wizard:
        fail("wizard must label the chat default as Grok / xAI")
    for needle in ("OpenAI", "Anthropic", "Google Gemini", "Self-hosted / custom endpoint"):
        if needle not in wizard:
            fail(f"wizard chat picker must offer {needle}")
    if "function Get-WizardChatCatalog" not in wizard:
        fail("wizard must share a chat catalog (cloud + self-hosted)")
    if "Hermes Agent" in wizard:
        fail("wizard copy must say Dragon AI Agent, not Hermes Agent")
    if "XAI_API_KEY" not in wizard:
        fail("wizard must say it reuses xAI OAuth / XAI_API_KEY")
    if "Apply-GatewayModels" not in wizard and "gateway_models.py" not in wizard:
        fail("wizard must persist choices through the gateway_models engine")
    if "Set-WizardControlText" not in wizard or "Format-WizardStatusLine" not in wizard:
        fail("wizard must guard Text assignment and format a short Welcome/Models status line")
    if "Teams Marketplace" not in wizard:
        fail("Teams Marketplace path must stay on the welcome step")
    apply = read(APPLY)
    if "gateway_models.py" not in apply:
        fail("Apply-GatewayModels.ps1 must call gateway_models.py")
    if "[string]$HermesHome" not in apply:
        fail("Apply-GatewayModels.ps1 must take -HermesHome (not -Home; $HOME is read-only)")
    if "[string]$BaseUrl" not in apply or "[string]$CustomModel" not in apply:
        fail("Apply-GatewayModels.ps1 must pass self-hosted --base-url / --custom-model")
    launcher = read(LAUNCHER)
    if "gateway_models" not in launcher and "Apply-GatewayModels" not in launcher:
        fail("start-embedded.ps1 must apply model defaults before compose up")
    if "-HermesHome" not in launcher:
        fail("start-embedded.ps1 must pass -HermesHome to Apply-GatewayModels.ps1")
    for path in (INSTALL, SETUP):
        text = read(path)
        if "gateway_models.py" not in text:
            fail(f"{path.name} must install gateway_models.py")
        if "Apply-GatewayModels.ps1" not in text:
            fail(f"{path.name} must install Apply-GatewayModels.ps1")
    guide = read(SETUP_GUIDE)
    if "Default chat LLM" not in guide or "Grok Imagine" not in guide:
        fail("SETUP_GUIDE.md must document the Models step")
    readme = read(README)
    if "image LLM" not in readme.lower() and "Grok Imagine" not in readme:
        fail("README onboarding snippet must mention image LLM / Grok Imagine")
    log = read(CHANGELOG)
    if "Grok Imagine" not in log:
        fail("CHANGELOG.md must mention first-run Grok Imagine")
    print("OK  wizard pickers + launch/install + docs wired")


def main() -> int:
    test_design_recorded()
    gm = load_engine()
    if hasattr(gm, "self_test") and gm.self_test() != 0:
        fail("gateway_models --self-test failed")
    test_defaults_and_apply(gm)
    test_quality_variant_and_merge(gm)
    test_cloud_and_self_hosted(gm)
    test_wizard_and_launch_wired()
    if ONBOARD_WIZARD_TEST.is_file():
        proc = subprocess.run([sys.executable, str(ONBOARD_WIZARD_TEST)], cwd=str(ROOT))
        if proc.returncode != 0:
            fail("Test-OnboardWizard.py failed")
    print("SMOKE OK: first-run writes Grok + Grok Imagine into Hermes gateway config.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
