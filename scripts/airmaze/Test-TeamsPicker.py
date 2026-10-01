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
MARKETING = ROOT / "bot-groups" / "marketing-team" / "bot-group.json"
SEO_YAML = ROOT / "bot-groups" / "marketing-team" / "bots" / "seo-specialist" / "bot.yaml"
DESIGN = ROOT / "docs" / "airmaze" / "TEAMS_SEAT_DESCRIPTIONS.md"
BOT_GROUPS_DOC = ROOT / "docs" / "airmaze" / "BOT_GROUPS.md"

MARKETING_IDS = [
    "content-strategist",
    "seo-specialist",
    "social-media-manager",
    "paid-media-specialist",
    "lifecycle-marketer",
    "marketing-analyst",
]
SEO_BRIEF = "Runs seoagent.com Skill/CLI audits and optional DataForSEO research."
SEO_DETAIL_NEEDLES = (
    "Not a new teammate",
    "six",
    "seoagent",
    "seoagent.com",
    "@seoagent-official/seoagent",
    "seoagent init",
    "npx",
    "dataforseo",
    "computer-use",
    "browser",
    "Autopilot",
    "$49",
    "re-apply",
    "Buffer",
    "Brevo",
)


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
        marketing_ids = list(MARKETING_IDS)
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
    if "teams-picker" not in branding and "dragon-ai-teams" not in branding:
        fail("desktop overlay must inject the Teams picker into the desktop client")
    if "Personal Assistant is already installed" not in branding:
        fail("Teams dialog must say Personal Assistant is already installed")
    if "finishApply" not in branding or "location.reload" not in branding:
        fail("after apply the Teams dialog must close and reload the bot roster")
    css = read(CSS)
    if "[data-dragon-ai-teams-panel]" not in css or "Teams" not in css:
        fail("dragon-ui.css must style the in-app Teams screen")
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
    if "Teams" not in product or "8653" not in product:
        fail("PRODUCT_BRANDING.md must describe the in-app Teams picker")
    if "descriptionDetail" not in product and "hover" not in product.lower():
        fail("PRODUCT_BRANDING.md must mention seat brief + hover detail")
    branding = read(BRANDING_PY)
    if "data-dragon-ai-team-seats" not in branding:
        fail("Teams overlay must list seats under each team name")
    if "descriptionDetail" not in branding:
        fail("Teams overlay must render descriptionDetail on hover/focus")
    if "data-dragon-ai-seat-tooltip" not in branding:
        fail("Teams overlay must pop a tooltip for seat detail")
    if 'setAttribute("role","tooltip")' not in branding and 'role="tooltip"' not in branding:
        fail("Teams overlay must mark seat detail as role=tooltip")
    if "data-dragon-ai-team-apply" not in branding:
        fail("Apply must stay on the team row, not a seat")
    if "createElement(\"li\")" not in branding and "createElement('li')" not in branding:
        fail("seat rows must be list items, not nested buttons")
    css = read(CSS)
    if "[data-dragon-ai-seat-tooltip]" not in css:
        fail("dragon-ui.css must style the seat hover/focus tooltip")
    if ":hover [data-dragon-ai-seat-tooltip]" not in css or ":focus" not in css:
        fail("seat detail must show on hover and keyboard focus, not hover-only")
    if "grid-template-columns: repeat(4, 1fr)" not in css:
        fail("Teams seats must use a 4-column CSS grid (repeat(4, 1fr))")
    if "[data-dragon-ai-team-seats] {\n  list-style: none;\n  margin: 0;\n  padding: 0;\n  display: grid;" not in css:
        fail("[data-dragon-ai-team-seats] must be display:grid")
    seat_card = css.split("[data-dragon-ai-team-seats] li {", 1)
    if len(seat_card) < 2 or "box-shadow:" not in seat_card[1].split("}", 1)[0]:
        fail("seat cards must have a box-shadow")
    if "border-radius: 12px" not in css:
        fail("seat/team cards must share a 12px corner radius")
    if "data-dragon-ai-seat-icon" not in branding:
        fail("Teams overlay must place a seat icon beside the title/brief")
    if "aria-hidden" not in branding:
        fail("seat icons beside visible text must be aria-hidden")
    if "dragon-ai-branding/teams/" not in branding:
        fail("seat icons must load from the overlay branding pack")
    if "[data-dragon-ai-seat-icon]" not in css:
        fail("dragon-ui.css must size the seat icon beside the copy")
    if "display: flex" not in seat_card[1].split("}", 1)[0]:
        fail("seat cards must flex icon left of title/brief")
    icons_dir = ROOT / "branding" / "teams"
    if not (icons_dir / "seat.svg").is_file():
        fail("branding/teams/seat.svg fallback must exist")
    for seat_id in (
        "content-strategist",
        "seo-specialist",
        "social-media-manager",
        "paid-media-specialist",
        "lifecycle-marketer",
        "marketing-analyst",
        "lead-sourcer",
        "email-warmer",
        "cold-call-script-writer",
        "follow-up-sequencer",
        "market-researcher",
        "trade-journal",
        "risk-analyst",
        "news-scanner",
    ):
        icon = icons_dir / f"{seat_id}.svg"
        if not icon.is_file():
            fail(f"missing Teams seat icon {icon.name}")
        svg = read(icon)
        if 'xmlns="http://www.w3.org/2000/svg"' not in svg:
            fail(f"{icon.name} must be an SVG")
        if "#314A73" not in svg or "#C41E3A" not in svg:
            fail(f"{icon.name} must use Dragon navy + crimson")
        if "<rect" in svg.lower():
            fail(f"{icon.name} must stay transparent (no boxed plate)")
    apply_ps = read(SCRIPTS / "Apply-DesktopBranding.ps1")
    if "branding" not in apply_ps or "teams" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must copy branding/teams icons")
    design = read(DESIGN)
    for needle in ("descriptionDetail", "seoagent.com", "six", "hover", "4-column", "icon"):
        if needle not in design:
            fail(f"TEAMS_SEAT_DESCRIPTIONS.md must document {needle!r}")
    groups_doc = read(BOT_GROUPS_DOC)
    if "descriptionDetail" not in groups_doc:
        fail("BOT_GROUPS.md must document bots[].descriptionDetail")
    print("OK  Teams picker wired into overlay, first-run, and launch")


