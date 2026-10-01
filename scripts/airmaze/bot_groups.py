#!/usr/bin/env python3
"""Dragon AI Agent bot groups — GitHub-synced department packs.

Customization overlay on the desktop agent. Lists groups from
https://github.com/ShengLong76/airmaze-agent (bot-groups/), deploys them
into the existing desktop picker, exports the same file the repo stores,
and gates singular bot import/export behind a toggle that stays off.

Do not hard-code the group list. Do not add a Hermes bot. Do not restyle.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

KIND_GROUP = "bot-group"
KIND_BOT = "bot"
KIND_CATALOG = "bot-group-catalog"
SCHEMA_VERSION = 1
DEFAULT_REPO = "ShengLong76/airmaze-agent"
DEFAULT_REF = "main"
REPO_PATH = "bot-groups"
CATALOG_NAME = "catalog.json"
MANIFEST_NAME = "bot-group.json"
LEGACY_MANIFEST_NAME = "profile.json"
SETTINGS_NAME = "bot-group-settings.json"
ACTIVE_NAME = "active-bot-group.json"
UI_SECTIONS_NAME = "bot-ui-sections.json"
UI_SECTION_MARK = "# dragon-ai-ui-section"
UI_SECTION_PREFIX = "sec-dragon-"
DEFAULT_TIMEOUT_SEC = 8


class GitHubUnreachable(Exception):
    """GitHub (or the injected fetcher) could not be reached."""


class SingularBotDisabled(Exception):
    """One-bot import/export is off unless the user turns the toggle on."""


class UrlFetcher:
    def get_text(self, url: str) -> str:
        req = Request(url, headers={"User-Agent": "DragonAIAgent-bot-groups"})
        try:
            with urlopen(req, timeout=DEFAULT_TIMEOUT_SEC) as resp:
                return resp.read().decode("utf-8")
        except (URLError, TimeoutError, OSError) as exc:
            raise GitHubUnreachable(str(exc)) from exc


def catalog_url(repo: str = DEFAULT_REPO, ref: str = DEFAULT_REF) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{REPO_PATH}/{CATALOG_NAME}"


def group_file_url(rel: str, repo: str = DEFAULT_REPO, ref: str = DEFAULT_REF) -> str:
    rel = rel.lstrip("/")
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{REPO_PATH}/{rel}"


def default_settings() -> dict[str, Any]:
    return {"allowSingularBotImportExport": False}


def settings_path(install_root: Path | str) -> Path:
    return Path(install_root) / SETTINGS_NAME


def load_settings(install_root: Path | str) -> dict[str, Any]:
    path = settings_path(install_root)
    settings = default_settings()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                settings.update(data)
        except (OSError, json.JSONDecodeError):
            pass
    if settings.get("allowSingularBotImportExport") is not True:
        settings["allowSingularBotImportExport"] = False
    if not path.is_file():
        save_settings(install_root, settings)
    return settings


def save_settings(install_root: Path | str, settings: dict[str, Any]) -> Path:
    path = settings_path(install_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    merged = default_settings()
    merged.update(settings)
    if merged.get("allowSingularBotImportExport") is not True:
        merged["allowSingularBotImportExport"] = False
    path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return path


def is_excluded_bot(bot_id: str, title: str = "", meta: dict[str, Any] | None = None) -> bool:
    """Skip the stock Hermes bot. Consult exclude_hermes_bot when present."""
    try:
        from exclude_hermes_bot import is_excluded_profile  # noqa: WPS433
    except ImportError:
        here = str(Path(__file__).resolve().parent)
        if here not in sys.path:
            sys.path.insert(0, here)
        try:
            from exclude_hermes_bot import is_excluded_profile  # noqa: WPS433
        except ImportError:
            return str(bot_id or "").strip().lower() in {"default", "hermes"}
    return is_excluded_profile(bot_id, title=title, meta=meta)


def ui_section_id(group_id: str) -> str:
    raw = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(group_id or "").strip().lower())
    clean = "-".join(part for part in raw.split("-") if part) or "group"
    return f"{UI_SECTION_PREFIX}{clean}"


def ui_section_for_group(group: dict[str, Any]) -> dict[str, str]:
    return {
        "sectionId": ui_section_id(str(group.get("id") or "")),
        "sectionName": str(
            group.get("displayName") or group.get("name") or group.get("id") or ""
        ).strip(),
    }


def _yaml_scalar(value: Any) -> str:
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def stamp_profile_ui_section(path: Path, bot: dict[str, Any], section: dict[str, str]) -> None:
    """Write sectionId/sectionName so the BOTS pane files this bot (not UNASSIGNED)."""
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if UI_SECTION_MARK in text:
        text = text.split(UI_SECTION_MARK, 1)[0].rstrip() + "\n"
    title = str(bot.get("title") or bot.get("id") or "")
    description = str(bot.get("description") or "")
    block = (
        f"{UI_SECTION_MARK}\n"
        f"ui_meta:\n"
        f"  hermes-bots:\n"
        f"    title: {_yaml_scalar(title)}\n"
        f"    description: {_yaml_scalar(description)}\n"
        f"    sectionId: {_yaml_scalar(section['sectionId'])}\n"
        f"    sectionName: {_yaml_scalar(section['sectionName'])}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((text.rstrip() + "\n\n" + block).lstrip("\n"), encoding="utf-8")


def _record_ui_section(install: Path, section: dict[str, str]) -> None:
    path = install / UI_SECTIONS_NAME
    data: dict[str, Any] = {"key": "bot-sections-v1", "sections": []}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass
    sections = [s for s in (data.get("sections") or []) if isinstance(s, dict) and s.get("id") != section["sectionId"]]
    sections.append({"id": section["sectionId"], "name": section["sectionName"]})
    data["key"] = "bot-sections-v1"
    data["sections"] = sections
    _write_json(path, data)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _bot_dict(bot: Any) -> dict[str, Any]:
    if isinstance(bot, dict):
        return bot
    return {}


def normalize_manifest(data: dict[str, Any]) -> dict[str, Any]:
    """Accept bot-group.json or a one-time profile.json."""
    if not isinstance(data, dict):
        raise ValueError("manifest must be an object")
    kind = data.get("kind")
    if kind == KIND_BOT:
        return normalize_bot(data)

    connector_ids = []
    for conn in _as_list(data.get("connectors")):
        if isinstance(conn, dict) and conn.get("id"):
            connector_ids.append(str(conn["id"]))

    bots_out: list[dict[str, Any]] = []
    for raw in _as_list(data.get("bots")):
        bot = _bot_dict(raw)
        tools = [str(t) for t in _as_list(bot.get("tools")) if t]
        if not tools:
            tools = list(connector_ids)
        bots_out.append(
            {
                "id": str(bot.get("id") or ""),
                "title": str(bot.get("title") or bot.get("displayName") or bot.get("id") or ""),
                "description": str(bot.get("description") or ""),
                "tools": tools,
                "soul": str(bot.get("soul") or ""),
                "config": str(bot.get("config") or ""),
            }
        )

    name = str(data.get("name") or data.get("displayName") or data.get("id") or "")
    department = str(data.get("departmentJob") or data.get("description") or "")
    out: dict[str, Any] = {
        "kind": KIND_GROUP,
        "schemaVersion": int(data.get("schemaVersion") or SCHEMA_VERSION),
        "id": str(data.get("id") or ""),
        "name": name,
        "departmentJob": department,
        "version": str(data.get("version") or "1.0.0"),
        "bots": bots_out,
    }
    display = str(data.get("displayName") or "").strip()
    if display:
        out["displayName"] = display
    if data.get("connectors"):
        out["connectors"] = data["connectors"]
    return out


def normalize_bot(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": KIND_BOT,
        "schemaVersion": int(data.get("schemaVersion") or SCHEMA_VERSION),
        "id": str(data.get("id") or ""),
        "title": str(data.get("title") or data.get("displayName") or data.get("id") or ""),
        "description": str(data.get("description") or ""),
        "tools": [str(t) for t in _as_list(data.get("tools")) if t],
        "soul": data.get("soul") or "",
        "config": data.get("config") or "",
    }


def normalize_catalog(data: dict[str, Any]) -> dict[str, Any]:
    entries = data.get("groups")
    if entries is None:
        entries = data.get("profiles") or []
    groups = []
    for raw in _as_list(entries):
        if not isinstance(raw, dict):
            continue
        entry = {
            "id": str(raw.get("id") or ""),
            "name": str(raw.get("name") or raw.get("displayName") or raw.get("id") or ""),
            "departmentJob": str(raw.get("departmentJob") or raw.get("description") or ""),
            "path": str(raw.get("path") or raw.get("id") or ""),
        }
        display = str(raw.get("displayName") or "").strip()
        if display:
            entry["displayName"] = display
        if raw.get("picker") is False:
            entry["picker"] = False
        tags = raw.get("tags")
        if isinstance(tags, list) and tags:
            entry["tags"] = [str(t) for t in tags if t]
        groups.append(entry)
    return {
        "kind": KIND_CATALOG,
        "schemaVersion": int(data.get("schemaVersion") or SCHEMA_VERSION),
        "product": str(data.get("product") or "Dragon AI Agent"),
        "repository": data.get("repository")
        or {
            "owner": DEFAULT_REPO.split("/")[0],
            "name": DEFAULT_REPO.split("/")[1],
            "ref": DEFAULT_REF,
            "path": REPO_PATH,
        },
        "groups": groups,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _find_manifest(folder: Path) -> Path | None:
    for name in (MANIFEST_NAME, LEGACY_MANIFEST_NAME):
        candidate = folder / name
        if candidate.is_file():
            return candidate
    return None


def _title_from_id(bot_id: str) -> str:
    special = {
        "seo-specialist": "SEO Specialist",
    }
    if bot_id in special:
        return special[bot_id]
    return " ".join(part.capitalize() for part in str(bot_id).replace("_", "-").split("-") if part)


def _disk_bot(folder: Path, bot_id: str) -> dict[str, Any]:
    bot_dir = folder / "bots" / bot_id
    soul = f"bots/{bot_id}/SOUL.md" if (bot_dir / "SOUL.md").is_file() else ""
    config = f"bots/{bot_id}/bot.yaml" if (bot_dir / "bot.yaml").is_file() else ""
    title = _title_from_id(bot_id)
    description = ""
    cfg = bot_dir / "bot.yaml"
    if cfg.is_file():
        for line in cfg.read_text(encoding="utf-8").splitlines():
            if line.startswith("display_name:"):
                title = line.split(":", 1)[1].strip().strip("'\"") or title
            if line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip(">'\"") or description
    return {
        "id": bot_id,
        "title": title,
        "description": description,
        "tools": ["computer-use", "browser"],
        "soul": soul,
        "config": config,
    }


def _merge_disk_bots(folder: Path, group: dict[str, Any]) -> dict[str, Any]:
    """Union bot-group.json with bots/ so a partial manifest cannot drop Cos's roster."""
    bots_dir = folder / "bots"
    by_id: dict[str, dict[str, Any]] = {}
    for bot in group.get("bots") or []:
        if isinstance(bot, dict) and bot.get("id"):
            by_id[str(bot["id"])] = bot
    if bots_dir.is_dir():
        for child in sorted(bots_dir.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            disk = _disk_bot(folder, child.name)
            if child.name not in by_id:
                by_id[child.name] = disk
            else:
                existing = by_id[child.name]
                if not existing.get("soul"):
                    existing["soul"] = disk["soul"]
                if not existing.get("config"):
                    existing["config"] = disk["config"]
                if not existing.get("title"):
                    existing["title"] = disk["title"]
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bot in group.get("bots") or []:
        bot_id = str(bot.get("id") or "")
        if bot_id and bot_id in by_id and bot_id not in seen:
            ordered.append(by_id[bot_id])
            seen.add(bot_id)
    for bot_id, bot in by_id.items():
        if bot_id not in seen:
            ordered.append(bot)
    group["bots"] = ordered
    return group


def _load_group_folder(folder: Path) -> dict[str, Any]:
    manifest = _find_manifest(folder)
    if not manifest:
        raise FileNotFoundError(f"no {MANIFEST_NAME} in {folder}")
    return _merge_disk_bots(folder, normalize_manifest(_read_json(manifest)))


def _profile_belongs_to_group(dest: Path, group_id: str, section: dict[str, str]) -> bool:
    meta_path = dest / "bot.meta.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            meta = {}
        if isinstance(meta, dict):
            if str(meta.get("bot_group_id") or "") == group_id:
                return True
            if str(meta.get("sectionId") or "") == section.get("sectionId"):
                return True
    profile = dest / "profile.yaml"
    if profile.is_file():
        text = profile.read_text(encoding="utf-8")
        section_id = section.get("sectionId") or ""
        if section_id and section_id in text:
            return True
    return False


def _clear_stale_group_bots(
    desktop: Path,
    embedded: Path | None,
    group_id: str,
    keep_ids: set[str],
    section: dict[str, str],
) -> list[str]:
    """Drop leftover stubs (e.g. Copywriter) when re-applying Cos's roster."""
    removed: list[str] = []
    roots = [desktop]
    if embedded is not None:
        roots.append(Path(embedded))
    for root in roots:
        if not root.is_dir():
            continue
        for dest in list(root.iterdir()):
            if not dest.is_dir() or dest.name in keep_ids:
                continue
            if not _profile_belongs_to_group(dest, group_id, section):
                continue
            shutil.rmtree(dest)
            if dest.name not in removed:
                removed.append(dest.name)
    return removed


def list_groups(
    payload_root: Path | str,
    install_root: Path | str,
    fetcher: Any | None = None,
    repo: str = DEFAULT_REPO,
    ref: str = DEFAULT_REF,
) -> dict[str, Any]:
    payload = Path(payload_root)
    install = Path(install_root)
    cache_path = install / REPO_PATH / "cache" / CATALOG_NAME
    bundled = payload / REPO_PATH / CATALOG_NAME
    fetch = fetcher or UrlFetcher()
    url = catalog_url(repo, ref)
    try:
        text = fetch.get_text(url)
        catalog = normalize_catalog(json.loads(text))
        _write_json(cache_path, catalog)
        return {"groups": catalog["groups"], "source": "github", "url": url}
    except (GitHubUnreachable, json.JSONDecodeError, TypeError, ValueError) as exc:
        if cache_path.is_file():
            catalog = normalize_catalog(_read_json(cache_path))
            return {
                "groups": catalog["groups"],
                "source": "cache",
                "error": str(exc),
            }
        if bundled.is_file():
            catalog = normalize_catalog(_read_json(bundled))
            return {
                "groups": catalog["groups"],
                "source": "bundled",
                "error": str(exc),
            }
        raise GitHubUnreachable(str(exc)) from exc


def _candidate_group_dirs(group_id: str, rel: str, payload: Path, install: Path) -> list[Path]:
    rel_os = rel.replace("/", "/")
    return [
        payload / REPO_PATH / rel_os,
        install / REPO_PATH / "cache" / rel_os,
        install / REPO_PATH / "imported" / group_id,
        payload / "profiles" / rel_os,
        install / REPO_PATH / "applied" / group_id,
        payload / REPO_PATH / group_id,
        payload / "profiles" / group_id,
    ]


def _catalog_rel(group_id: str, payload: Path, install: Path) -> str:
    for catalog_file in (
        install / REPO_PATH / "cache" / CATALOG_NAME,
        payload / REPO_PATH / CATALOG_NAME,
        payload / "profiles" / CATALOG_NAME,
    ):
        if not catalog_file.is_file():
            continue
        catalog = normalize_catalog(_read_json(catalog_file))
        for entry in catalog["groups"]:
            if entry["id"] == group_id:
                return entry["path"] or group_id
    return group_id


def _fetch_group_tree(
    group_id: str,
    rel: str,
    install: Path,
    fetcher: Any,
    repo: str,
    ref: str,
) -> Path:
    dest = install / REPO_PATH / "cache" / rel
    dest.mkdir(parents=True, exist_ok=True)
    manifest_text = None
    last_err: Exception | None = None
    for name in (MANIFEST_NAME, LEGACY_MANIFEST_NAME):
        url = group_file_url(f"{rel}/{name}", repo, ref)
        try:
            manifest_text = fetcher.get_text(url)
            break
        except GitHubUnreachable as exc:
            last_err = exc
    if manifest_text is None:
        raise GitHubUnreachable(str(last_err) if last_err else f"missing group {group_id}")
    manifest = normalize_manifest(json.loads(manifest_text))
    _write_json(dest / MANIFEST_NAME, manifest)
    for bot in manifest["bots"]:
        for key in ("soul", "config"):
            rel_file = bot.get(key)
            if not rel_file or "\n" in str(rel_file):
                continue
            url = group_file_url(f"{rel}/{rel_file}", repo, ref)
            try:
                body = fetcher.get_text(url)
            except GitHubUnreachable:
                continue
            out = dest / str(rel_file)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(body, encoding="utf-8")
    return dest


def resolve_group_dir(
    group_id: str,
    payload_root: Path | str,
    install_root: Path | str,
    fetcher: Any | None = None,
    repo: str = DEFAULT_REPO,
    ref: str = DEFAULT_REF,
) -> Path:
    payload = Path(payload_root)
    install = Path(install_root)
    rel = _catalog_rel(group_id, payload, install)
    for folder in _candidate_group_dirs(group_id, rel, payload, install):
        if _find_manifest(folder):
            return folder
    if fetcher is not None:
        return _fetch_group_tree(group_id, rel, install, fetcher, repo, ref)
    try:
        return _fetch_group_tree(group_id, rel, install, UrlFetcher(), repo, ref)
    except GitHubUnreachable as exc:
        raise FileNotFoundError(f"bot group {group_id!r} not found locally and GitHub is unreachable: {exc}") from exc


def _copy_bot_files(group_dir: Path, bot: dict[str, Any], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    soul_rel = bot.get("soul") or ""
    cfg_rel = bot.get("config") or ""
    if soul_rel and "\n" not in soul_rel:
        src = group_dir / soul_rel.replace("/", "/")
        if src.is_file():
            shutil.copy2(src, dest / "SOUL.md")
    elif soul_rel:
        (dest / "SOUL.md").write_text(str(soul_rel), encoding="utf-8")
    if cfg_rel and "\n" not in cfg_rel:
        src = group_dir / cfg_rel.replace("/", "/")
        if src.is_file():
            shutil.copy2(src, dest / "bot.yaml")
            shutil.copy2(src, dest / "profile.yaml")
    elif cfg_rel:
        (dest / "bot.yaml").write_text(str(cfg_rel), encoding="utf-8")
        (dest / "profile.yaml").write_text(str(cfg_rel), encoding="utf-8")


def _write_bot_meta(dest: Path, bot: dict[str, Any], group_id: str, section: dict[str, str] | None = None) -> None:
    meta = {
        "id": bot["id"],
        "title": bot["title"],
        "display_name": bot["title"],
        "description": bot["description"],
        "tools": list(bot.get("tools") or []),
        "bot_group_id": group_id,
    }
    if section:
        meta["sectionId"] = section["sectionId"]
        meta["sectionName"] = section["sectionName"]
    _write_json(dest / "bot.meta.json", meta)


def _copy_connectors(group_dir: Path, group: dict[str, Any], install: Path) -> None:
    conn_root = install / "connectors" / group["id"]
    conn_root.mkdir(parents=True, exist_ok=True)
    src_dir = group_dir / "connectors"
    if src_dir.is_dir():
        for item in src_dir.iterdir():
            target = conn_root / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
    for conn in _as_list(group.get("connectors")):
        if not isinstance(conn, dict):
            continue
        tpl = conn.get("configTemplate")
        if not tpl:
            continue
        src = group_dir / str(tpl).replace("/", "/")
        if src.is_file():
            shutil.copy2(src, conn_root / src.name)


def _keep_applied_copy(group_dir: Path, group: dict[str, Any], install: Path) -> Path:
    applied = install / REPO_PATH / "applied" / group["id"]
    applied.mkdir(parents=True, exist_ok=True)
    if group_dir.resolve() != applied.resolve():
        shutil.copytree(group_dir, applied, dirs_exist_ok=True)
    _write_json(applied / MANIFEST_NAME, group)
    return applied


def _mirror_embedded(desktop: Path, bot_id: str, embedded: Path | None) -> None:
    if embedded is None:
        return
    src = desktop / bot_id
    if not src.is_dir():
        return
    dest = Path(embedded) / bot_id
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, dirs_exist_ok=True)
    bot_yaml = dest / "bot.yaml"
    cfg_yaml = dest / "config.yaml"
    if bot_yaml.is_file() and not cfg_yaml.is_file():
        shutil.copy2(bot_yaml, cfg_yaml)


def deploy_group(
    group_id: str,
    payload_root: Path | str,
    install_root: Path | str,
    desktop_profiles_root: Path | str,
    embedded_profiles_root: Path | str | None = None,
    fetcher: Any | None = None,
    repo: str = DEFAULT_REPO,
    ref: str = DEFAULT_REF,
) -> dict[str, Any]:
    install = Path(install_root)
    desktop = Path(desktop_profiles_root)
    desktop.mkdir(parents=True, exist_ok=True)
    group_dir = resolve_group_dir(group_id, payload_root, install, fetcher=fetcher, repo=repo, ref=ref)
    group = _load_group_folder(group_dir)
    if not group.get("id"):
        group["id"] = group_id
    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []
    section = ui_section_for_group(group)
    for bot in group["bots"]:
        bot_id = bot.get("id")
        if not bot_id:
            continue
        if is_excluded_bot(bot_id, title=str(bot.get("title") or "")):
            skipped.append(bot_id)
            continue
        dest = desktop / bot_id
        existed = dest.is_dir() and any(dest.iterdir())
        _copy_bot_files(group_dir, bot, dest)
        stamp_profile_ui_section(dest / "profile.yaml", bot, section)
        if (dest / "bot.yaml").is_file():
            stamp_profile_ui_section(dest / "bot.yaml", bot, section)
        _write_bot_meta(dest, bot, group["id"], section)
        _mirror_embedded(desktop, bot_id, Path(embedded_profiles_root) if embedded_profiles_root else None)
        (updated if existed else created).append(bot_id)
    keep_ids = {b["id"] for b in group["bots"] if b.get("id") and b["id"] not in skipped}
    removed = _clear_stale_group_bots(
        desktop,
        Path(embedded_profiles_root) if embedded_profiles_root else None,
        group["id"],
        keep_ids,
        section,
    )
    _copy_connectors(group_dir, group, install)
    _keep_applied_copy(group_dir, group, install)
    _record_ui_section(install, section)
    applied_bots = [b["id"] for b in group["bots"] if b.get("id") and b["id"] not in skipped]
    active = {
        "botGroupId": group["id"],
        "name": group["name"],
        "departmentJob": group["departmentJob"],
        "appliedAt": datetime.now(timezone.utc).isoformat(),
        "bots": applied_bots,
        "desktopRoot": str(desktop),
        "uiSection": section,
    }
    _write_json(install / ACTIVE_NAME, active)
    # One-time bridge for the setup wizard until it reads botGroupId.
    _write_json(
        install / "active-profile.json",
        {
            "profileId": group["id"],
            "botGroupId": group["id"],
            "displayName": group["name"],
            "appliedAt": active["appliedAt"],
            "bots": active["bots"],
            "desktopRoot": str(desktop),
        },
    )
    return {
        "botGroupId": group["id"],
        "id": group["id"],
        "name": group["name"],
        "departmentJob": group["departmentJob"],
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "removed": removed,
        "uiSection": section,
        "bots": [b for b in group["bots"] if b.get("id") and b["id"] not in skipped],
    }


def export_group(
    group_id: str,
    dest: Path | str,
    install_root: Path | str,
    payload_root: Path | str | None = None,
) -> str:
    install = Path(install_root)
    payload = Path(payload_root) if payload_root else install
    source = resolve_group_dir(group_id, payload, install, fetcher=None)
    group = _load_group_folder(source)
    out = Path(dest)
    if out.suffix.lower() == ".zip":
        folder = out.with_suffix("")
    else:
        folder = out
    folder.mkdir(parents=True, exist_ok=True)
    if source.resolve() != folder.resolve():
        shutil.copytree(source, folder, dirs_exist_ok=True)
    _write_json(folder / MANIFEST_NAME, group)
    legacy = folder / LEGACY_MANIFEST_NAME
    if legacy.is_file() and (folder / MANIFEST_NAME).is_file():
        legacy.unlink()
    if out.suffix.lower() == ".zip":
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in folder.rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(folder.parent).as_posix())
        return str(out)
    return str(folder)


