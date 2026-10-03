#!/usr/bin/env python3
"""Tests first: in-app Teams picker (catalog + one-click apply + import).

James (2026-10-01): pick a team from the Dragon AI UI, not only Import-Profile.ps1.
Applied bots file under the pack displayName, not UNASSIGNED.
No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import json
import pathlib
import re
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
TRADING = ROOT / "bot-groups" / "trading-team" / "bot-group.json"
RESEARCHER_YAML = ROOT / "bot-groups" / "trading-team" / "bots" / "market-researcher" / "bot.yaml"
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
TRADING_IDS = [
    "market-researcher",
    "trade-journal",
    "risk-analyst",
    "news-scanner",
]
RESEARCHER_BRIEF = (
    "Research notes from an adapted Anthropic financial-services skill pack (paper/read-only)."
)
RESEARCHER_DETAIL_NEEDLES = (
    "Not a new teammate",
    "four",
    "financial-services",
    "github.com/anthropics/financial-services",
    "computer-use",
    "browser",
    "re-apply",
    "Not a broker",
    "FactSet",
    "OpenBB",
)
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
    picker_js = read(ROOT / "branding" / "fonts" / "syne" / "teams-picker.js")
    if "teams-picker" not in branding and "dragon-ai-teams" not in branding:
        fail("desktop overlay must inject the Teams picker into the desktop client")
    if "Personal Assistant is already installed" not in picker_js:
        fail("Teams dialog must say Personal Assistant is already installed")
    if "Teams Marketplace" not in picker_js:
        fail("user-visible control label must be Teams Marketplace")
    if 'textContent = "Teams"' in picker_js or 'textContent="Teams"' in picker_js:
        fail("sidebar control must not be labeled Teams (use Teams Marketplace)")
    if "<h2>Teams Marketplace</h2>" not in picker_js:
        fail("Teams dialog title must be Teams Marketplace")
    if "data-dragon-ai-teams-visible" not in picker_js:
        fail("open/close must toggle data-dragon-ai-teams-visible (not hidden-only)")
    if "setTimeout" not in picker_js:
        fail("close must finish with a timeout, not transitionend-only")
    if "findColumnHost" not in picker_js or "data-dragon-ai-sidebar-fixed" not in picker_js:
        fail("Teams Marketplace must try column hosts then the body fixed overlay")
    if "findInFlowColumn" not in picker_js or "data-dragon-ai-sidebar-chrome" not in picker_js:
        fail("Teams Marketplace must prefer an in-flow rail column above Sessions/Bots")
    if "findBotsTab" not in picker_js or "data-dragon-ai-sidebar-clearance" not in picker_js:
        fail("fixed overlay must reserve clearance so the BOTS tab stays clickable")
    if "lockup → Teams Marketplace → Sessions/Bots" not in picker_js:
        fail("Teams Marketplace must document expected DOM order: lockup → Teams Marketplace → Sessions/Bots")
    picker_compact = picker_js.replace(" ", "")
    if "vartop=0" not in picker_compact or "return96" not in picker_compact:
        fail("Teams Marketplace overlay must pin to rail top and reserve 96px stacked height")
    if "vartop=96" in picker_compact:
        fail("Teams Marketplace overlay must not default top to 96px (leaves SESSIONS first)")
    if "vartop=48" in picker_compact or "return48" in picker_compact:
        fail("Teams Marketplace overlay must not use 48px (covers BOTS)")
    if re.search(r'querySelector\(\s*[\'"]\[data-slot="sidebar-wrapper"\]', picker_js):
        fail("Teams Marketplace must not query sidebar-wrapper as a column host")
    if "finishApply" not in picker_js or "location.reload" not in picker_js:
        fail("after apply the Teams dialog must close and reload the bot roster")
    if 'box.type = "checkbox"' in picker_js or 'type = "checkbox"' in picker_js:
        fail("Teams popup must not list each team with a checkbox")
    if 'textContent = "Install"' not in picker_js or "data-dragon-ai-team-apply" not in picker_js:
        fail("Teams popup must list each team with an Install button")
    if "function installTeam" not in picker_js or "/api/marketplace/install" not in picker_js:
        fail("Install must apply that team's pack through the existing marketplace install path")
    if "data-dragon-ai-teams-launch" not in picker_js or "Launch" not in picker_js:
        fail("Teams popup must have a Launch button for the checked teams")
    if "Launch needs a team" not in picker_js and "empty-result" not in picker_js:
        fail("Teams Launch must give visible feedback when it cannot run")
    if "data-dragon-ai-teams-export" not in picker_js or "/api/teams/export" not in picker_js:
        fail("Teams popup must expose Export against the helper")
    if "data-dragon-ai-teams-import" not in picker_js:
        fail("Teams popup must keep Import next to Export")
    if "data-dragon-ai-teams-install" not in picker_js or "Install" not in picker_js:
        fail("Teams popup must Install a marketplace pack")
    if "data-dragon-ai-teams-detail" not in picker_js or "/api/marketplace" not in picker_js:
        fail("Teams popup must browse marketplace Details")
    if "data-dragon-ai-teams-backdrop" not in picker_js:
        fail("Teams Marketplace must open a popup with a backdrop, not a dropdown")
    if "aria-modal" not in picker_js:
        fail("Teams popup must be a modal dialog")
    if "<select" in picker_js:
        fail("in-app Teams control must stay a popup, not a dropdown")
    css = read(CSS)
    if "[data-dragon-ai-teams-panel]" not in css or "Teams Marketplace" not in css:
        fail("dragon-ui.css must style the in-app Teams Marketplace screen")
    if "flex-direction: column" not in css:
        fail("Teams Marketplace control must sit under the logo")
    if "dragon-ai-marketplace-label:1" not in css or "min-width: max-content" in css:
        fail("Teams Marketplace label must fit in full (no max-content clip)")
    if "dragon-ai-marketplace-blue:1" not in css or "#2563eb" not in css.lower():
        fail("Teams Marketplace sidebar button must be filled blue")
    if "dragon-ai-logo-clearance:1" not in css or "--dragon-logo-clearance: 12px" not in css:
        fail("logo lockup must reserve gap so Marketplace does not overlay the dragon")
    if "dragon-ai-logo-175:1" not in css or "--dragon-sidebar-logo-size: 56px" not in css:
        fail("Teams Marketplace must sit under the 56px (1.75×) logo")
    if "Math.max(256" not in picker_js.replace(" ", ""):
        fail("Teams overlay width must stay at least 16rem so the label is not clipped")
    if "must not cover BOTS" not in css:
        fail("Marketplace lockup must not cover BOTS")
    if "--dragon-ui-font-size-body: 16px" not in css:
        fail("Teams overlay must share the 16px Grok Bot body size")
    if "font-size: var(--dragon-ui-font-size-body)" not in css:
        fail("Teams list rows must use the 16px body token, not 0.8125rem")
    teams_css = "".join(
        css.split(marker, 1)[-1].split("}", 1)[0]
        for marker in (
            "[data-dragon-ai-teams-panel] {",
            "[data-dragon-ai-team-row] {",
            "[data-dragon-ai-team-row] [data-dragon-ai-team-apply] {",
            "[data-dragon-ai-teams-list] {",
        )
        if marker in css
    )
    if "font-size: 0.8125rem" in teams_css:
        fail("Teams picker CSS must not keep Hermes 13px captions")
    if "background: #000" not in css.split("[data-dragon-ai-teams-panel] {", 1)[-1].split("}", 1)[0]:
        fail("marketplace panel must use a black background")
    if "opacity" not in css.split("[data-dragon-ai-teams-panel] {", 1)[-1]:
        fail("marketplace open/close must fade")
    if "translateY" not in css or "scale(" not in css:
        fail("marketplace open/close must fade + slight slide/scale")
    if "min(72rem" not in css and "min(44rem" not in css:
        fail("Teams popup must be roomier than the old 28rem dropdown panel")
    if "[data-dragon-ai-teams-backdrop]" not in css:
        fail("Teams popup must use a backdrop, not a tight dropdown")
    if "[data-dragon-ai-teams-panel][hidden]" not in css or "display: none !important" not in css:
        fail("Teams popup CSS must honor [hidden] so display:flex does not leave the dialog stuck open")
    if "[data-dragon-ai-team-row] [data-dragon-ai-team-apply]" not in css:
        fail("overlay CSS must style the per-team Install button")
    if "left: 50%" not in css.split("[data-dragon-ai-teams-panel] {", 1)[-1].split("}", 1)[0]:
        fail("Teams popup must be a centered modal, not a left-rail dropdown")
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
    if "Teams Marketplace" not in wizard:
        fail("first-run wizard must offer Teams Marketplace")
    if "Choose a Team" in wizard:
        fail("wizard must not keep a Teams label; use Teams Marketplace")
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
    if "Teams Marketplace" not in product or "8653" not in product:
        fail("PRODUCT_BRANDING.md must describe the in-app Teams Marketplace picker")
    if "descriptionDetail" not in product and "hover" not in product.lower():
        fail("PRODUCT_BRANDING.md must mention seat brief + hover detail")
    if "popup" not in product.lower() and "modal" not in product.lower():
        fail("PRODUCT_BRANDING.md must describe the roomy Teams Marketplace popup")
    design = read(ROOT / "docs" / "airmaze" / "TEAMS_POPUP.md")
    if "own named section" not in design and "own named BOTS section" not in design:
        fail("TEAMS_POPUP.md must document applying each selected roster into its named section")
    if "4-column" not in design and "repeat(4, 1fr)" not in design:
        fail("TEAMS_POPUP.md must keep the 4-column seat-card grid inside the popup")
    host_note = ROOT / "docs" / "airmaze" / "SIDEBAR_HOST.md"
    host_txt = read(host_note)
    if not host_note.is_file() or "data-dragon-ai-sidebar-fixed" not in host_txt:
        fail("SIDEBAR_HOST.md must describe the body fixed-overlay fallback")
    if "lockup → Teams Marketplace → Sessions/Bots" not in host_txt:
        fail("SIDEBAR_HOST.md must document expected DOM order: lockup → Teams Marketplace → Sessions/Bots")
    if "data-dragon-ai-team-seats" not in picker_js:
        fail("Teams overlay must list seats under each team name")
    if "descriptionDetail" not in picker_js:
        fail("Teams overlay must render descriptionDetail on hover/focus")
    if "data-dragon-ai-seat-tooltip" not in picker_js:
        fail("Teams overlay must pop a tooltip for seat detail")
    if 'setAttribute("role", "tooltip")' not in picker_js and 'role="tooltip"' not in picker_js:
        fail("Teams overlay must mark seat detail as role=tooltip")
    if "data-dragon-ai-team-apply" not in picker_js:
        fail("Apply must stay on the team row, not a seat")
    if 'createElement("li")' not in picker_js and "createElement('li')" not in picker_js:
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
    seat_shadow = seat_card[1].split("}", 1)[0]
    if seat_shadow.count(",") < 3:
        fail("seat cards must use layered shadows for elevation")
    if "border-radius: 12px" not in css:
        fail("seat/team cards must share a 12px corner radius")
    if "data-dragon-ai-seat-icon" not in picker_js:
        fail("Teams overlay must place a seat icon beside the title/brief")
    if "aria-hidden" not in picker_js:
        fail("seat icons beside visible text must be aria-hidden")
    if "dragon-ai-branding/teams/" not in picker_js:
        fail("seat icons must load from the overlay branding pack")
    if "[data-dragon-ai-seat-icon]" not in css:
        fail("dragon-ui.css must size the seat icon beside the copy")
    if "display: flex" not in seat_card[1].split("}", 1)[0]:
        fail("seat cards must flex icon left of title/brief")
    if "@media (max-width: 1100px)" not in css:
        fail("dragon-ui.css must wrap the overlay Marketplace control at max-width 1100px")
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
    for needle in ("descriptionDetail", "seoagent.com", "six", "hover", "4-column", "icon", "Teams Marketplace", "financial-services"):
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


def test_trading_seat_descriptions() -> None:
    group = json.loads(read(TRADING))
    bots = [b for b in (group.get("bots") or []) if isinstance(b, dict) and b.get("id")]
    ids = [str(b["id"]) for b in bots]
    if ids != TRADING_IDS:
        fail(f"Trading Team must stay Cos's 4 seats {TRADING_IDS}, got {ids}")
    for forbidden in ("financial-services", "finance", "investment"):
        if forbidden in ids:
            fail(f"{forbidden} must not be a Trading seat")
    by_id = {str(b["id"]): b for b in bots}
    researcher = by_id["market-researcher"]
    if researcher.get("description") != RESEARCHER_BRIEF:
        fail(f"Market Researcher brief must be {RESEARCHER_BRIEF!r}, got {researcher.get('description')!r}")
    detail = str(researcher.get("descriptionDetail") or "")
    for needle in RESEARCHER_DETAIL_NEEDLES:
        if needle not in detail:
            fail(f"Market Researcher hover detail must include {needle!r}")
    yaml_text = read(RESEARCHER_YAML)
    if RESEARCHER_BRIEF not in yaml_text:
        fail("Market Researcher bot.yaml brief must match the Teams picker one-liner")
    for bot_id, bot in by_id.items():
        if not str(bot.get("description") or "").strip():
            fail(f"{bot_id} must have a brief description under the seat name")
        if bot_id == "market-researcher":
            continue
        if str(bot.get("descriptionDetail") or "").strip():
            fail(f"{bot_id} must omit descriptionDetail")
    print("OK  Trading seat brief + hover copy (Market Researcher financial-services)")


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
        trading = next((t for t in listed.get("teams") or [] if t.get("id") == "trading-team"), None)
        if not trading:
            fail("list_teams must include Trading Team")
        trading_seats = trading.get("bots") or []
        trading_ids = [s.get("id") for s in trading_seats]
        if trading_ids != TRADING_IDS:
            fail(f"present_team must list Cos's 4 Trading seats, got {trading_ids}")
        researcher = next((s for s in trading_seats if s.get("id") == "market-researcher"), {})
        if researcher.get("description") != RESEARCHER_BRIEF:
            fail("present_team must ship the Market Researcher brief")
        if not researcher.get("descriptionDetail") or "financial-services" not in researcher["descriptionDetail"]:
            fail("present_team must ship Market Researcher descriptionDetail")
        if any(s.get("id") == "financial-services" for s in trading_seats):
            fail("financial-services is a tool, not a Teams picker seat")
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
    test_launch_many_named_sections(tp)
    test_marketing_seat_descriptions()
    test_trading_seat_descriptions()
    test_present_team_exposes_seat_copy(tp)
    test_overlay_and_launch_wired()
    print("SMOKE OK: Teams popup lists Install per team + 4-col seats; Launch files each named section; export/import stay.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
