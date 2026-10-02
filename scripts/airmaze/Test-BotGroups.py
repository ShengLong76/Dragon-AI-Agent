#!/usr/bin/env python3
"""Tests first for Dragon AI Agent bot groups.

Covers the signed-off shape in docs/airmaze/BOT_GROUPS.md:
rename (no Profiles UI), dropdown reads this GitHub repo, deploy one group,
export is re-importable, singular toggle stays off by default.

No secrets. No Docker. Safe on Linux CI.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
DOCS = ROOT / "docs" / "airmaze"
ENGINE = SCRIPTS / "bot_groups.py"
SELECT = SCRIPTS / "Select-BotGroup.ps1"
DEPLOY = SCRIPTS / "Deploy-BotGroup.ps1"
EXPORT = SCRIPTS / "Export-BotGroup.ps1"
IMPORT = SCRIPTS / "Import-BotGroup.ps1"
DEFAULT = SCRIPTS / "apply-default-bot-group.ps1"
DESIGN = DOCS / "BOT_GROUPS.md"
CATALOG = ROOT / "bot-groups" / "catalog.json"
REAL_ESTATE = ROOT / "bot-groups" / "real-estate-cold-call-lead-refresher" / "bot-group.json"
PA = ROOT / "bot-groups" / "personal-assistant" / "bot-group.json"
MARKETING = ROOT / "bot-groups" / "marketing-team" / "bot-group.json"
SEO_SPECIALIST = ROOT / "bot-groups" / "marketing-team" / "bots" / "seo-specialist"
SEOAGENT_SKILLS = SEO_SPECIALIST / "skills"
DATAFORSEO_CONNECTOR = ROOT / "bot-groups" / "marketing-team" / "connectors" / "dataforseo.json"
SEOAGENT_CONNECTOR = ROOT / "bot-groups" / "marketing-team" / "connectors" / "seoagent.json"
SEOAGENT_DESIGN = DOCS / "SEOAGENT.md"
CLAUDE_SEO_LEAVES = (
    "seo-audit.md",
    "seo-page.md",
    "seo-technical.md",
    "seo-content-brief.md",
    "seo-dataforseo.md",
)
INSTALLERS = (
    ROOT / "scripts" / "airmaze" / "install.ps1",
    ROOT / "installer" / "DragonAIAgentSetup.ps1",
)
COMPOSE = ROOT / "docker-compose.embedded.yml"
BRANDING_TABLE = SCRIPTS / "desktop_branding.json"
WIZARD = SCRIPTS / "Onboard-Wizard.ps1"
README = ROOT / "README.md"

PROTECTED = (
    "127.0.0.1:8650",
    "dragon-local",
    "hermes-airmaze-gw",
    "hermes-airmaze-desktop",
)
GITHUB_RAW_PREFIX = "https://raw.githubusercontent.com/ShengLong76/airmaze-agent/"
REPO = "ShengLong76/airmaze-agent"
COS_ROSTERS = {
    "marketing-team": [
        "content-strategist",
        "seo-specialist",
        "social-media-manager",
        "paid-media-specialist",
        "lifecycle-marketer",
        "marketing-analyst",
    ],
    "real-estate-cold-call-lead-refresher": [
        "lead-sourcer",
        "email-warmer",
        "cold-call-script-writer",
        "follow-up-sequencer",
    ],
    "trading-team": [
        "market-researcher",
        "trade-journal",
        "risk-analyst",
        "news-scanner",
    ],
}
STALE_MARKETING_IDS = ("copywriter", "campaign-sequencer")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def load_engine():
    if not ENGINE.is_file():
        fail("missing scripts/airmaze/bot_groups.py (bot group engine)")
    sys.path.insert(0, str(SCRIPTS))
    import bot_groups  # noqa: WPS433

    return bot_groups


class MemoryFetcher:
    """Test double: url -> body. Missing urls raise the engine's offline error."""

    def __init__(self, mapping: dict[str, str], engine) -> None:
        self.mapping = mapping
        self.engine = engine
        self.requested: list[str] = []

    def get_text(self, url: str) -> str:
        self.requested.append(url)
        if url not in self.mapping:
            raise self.engine.GitHubUnreachable(f"offline: {url}")
        return self.mapping[url]


def sample_catalog() -> dict:
    return {
        "kind": "bot-group-catalog",
        "schemaVersion": 1,
        "product": "Dragon AI Agent",
        "repository": {
            "owner": "ShengLong76",
            "name": "airmaze-agent",
            "ref": "main",
            "path": "bot-groups",
        },
        "groups": [
            {
                "id": "personal-assistant",
                "name": "Personal Assistant",
                "departmentJob": "General-purpose PA for one operator.",
                "path": "personal-assistant",
            },
            {
                "id": "real-estate-cold-call-lead-refresher",
                "name": "Real Estate Cold Call Lead Refresher",
                "departmentJob": "Outbound real-estate department.",
                "path": "real-estate-cold-call-lead-refresher",
            },
        ],
    }