def _require_singular(install_root: Path | str) -> None:
    if not load_settings(install_root).get("allowSingularBotImportExport"):
        raise SingularBotDisabled(
            "Import or export of one bot is off. Turn on Allow import or export of one bot."
        )


def _read_bot_from_desktop(bot_id: str, desktop: Path, install: Path) -> dict[str, Any]:
    dest = Path(desktop) / bot_id
    meta: dict[str, Any] = {}
    meta_path = dest / "bot.meta.json"
    if meta_path.is_file():
        meta = _read_json(meta_path)
    soul = ""
    soul_path = dest / "SOUL.md"
    if soul_path.is_file():
        soul = soul_path.read_text(encoding="utf-8")
    config = ""
    for name in ("bot.yaml", "profile.yaml", "config.yaml"):
        cfg = dest / name
        if cfg.is_file():
            config = cfg.read_text(encoding="utf-8")
            break
    if not dest.is_dir():
        applied = install / REPO_PATH / "applied"
        if applied.is_dir():
            for group_dir in applied.iterdir():
                if not group_dir.is_dir():
                    continue
                try:
                    group = _load_group_folder(group_dir)
                except (OSError, ValueError, json.JSONDecodeError):
                    continue
                for bot in group["bots"]:
                    if bot["id"] == bot_id:
                        return {
                            "kind": KIND_BOT,
                            "schemaVersion": SCHEMA_VERSION,
                            "id": bot_id,
                            "title": bot["title"],
                            "description": bot["description"],
                            "tools": list(bot.get("tools") or []),
                            "soul": (group_dir / bot["soul"]).read_text(encoding="utf-8")
                            if bot.get("soul") and (group_dir / bot["soul"]).is_file()
                            else soul,
                            "config": (group_dir / bot["config"]).read_text(encoding="utf-8")
                            if bot.get("config") and (group_dir / bot["config"]).is_file()
                            else config,
                        }
    return {
        "kind": KIND_BOT,
        "schemaVersion": SCHEMA_VERSION,
        "id": bot_id,
        "title": str(meta.get("title") or meta.get("display_name") or bot_id),
        "description": str(meta.get("description") or ""),
        "tools": list(meta.get("tools") or []),
        "soul": soul,
        "config": config,
    }


