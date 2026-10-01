#!/usr/bin/env python3
"""Offline tests: Dragon AI Agent excludes the Hermes bot (does not hide-only).

James (2026-10-01): no Hermes bot in BOTS. Purge leftover profiles so they
do not come back. Do not seed default/hermes. Personal Assistant stays.
No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
ENGINE = SCRIPTS / "exclude_hermes_bot.py"
TABLE = SCRIPTS / "desktop_branding.json"
LAUNCHER = SCRIPTS / "start-embedded.ps1"
FINDER = SCRIPTS / "Find-HermesDesktop.ps1"
INSTALL = SCRIPTS / "install.ps1"
SETUP = ROOT / "installer" / "DragonAIAgentSetup.ps1"
BOT_GROUPS = SCRIPTS / "bot_groups.py"
BRANDING = ROOT / "docs" / "airmaze" / "BRANDING.md"
DESIGN = ROOT / "docs" / "airmaze" / "DESIGN.md"
PRODUCT = ROOT / "docs" / "airmaze" / "PRODUCT_BRANDING.md"
PLAN = ROOT / "docs" / "airmaze" / "PRODUCT_BRANDING_PLAN.md"
CATALOG = ROOT / "bot-groups" / "catalog.json"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def load_engine():
    sys.path.insert(0, str(SCRIPTS))
    import exclude_hermes_bot as eh  # noqa: WPS433

    return eh


def test_docs_and_table() -> None:
    if not ENGINE.is_file():
        fail("exclude_hermes_bot.py must exist")
    table = json.loads(read(TABLE))
    sidebar = table.get("sidebar") or {}
    if sidebar.get("excludeHermes") is not True:
        fail("desktop_branding.json must exclude Hermes (not hide-only)")
    ids = {str(x).lower() for x in (sidebar.get("excludedProfileIds") or [])}
    if "default" not in ids or "hermes" not in ids:
        fail("table must list excluded profile ids default and hermes")
    if sidebar.get("userFacingBots") != ["Personal Assistant"]:
        fail("table sidebar must list only Personal Assistant")
    product = read(PRODUCT)
    if "exclude" not in product.lower() or "Dragon AI" not in product:
        fail("PRODUCT_BRANDING.md must agree exclude + sidebar name")
    if "profiles\\hermes" not in product and "profiles/hermes" not in product:
        fail("PRODUCT_BRANDING.md must name the leftover profiles path")
    if not PLAN.is_file():
        fail("PRODUCT_BRANDING_PLAN.md missing")
    branding = read(BRANDING)
    if "exclude" not in branding.lower() and "drop" not in branding.lower():
        fail("BRANDING.md must say Hermes is excluded from BOTS, not only hidden")
    design = read(DESIGN)
    if "exclude" not in design.lower() and "removed" not in design.lower() and "drop" not in design.lower():
        fail("DESIGN.md must say the Hermes bot is excluded, not only hidden")
    catalog = json.loads(read(CATALOG))
    for g in catalog.get("groups") or []:
        if str(g.get("id") or "").lower() in {"hermes", "default"}:
            fail("catalog must not ship a Hermes/default group")
        if "hermes" in str(g.get("name") or "").lower():
            fail("catalog must not ship a Hermes-named group")
    print("OK  exclude-Hermes docs + table")


def test_classifier(eh) -> None:
    if not eh.is_excluded_profile("default"):
        fail("id default must be excluded")
    if not eh.is_excluded_profile("Hermes"):
        fail("id hermes must be excluded")
    if not eh.is_excluded_profile("  DEFAULT  "):
        fail("id default must match case-insensitively")
    if eh.is_excluded_profile("personal-assistant"):
        fail("Personal Assistant must not be excluded")
    if eh.is_excluded_profile("email-warmer"):
        fail("catalog bots must not be excluded")
    if not eh.is_excluded_profile("custom", title="Hermes"):
        fail("display title Hermes must be excluded")
    if not eh.is_excluded_profile("custom", meta={"title": "Hermes Agent"}):
        fail("meta title Hermes Agent must be excluded")
    if eh.is_excluded_profile("personal-assistant", title="Personal Assistant"):
        fail("Personal Assistant title must stay")
    print("OK  exclude classifier")


def test_purge_keeps_pa(eh) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-ex-hermes-") as tmp:
        root = pathlib.Path(tmp)
        desktop = root / "hermes" / "profiles"
        embedded = root / ".hermes-airmaze-embedded" / "profiles"
        for base in (desktop, embedded):
            (base / "default").mkdir(parents=True)
            (base / "default" / "SOUL.md").write_text("stock default\n", encoding="utf-8")
            (base / "hermes").mkdir(parents=True)
            (base / "hermes" / "bot.meta.json").write_text(
                json.dumps({"title": "Hermes"}), encoding="utf-8"
            )
            (base / "personal-assistant").mkdir(parents=True)
            (base / "personal-assistant" / "SOUL.md").write_text("PA\n", encoding="utf-8")
            (base / "email-warmer").mkdir(parents=True)
            (base / "email-warmer" / "SOUL.md").write_text("EW\n", encoding="utf-8")
        summary = eh.purge_hermes_profiles([desktop, embedded])
        removed = {pathlib.Path(p).name for p in summary.get("removed") or []}
        if "default" not in removed or "hermes" not in removed:
            fail(f"purge must remove default and hermes, got {summary}")
        if (desktop / "default").exists() or (desktop / "hermes").exists():
            fail("desktop leftover Hermes folders still present")
        if (embedded / "default").exists() or (embedded / "hermes").exists():
            fail("embedded leftover Hermes folders still present")
        if not (desktop / "personal-assistant" / "SOUL.md").is_file():
            fail("purge deleted Personal Assistant")
        if not (desktop / "email-warmer" / "SOUL.md").is_file():
            fail("purge deleted a catalog bot")
        again = eh.purge_hermes_profiles([desktop, embedded])
        if again.get("removed"):
            fail(f"second purge must be idempotent, got {again}")
    print("OK  purge default/hermes; keep PA")


def test_deploy_refuses_hermes(eh) -> None:
    sys.path.insert(0, str(SCRIPTS))
    import bot_groups as bg  # noqa: WPS433

    with tempfile.TemporaryDirectory(prefix="dragon-ex-deploy-") as tmp:
        root = pathlib.Path(tmp)
        payload = root / "payload"
        group = payload / "bot-groups" / "evil"
        (group / "bots" / "hermes").mkdir(parents=True)
        (group / "bots" / "hermes" / "SOUL.md").write_text("no\n", encoding="utf-8")
        (group / "bot-group.json").write_text(
            json.dumps(
                {
                    "kind": "bot-group",
                    "schemaVersion": 1,
                    "id": "evil",
                    "name": "Evil",
                    "departmentJob": "no",
                    "bots": [{"id": "hermes", "title": "Hermes", "description": "", "tools": [], "soul": "bots/hermes/SOUL.md"}],
                }
            ),
            encoding="utf-8",
        )
        desktop = root / "profiles"
        result = bg.deploy_group(
            "evil",
            payload_root=payload,
            install_root=root / "install",
            desktop_profiles_root=desktop,
        )
        if (desktop / "hermes").exists():
            fail("deploy must not create a hermes profile folder")
        skipped = result.get("skipped") or []
        if "hermes" not in skipped:
            fail(f"deploy must report skipped hermes, got {result}")
    print("OK  deploy refuses hermes id")


def test_launch_and_install_wired() -> None:
    launcher = read(LAUNCHER)
    finder = read(FINDER)
    install = read(INSTALL)
    setup = read(SETUP)
    engine = read(BOT_GROUPS)
    for text, name in (
        (launcher, "start-embedded.ps1"),
        (finder, "Find-HermesDesktop.ps1"),
        (install, "install.ps1"),
    ):
        if "Exclude-DragonAIHermesBots" not in text and "exclude_hermes_bot" not in text:
            fail(f"{name} must run the Hermes exclude/purge before the client lists bots")
    if "exclude_hermes_bot" not in engine:
        fail("bot_groups.py must consult the Hermes exclude list")
    if "exclude_hermes_bot.py" not in install or "exclude_hermes_bot.py" not in setup:
        fail("installers must copy exclude_hermes_bot.py")
    if "Sync-EmbeddedGatewayProfiles" in launcher:
        if "exclude" not in launcher.lower() and "hermes" not in launcher.lower():
            fail("profile sync must not copy excluded Hermes folders back")
    print("OK  launch/install/sync wired to exclude Hermes")


def main() -> int:
    test_docs_and_table()
    eh = load_engine()
    if hasattr(eh, "self_test") and eh.self_test() != 0:
        fail("exclude_hermes_bot --self-test failed")
    test_classifier(eh)
    test_purge_keeps_pa(eh)
    test_deploy_refuses_hermes(eh)
    test_launch_and_install_wired()
    print("SMOKE OK: Hermes bot excluded from product; leftover profiles purged; PA stays.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