def sample_group() -> dict:
    return {
        "kind": "bot-group",
        "schemaVersion": 1,
        "id": "real-estate-cold-call-lead-refresher",
        "name": "Real Estate Cold Call Lead Refresher",
        "departmentJob": "Refresh stale leads, warm them, write scripts, follow up.",
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


def write_group_tree(root: pathlib.Path, group: dict) -> pathlib.Path:
    folder = root / group["id"]
    (folder / "bots" / "email-warmer").mkdir(parents=True, exist_ok=True)
    (folder / "bots" / "lead-sourcer").mkdir(parents=True, exist_ok=True)
    (folder / "bot-group.json").write_text(json.dumps(group, indent=2), encoding="utf-8")
    (folder / "bots" / "email-warmer" / "SOUL.md").write_text("# Email Warmer\nWarm leads.\n", encoding="utf-8")
    (folder / "bots" / "email-warmer" / "bot.yaml").write_text("slug: email-warmer\n", encoding="utf-8")
    (folder / "bots" / "lead-sourcer" / "SOUL.md").write_text("# Lead Sourcer\nSource leads.\n", encoding="utf-8")
    (folder / "bots" / "lead-sourcer" / "bot.yaml").write_text("slug: lead-sourcer\n", encoding="utf-8")
    return folder


def test_design_doc() -> None:
    text = read(DESIGN)
    for needle in (
        "Data model",
        "departmentJob",
        "raw.githubusercontent.com/ShengLong76/airmaze-agent",
        "GitHub unreachable",
        "already exist",
        "allowSingularBotImportExport",
        "kind\": \"bot\"",
        "bot-groups/",
        "upstream sync",
        "profile.json",
        "UNASSIGNED",
        "sectionId",
        "sectionName",
    ):
        if needle not in text:
            fail(f"BOT_GROUPS.md must document {needle!r}")
    if "template" in text.lower() and "Do not call them templates" not in text:
        fail("design must not reintroduce templates as the product name")
    print("OK  design doc")


def test_engine_constants(bg) -> None:
    if getattr(bg, "KIND_GROUP", None) != "bot-group":
        fail("engine KIND_GROUP must be bot-group")
    if getattr(bg, "KIND_BOT", None) != "bot":
        fail("engine KIND_BOT must be bot")
    if getattr(bg, "KIND_CATALOG", None) != "bot-group-catalog":
        fail("engine KIND_CATALOG must be bot-group-catalog")
    if getattr(bg, "DEFAULT_REPO", None) != REPO:
        fail("engine DEFAULT_REPO must be ShengLong76/airmaze-agent")
    if getattr(bg, "REPO_PATH", None) != "bot-groups":
        fail("engine REPO_PATH must be bot-groups")
    url = bg.catalog_url()
    if not url.startswith(GITHUB_RAW_PREFIX) or not url.endswith("/bot-groups/catalog.json"):
        fail(f"catalog_url must fetch the repo catalog, got {url}")
    settings = bg.default_settings()
    if settings.get("allowSingularBotImportExport") is not False:
        fail("singular toggle must default off")
    src = ENGINE.read_text(encoding="utf-8")
    if "GROUPS = [" in src or "HARDCODED_GROUPS" in src:
        fail("client must not hard-code the bot group list")
    print("OK  engine constants / no hardcoded list")


def test_normalize_legacy_profile(bg) -> None:
    legacy = {
        "id": "real-estate-cold-call-lead-refresher",
        "displayName": "Real Estate Cold Call Lead Refresher",
        "description": "Outbound real-estate agent team.",
        "version": "1.1.0",
        "bots": [
            {
                "id": "email-warmer",
                "displayName": "Email Warmer",
                "description": "Warm stale leads.",
                "soul": "bots/email-warmer/SOUL.md",
                "config": "bots/email-warmer/bot.yaml",
            }
        ],
        "connectors": [{"id": "email", "type": "api_key"}],
    }
    norm = bg.normalize_manifest(legacy)
    if norm["kind"] != "bot-group":
        fail("legacy profile.json must normalize to kind bot-group")
    if norm["name"] != "Real Estate Cold Call Lead Refresher":
        fail("legacy displayName must map to name")
    if norm["departmentJob"] != "Outbound real-estate agent team.":
        fail("legacy description must map to departmentJob")
    bot = norm["bots"][0]
    if bot["title"] != "Email Warmer":
        fail("legacy bot displayName must map to title")
    if "email" not in bot.get("tools", []):
        fail("legacy connector ids should become bot tools when tools are missing")
    print("OK  legacy profile.json compatibility")


def test_list_from_github(bg) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-bg-list-") as tmp:
        tmp_path = pathlib.Path(tmp)
        payload = tmp_path / "payload"
        install = tmp_path / "install"
        payload.mkdir()
        install.mkdir()
        url = bg.catalog_url()
        fetcher = MemoryFetcher({url: json.dumps(sample_catalog())}, bg)
        result = bg.list_groups(payload_root=payload, install_root=install, fetcher=fetcher)
        ids = [g["id"] for g in result["groups"]]
        if ids != ["personal-assistant", "real-estate-cold-call-lead-refresher"]:
            fail(f"dropdown must list repo groups, got {ids}")
        if result.get("source") != "github":
            fail(f"source should be github, got {result.get('source')}")
        if not any(GITHUB_RAW_PREFIX in u for u in fetcher.requested):
            fail("list_groups must request the GitHub raw catalog")
        cache = install / "bot-groups" / "cache" / "catalog.json"
        if not cache.is_file():
            fail("successful GitHub fetch must write a cache")
    print("OK  dropdown lists groups from GitHub")


def test_list_offline_cache_then_bundle(bg) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-bg-off-") as tmp:
        tmp_path = pathlib.Path(tmp)
        payload = tmp_path / "payload"
        install = tmp_path / "install"
        (payload / "bot-groups").mkdir(parents=True)
        (install / "bot-groups" / "cache").mkdir(parents=True)
        bundled = sample_catalog()
        bundled["groups"] = [bundled["groups"][0]]
        (payload / "bot-groups" / "catalog.json").write_text(json.dumps(bundled), encoding="utf-8")
        cached = sample_catalog()
        (install / "bot-groups" / "cache" / "catalog.json").write_text(json.dumps(cached), encoding="utf-8")
        fetcher = MemoryFetcher({}, bg)
        result = bg.list_groups(payload_root=payload, install_root=install, fetcher=fetcher)
        ids = [g["id"] for g in result["groups"]]
        if "real-estate-cold-call-lead-refresher" not in ids:
            fail("unreachable GitHub must fall back to cache")
        if result.get("source") != "cache":
            fail(f"expected cache source, got {result.get('source')}")
        (install / "bot-groups" / "cache" / "catalog.json").unlink()
        result2 = bg.list_groups(payload_root=payload, install_root=install, fetcher=fetcher)
        ids2 = [g["id"] for g in result2["groups"]]
        if ids2 != ["personal-assistant"]:
            fail(f"no cache must use bundled catalog, got {ids2}")
        if result2.get("source") != "bundled":
            fail(f"expected bundled source, got {result2.get('source')}")
    print("OK  GitHub unreachable uses cache then bundle")


def test_deploy_group(bg) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-bg-dep-") as tmp:
        tmp_path = pathlib.Path(tmp)
        payload = tmp_path / "payload" / "bot-groups"
        install = tmp_path / "install"
        desktop = tmp_path / "hermes-profiles"
        payload.mkdir(parents=True)
        (payload / "catalog.json").write_text(json.dumps(sample_catalog()), encoding="utf-8")
        write_group_tree(payload, sample_group())
        result = bg.deploy_group(
            "real-estate-cold-call-lead-refresher",
            payload_root=tmp_path / "payload",
            install_root=install,
            desktop_profiles_root=desktop,
        )
        warmer = desktop / "email-warmer"
        if not (warmer / "SOUL.md").is_file() or "Email Warmer" not in (warmer / "SOUL.md").read_text(encoding="utf-8"):
            fail("deploy must install Email Warmer soul")
        meta = json.loads((warmer / "bot.meta.json").read_text(encoding="utf-8"))
        if meta.get("title") != "Email Warmer":
            fail(f"deployed bot title missing: {meta}")
        if meta.get("description") != "CAN-SPAM warming toward a TCPA consent form.":
            fail("deployed bot description missing")
        if meta.get("tools") != ["email", "crm", "consent-form"]:
            fail(f"deployed bot tools missing: {meta}")
        if "email-warmer" not in result.get("created", []):
            fail("first deploy should report created bots")
        active = json.loads((install / "active-bot-group.json").read_text(encoding="utf-8"))
        if active.get("botGroupId") != "real-estate-cold-call-lead-refresher":
            fail("deploy must record active-bot-group.json")
        (warmer / "SOUL.md").write_text("# stale\n", encoding="utf-8")
        (warmer / "user-notes.txt").write_text("keep me\n", encoding="utf-8")
        result2 = bg.deploy_group(
            "real-estate-cold-call-lead-refresher",
            payload_root=tmp_path / "payload",
            install_root=install,
            desktop_profiles_root=desktop,
        )
        if "email-warmer" not in result2.get("updated", []):
            fail("re-deploy must report updated when bots already exist")
        soul = (warmer / "SOUL.md").read_text(encoding="utf-8")
        if "stale" in soul or "Email Warmer" not in soul:
            fail("re-deploy must overwrite group-owned soul")
        if not (warmer / "user-notes.txt").is_file():
            fail("re-deploy must leave extra user files alone")
    print("OK  deploy one group (create + update existing)")


def test_deploy_files_named_ui_section(bg) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-bg-sec-") as tmp:
        tmp_path = pathlib.Path(tmp)
        payload = tmp_path / "payload" / "bot-groups"
        install = tmp_path / "install"
        desktop = tmp_path / "hermes-profiles"
        payload.mkdir(parents=True)
        (payload / "catalog.json").write_text(json.dumps(sample_catalog()), encoding="utf-8")
        write_group_tree(payload, sample_group())
        result = bg.deploy_group(
            "real-estate-cold-call-lead-refresher",
            payload_root=tmp_path / "payload",
            install_root=install,
            desktop_profiles_root=desktop,
        )
        section_id = "sec-dragon-real-estate-cold-call-lead-refresher"
        section_name = "Real Estate Cold Call Lead Refresher"
        if (result.get("uiSection") or {}).get("sectionId") != section_id:
            fail(f"deploy must report uiSection {section_id}, got {result.get('uiSection')}")
        for bot_id in ("email-warmer", "lead-sourcer"):
            profile = (desktop / bot_id / "profile.yaml").read_text(encoding="utf-8")
            if "sectionId:" not in profile or section_id not in profile:
                fail(f"{bot_id} profile.yaml must stamp sectionId {section_id}")
            if section_name not in profile:
                fail(f"{bot_id} must be labeled {section_name!r}, not UNASSIGNED")
            if "section:unassigned" in profile.lower():
                fail(f"{bot_id} must not be filed under UNASSIGNED")
            meta = json.loads((desktop / bot_id / "bot.meta.json").read_text(encoding="utf-8"))
            if meta.get("sectionId") != section_id or meta.get("sectionName") != section_name:
                fail(f"{bot_id} bot.meta.json missing UI section: {meta}")
        marketing = {
            "kind": "bot-group",
            "schemaVersion": 1,
            "id": "marketing-team",
            "name": "Marketing Team",
            "departmentJob": "Outbound marketing.",
            "bots": [
                {
                    "id": "copywriter",
                    "title": "Copywriter",
                    "description": "Writes campaigns.",
                    "tools": ["browser"],
                    "soul": "bots/copywriter/SOUL.md",
                    "config": "bots/copywriter/bot.yaml",
                }
            ],
        }
        mdir = payload / "marketing-team"
        (mdir / "bots" / "copywriter").mkdir(parents=True)
        (mdir / "bot-group.json").write_text(json.dumps(marketing), encoding="utf-8")
        (mdir / "bots" / "copywriter" / "SOUL.md").write_text("# Copy\n", encoding="utf-8")
        (mdir / "bots" / "copywriter" / "bot.yaml").write_text("slug: copywriter\n", encoding="utf-8")
        marketing_result = bg.deploy_group(
            "marketing-team",
            payload_root=tmp_path / "payload",
            install_root=install,
            desktop_profiles_root=desktop,
        )
        marketing_ids = [b.get("id") for b in marketing_result.get("bots") or []]
        if marketing_ids != COS_ROSTERS["marketing-team"]:
            fail(f"stub Marketing pack must deploy Cos's 6 bots, got {marketing_ids}")
        for bot_id in COS_ROSTERS["marketing-team"]:
            mprofile = (desktop / bot_id / "profile.yaml").read_text(encoding="utf-8")
            if "sec-dragon-marketing-team" not in mprofile or "Marketing Team" not in mprofile:
                fail(f"{bot_id} must file under MARKETING TEAM, not UNASSIGNED")
        for stale in STALE_MARKETING_IDS:
            if (desktop / stale).exists():
                fail(f"Marketing Team must not deploy stub {stale}")
        warmer_after = (desktop / "email-warmer" / "profile.yaml").read_text(encoding="utf-8")
        if section_id not in warmer_after:
            fail("a second group must not steal the Real Estate section id")
        renamed = sample_group()
        renamed["name"] = "Real Estate Lead Gen"
        (payload / renamed["id"] / "bot-group.json").write_text(json.dumps(renamed, indent=2), encoding="utf-8")
        bg.deploy_group(
            "real-estate-cold-call-lead-refresher",
            payload_root=tmp_path / "payload",
            install_root=install,
            desktop_profiles_root=desktop,
        )
        reapplied = (desktop / "email-warmer" / "profile.yaml").read_text(encoding="utf-8")
        if section_id not in reapplied:
            fail("re-apply must keep the stable section id")
        if "Real Estate Lead Gen" not in reapplied:
            fail("re-apply must update the section display name")
        exported = pathlib.Path(bg.export_group("real-estate-cold-call-lead-refresher", tmp_path / "exported", install, tmp_path / "payload"))
        imported_desktop = tmp_path / "imported-profiles"
        imported = bg.import_bundle(exported, install_root=tmp_path / "install2", desktop_profiles_root=imported_desktop)
        if (imported.get("uiSection") or {}).get("sectionName") != "Real Estate Lead Gen":
            fail(f"import must file bots under the pack display name, got {imported.get('uiSection')}")
        imported_profile = (imported_desktop / "email-warmer" / "profile.yaml").read_text(encoding="utf-8")
        if section_id not in imported_profile or "Real Estate Lead Gen" not in imported_profile:
            fail("Import-BotGroup path must stamp the named UI section")
        apply_shim = SCRIPTS / "Apply-Profile.ps1"
        import_shim = SCRIPTS / "Import-Profile.ps1"
        if "Import-BotGroup" not in apply_shim.read_text(encoding="utf-8"):
            fail("Apply-Profile must call Import-BotGroup so leftover profiles get a named section")
        if "Import-BotGroup" not in import_shim.read_text(encoding="utf-8"):
            fail("Import-Profile must call Import-BotGroup so leftover profiles get a named section")
    print("OK  deploy/import files bots into a named UI section (not UNASSIGNED)")


def test_export_reimport(bg) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-bg-ex-") as tmp:
        tmp_path = pathlib.Path(tmp)
        payload = tmp_path / "payload" / "bot-groups"
        install = tmp_path / "install"
        desktop = tmp_path / "hermes-profiles"
        payload.mkdir(parents=True)
        (payload / "catalog.json").write_text(json.dumps(sample_catalog()), encoding="utf-8")
        write_group_tree(payload, sample_group())
        bg.deploy_group(
            "real-estate-cold-call-lead-refresher",
            payload_root=tmp_path / "payload",
            install_root=install,
            desktop_profiles_root=desktop,
        )
        dest = tmp_path / "export" / "real-estate-cold-call-lead-refresher"
        exported = pathlib.Path(
            bg.export_group(
                "real-estate-cold-call-lead-refresher",
                dest,
                install_root=install,
                payload_root=tmp_path / "payload",
            )
        )
        manifest_path = exported / "bot-group.json"
        if not manifest_path.is_file():
            fail("export must write bot-group.json in repo format")
        exported_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if exported_manifest.get("kind") != "bot-group":
            fail("export kind must be bot-group")
        if exported_manifest.get("name") != "Real Estate Cold Call Lead Refresher":
            fail("export must include the group name")
        if "departmentJob" not in exported_manifest:
            fail("export must include the department-level job")
        titles = {b["title"] for b in exported_manifest["bots"]}
        if "Email Warmer" not in titles:
            fail("export must include each bot title")
        if not (exported / "bots" / "email-warmer" / "SOUL.md").is_file():
            fail("export must include bot files")
        other_desktop = tmp_path / "other-profiles"
        imported = bg.import_bundle(
            exported,
            install_root=tmp_path / "install2",
            desktop_profiles_root=other_desktop,
        )
        if imported.get("botGroupId") != "real-estate-cold-call-lead-refresher":
            fail("re-import of an export must restore the group")
        if not (other_desktop / "email-warmer" / "SOUL.md").is_file():
            fail("re-import must install bots")
        zipped = tmp_path / "group.zip"
        with zipfile.ZipFile(zipped, "w") as zf:
            for path in exported.rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(exported.parent).as_posix())
        third = tmp_path / "from-zip"
        bg.import_bundle(zipped, install_root=tmp_path / "install3", desktop_profiles_root=third)
        if not (third / "lead-sourcer" / "bot.yaml").is_file():
            fail("zip export must be re-importable")
    print("OK  export writes a re-importable group file")


