#!/usr/bin/env python3
"""Tests first: Teams marketplace v1 on the Teams Marketplace popup.

James: same job as the roomy popup (checkbox Launch / Import / Export)
plus GitHub catalog browse + detail + Install + scrubbed export.
4-column seat cards from main stay inside the popup.
No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
CATALOG = ROOT / "bot-groups" / "catalog.json"
MARKETING = ROOT / "bot-groups" / "marketing-team" / "bot-group.json"
DESIGN = ROOT / "docs" / "airmaze" / "TEAMS_MARKETPLACE.md"
POPUP = ROOT / "docs" / "airmaze" / "TEAMS_POPUP.md"
BRANDING_PY = SCRIPTS / "desktop_branding.py"
PICKER_JS = ROOT / "branding" / "fonts" / "syne" / "teams-picker.js"
CSS = ROOT / "branding" / "fonts" / "syne" / "dragon-ui.css"
INSTALL = SCRIPTS / "install.ps1"
SETUP = ROOT / "installer" / "DragonAIAgentSetup.ps1"

FEATURED = (
    "real-estate-cold-call-lead-refresher",
    "marketing-team",
    "trading-team",
)
COS_MARKETING = [
    "content-strategist",
    "seo-specialist",
    "social-media-manager",
    "paid-media-specialist",
    "lifecycle-marketer",
    "marketing-analyst",
]
SECRET_NEEDLES = (
    "sk-secretLIVEKEY1234567890",
    "james.operator@dragonsden.work",
    r"C:\Users\James\leads.csv",
    "hunter2-password",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def load_modules():
    sys.path.insert(0, str(SCRIPTS))
    import bot_groups as bg  # noqa: WPS433
    import team_marketplace as tm  # noqa: WPS433
    import teams_picker as tp  # noqa: WPS433

    return bg, tm, tp


def test_catalog_parse(bg) -> None:
    raw = json.loads(read(CATALOG))
    catalog = bg.normalize_catalog(raw)
    mp = catalog.get("marketplace") or {}
    if mp.get("version") != 1 or mp.get("hosting") != "github":
        fail(f"catalog marketplace block must be GitHub v1, got {mp}")
    if mp.get("path") != "bot-groups":
        fail("marketplace hosting path must stay bot-groups/ (no second store tree)")
    by_id = {g["id"]: g for g in catalog.get("groups") or []}
    for pack_id in FEATURED:
        entry = by_id.get(pack_id)
        if not entry:
            fail(f"catalog must seed featured pack {pack_id}")
        for field in ("blurb", "detail", "author", "seats", "requiredConnectors"):
            if not entry.get(field):
                fail(f"{pack_id} catalog entry must include {field}")
        if entry.get("featured") is not True:
            fail(f"{pack_id} must be featured")
        blob = json.dumps(entry)
        for needle in ("sk-", "password", "@gmail.", "C:\\Users\\", "/Users/"):
            if needle in blob:
                fail(f"catalog listing must not ship secrets or local paths: {needle}")
    marketing = by_id["marketing-team"]
    if int(marketing["seats"]) != 6:
        fail(f"Marketing Team seats must stay 6, got {marketing['seats']}")
    if marketing.get("displayName") != "Marketing Team":
        fail("Marketing Team displayName must stay Marketing Team")
    re_pack = by_id["real-estate-cold-call-lead-refresher"]
    if re_pack.get("displayName") != "Real Estate Lead Gen":
        fail("Real Estate catalog label must stay Real Estate Lead Gen")
    if int(re_pack["seats"]) != 4:
        fail("Real Estate Lead Gen must list 4 seats")
    trading = by_id["trading-team"]
    if int(trading["seats"]) != 4 or trading.get("displayName") != "Trading Team":
        fail("Trading Team must list 4 seats under Trading Team")
    pa = by_id.get("personal-assistant") or {}
    if pa.get("picker") is not False or pa.get("featured") is True:
        fail("Personal Assistant must stay picker:false and not featured")
    group = json.loads(read(MARKETING))
    ids = [b.get("id") for b in group.get("bots") or []]
    if ids != COS_MARKETING:
        fail(f"Marketing Team must stay Cos's 6 seats, got {ids}")
    if "seoagent" in ids or len(ids) != 6:
        fail("do not add a 7th Marketing seat")
    print("OK  catalog parse: marketplace fields + three featured packs")


def test_browse_and_install(tm, tp) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-mkt-") as tmp:
        tmp_path = pathlib.Path(tmp)
        install = tmp_path / "install"

        class Offline:
            def get_text(self, url: str) -> str:
                raise tp.bg.GitHubUnreachable("offline")

        listed = tm.list_marketplace(ROOT, install, fetcher=Offline())
        if listed.get("kind") != "dragon-teams-marketplace":
            fail(f"list_marketplace kind, got {listed.get('kind')}")
        packs = listed.get("teams") or []
        ids = [p.get("id") for p in packs]
        labels = [p.get("displayName") for p in packs]
        if ids[:3] != list(FEATURED) and set(FEATURED) - set(ids):
            fail(f"marketplace must list the three featured packs, got {ids}")
        for label in ("Real Estate Lead Gen", "Marketing Team", "Trading Team"):
            if label not in labels:
                fail(f"browse missing {label!r}")
        if "personal-assistant" in ids or "Personal Assistant" in labels:
            fail("marketplace must not list Personal Assistant")
        for pack in packs:
            for field in ("blurb", "detail", "author", "seats", "requiredConnectors"):
                if not pack.get(field):
                    fail(f"{pack.get('id')} browse card missing {field}")
            if int(pack.get("seats") or 0) < 2:
                fail(f"{pack.get('id')} must report multi-bot seats")
            blob = json.dumps(pack)
            if any(s in blob for s in ("sk-secret", "hunter2", "BEGIN RSA")):
                fail("browse payload must not include secrets")
        marketing = next((p for p in packs if p.get("id") == "marketing-team"), {})
        seat_ids = [s.get("id") for s in (marketing.get("bots") or [])]
        if seat_ids != COS_MARKETING:
            fail(f"marketplace Marketing pack must keep Cos seat rows, got {seat_ids}")
        seo = next((s for s in marketing.get("bots") or [] if s.get("id") == "seo-specialist"), {})
        if not seo.get("description") or not seo.get("descriptionDetail"):
            fail("marketplace seats must keep brief + hover detail from present_team")
        detail = tm.get_marketplace_pack(
            "marketing-team", ROOT, install, fetcher=Offline()
        )
        if detail.get("displayName") != "Marketing Team":
            fail("detail must keep Marketing Team")
        if int(detail.get("seats") or 0) != 6:
            fail("Marketing detail seats must be 6")
        if not detail.get("detail") or detail.get("detail") == detail.get("blurb"):
            fail("detail view needs longer copy than the blurb")
        desktop = tmp_path / "profiles"
        installed = tm.install_pack(
            "marketing-team",
            payload_root=ROOT,
            install_root=install,
            desktop_profiles_root=desktop,
        )
        applied = [b.get("id") for b in installed.get("bots") or []]
        if applied != COS_MARKETING:
            fail(f"Install must use existing apply path (6 Cos seats), got {applied}")
        profile = (desktop / "content-strategist" / "profile.yaml").read_text(encoding="utf-8")
        if "Marketing Team" not in profile or "sec-dragon-marketing-team" not in profile:
            fail("Install must file bots under Marketing Team, not UNASSIGNED")
        via_http = tp.apply_team(
            "trading-team",
            payload_root=ROOT,
            install_root=tmp_path / "install-t",
            desktop_profiles_root=tmp_path / "desktop-t",
        )
        if via_http.get("displayName") != "Trading Team":
            fail("Install/apply must stay the Teams helper path")
    print("OK  browse + detail + Install apply named sections")


def test_export_scrubs_and_reinstalls(tm, tp) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-mkt-pub-") as tmp:
        tmp_path = pathlib.Path(tmp)
        dirty_root = tmp_path / "payload" / "bot-groups"
        shutil.copytree(ROOT / "bot-groups" / "marketing-team", dirty_root / "marketing-team")
        shutil.copy2(CATALOG, dirty_root / "catalog.json")
        soul = dirty_root / "marketing-team" / "bots" / "content-strategist" / "SOUL.md"
        soul.write_text(
            soul.read_text(encoding="utf-8")
            + "\nContact james.operator@dragonsden.work from C:\\Users\\James\\leads.csv\n"
            + "API sk-secretLIVEKEY1234567890\n",
            encoding="utf-8",
        )
        (dirty_root / "marketing-team" / "secrets.json").write_text(
            json.dumps({"api_key": "sk-secretLIVEKEY1234567890", "password": "hunter2-password"}),
            encoding="utf-8",
        )
        conn = dirty_root / "marketing-team" / "connectors"
        conn.mkdir(exist_ok=True)
        (conn / "leaky.json").write_text(
            json.dumps(
                {
                    "id": "leaky",
                    "api_key": "sk-secretLIVEKEY1234567890",
                    "password": "hunter2-password",
                    "notes": "email james.operator@dragonsden.work",
                }
            ),
            encoding="utf-8",
        )
        dest = tmp_path / "published" / "marketing-team.zip"
        result = tm.publish_pack(
            "marketing-team",
            dest,
            payload_root=tmp_path / "payload",
            install_root=tmp_path / "install",
        )
        published = pathlib.Path(result["path"])
        if not published.is_file():
            fail("publish must write a catalog-ready zip")
        if not result.get("scrubbed"):
            fail("publish must report scrubbed=true")
        if not result.get("catalogEntry"):
            fail("publish must include a catalog-entry stub")
        entry = result["catalogEntry"]
        if entry.get("id") != "marketing-team" or int(entry.get("seats") or 0) != 6:
            fail(f"catalog-entry must describe Marketing Team 6 seats, got {entry}")
        with zipfile.ZipFile(published) as zf:
            names = zf.namelist()
            blob = b"".join(zf.read(n) for n in names if not n.endswith("/"))
        text = blob.decode("utf-8", errors="replace")
        for needle in SECRET_NEEDLES:
            if needle in text:
                fail(f"published pack still contains {needle!r}")
        if "secrets.json" in "".join(names):
            fail("publish must drop secrets.json")
        if "catalog-entry.json" not in "".join(names):
            fail("publish zip must include catalog-entry.json")
        exported = pathlib.Path(
            tp.export_teams(
                ["marketing-team"],
                tmp_path / "export" / "marketing-team.zip",
                payload_root=tmp_path / "payload",
                install_root=tmp_path / "install-export",
            )
        )
        with zipfile.ZipFile(exported) as zf:
            export_text = b"".join(zf.read(n) for n in zf.namelist() if not n.endswith("/")).decode(
                "utf-8", errors="replace"
            )
        for needle in SECRET_NEEDLES:
            if needle in export_text:
                fail(f"Export must scrub {needle!r} for the public catalog")
        again = tp.import_team_file(
            exported,
            payload_root=ROOT,
            install_root=tmp_path / "install-reimport",
            desktop_profiles_root=tmp_path / "from-export",
        )
        if again.get("displayName") != "Marketing Team":
            fail("scrubbed export must still Install/import as Marketing Team")
        if not (tmp_path / "from-export" / "content-strategist" / "SOUL.md").is_file():
            fail("scrubbed export must keep Cos Marketing souls")
        sample = (
            "api_key: sk-secretLIVEKEY1234567890\n"
            "email james.operator@dragonsden.work\n"
            r"path C:\Users\James\leads.csv" + "\n"
            "ok operator@example.com\n"
        )
        cleaned, findings = tm.scrub_text(sample)
        if any(n in cleaned for n in SECRET_NEEDLES):
            fail("scrub_text must remove keys, personal email, and local paths")
        if "operator@example.com" not in cleaned:
            fail("scrub must keep example.com emails")
        if not findings:
            fail("scrub_text must report what it stripped")
    print("OK  export/publish scrub secrets and stay installable")


def test_overlay_is_popup_plus_marketplace() -> None:
    branding = read(BRANDING_PY)
    picker_js = read(PICKER_JS)
    css = read(CSS)
    design = read(DESIGN)
    popup = read(POPUP)
    overlay = branding + "\n" + picker_js
    for needle in (
        'type="checkbox"',
        "data-dragon-ai-teams-launch",
        "Launch",
        "data-dragon-ai-teams-export",
        "/api/teams/export",
        "data-dragon-ai-teams-import",
        "data-dragon-ai-teams-install",
        "Install",
        "data-dragon-ai-teams-detail",
        "/api/marketplace",
        "Personal Assistant is already installed",
        "finishApply",
        "location.reload",
        "data-dragon-ai-team-seats",
        "grid-template-columns: repeat(4, 1fr)",
    ):
        haystack = overlay if needle != "grid-template-columns: repeat(4, 1fr)" else css
        if needle not in haystack:
            fail(f"Teams popup overlay must include {needle!r}")
    if "<select" in picker_js:
        fail("in-app Teams control must stay a popup, not a dropdown")
    if "Teams Marketplace" not in picker_js:
        fail("overlay label must stay Teams Marketplace")
    for needle in (
        "[data-dragon-ai-teams-detail]",
        "[data-dragon-ai-teams-install]",
        "[data-dragon-ai-teams-panel][hidden]",
        "display: none !important",
        "[data-dragon-ai-teams-backdrop]",
    ):
        if needle not in css:
            fail(f"overlay CSS must style marketplace popup ({needle})")
    if "min(72rem" not in css and "min(44rem" not in css:
        fail("overlay CSS must use a roomy popup width (min(72rem) or min(44rem))")
    for needle in (
        "catalog.json",
        "requiredConnectors",
        "Install",
        "scrub",
        "Real Estate Lead Gen",
        "Marketing Team",
        "Trading Team",
        "bot-groups/",
        "4-column",
    ):
        if needle not in design:
            fail(f"TEAMS_MARKETPLACE.md must document {needle!r}")
    if "marketplace" not in popup.lower():
        fail("TEAMS_POPUP.md must say marketplace is the same popup job")
    for path in (INSTALL, SETUP):
        text = read(path)
        if "team_marketplace.py" not in text:
            fail(f"{path.name} must ship team_marketplace.py")
    print("OK  popup stays Launch/Import/Export and adds marketplace browse/Install")


def main() -> int:
    if not (SCRIPTS / "team_marketplace.py").is_file():
        fail("scripts/airmaze/team_marketplace.py must exist")
    bg, tm, tp = load_modules()
    test_catalog_parse(bg)
    if tm.self_test() != 0:
        fail("team_marketplace --self-test failed")
    test_browse_and_install(tm, tp)
    test_export_scrubs_and_reinstalls(tm, tp)
    test_overlay_is_popup_plus_marketplace()
    print("SMOKE OK: marketplace catalog parses; Install uses Teams apply; export scrubs secrets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
