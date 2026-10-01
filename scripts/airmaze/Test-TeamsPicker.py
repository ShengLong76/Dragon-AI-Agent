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


def test_launch_many_named_sections(tp) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-teams-multi-") as tmp:
        tmp_path = pathlib.Path(tmp)
        desktop = tmp_path / "profiles"
        batch = tp.apply_teams(
            ["marketing-team", "trading-team"],
            payload_root=ROOT,
            install_root=tmp_path / "install",
            desktop_profiles_root=desktop,
        )
        ids = [a.get("id") for a in batch.get("applied") or []]
        if ids != ["marketing-team", "trading-team"]:
            fail(f"Launch must apply each selected team in order, got {ids}")
        marketing = (desktop / "content-strategist" / "profile.yaml").read_text(encoding="utf-8")
        trading = (desktop / "market-researcher" / "profile.yaml").read_text(encoding="utf-8")
        if "Marketing Team" not in marketing or "Trading Team" not in trading:
            fail("Launch must file each roster into its own named section")
        if "Trading Team" in marketing or "Marketing Team" in trading:
            fail("Launch must not merge Marketing and Trading into one section")
        try:
            tp.apply_teams(
                ["personal-assistant", "marketing-team"],
                payload_root=ROOT,
                install_root=tmp_path / "install-pa",
                desktop_profiles_root=tmp_path / "desktop-pa",
            )
            fail("Launch must refuse a batch that includes Personal Assistant")
        except ValueError:
            pass
        dest = tmp_path / "export" / "marketing-team.zip"
        exported = pathlib.Path(
            tp.export_teams(
                ["marketing-team"],
                dest,
                payload_root=ROOT,
                install_root=tmp_path / "install-export",
            )
        )
        if exported.suffix != ".zip" or not exported.is_file():
            fail("export must write a zip in repo group format")
        imported = tmp_path / "from-export"
        again = tp.import_team_file(
            exported,
            payload_root=ROOT,
            install_root=tmp_path / "install-reimport",
            desktop_profiles_root=imported,
        )
        if again.get("displayName") != "Marketing Team":
            fail("exported zip must re-import as Marketing Team")
        if not (imported / "content-strategist" / "SOUL.md").is_file():
            fail("exported zip must include Cos Marketing bots")
        bundle = pathlib.Path(
            tp.export_teams(
                ["marketing-team", "trading-team"],
                tmp_path / "export" / "dragon-teams.zip",
                payload_root=ROOT,
                install_root=tmp_path / "install-bundle",
            )
        )
        if not bundle.is_file():
            fail("multi-team export must write a zip")
    print("OK  Launch applies each team into its named section; export re-imports")


def test_overlay_and_launch_wired() -> None:
    branding = read(BRANDING_PY)
    if "teams-picker" not in branding and "dragon-ai-teams" not in branding:
        fail("desktop overlay must inject the Teams picker into the desktop client")
    if "Personal Assistant is already installed" not in branding:
        fail("Teams dialog must say Personal Assistant is already installed")
    if "finishApply" not in branding or "location.reload" not in branding:
        fail("after apply the Teams dialog must close and reload the bot roster")
    if "type=\"checkbox\"" not in branding and 'type="checkbox"' not in branding:
        fail("Teams popup must list each team with a checkbox")
    if "data-dragon-ai-teams-launch" not in branding or "Launch" not in branding:
        fail("Teams popup must have a Launch button for the checked teams")
    if "data-dragon-ai-teams-export" not in branding or "/api/teams/export" not in branding:
        fail("Teams popup must expose Export against the helper")
    if "data-dragon-ai-teams-import" not in branding:
        fail("Teams popup must keep Import next to Export")
    if "<select" in branding or "ComboBox" in branding:
        fail("in-app Teams control must be a popup, not a dropdown")
    css = read(CSS)
    if "[data-dragon-ai-teams-panel]" not in css or "Teams" not in css:
        fail("dragon-ui.css must style the in-app Teams screen")
    if "min(44rem" not in css and "min(42rem" not in css:
        fail("Teams popup must be roomier than the old 28rem dropdown panel")
    if "[data-dragon-ai-teams-backdrop]" not in css:
        fail("Teams popup must use a backdrop, not a tight dropdown")
    if 'input[type="checkbox"]' not in css and "checkbox" not in css:
        fail("overlay CSS must style Teams checkboxes")
    helper = read(ENGINE)
    if "/api/teams/export" not in helper:
        fail("teams helper must serve POST /api/teams/export")
    if "apply_teams" not in helper or "export_teams" not in helper:
        fail("teams helper must apply/export multiple selected teams")
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
    if "Export" not in select:
        fail("Teams UI must keep Export next to Import")
    if "Launch" not in select:
        fail("WinForms Teams popup must Launch the checked teams")
    if "CheckedListBox" not in select:
        fail("WinForms Teams control must be a popup list (CheckedListBox), not a dropdown")
    if "ComboBox" in select:
        fail("WinForms Teams control must not stay a ComboBox dropdown")
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
    if "Teams" not in product or "8653" not in product:
        fail("PRODUCT_BRANDING.md must describe the in-app Teams picker")
    design = read(ROOT / "docs" / "airmaze" / "TEAMS_POPUP.md")
    if "own named section" not in design and "own named BOTS section" not in design:
        fail("TEAMS_POPUP.md must document applying each selected roster into its named section")
    print("OK  Teams picker wired into overlay, first-run, and launch")


def main() -> int:
    test_catalog_has_teams()
    tp = load_engine()
    if tp.self_test() != 0:
        fail("teams_picker --self-test failed")
    test_apply_files_named_section(tp)
    test_launch_many_named_sections(tp)
    test_overlay_and_launch_wired()
    print("SMOKE OK: Teams popup lists checkboxes; Launch files each named section; export/import stay.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