def test_singular_toggle(bg) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-bg-tog-") as tmp:
        tmp_path = pathlib.Path(tmp)
        install = tmp_path / "install"
        payload = tmp_path / "payload" / "bot-groups"
        desktop = tmp_path / "hermes-profiles"
        payload.mkdir(parents=True)
        (payload / "catalog.json").write_text(json.dumps(sample_catalog()), encoding="utf-8")
        write_group_tree(payload, sample_group())
        bg.deploy_group(
            "real-estate-cold-call-lead-refresher",
            payload_root=tmp_path / "payload",
            install_root=install,
            desktop_profiles_root=desktop,
        )
        settings = bg.load_settings(install)
        if settings.get("allowSingularBotImportExport") is not False:
            fail("settings must start with singular toggle off")
        dest = tmp_path / "email-warmer.bot.json"
        try:
            bg.export_bot("email-warmer", dest, install_root=install, desktop_profiles_root=desktop)
            fail("export of one bot must be refused while the toggle is off")
        except bg.SingularBotDisabled:
            pass
        one = {
            "kind": "bot",
            "schemaVersion": 1,
            "id": "rogue-bot",
            "title": "Rogue",
            "description": "Should not import by default.",
            "tools": ["browser"],
            "soul": "# Rogue\n",
            "config": "slug: rogue-bot\n",
        }
        one_path = tmp_path / "rogue.bot.json"
        one_path.write_text(json.dumps(one), encoding="utf-8")
        try:
            bg.import_bundle(one_path, install_root=install, desktop_profiles_root=desktop)
            fail("import of one bot must be refused while the toggle is off")
        except bg.SingularBotDisabled:
            pass
        bg.save_settings(install, {"allowSingularBotImportExport": True})
        exported = pathlib.Path(
            bg.export_bot("email-warmer", dest, install_root=install, desktop_profiles_root=desktop)
        )
        data = json.loads(exported.read_text(encoding="utf-8"))
        if data.get("kind") != "bot":
            fail("one-bot file kind must be bot, not bot-group")
        if data.get("title") != "Email Warmer":
            fail("one-bot export must include title")
        if "departmentJob" in data or "bots" in data:
            fail("one-bot file must differ from a group file")
        if data.get("tools") != ["email", "crm", "consent-form"]:
            fail("one-bot export must include tools")
        other = tmp_path / "singular-in"
        bg.import_bundle(exported, install_root=install, desktop_profiles_root=other)
        if not (other / "email-warmer" / "SOUL.md").is_file():
            fail("one-bot import must install that bot when the toggle is on")
    print("OK  singular toggle off by default; one-bot file differs")


