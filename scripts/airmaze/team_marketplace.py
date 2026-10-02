#!/usr/bin/env python3
"""Dragon AI Teams marketplace v1 — catalog listing, Install, scrubbed publish.

Same job as the Teams popup. Browse GitHub `bot-groups/catalog.json`,
Install through apply_team / deploy_group, Export/Publish with secrets stripped.
Recipe packs only. No payments. No live logins.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bot_groups as bg  # noqa: E402
import teams_picker as tp  # noqa: E402

KIND_MARKETPLACE = "dragon-teams-marketplace"
DEFAULT_AUTHOR = "Dragon AI"
FEATURED_IDS = (
    "real-estate-cold-call-lead-refresher",
    "marketing-team",
    "trading-team",
)
SKIP_PUBLISH_NAMES = {".env", "secrets.json", "credentials.json", ".netrc", "id_rsa"}
SECRET_KEY_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "api_key_value",
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "private_key",
        "client_secret",
        "authorization",
        "auth_token",
        "xai_api_key",
        "openai_api_key",
        "secret_key",
        "access_key",
    }
)
SECRET_KEY_SUFFIXES = ("_secret", "_password", "_token")
ALLOWED_EMAIL_DOMAINS = frozenset({"example.com", "example.org", "example.net"})
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
WIN_PATH_RE = re.compile(r"(?i)(?:[A-Z]:\\|\\\\)[^\s\"']+")
UNIX_HOME_RE = re.compile(r"(?i)(?:/Users/|/home/)[^\s\"']+")
ENV_PATH_RE = re.compile(r"(?i)%(?:USERPROFILE|LOCALAPPDATA|APPDATA|HOME)%[^\s\"']*")
KEY_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|xai-[A-Za-z0-9_-]{16,}|"
    r"Bearer\s+[A-Za-z0-9._\-]{16,})\b"
)
TEXT_SUFFIXES = {".json", ".md", ".yaml", ".yml", ".txt", ".env", ".csv"}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_connectors(raw: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in _as_list(raw):
        if isinstance(item, str) and item.strip():
            conn_id = item.strip()
            display = conn_id
        elif isinstance(item, dict) and item.get("id"):
            conn_id = str(item["id"]).strip()
            display = str(item.get("displayName") or item.get("name") or conn_id).strip()
        else:
            continue
        if not conn_id or conn_id in seen:
            continue
        seen.add(conn_id)
        out.append({"id": conn_id, "displayName": display})
    return out


def required_connectors(listing: dict[str, Any], group: dict[str, Any] | None = None) -> list[dict[str, str]]:
    group = group if isinstance(group, dict) else {}
    listed = listing.get("requiredConnectors") or group.get("requiredConnectors")
    found = normalize_connectors(listed)
    if found:
        return found
    found = normalize_connectors(group.get("connectors") or listing.get("connectors"))
    if found:
        return found
    tools: list[str] = []
    for bot in group.get("bots") or []:
        if isinstance(bot, dict):
            tools.extend(str(t) for t in _as_list(bot.get("tools")) if t)
    return normalize_connectors(tools)


def listing_fields(entry: dict[str, Any], group: dict[str, Any] | None = None) -> dict[str, Any]:
    group = group if isinstance(group, dict) else {}
    bots = [b for b in (group.get("bots") or []) if isinstance(b, dict) and b.get("id")]
    seats_raw = entry.get("seats") or entry.get("seatCount") or group.get("seats")
    if seats_raw in (None, ""):
        seats_raw = len(bots) if bots else entry.get("botCount") or 0
    blurb = str(entry.get("blurb") or group.get("blurb") or group.get("departmentJob") or entry.get("departmentJob") or "").strip()
    detail = str(entry.get("detail") or group.get("detail") or "").strip() or blurb
    author = str(entry.get("author") or group.get("author") or DEFAULT_AUTHOR).strip() or DEFAULT_AUTHOR
    return {
        "blurb": blurb,
        "detail": detail,
        "author": author,
        "seats": int(seats_raw or 0),
        "requiredConnectors": required_connectors(entry, group),
        "featured": bool(entry.get("featured") or group.get("featured")),
    }


def present_pack(group: dict[str, Any], listing: dict[str, Any] | None = None) -> dict[str, Any]:
    listing = listing if isinstance(listing, dict) else {}
    fields = listing_fields(listing, group)
    bots = [b for b in (group.get("bots") or []) if isinstance(b, dict) and b.get("id")]
    if not fields["seats"] and bots:
        fields["seats"] = len(bots)
    base = tp.present_team(group, listing)
    base.update(fields)
    base["seatCount"] = fields["seats"]
    if not base.get("bots"):
        base["bots"] = [tp.present_seat(b) for b in bots]
    return base


def _merge_listing(group: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    merged = dict(entry)
    merged.update({k: v for k, v in group.items() if v not in (None, "", [])})
    if entry.get("displayName") and not group.get("displayName"):
        merged["displayName"] = entry["displayName"]
    return merged


def list_marketplace(
    payload_root: Path | str,
    install_root: Path | str,
    fetcher: Any | None = None,
) -> dict[str, Any]:
    listed = tp.list_teams(payload_root, install_root, fetcher=fetcher)
    catalog_entries = {str(e.get("id")): e for e in tp._bundled_entries(payload_root) if e.get("id")}
    teams: list[dict[str, Any]] = []
    for team in listed.get("teams") or []:
        if not isinstance(team, dict) or not team.get("id"):
            continue
        entry = catalog_entries.get(str(team["id"])) or {}
        pack = dict(team)
        pack.update(listing_fields(entry, team))
        pack["seatCount"] = pack["seats"]
        if not pack.get("bots"):
            pack["bots"] = []
        teams.append(pack)
    featured = [p for p in teams if p.get("id") in FEATURED_IDS]
    featured.sort(key=lambda p: FEATURED_IDS.index(str(p["id"])))
    rest = [p for p in teams if p.get("id") not in FEATURED_IDS]
    rest.sort(key=lambda p: str(p.get("displayName") or p.get("name") or p.get("id") or "").lower())
    ordered = featured + rest
    return {
        "kind": KIND_MARKETPLACE,
        "source": listed.get("source"),
        "teams": ordered,
        "endpoint": listed.get("endpoint"),
    }


def get_marketplace_pack(
    pack_id: str,
    payload_root: Path | str,
    install_root: Path | str,
    fetcher: Any | None = None,
) -> dict[str, Any]:
    listed = list_marketplace(payload_root, install_root, fetcher=fetcher)
    for pack in listed.get("teams") or []:
        if str(pack.get("id")) == pack_id:
            return pack
    raise FileNotFoundError(f"marketplace pack {pack_id!r} not found")


def install_pack(
    pack_id: str,
    payload_root: Path | str,
    install_root: Path | str,
    desktop_profiles_root: Path | str,
    embedded_profiles_root: Path | str | None = None,
    fetcher: Any | None = None,
) -> dict[str, Any]:
    result = tp.apply_team(
        pack_id,
        payload_root=payload_root,
        install_root=install_root,
        desktop_profiles_root=desktop_profiles_root,
        embedded_profiles_root=embedded_profiles_root,
        fetcher=fetcher,
    )
    result["installedFrom"] = "marketplace"
    return result


def _is_secret_key(name: str) -> bool:
    key = str(name or "").strip().lower().replace("-", "_")
    if key in SECRET_KEY_NAMES:
        return True
    return any(key.endswith(suffix) for suffix in SECRET_KEY_SUFFIXES)


def scrub_text(text: str) -> tuple[str, list[str]]:
    findings: list[str] = []

    def email_sub(match: re.Match[str]) -> str:
        addr = match.group(0)
        domain = addr.rsplit("@", 1)[-1].lower()
        if domain in ALLOWED_EMAIL_DOMAINS:
            return addr
        findings.append("email")
        return "<redacted-email>"

    def path_sub(_match: re.Match[str]) -> str:
        findings.append("local-path")
        return "<local-path>"

    def key_sub(_match: re.Match[str]) -> str:
        findings.append("api-key")
        return "<redacted-key>"

    out = EMAIL_RE.sub(email_sub, text)
    out = WIN_PATH_RE.sub(path_sub, out)
    out = UNIX_HOME_RE.sub(path_sub, out)
    out = ENV_PATH_RE.sub(path_sub, out)
    out = KEY_RE.sub(key_sub, out)
    return out, findings


def scrub_json_obj(obj: Any, findings: list[str] | None = None) -> Any:
    found = findings if findings is not None else []
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            if _is_secret_key(str(key)) and isinstance(value, str) and value.strip():
                found.append(f"secret-field:{key}")
                out[key] = ""
            else:
                out[key] = scrub_json_obj(value, found)
        return out
    if isinstance(obj, list):
        return [scrub_json_obj(item, found) for item in obj]
    if isinstance(obj, str):
        cleaned, more = scrub_text(obj)
        found.extend(more)
        return cleaned
    return obj


def scrub_file(path: Path) -> list[str]:
    findings: list[str] = []
    if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in SKIP_PUBLISH_NAMES:
        return findings
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return findings
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            cleaned, findings = scrub_text(text)
            if cleaned != text:
                path.write_text(cleaned, encoding="utf-8")
            return findings
        scrubbed = scrub_json_obj(data, findings)
        path.write_text(json.dumps(scrubbed, indent=2) + "\n", encoding="utf-8")
        return findings
    cleaned, findings = scrub_text(text)
    if cleaned != text:
        path.write_text(cleaned, encoding="utf-8")
    return findings


def scrub_pack_dir(folder: Path | str) -> list[str]:
    root = Path(folder)
    findings: list[str] = []
    if not root.is_dir():
        return findings
    for path in list(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in SKIP_PUBLISH_NAMES:
            path.unlink()
            findings.append(f"removed:{path.name}")
            continue
        findings.extend(scrub_file(path))
    return findings


def catalog_entry_for_pack(pack: dict[str, Any]) -> dict[str, Any]:
    fields = listing_fields(pack, pack)
    entry = {
        "id": str(pack.get("id") or ""),
        "name": str(pack.get("name") or pack.get("displayName") or pack.get("id") or ""),
        "displayName": str(pack.get("displayName") or pack.get("name") or pack.get("id") or ""),
        "departmentJob": str(pack.get("departmentJob") or fields["blurb"]),
        "blurb": fields["blurb"],
        "detail": fields["detail"],
        "author": fields["author"],
        "seats": fields["seats"],
        "requiredConnectors": fields["requiredConnectors"],
        "path": str(pack.get("path") or pack.get("id") or ""),
        "featured": bool(pack.get("featured")),
        "tags": [str(t) for t in (pack.get("tags") or ["multi-bot"]) if t],
    }
    return entry


def _rewrite_zip(src: Path, dest: Path, scrub: bool, catalog_entry: dict[str, Any] | None) -> list[str]:
    findings: list[str] = []
    with tempfile.TemporaryDirectory(prefix="dragon-mkt-scrub-") as tmp:
        extracted = Path(tmp) / "pack"
        extracted.mkdir()
        with zipfile.ZipFile(src) as zf:
            zf.extractall(extracted)
        if scrub:
            findings = scrub_pack_dir(extracted)
        if catalog_entry:
            bg._write_json(extracted / "catalog-entry.json", catalog_entry)
            manifests = list(extracted.rglob(bg.MANIFEST_NAME))
            if len(manifests) == 1:
                bg._write_json(manifests[0].parent / "catalog-entry.json", catalog_entry)
        if dest.exists():
            dest.unlink()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in extracted.rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(extracted).as_posix())
    return findings


def export_catalog_pack(
    pack_id: str,
    dest: Path | str,
    payload_root: Path | str,
    install_root: Path | str,
    include_catalog_entry: bool = False,
) -> dict[str, Any]:
    tp._refuse_non_team(pack_id)
    dest_path = Path(dest)
    exported = Path(
        bg.export_group(
            pack_id,
            dest_path,
            install_root=install_root,
            payload_root=payload_root,
        )
    )
    pack = {}
    try:
        pack = get_marketplace_pack(pack_id, payload_root, install_root)
    except FileNotFoundError:
        pack = {"id": pack_id}
    entry = catalog_entry_for_pack(pack)
    entry_to_write = entry if include_catalog_entry else None
    if exported.suffix.lower() == ".zip":
        findings = _rewrite_zip(exported, exported, scrub=True, catalog_entry=entry_to_write)
    else:
        findings = scrub_pack_dir(exported)
        if entry_to_write:
            bg._write_json(Path(exported) / "catalog-entry.json", entry_to_write)
    return {
        "path": str(exported),
        "scrubbed": True,
        "findings": findings,
        "catalogEntry": entry,
        "id": pack_id,
        "displayName": pack.get("displayName") or pack_id,
    }


def publish_pack(
    pack_id: str,
    dest: Path | str,
    payload_root: Path | str,
    install_root: Path | str,
) -> dict[str, Any]:
    result = export_catalog_pack(
        pack_id,
        dest,
        payload_root=payload_root,
        install_root=install_root,
        include_catalog_entry=True,
    )
    result["kind"] = "dragon-teams-publish"
    return result


def self_test() -> int:
    cleaned, findings = scrub_text(
        "mail james.operator@dragonsden.work key sk-secretLIVEKEY1234567890 "
        r"path C:\Users\James\leads.csv keep operator@example.com"
    )
    if "james.operator@dragonsden.work" in cleaned or "sk-secretLIVEKEY1234567890" in cleaned:
        print("FAIL: scrub_text left secrets", file=sys.stderr)
        return 1
    if "operator@example.com" not in cleaned:
        print("FAIL: scrub_text dropped example.com email", file=sys.stderr)
        return 1
    if not findings:
        print("FAIL: scrub_text must report findings", file=sys.stderr)
        return 1
    if KIND_MARKETPLACE != "dragon-teams-marketplace":
        print("FAIL: marketplace kind", file=sys.stderr)
        return 1
    print("OK  team_marketplace self-test")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dragon AI Teams marketplace")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="cmd")
    p_list = sub.add_parser("list")
    p_list.add_argument("--payload", required=True)
    p_list.add_argument("--install", required=True)
    p_pub = sub.add_parser("publish")
    p_pub.add_argument("--id", required=True)
    p_pub.add_argument("--out", required=True)
    p_pub.add_argument("--payload", required=True)
    p_pub.add_argument("--install", required=True)
    args = parser.parse_args(argv)
    if args.self_test or args.cmd is None:
        return self_test()
    if args.cmd == "list":
        print(json.dumps(list_marketplace(args.payload, args.install), indent=2))
        return 0
    if args.cmd == "publish":
        print(
            json.dumps(
                publish_pack(args.id, args.out, args.payload, args.install),
                indent=2,
            )
        )
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