def export_bot(
    bot_id: str,
    dest: Path | str,
    install_root: Path | str,
    desktop_profiles_root: Path | str,
) -> str:
    _require_singular(install_root)
    data = _read_bot_from_desktop(bot_id, Path(desktop_profiles_root), Path(install_root))
    out = Path(dest)
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out, data)
    return str(out)


def _extract_import(source: Path, staging: Path) -> Path:
    if source.is_dir():
        shutil.copytree(source, staging, dirs_exist_ok=True)
        return staging
    name = source.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(source) as zf:
            zf.extractall(staging)
        kids = list(staging.iterdir())
        if len(kids) == 1 and kids[0].is_dir() and not _find_manifest(staging):
            return kids[0]
        found = next(staging.rglob(MANIFEST_NAME), None) or next(staging.rglob(LEGACY_MANIFEST_NAME), None)
        if found:
            return found.parent
        return staging
    if name.endswith(".json"):
        data = _read_json(source)
        if data.get("kind") == KIND_BOT:
            shutil.copy2(source, staging / "bot.json")
            return staging
        if source.name in (MANIFEST_NAME, LEGACY_MANIFEST_NAME):
            parent = source.parent
            shutil.copytree(parent, staging, dirs_exist_ok=True)
            return staging
        shutil.copy2(source, staging / MANIFEST_NAME)
        return staging
    raise ValueError(f"unsupported import type: {source}")