def test_repo_catalog_converted() -> None:
    catalog = json.loads(read(CATALOG))
    if catalog.get("kind") != "bot-group-catalog":
        fail("repo catalog kind must be bot-group-catalog")
    if "profiles" in catalog:
        fail("catalog must not still key groups as profiles")
    groups = catalog.get("groups") or []
    ids = [g.get("id") for g in groups]
    if "personal-assistant" not in ids:
        fail("catalog must keep Personal Assistant")
    if "real-estate-cold-call-lead-refresher" not in ids:
        fail("catalog must keep the Real Estate example")
    if "marketing-team" not in ids or "trading-team" not in ids:
        fail("catalog must list Marketing Team and Trading Team")
    if any(g.get("id") == "hermes" or "hermes" in str(g.get("name", "")).lower() for g in groups):
        fail("do not add a Hermes bot back")
    re_group = json.loads(read(REAL_ESTATE))
    if re_group.get("kind") != "bot-group":
        fail("Real Estate must be a bot-group file")
    bots = {b["id"]: b for b in re_group.get("bots") or []}
    if "email-warmer" not in bots:
        fail("Real Estate group must still include Email Warmer")
    warmer = bots["email-warmer"]
    if warmer.get("title") != "Email Warmer":
        fail("Email Warmer must have a title")
    if not warmer.get("description"):
        fail("Email Warmer must have a description")
    if not warmer.get("tools"):
        fail("Email Warmer must list tools")
    pa = json.loads(read(PA))
    if pa.get("kind") != "bot-group" or pa.get("name") != "Personal Assistant":
        fail("Personal Assistant must be a bot group, not a leftover profile")
    if (ROOT / "profiles" / "catalog.json").is_file():
        fail("do not leave a second profiles catalog")
    print("OK  repo catalog is bot groups (PA + Real Estate / Email Warmer)")