def test_marketing_seat_descriptions() -> None:
    group = json.loads(read(MARKETING))
    bots = [b for b in (group.get("bots") or []) if isinstance(b, dict) and b.get("id")]
    ids = [str(b["id"]) for b in bots]
    if ids != MARKETING_IDS:
        fail(f"Marketing Team must stay Cos's 6 seats {MARKETING_IDS}, got {ids}")
    for forbidden in ("seoagent", "claude-seo", "copywriter", "campaign-sequencer"):
        if forbidden in ids:
            fail(f"{forbidden} must not be a Marketing seat")
    by_id = {str(b["id"]): b for b in bots}
    seo = by_id["seo-specialist"]
    if seo.get("description") != SEO_BRIEF:
        fail(f"SEO Specialist brief must be {SEO_BRIEF!r}, got {seo.get('description')!r}")
    detail = str(seo.get("descriptionDetail") or "")
    for needle in SEO_DETAIL_NEEDLES:
        if needle not in detail:
            fail(f"SEO Specialist hover detail must include {needle!r}")
    if "claude-seo" in detail.lower():
        fail("SEO hover detail must not keep claude-seo identity")
    yaml_text = read(SEO_YAML)
    if SEO_BRIEF not in yaml_text:
        fail("SEO Specialist bot.yaml brief must match the Teams picker one-liner")
    for bot_id, bot in by_id.items():
        if not str(bot.get("description") or "").strip():
            fail(f"{bot_id} must have a brief description under the seat name")
        if not str(bot.get("descriptionDetail") or "").strip():
            fail(f"{bot_id} must have descriptionDetail for the hover popover")
    social_detail = str(by_id["social-media-manager"].get("descriptionDetail") or "")
    life_detail = str(by_id["lifecycle-marketer"].get("descriptionDetail") or "")
    if "Buffer" not in social_detail:
        fail("Social Media Manager hover must keep Buffer on that seat")
    if "Brevo" not in life_detail:
        fail("Lifecycle Marketer hover must keep Brevo on that seat")
    if "Buffer stays on Social Media Manager" not in detail:
        fail("SEO hover must say Buffer stays on Social Media Manager")
    if "Brevo stays on Lifecycle Marketer" not in detail:
        fail("SEO hover must say Brevo stays on Lifecycle Marketer")
    print("OK  Marketing seat brief + hover copy (SEO Specialist seoagent.com)")


def test_present_team_exposes_seat_copy(tp) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-teams-seats-") as tmp:
        install = pathlib.Path(tmp) / "install"

        class Offline:
            def get_text(self, url: str) -> str:
                raise tp.bg.GitHubUnreachable("offline")

        listed = tp.list_teams(ROOT, install, fetcher=Offline())
        marketing = next((t for t in listed.get("teams") or [] if t.get("id") == "marketing-team"), None)
        if not marketing:
            fail("list_teams must include Marketing Team")
        seats = marketing.get("bots") or []
        ids = [s.get("id") for s in seats]
        if ids != MARKETING_IDS:
            fail(f"present_team must list Cos's 6 Marketing seats, got {ids}")
        seo = next((s for s in seats if s.get("id") == "seo-specialist"), {})
        if seo.get("description") != SEO_BRIEF:
            fail("present_team must ship the SEO Specialist brief")
        if not seo.get("descriptionDetail") or "seoagent.com" not in seo["descriptionDetail"]:
            fail("present_team must ship SEO Specialist descriptionDetail")
        if any(s.get("id") == "seoagent" for s in seats):
            fail("seoagent is a tool, not a Teams picker seat")
        for team in listed.get("teams") or []:
            for seat in team.get("bots") or []:
                if not seat.get("title") or "description" not in seat:
                    fail(f"{team.get('id')} seat {seat} must have title + description")
        presented = tp.present_team(
            {
                "id": "marketing-team",
                "name": "Marketing Team",
                "displayName": "Marketing Team",
                "departmentJob": "desk",
                "bots": [
                    {
                        "id": "seo-specialist",
                        "title": "SEO Specialist",
                        "description": SEO_BRIEF,
                        "descriptionDetail": "Not a new teammate. six seoagent",
                    }
                ],
            }
        )
        if not presented.get("bots") or presented["bots"][0].get("descriptionDetail") != "Not a new teammate. six seoagent":
            fail("present_team must pass descriptionDetail through")
    print("OK  Teams API exposes seat brief + hover detail")


def main() -> int:
    test_catalog_has_teams()
    tp = load_engine()
    if tp.self_test() != 0:
        fail("teams_picker --self-test failed")
    test_apply_files_named_section(tp)
    test_marketing_seat_descriptions()
    test_present_team_exposes_seat_copy(tp)
    test_overlay_and_launch_wired()
    print("SMOKE OK: in-app Teams picker lists catalog teams; seats show brief + hover detail; apply files a named group.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