def _import_singular_bot(
    data: dict[str, Any],
    install_root: Path,
    desktop_profiles_root: Path,
    embedded_profiles_root: Path | None,
) -> dict[str, Any]:
    _require_singular(install_root)
    bot = normalize_bot(data)
    if not bot["id"]:
        raise ValueError("one-bot file missing id")
    dest = desktop_profiles_root / bot["id"]
    dest.mkdir(parents=True, exist_ok=True)
    if bot.get("soul"):
        (dest / "SOUL.md").write_text(str(bot["soul"]), encoding="utf-8")
    if bot.get("config"):
        (dest / "bot.yaml").write_text(str(bot["config"]), encoding="utf-8")
        (dest / "profile.yaml").write_text(str(bot["config"]), encoding="utf-8")
    _write_bot_meta(dest, bot, "")
    _mirror_embedded(desktop_profiles_root, bot["id"], embedded_profiles_root)
    return {"kind": KIND_BOT, "botId": bot["id"], "title": bot["title"]}


def import_bundle(
    source: Path | str,
    install_root: Path | str,
    desktop_profiles_root: Path | str,
    payload_root: Path | str | None = None,
    embedded_profiles_root: Path | str | None = None,
) -> dict[str, Any]:
    src = Path(source)
    install = Path(install_root)
    desktop = Path(desktop_profiles_root)
    if src.is_file() and src.suffix.lower() == ".json":
        data = _read_json(src)
        if data.get("kind") == KIND_BOT:
            return _import_singular_bot(data, install, desktop, Path(embedded_profiles_root) if embedded_profiles_root else None)
    with tempfile.TemporaryDirectory(prefix="dragon-bg-import-") as tmp:
        staging = Path(tmp) / "bundle"
        staging.mkdir()
        folder = _extract_import(src, staging)
        bot_json = folder / "bot.json"
        if bot_json.is_file():
            return _import_singular_bot(
                _read_json(bot_json),
                install,
                desktop,
                Path(embedded_profiles_root) if embedded_profiles_root else None,
            )
        if not _find_manifest(folder):
            found = next(folder.rglob(MANIFEST_NAME), None) or next(folder.rglob(LEGACY_MANIFEST_NAME), None)
            if found:
                folder = found.parent
            else:
                raise FileNotFoundError(f"imported bundle has no {MANIFEST_NAME}")
        group = _load_group_folder(folder)
        imported = install / REPO_PATH / "imported" / group["id"]
        if imported.exists():
            shutil.rmtree(imported)
        shutil.copytree(folder, imported)
        _write_json(imported / MANIFEST_NAME, group)
        payload = Path(payload_root) if payload_root else install
        return deploy_group(
            group["id"],
            payload_root=payload,
            install_root=install,
            desktop_profiles_root=desktop,
            embedded_profiles_root=embedded_profiles_root,
        )