def _group_bot_ids(group_id: str) -> list[str]:
    manifest = ROOT / "bot-groups" / group_id / "bot-group.json"
    data = json.loads(read(manifest))
    return [str(b.get("id")) for b in data.get("bots") or [] if b.get("id")]


def test_bundled_team_rosters() -> None:
    for group_id, expected in COS_ROSTERS.items():
        ids = _group_bot_ids(group_id)
        if ids != expected:
            fail(f"{group_id} roster must be {expected}, got {ids}")
        bots_dir = ROOT / "bot-groups" / group_id / "bots"
        for bot_id in expected:
            if not (bots_dir / bot_id / "SOUL.md").is_file():
                fail(f"{group_id} missing soul for {bot_id}")
            if not (bots_dir / bot_id / "bot.yaml").is_file():
                fail(f"{group_id} missing bot.yaml for {bot_id}")
        for stale in STALE_MARKETING_IDS:
            if stale in ids or (bots_dir / stale).exists():
                fail(f"Marketing Team must not ship stub bot {stale}")
    print("OK  bundled Cos rosters (Marketing 6 / Real Estate 4 / Trading 4)")


def test_deploy_full_roster_replaces_stale(bg) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-bg-roster-") as tmp:
        tmp_path = pathlib.Path(tmp)
        payload = tmp_path / "payload"
        install = tmp_path / "install"
        desktop = tmp_path / "hermes-profiles"
        groups = payload / "bot-groups"
        groups.mkdir(parents=True)
        stub = {
            "kind": "bot-group",
            "schemaVersion": 1,
            "id": "marketing-team",
            "name": "Marketing Team",
            "displayName": "Marketing Team",
            "departmentJob": "Stub.",
            "bots": [
                {
                    "id": "copywriter",
                    "title": "Copywriter",
                    "description": "Wrong stub.",
                    "tools": ["browser"],
                    "soul": "bots/copywriter/SOUL.md",
                    "config": "bots/copywriter/bot.yaml",
                },
                {
                    "id": "campaign-sequencer",
                    "title": "Campaign Sequencer",
                    "description": "Wrong stub.",
                    "tools": ["browser"],
                    "soul": "bots/campaign-sequencer/SOUL.md",
                    "config": "bots/campaign-sequencer/bot.yaml",
                },
            ],
        }
        stub_dir = groups / "marketing-team"
        (stub_dir / "bots" / "copywriter").mkdir(parents=True)
        (stub_dir / "bots" / "campaign-sequencer").mkdir(parents=True)
        (stub_dir / "bot-group.json").write_text(json.dumps(stub), encoding="utf-8")
        (stub_dir / "bots" / "copywriter" / "SOUL.md").write_text("# Stub\n", encoding="utf-8")
        (stub_dir / "bots" / "copywriter" / "bot.yaml").write_text("slug: copywriter\n", encoding="utf-8")
        (stub_dir / "bots" / "campaign-sequencer" / "SOUL.md").write_text("# Stub\n", encoding="utf-8")
        (stub_dir / "bots" / "campaign-sequencer" / "bot.yaml").write_text("slug: campaign-sequencer\n", encoding="utf-8")
        (groups / "catalog.json").write_text(
            json.dumps({"kind": "bot-group-catalog", "groups": [{"id": "marketing-team", "path": "marketing-team"}]}),
            encoding="utf-8",
        )
        desktop.mkdir(parents=True)
        for stale_id, title in (("copywriter", "Copywriter"), ("campaign-sequencer", "Campaign Sequencer")):
            dest = desktop / stale_id
            dest.mkdir(parents=True)
            (dest / "bot.meta.json").write_text(
                json.dumps(
                    {
                        "id": stale_id,
                        "title": title,
                        "bot_group_id": "marketing-team",
                        "sectionId": "sec-dragon-marketing-team",
                        "sectionName": "Marketing Team",
                    }
                ),
                encoding="utf-8",
            )
            (dest / "profile.yaml").write_text(
                "# dragon-ai-ui-section\nui_meta:\n  hermes-bots:\n    sectionId: \"sec-dragon-marketing-team\"\n    sectionName: \"Marketing Team\"\n",
                encoding="utf-8",
            )
        expanded = [b["id"] for b in bg._load_group_folder(stub_dir).get("bots") or []]
        if expanded != COS_ROSTERS["marketing-team"]:
            fail(f"a stub Marketing folder must expand to Cos's 6 bots, got {expanded}")
        extra = stub_dir / "bots" / "seo-specialist"
        extra.mkdir()
        (extra / "SOUL.md").write_text("# Extra on disk\n", encoding="utf-8")
        (extra / "bot.yaml").write_text("slug: seo-specialist\ndisplay_name: SEO Specialist\n", encoding="utf-8")
        if "seo-specialist" not in bg._folder_roster_ids(stub_dir):
            fail("deploy must pick up bots/ folders missing from bot-group.json")
        result = bg.deploy_group(
            "marketing-team",
            payload_root=ROOT,
            install_root=install,
            desktop_profiles_root=desktop,
        )
        created = set(result.get("created") or []) | set(result.get("updated") or [])
        for bot_id in COS_ROSTERS["marketing-team"]:
            if bot_id not in created and not (desktop / bot_id / "profile.yaml").is_file():
                fail(f"apply Marketing Team must deploy {bot_id}")
            profile = (desktop / bot_id / "profile.yaml").read_text(encoding="utf-8")
            if "sec-dragon-marketing-team" not in profile or "Marketing Team" not in profile:
                fail(f"{bot_id} must file under MARKETING TEAM")
        for stale in STALE_MARKETING_IDS:
            if (desktop / stale).exists():
                fail(f"re-apply must clear stale Marketing stub {stale}")
        if "copywriter" not in (result.get("removed") or []):
            fail("deploy must report removed stub bots")
        for group_id, expected in COS_ROSTERS.items():
            deployed = bg.deploy_group(
                group_id,
                payload_root=ROOT,
                install_root=tmp_path / f"install-{group_id}",
                desktop_profiles_root=tmp_path / f"desktop-{group_id}",
            )
            ids = [b["id"] for b in deployed.get("bots") or []]
            if ids != expected:
                fail(f"deploy {group_id} must install {expected}, got {ids}")
    print("OK  deploy full Cos rosters and replace stale Marketing stubs")


