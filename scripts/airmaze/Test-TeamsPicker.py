#!/usr/bin/env python3
"""Tests first: in-app Teams picker (catalog + one-click apply + import).

James (2026-10-01): pick a team from the Dragon AI UI, not only Import-Profile.ps1.
Applied bots file under the pack displayName, not UNASSIGNED.
No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
ENGINE = SCRIPTS / "teams_picker.py"
CATALOG = ROOT / "bot-groups" / "catalog.json"
BRANDING_PY = SCRIPTS / "desktop_branding.py"
CSS = ROOT / "branding" / "fonts" / "syne" / "dragon-ui.css"
LAUNCHER = SCRIPTS / "start-embedded.ps1"
WIZARD = SCRIPTS / "Onboard-Wizard.ps1"
SELECT = SCRIPTS / "Select-BotGroup.ps1"
INSTALL = SCRIPTS / "install.ps1"
SETUP = ROOT / "installer" / "DragonAIAgentSetup.ps1"
PRODUCT = ROOT / "docs" / "airmaze" / "PRODUCT_BRANDING.md"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def load_engine():
    if not ENGINE.is_file():
        fail("teams_picker.py must exist")
    sys.path.insert(0, str(SCRIPTS))
    import teams_picker as tp  # noqa: WPS433

    return tp


def test_catalog_has_teams() -> None:
    catalog = json.loads(read(CATALOG))
    ids = [g.get("id") for g in catalog.get("groups") or []]
    names = [str(g.get("displayName") or g.get("name") or "") for g in catalog.get("groups") or []]
    for required in ("personal-assistant", "real-estate-cold-call-lead-refresher", "marketing-team", "trading-team"):
        if required not in ids:
            fail(f"catalog must include {required}")
    for label in ("Real Estate Lead Gen", "Marketing Team", "Trading Team"):
        if label not in names:
            fail(f"catalog must show {label!r}")
    pa = next((g for g in catalog.get("groups") or [] if g.get("id") == "personal-assistant"), None)
    if pa is None or pa.get("picker") is not False:
        fail("catalog must keep Personal Assistant as the default profile (picker: false), not a team")
    if any("hermes" in str(x).lower() for x in ids + names):
        fail("catalog must not add a Hermes team")
    print("OK  catalog lists PA + Real Estate Lead Gen + Marketing + Trading")


def test_apply_files_named_section(tp) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-teams-") as tmp:
        tmp_path = pathlib.Path(tmp)
        install = tmp_path / "install"
        desktop = tmp_path / "profiles"
        class Offline:
            def get_text(self, url: str) -> str:
                raise tp.bg.GitHubUnreachable("offline")

        listed = tp.list_teams(ROOT, install, fetcher=Offline())
        labels = [t.get("displayName") for t in listed.get("teams") or []]
        ids = [t.get("id") for t in listed.get("teams") or []]
        for label in ("Real Estate Lead Gen", "Marketing Team", "Trading Team"):
            if label not in labels:
                fail(f"list_teams missing {label!r}: {labels}")
        if "Personal Assistant" in labels or "personal-assistant" in ids:
            fail("Teams picker must not list Personal Assistant")
        marketing_ids = [
            "content-strategist",
            "seo-specialist",
            "social-media-manager",
            "paid-media-specialist",
            "lifecycle-marketer",
            "marketing-analyst",
        ]
        result = tp.apply_team(
            "marketing-team",
            payload_root=ROOT,
            install_root=install,
            desktop_profiles_root=desktop,
        )
        if result.get("displayName") != "Marketing Team":
            fail(f"apply must report Marketing Team, got {result.get('displayName')}")
        applied = [b.get("id") for b in result.get("bots") or []]
        if applied != marketing_ids:
            fail(f"apply Marketing Team must deploy all 6 Cos bots, got {applied}")
        if (desktop / "copywriter").exists() or (desktop / "campaign-sequencer").exists():
            fail("apply must not leave Copywriter / Campaign Sequencer in MARKETING TEAM")
        profile = (desktop / "content-strategist" / "profile.yaml").read_text(encoding="utf-8")
        if "sec-dragon-marketing-team" not in profile or "Marketing Team" not in profile:
            fail("one-click apply must file bots under Marketing Team, not UNASSIGNED")
        if "section:unassigned" in profile.lower():
            fail("applied Marketing Team bots must not be Unassigned")
        roster_cases = (
            (
                "real-estate-cold-call-lead-refresher",
                [
                    "lead-sourcer",
                    "email-warmer",
                    "cold-call-script-writer",
                    "follow-up-sequencer",
                ],
                "Real Estate Lead Gen",
            ),
            (
                "trading-team",
                ["market-researcher", "trade-journal", "risk-analyst", "news-scanner"],
                "Trading Team",
            ),
        )
        for team_id, expected, label in roster_cases:
            pack = tp.apply_team(
                team_id,
                payload_root=ROOT,
                install_root=tmp_path / f"install-{team_id}",
                desktop_profiles_root=tmp_path / f"desktop-{team_id}",
            )
            ids = [b.get("id") for b in pack.get("bots") or []]
            if ids != expected:
                fail(f"apply {label} must deploy {expected}, got {ids}")
            first = (tmp_path / f"desktop-{team_id}" / expected[0] / "profile.yaml").read_text(encoding="utf-8")
            if label not in first:
                fail(f"apply {label} must file bots under that section")
        try:
            tp.apply_team(
                "personal-assistant",
                payload_root=ROOT,
                install_root=install,
                desktop_profiles_root=desktop,
            )
            fail("Teams apply must refuse Personal Assistant")
        except ValueError:
            pass
        imported = tmp_path / "from-file"
        again = tp.import_team_file(
            ROOT / "bot-groups" / "trading-team",
            payload_root=ROOT,
            install_root=tmp_path / "install2",
            desktop_profiles_root=imported,
        )
        if again.get("displayName") != "Trading Team":
            fail("import-from-file must keep Trading Team as the section name")
        tprofile = (imported / "market-researcher" / "profile.yaml").read_text(encoding="utf-8")
        if "Trading Team" not in tprofile:
            fail("imported custom/catalog zip path must stamp Trading Team")
    print("OK  apply/import file bots into the team displayName")


def test_overlay_and_launch_wired() -> None:
    branding = read(BRANDING_PY)
    picker_js = read(ROOT / "branding" / "fonts" / "syne" / "teams-picker.js")
    if "teams-picker" not in branding and "dragon-ai-teams" not in branding:
        fail("desktop overlay must inject the Teams picker into the desktop client")
    if "Personal Assistant is already installed" not in picker_js:
        fail("Teams dialog must say Personal Assistant is already installed")
    if "Teams Marketplace" not in picker_js:
        fail("user-visible control label must be Teams Marketplace")
    if 'textContent = "Teams"' in picker_js or 'textContent="Teams"' in picker_js:
        fail("sidebar control must not be labeled Teams (use Teams Marketplace)")
    if "findColumnHost" not in picker_js or "data-dragon-ai-sidebar-fixed" not in picker_js:
        fail("Teams Marketplace must try column hosts then the body fixed overlay")
    if "findSessionsBotsStrip" not in picker_js:
        fail("fixed overlay must sit below Sessions / Bots so those tabs stay clickable")
    if 'data-slot="sidebar-wrapper"' in picker_js:
        fail("Teams Marketplace must not treat sidebar-wrapper as a column host")
    if "finishApply" not in picker_js or "location.reload" not in picker_js:
        fail("after apply the Teams dialog must close and reload the bot roster")
    css = read(CSS)
    if "[data-dragon-ai-teams-panel]" not in css or "Teams" not in css:
        fail("dragon-ui.css must style the in-app Teams screen")
    if "--dragon-ui-font-size-body: 16px" not in css:
        fail("Teams overlay must share the 16px Grok Bot body size")
    if "font-size: var(--dragon-ui-font-size-body)" not in css:
        fail("Teams list rows must use the 16px body token, not 0.8125rem")
    if "font-size: 0.8125rem" in css:
        fail("Teams picker CSS must not keep Hermes 13px captions")
    launcher = read(LAUNCHER)
    if "teams_picker" not in launcher:
        fail("start-embedded.ps1 must start the Teams picker helper")
    if "8653" not in launcher:
        fail("Teams helper must use loopback :8653 (not Bot Screen :8650)")
    if "content-strategist" not in launcher:
        fail("Teams helper must prefer the Cos Marketing pack over a stale InstallRoot stub")
    wizard = read(WIZARD)
    if "Teams" not in wizard:
        fail("first-run wizard must offer Teams selection")
    select = read(SELECT)
    if "Teams" not in select:
        fail("Select-BotGroup must present Teams (not a hidden PowerShell-only path)")
    if "Import file" not in select:
        fail("Teams UI must still support Import from file")
    if "ComboBox" not in select:
        fail("dropdown path must stay (WinForms ComboBox)")
    if 'id -ne "personal-assistant"' not in select:
        fail("Select-BotGroup Teams list must drop Personal Assistant")
    if "already installed" not in select:
        fail("Teams UI must say Personal Assistant is already installed")
    default_apply = read(SCRIPTS / "apply-default-bot-group.ps1")
    if "personal-assistant" not in default_apply:
        fail("default deploy must ship Personal Assistant only")
    if "marketing-team" in default_apply or "trading-team" in default_apply:
        fail("default deploy must not apply Marketing or Trading")
    for path in (INSTALL, SETUP):
        text = read(path)
        if "teams_picker.py" not in text:
            fail(f"{path.name} must install teams_picker.py")
    product = read(PRODUCT)
    if "Teams Marketplace" not in product or "8653" not in product:
        fail("PRODUCT_BRANDING.md must describe the in-app Teams Marketplace picker")
    host_note = ROOT / "docs" / "airmaze" / "SIDEBAR_HOST.md"
    if not host_note.is_file() or "data-dragon-ai-sidebar-fixed" not in read(host_note):
        fail("SIDEBAR_HOST.md must describe the body fixed-overlay fallback")
    css = read(CSS)
    if "@media (max-width: 1100px)" not in css:
        fail("dragon-ui.css must wrap the overlay Marketplace control at max-width 1100px")
    print("OK  Teams picker wired into overlay, first-run, and launch")


def main() -> int:
    test_catalog_has_teams()
    tp = load_engine()
    if tp.self_test() != 0:
        fail("teams_picker --self-test failed")
    test_apply_files_named_section(tp)
    test_overlay_and_launch_wired()
    print("SMOKE OK: in-app Teams picker lists catalog teams; apply files a named group; import from file stays.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