def _json_out(data: Any) -> None:
    print(json.dumps(data, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dragon AI Agent bot groups")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_list = sub.add_parser("list", help="List bot groups from GitHub (cache/bundle fallback)")
    p_list.add_argument("--payload", required=True)
    p_list.add_argument("--install", required=True)
    p_dep = sub.add_parser("deploy", help="Deploy one bot group from the repo dropdown")
    p_dep.add_argument("--id", required=True)
    p_dep.add_argument("--payload", required=True)
    p_dep.add_argument("--install", required=True)
    p_dep.add_argument("--desktop", required=True)
    p_dep.add_argument("--embedded", default="")
    p_exp = sub.add_parser("export", help="Export a bot group in repo format")
    p_exp.add_argument("--id", required=True)
    p_exp.add_argument("--out", required=True)
    p_exp.add_argument("--install", required=True)
    p_exp.add_argument("--payload", default="")
    p_imp = sub.add_parser("import", help="Import a group file (or one bot if the toggle is on)")
    p_imp.add_argument("--source", required=True)
    p_imp.add_argument("--install", required=True)
    p_imp.add_argument("--desktop", required=True)
    p_imp.add_argument("--payload", default="")
    p_imp.add_argument("--embedded", default="")
    p_eb = sub.add_parser("export-bot", help="Export one bot (toggle must be on)")
    p_eb.add_argument("--id", required=True)
    p_eb.add_argument("--out", required=True)
    p_eb.add_argument("--install", required=True)
    p_eb.add_argument("--desktop", required=True)
    p_set = sub.add_parser("settings", help="Read or set the singular-bot toggle")
    p_set.add_argument("--install", required=True)
    p_set.add_argument("--set-singular", choices=("on", "off"), default="")
    args = parser.parse_args(argv)

    try:
        if args.cmd == "list":
            _json_out(list_groups(args.payload, args.install))
        elif args.cmd == "deploy":
            _json_out(
                deploy_group(
                    args.id,
                    payload_root=args.payload,
                    install_root=args.install,
                    desktop_profiles_root=args.desktop,
                    embedded_profiles_root=args.embedded or None,
                )
            )
        elif args.cmd == "export":
            path = export_group(args.id, args.out, args.install, args.payload or None)
            _json_out({"path": path})
        elif args.cmd == "import":
            _json_out(
                import_bundle(
                    args.source,
                    install_root=args.install,
                    desktop_profiles_root=args.desktop,
                    payload_root=args.payload or None,
                    embedded_profiles_root=args.embedded or None,
                )
            )
        elif args.cmd == "export-bot":
            path = export_bot(args.id, args.out, args.install, args.desktop)
            _json_out({"path": path})
        elif args.cmd == "settings":
            if args.set_singular:
                save_settings(args.install, {"allowSingularBotImportExport": args.set_singular == "on"})
            _json_out(load_settings(args.install))
        return 0
    except SingularBotDisabled as exc:
        print(json.dumps({"error": "singular-disabled", "message": str(exc)}), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