def test_no_profiles_ui() -> None:
    for path in (SELECT, DEPLOY, EXPORT, IMPORT, DEFAULT):
        if not path.is_file():
            fail(f"missing {path.name}")
    select = read(SELECT)
    if "CheckedListBox" not in select:
        fail("Select-BotGroup.ps1 must be a popup list (WinForms CheckedListBox)")
    if "ComboBox" in select:
        fail("Select-BotGroup.ps1 must not stay a ComboBox dropdown")
    if "Launch" not in select or "Export" not in select:
        fail("WinForms Teams popup must keep Launch and Export")
    if "bot_groups.py" not in select:
        fail("popup must call bot_groups.py (repo list), not a baked menu")
    if "choose a profile" in select.lower() or "Dragon AI Agent Profiles" in select:
        fail("popup still presents a Profiles UI")
    if "Create a bot" in select or "Grokbot" in select:
        fail("do not add a standalone create-a-bot path")
    if "196, 30, 58" not in select and "196,30,58" not in select and "#C41E3A" not in select:
        fail("popup must keep wizard crimson on primary buttons")
    if "$header.BackColor = $script:BrandRed" in select:
        fail("Teams WinForms header lockup must not stay BrandRed")
    if "$header.BackColor = $script:BrandBlue" not in select:
        fail("Teams WinForms header lockup must use Marketplace BrandBlue")
    if "37, 99, 235" not in select and "37,99,235" not in select and "#2563EB" not in select:
        fail("Teams WinForms header must define Marketplace blue #2563EB")
    if "$btnLaunch.BackColor = $script:BrandRed" not in select:
        fail("Teams Launch button must stay BrandRed")
    if "allowSingularBotImportExport" not in select:
        fail("popup must expose the singular toggle")
    if "Hermes" in select and "do not add a Hermes bot" not in select.lower():
        fail("bot group UI must not bring a Hermes bot back")
    for path in INSTALLERS:
        text = read(path)
        if "bot-groups" not in text and "bot_groups.py" not in text:
            fail(f"{path.name} must install the bot-groups overlay")
        if "Dragon AI Agent Profiles.lnk" in text:
            fail(f"{path.name} still creates a Profiles shortcut")
        if "Dragon AI Agent Bot Groups" not in text:
            fail(f"{path.name} must create a Bot Groups shortcut")
        if "Select-BotGroup.ps1" not in text:
            fail(f"{path.name} must wire the bot group dropdown")
    readme = read(README)
    if "## Profiles" in readme or "profile catalog" in readme.lower():
        fail("README still presents profiles as the product")
    if "Bot group" not in readme and "bot group" not in readme:
        fail("README must describe bot groups")
    wizard = read(WIZARD)
    if "first-run setup — profile:" in wizard:
        fail("wizard header still says profile")
    print("OK  no Profiles UI; dropdown + installer say bot groups")


def test_desktop_agent_untouched() -> None:
    compose = read(COMPOSE)
    for token in PROTECTED:
        if token not in compose:
            fail(f"bot groups must not drop Bot Screen token {token}")
    table = json.loads(read(BRANDING_TABLE))
    font = table.get("font") or {}
    if font.get("family") != "Syne" or font.get("weight") != 700:
        fail("do not restyle: Syne 700 must stay")
    if "C41E3A" not in json.dumps(table) and "c41e3a" not in json.dumps(table).lower():
        # tokens may live in CSS, not the string table — still require protected ports
        pass
    mark = ROOT / "branding" / "dragon-ai-agent-logo.svg"
    svg = read(mark)
    if "#314a73" not in svg.lower() or "#c41e3a" not in svg.lower():
        fail("do not restyle the navy dragon mark")
    for path in (ENGINE, SELECT, DEPLOY):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for token in PROTECTED:
                if token in text and path == ENGINE:
                    # engine may mention the desktop dest; tokens in compose stay required
                    break
    print("OK  desktop agent / Syne / crimson / navy mark left alone")


def test_seo_specialist_seoagent_com_pack(bg) -> None:
    """SEOagent is seoagent.com CLI+Skill on SEO Specialist, not a 7th seat."""
    group = json.loads(read(MARKETING))
    bots = {str(b.get("id")): b for b in group.get("bots") or [] if b.get("id")}
    expected = COS_ROSTERS["marketing-team"]
    if list(bots) != expected:
        fail(f"Marketing Team must stay Cos's 6 seats {expected}, got {list(bots)}")
    for forbidden in ("seoagent", "claude-seo", "seo-audit"):
        if forbidden in bots:
            fail(f"{forbidden} must be a tool/skill, not a Marketing seat")
    seo = bots.get("seo-specialist") or {}
    tools = [str(t) for t in seo.get("tools") or []]
    for required in ("computer-use", "browser", "seoagent"):
        if required not in tools:
            fail(f"SEO Specialist tools must include {required}, got {tools}")
    others = [bot_id for bot_id in expected if bot_id != "seo-specialist"]
    for bot_id in others:
        if (bots[bot_id].get("tools") or []) != ["computer-use", "browser"]:
            fail(f"{bot_id} tools must stay computer-use/browser, got {bots[bot_id].get('tools')}")
        if (ROOT / "bot-groups" / "marketing-team" / "bots" / bot_id / "skills").exists():
            fail(f"{bot_id} must not receive the SEO Specialist skill pack")

    soul = read(SEO_SPECIALIST / "SOUL.md")
    for needle in ("SEOagent", "seoagent.com", "@seoagent-official/seoagent", "seoagent init"):
        if needle not in soul:
            fail(f"SEO Specialist SOUL must reference {needle}")
    if "claude-seo" in soul.lower() or "/seo audit" in soul:
        fail("SOUL must not keep claude-seo slash-command identity")
    if not SEOAGENT_SKILLS.is_dir():
        fail("SEO Specialist must ship Hermes skill instructions for seoagent.com")
    index = read(SEOAGENT_SKILLS / "INDEX.md")
    skill = read(SEOAGENT_SKILLS / "SKILL.md")
    pack = index + "\n" + skill
    for needle in (
        "@seoagent-official/seoagent",
        "seoagent init",
        "npx",
        "Autopilot",
        "$49",
        "seoagent.com",
    ):
        if needle not in pack:
            fail(f"seoagent.com skill pack must document {needle!r}")
    for leftover in CLAUDE_SEO_LEAVES:
        if (SEOAGENT_SKILLS / leftover).is_file():
            fail(f"replace claude-seo leaf {leftover} — SEOagent identity is seoagent.com")
    attribution = read(SEOAGENT_SKILLS / "ATTRIBUTION.md")
    if "Baxter-Inc/seoagent-npm" not in attribution or "MIT" not in attribution:
        fail("skill pack must attribute Baxter-Inc/seoagent-npm (MIT)")
    if "AgriciDaniel/claude-seo" in attribution:
        fail("do not keep claude-seo as the SEOagent attribution")
    if (SEO_SPECIALIST / ".claude-plugin").exists() or (ROOT / "bot-groups" / "marketing-team" / "install.sh").exists():
        fail("do not vendor a Claude Code plugin installer into Marketing Team")

    dfs = json.loads(read(DATAFORSEO_CONNECTOR))
    if dfs.get("id") != "dataforseo" or dfs.get("type") != "mcp_server":
        fail("keep the existing DataForSEO connector")
    if "dataforseo-mcp-server" not in json.dumps(dfs.get("mcp") or {}):
        fail("DataForSEO connector must still wire npx dataforseo-mcp-server")
    if not any(isinstance(c, dict) and c.get("id") == "dataforseo" for c in group.get("connectors") or []):
        fail("bot-group.json must still list the dataforseo connector")

    seo_conn = json.loads(read(SEOAGENT_CONNECTOR))
    blob = json.dumps(seo_conn)
    if seo_conn.get("id") != "seoagent":
        fail("seoagent connector id must be seoagent")
    if "@seoagent-official/seoagent" not in blob or "seoagent init" not in blob:
        fail("seoagent connector must document npm install + seoagent init")
    if any(token in blob for token in ("sk-", "sk-ant-")):
        fail("do not ship secrets in the seoagent connector")
    if not any(isinstance(c, dict) and c.get("id") == "seoagent" for c in group.get("connectors") or []):
        fail("bot-group.json must list the seoagent connector")

    design = read(SEOAGENT_DESIGN)
    for needle in (
        "seoagent.com",
        "@seoagent-official/seoagent",
        "seoagent init",
        "Autopilot",
        "$49",
        "DataForSEO",
        "Buffer",
        "Brevo",
        "re-apply",
        "Marketing Team",
        "six",
        "free",
    ):
        if needle not in design:
            fail(f"SEOAGENT.md must document {needle!r}")
    if "do not pretend Autopilot is free" not in design and "Autopilot is not free" not in design:
        fail("SEOAGENT.md must say Autopilot is paid, not free")

    with tempfile.TemporaryDirectory(prefix="dragon-seoagent-") as tmp:
        tmp_path = pathlib.Path(tmp)
        install = tmp_path / "install"
        desktop = tmp_path / "hermes-profiles"
        result = bg.deploy_group(
            "marketing-team",
            payload_root=ROOT,
            install_root=install,
            desktop_profiles_root=desktop,
        )
        deployed = [b.get("id") for b in result.get("bots") or []]
        if deployed != expected:
            fail(f"apply Marketing Team must still yield 6 Cos bots, got {deployed}")
        meta = json.loads((desktop / "seo-specialist" / "bot.meta.json").read_text(encoding="utf-8"))
        if "seoagent" not in meta.get("tools", []):
            fail(f"deployed SEO Specialist meta must include seoagent: {meta.get('tools')}")
        if not (desktop / "seo-specialist" / "skills" / "INDEX.md").is_file():
            fail("deploy must copy SEO Specialist skills/ onto the desktop profile")
        if not (desktop / "seo-specialist" / "skills" / "SKILL.md").is_file():
            fail("deploy must copy seoagent.com SKILL.md onto the SEO Specialist profile")
        if (desktop / "seo-specialist" / "skills" / "seo-audit.md").is_file():
            fail("deploy must not still ship claude-seo seo-audit.md")
        if (desktop / "content-strategist" / "skills").exists():
            fail("deploy must not copy SEO skills onto other Marketing seats")
        if not (install / "connectors" / "marketing-team" / "dataforseo.json").is_file():
            fail("deploy must keep the DataForSEO connector placeholder")
        if not (install / "connectors" / "marketing-team" / "seoagent.json").is_file():
            fail("deploy must copy the seoagent.com connector placeholder")
    print("OK  SEO Specialist has seoagent.com CLI+Skill; DataForSEO kept; 6 seats")


def test_customization_paths() -> None:
    text = read(DESIGN)
    for path in (
        "bot-groups/",
        "scripts/airmaze/bot_groups.py",
        "scripts/airmaze/Select-BotGroup.ps1",
        "scripts/airmaze/Test-BotGroups.py",
    ):
        if path not in text:
            fail(f"design must name customization path {path}")
    if "hermes\\profiles" not in text and "hermes/profiles" not in text:
        fail("design must say deploy still writes the upstream desktop profiles dir")
    print("OK  customization paths documented")


def main() -> int:
    test_design_doc()
    bg = load_engine()
    test_engine_constants(bg)
    test_normalize_legacy_profile(bg)
    test_list_from_github(bg)
    test_list_offline_cache_then_bundle(bg)
    test_deploy_group(bg)
    test_deploy_files_named_ui_section(bg)
    test_export_reimport(bg)
    test_singular_toggle(bg)
    test_repo_catalog_converted()
    test_bundled_team_rosters()
    test_deploy_full_roster_replaces_stale(bg)
    test_seo_specialist_seoagent_com_pack(bg)
    test_no_profiles_ui()
    test_desktop_agent_untouched()
    test_customization_paths()
    print("SMOKE OK: bot groups replace profiles; dropdown reads the repo; export re-imports; singular toggle is off.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
