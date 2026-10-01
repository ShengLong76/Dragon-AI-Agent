#!/usr/bin/env python3
"""Dragon AI Agent Teams picker — in-app catalog + apply + import.

Loopback-only helper the desktop overlay calls so James can pick a team
from the Dragon AI UI (not only Import-Profile.ps1). Apply still goes
through bot_groups.deploy_group, which files bots under the pack
displayName (not UNASSIGNED).

Bind 127.0.0.1 only. Do not collide with Bot Screen :8650.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import tempfile
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bot_groups as bg  # noqa: E402

TEAMS_HOST = "127.0.0.1"
TEAMS_PORT = 8653
MAX_IMPORT_BYTES = 20 * 1024 * 1024


DEFAULT_PROFILE_IDS = frozenset({"personal-assistant"})


def team_label(group: dict[str, Any]) -> str:
    return str(group.get("displayName") or group.get("name") or group.get("id") or "").strip()


def is_default_profile(group_id: str) -> bool:
    return str(group_id or "").strip().lower() in DEFAULT_PROFILE_IDS


def is_picker_team(group: dict[str, Any]) -> bool:
    """Teams picker is multi-bot packs only. PA is the default profile, not a team."""
    if not isinstance(group, dict):
        return False
    if is_default_profile(str(group.get("id") or "")):
        return False
    if group.get("picker") is False:
        return False
    tags = group.get("tags") or []
    if "default" in tags and "multi-bot" not in tags:
        return False
    bots = [b for b in (group.get("bots") or []) if isinstance(b, dict) and b.get("id")]
    if "bots" in group:
        return len(bots) >= 2
    return True


def present_team(group: dict[str, Any], listing: dict[str, Any] | None = None) -> dict[str, Any]:
    section = bg.ui_section_for_group(group)
    bots = [b for b in (group.get("bots") or []) if isinstance(b, dict) and b.get("id")]
    out: dict[str, Any] = {
        "id": group.get("id"),
        "name": group.get("name"),
        "displayName": team_label(group),
        "departmentJob": group.get("departmentJob") or "",
        "botCount": len(bots),
        "uiSection": section,
    }
    try:
        import team_marketplace as tm  # noqa: WPS433

        fields = tm.listing_fields(listing or {}, group)
        out.update(fields)
        out["seatCount"] = fields["seats"]
        out["bots"] = [{"id": b["id"], "title": str(b.get("title") or b["id"])} for b in bots]
    except Exception:
        pass
    return out


def _bundled_entries(payload_root: Path | str) -> list[dict[str, Any]]:
    catalog = Path(payload_root) / bg.REPO_PATH / bg.CATALOG_NAME
    if not catalog.is_file():
        return []
    try:
        return list(bg.normalize_catalog(bg._read_json(catalog)).get("groups") or [])
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return []


def list_teams(
    payload_root: Path | str,
    install_root: Path | str,
    fetcher: Any | None = None,
) -> dict[str, Any]:
    listed = bg.list_groups(payload_root, install_root, fetcher=fetcher)
    by_id: dict[str, dict[str, Any]] = {}
    for entry in _bundled_entries(payload_root) + list(listed.get("groups") or []):
        if isinstance(entry, dict) and entry.get("id"):
            by_id[str(entry["id"])] = entry
    teams: list[dict[str, Any]] = []
    for entry in by_id.values():
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        if bg.is_excluded_bot(str(entry.get("id") or ""), title=str(entry.get("name") or "")):
            continue
        if is_default_profile(str(entry.get("id") or "")) or entry.get("picker") is False:
            continue
        try:
            folder = bg.resolve_group_dir(
                str(entry["id"]),
                payload_root,
                install_root,
                fetcher=fetcher,
            )
            group = bg._load_group_folder(folder)
        except (OSError, ValueError, FileNotFoundError, json.JSONDecodeError):
            group = {
                "id": entry["id"],
                "name": entry.get("name") or entry["id"],
                "displayName": entry.get("displayName") or entry.get("name"),
                "departmentJob": entry.get("departmentJob") or "",
                "bots": [],
            }
        if not is_picker_team(group):
            continue
        teams.append(present_team(group, entry))
    return {
        "kind": "dragon-teams",
        "source": listed.get("source"),
        "teams": teams,
        "endpoint": f"http://{TEAMS_HOST}:{TEAMS_PORT}",
    }


def requested_team_ids(data: dict[str, Any] | None) -> list[str]:
    ids: list[str] = []
    payload = data if isinstance(data, dict) else {}
    raw = payload.get("ids")
    if isinstance(raw, list):
        ids.extend(str(item).strip() for item in raw if str(item).strip())
    single = str(payload.get("id") or payload.get("teamId") or "").strip()
    if single and single not in ids:
        ids.insert(0, single)
    return ids


def _refuse_non_team(team_id: str) -> None:
    if bg.is_excluded_bot(team_id):
        raise ValueError("that team is excluded from Dragon AI Agent")
    if is_default_profile(team_id):
        raise ValueError("Personal Assistant is the default profile, not a Teams pack")


def apply_team(
    team_id: str,
    payload_root: Path | str,
    install_root: Path | str,
    desktop_profiles_root: Path | str,
    embedded_profiles_root: Path | str | None = None,
    fetcher: Any | None = None,
) -> dict[str, Any]:
    _refuse_non_team(team_id)
    result = bg.deploy_group(
        team_id,
        payload_root=payload_root,
        install_root=install_root,
        desktop_profiles_root=desktop_profiles_root,
        embedded_profiles_root=embedded_profiles_root,
        fetcher=fetcher,
    )
    result["displayName"] = team_label(result)
    return result


def apply_teams(
    team_ids: list[str],
    payload_root: Path | str,
    install_root: Path | str,
    desktop_profiles_root: Path | str,
    embedded_profiles_root: Path | str | None = None,
    fetcher: Any | None = None,
) -> dict[str, Any]:
    """Launch each selected pack into its own named section. No merged roster."""
    ids = [str(item).strip() for item in team_ids if str(item).strip()]
    if not ids:
        raise ValueError("missing team id")
    for team_id in ids:
        _refuse_non_team(team_id)
    applied = [
        apply_team(
            team_id,
            payload_root=payload_root,
            install_root=install_root,
            desktop_profiles_root=desktop_profiles_root,
            embedded_profiles_root=embedded_profiles_root,
            fetcher=fetcher,
        )
        for team_id in ids
    ]
    return {
        "kind": "dragon-teams-apply",
        "applied": applied,
        "ids": [item.get("id") for item in applied],
        "displayNames": [item.get("displayName") for item in applied],
    }


def export_teams(
    team_ids: list[str],
    dest: Path | str,
    payload_root: Path | str,
    install_root: Path | str,
) -> str:
    ids = [str(item).strip() for item in team_ids if str(item).strip()]
    if not ids:
        raise ValueError("missing team id")
    for team_id in ids:
        _refuse_non_team(team_id)
    dest_path = Path(dest)
    import team_marketplace as tm  # noqa: WPS433

    if len(ids) == 1:
        result = tm.export_catalog_pack(
            ids[0],
            dest_path,
            payload_root=payload_root,
            install_root=install_root,
            include_catalog_entry=False,
        )
        return str(result["path"])
    folder = dest_path.with_suffix("") if dest_path.suffix.lower() == ".zip" else dest_path
    folder.mkdir(parents=True, exist_ok=True)
    for team_id in ids:
        bg.export_group(
            team_id,
            folder / team_id,
            install_root=install_root,
            payload_root=payload_root,
        )
    tm.scrub_pack_dir(folder)
    if dest_path.suffix.lower() != ".zip":
        return str(folder)
    if dest_path.exists():
        dest_path.unlink()
    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in folder.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(folder).as_posix())
    tm._rewrite_zip(dest_path, dest_path, scrub=True, catalog_entry=None)
    return str(dest_path)


def import_team_file(
    source: Path | str,
    payload_root: Path | str,
    install_root: Path | str,
    desktop_profiles_root: Path | str,
    embedded_profiles_root: Path | str | None = None,
) -> dict[str, Any]:
    result = bg.import_bundle(
        source,
        install_root=install_root,
        desktop_profiles_root=desktop_profiles_root,
        payload_root=payload_root,
        embedded_profiles_root=embedded_profiles_root,
    )
    result["displayName"] = team_label(result)
    return result


def import_team_bytes(
    filename: str,
    payload: bytes,
    payload_root: Path | str,
    install_root: Path | str,
    desktop_profiles_root: Path | str,
    embedded_profiles_root: Path | str | None = None,
) -> dict[str, Any]:
    if len(payload) > MAX_IMPORT_BYTES:
        raise ValueError("import file is too large")
    suffix = Path(filename or "team.zip").suffix or ".zip"
    with tempfile.TemporaryDirectory(prefix="dragon-teams-import-") as tmp:
        dest = Path(tmp) / f"upload{suffix}"
        dest.write_bytes(payload)
        return import_team_file(
            dest,
            payload_root=payload_root,
            install_root=install_root,
            desktop_profiles_root=desktop_profiles_root,
            embedded_profiles_root=embedded_profiles_root,
        )


def _json_bytes(data: Any, status: int = 200) -> tuple[int, bytes]:
    return status, (json.dumps(data) + "\n").encode("utf-8")


def make_handler(
    payload_root: Path,
    install_root: Path,
    desktop_root: Path,
    embedded_root: Path | None,
) -> type[BaseHTTPRequestHandler]:
    class TeamsHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
            return

        def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._send(204, b"")

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in ("/api/teams", "/teams"):
                status, body = _json_bytes(list_teams(payload_root, install_root))
                self._send(status, body)
                return
            import team_marketplace as tm  # noqa: WPS433

            if path in ("/api/marketplace", "/marketplace"):
                status, body = _json_bytes(tm.list_marketplace(payload_root, install_root))
                self._send(status, body)
                return
            if path.startswith("/api/marketplace/") or path.startswith("/marketplace/"):
                pack_id = path.rstrip("/").rsplit("/", 1)[-1].strip()
                if pack_id in {"", "install", "publish"}:
                    self._send(404, b'{"error":"not found"}\n')
                    return
                status, body = _json_bytes(tm.get_marketplace_pack(pack_id, payload_root, install_root))
                self._send(status, body)
                return
            if path in ("/api/health", "/health"):
                self._send(200, b'{"ok":true,"service":"dragon-teams"}\n')
                return
            self._send(404, b'{"error":"not found"}\n')

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._send(400, b'{"error":"invalid json"}\n')
                return
            if not isinstance(data, dict):
                data = {}
            try:
                if path in ("/api/marketplace/install", "/marketplace/install"):
                    team_id = str(data.get("id") or data.get("teamId") or "").strip()
                    if not team_id:
                        raise ValueError("missing team id")
                    import team_marketplace as tm  # noqa: WPS433

                    result = tm.install_pack(
                        team_id,
                        payload_root=payload_root,
                        install_root=install_root,
                        desktop_profiles_root=desktop_root,
                        embedded_profiles_root=embedded_root,
                    )
                    status, body = _json_bytes(result)
                    self._send(status, body)
                    return
                if path in ("/api/teams/publish", "/teams/publish"):
                    ids = requested_team_ids(data)
                    if not ids:
                        raise ValueError("missing team id")
                    import team_marketplace as tm  # noqa: WPS433

                    filename = f"{ids[0]}.zip"
                    with tempfile.TemporaryDirectory(prefix="dragon-teams-publish-") as tmp:
                        dest = Path(tmp) / filename
                        result = tm.publish_pack(
                            ids[0],
                            dest,
                            payload_root=payload_root,
                            install_root=install_root,
                        )
                        blob = Path(result["path"]).read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/zip")
                    self.send_header("Content-Length", str(len(blob)))
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Access-Control-Expose-Headers", "Content-Disposition")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(blob)
                    return
                if path in ("/api/teams/apply", "/teams/apply"):
                    ids = requested_team_ids(data)
                    if not ids:
                        raise ValueError("missing team id")
                    if len(ids) == 1:
                        result = apply_team(
                            ids[0],
                            payload_root=payload_root,
                            install_root=install_root,
                            desktop_profiles_root=desktop_root,
                            embedded_profiles_root=embedded_root,
                        )
                    else:
                        result = apply_teams(
                            ids,
                            payload_root=payload_root,
                            install_root=install_root,
                            desktop_profiles_root=desktop_root,
                            embedded_profiles_root=embedded_root,
                        )
                    status, body = _json_bytes(result)
                    self._send(status, body)
                    return
                if path in ("/api/teams/export", "/teams/export"):
                    ids = requested_team_ids(data)
                    if not ids:
                        raise ValueError("missing team id")
                    filename = f"{ids[0]}.zip" if len(ids) == 1 else "dragon-teams.zip"
                    with tempfile.TemporaryDirectory(prefix="dragon-teams-export-") as tmp:
                        dest = Path(tmp) / filename
                        export_teams(
                            ids,
                            dest,
                            payload_root=payload_root,
                            install_root=install_root,
                        )
                        blob = Path(dest).read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/zip")
                    self.send_header("Content-Length", str(len(blob)))
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Access-Control-Expose-Headers", "Content-Disposition")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(blob)
                    return
                if path in ("/api/teams/import", "/teams/import"):
                    if data.get("path"):
                        result = import_team_file(
                            str(data["path"]),
                            payload_root=payload_root,
                            install_root=install_root,
                            desktop_profiles_root=desktop_root,
                            embedded_profiles_root=embedded_root,
                        )
                    elif data.get("contentBase64"):
                        blob = base64.b64decode(str(data["contentBase64"]))
                        result = import_team_bytes(
                            str(data.get("filename") or "team.zip"),
                            blob,
                            payload_root=payload_root,
                            install_root=install_root,
                            desktop_profiles_root=desktop_root,
                            embedded_profiles_root=embedded_root,
                        )
                    else:
                        raise ValueError("import needs path or contentBase64")
                    status, body = _json_bytes(result)
                    self._send(status, body)
                    return
            except Exception as exc:  # noqa: BLE001 — HTTP boundary
                status, body = _json_bytes({"error": type(exc).__name__, "message": str(exc)}, 400)
                self._send(status, body)
                return
            self._send(404, b'{"error":"not found"}\n')

    return TeamsHandler


def serve(
    payload_root: Path | str,
    install_root: Path | str,
    desktop_profiles_root: Path | str,
    embedded_profiles_root: Path | str | None = None,
    host: str = TEAMS_HOST,
    port: int = TEAMS_PORT,
) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("teams picker binds loopback only")
    handler = make_handler(
        Path(payload_root),
        Path(install_root),
        Path(desktop_profiles_root),
        Path(embedded_profiles_root) if embedded_profiles_root else None,
    )
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"Dragon AI Teams picker on http://{host}:{port}/api/teams", flush=True)
    httpd.serve_forever()


def self_test() -> int:
    if TEAMS_PORT == 8650:
        print("FAIL: teams picker must not take Bot Screen :8650", file=sys.stderr)
        return 1
    if team_label({"name": "Long", "displayName": "Real Estate Lead Gen"}) != "Real Estate Lead Gen":
        print("FAIL: displayName must win the team label", file=sys.stderr)
        return 1
    if is_picker_team({"id": "personal-assistant", "bots": [{"id": "personal-assistant"}]}):
        print("FAIL: Personal Assistant must not be a Teams picker entry", file=sys.stderr)
        return 1
    if not is_picker_team({"id": "marketing-team", "bots": [{"id": "a"}, {"id": "b"}]}):
        print("FAIL: multi-bot packs must stay in the Teams picker", file=sys.stderr)
        return 1
    try:
        apply_teams([], ".", ".", ".")
        print("FAIL: apply_teams must require at least one team id", file=sys.stderr)
        return 1
    except ValueError:
        pass
    if requested_team_ids({"ids": ["marketing-team", "trading-team"]}) != [
        "marketing-team",
        "trading-team",
    ]:
        print("FAIL: apply/export must accept ids[] for Launch", file=sys.stderr)
        return 1
    print("OK  teams_picker self-test")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dragon AI Agent Teams picker")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="cmd")
    p_list = sub.add_parser("list")
    p_list.add_argument("--payload", required=True)
    p_list.add_argument("--install", required=True)
    p_apply = sub.add_parser("apply")
    p_apply.add_argument("--id", required=True)
    p_apply.add_argument("--payload", required=True)
    p_apply.add_argument("--install", required=True)
    p_apply.add_argument("--desktop", required=True)
    p_apply.add_argument("--embedded", default="")
    p_imp = sub.add_parser("import")
    p_imp.add_argument("--source", required=True)
    p_imp.add_argument("--payload", required=True)
    p_imp.add_argument("--install", required=True)
    p_imp.add_argument("--desktop", required=True)
    p_imp.add_argument("--embedded", default="")
    p_exp = sub.add_parser("export")
    p_exp.add_argument("--id", action="append", dest="ids", required=True)
    p_exp.add_argument("--out", required=True)
    p_exp.add_argument("--payload", required=True)
    p_exp.add_argument("--install", required=True)
    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--payload", required=True)
    p_serve.add_argument("--install", required=True)
    p_serve.add_argument("--desktop", required=True)
    p_serve.add_argument("--embedded", default="")
    p_serve.add_argument("--host", default=TEAMS_HOST)
    p_serve.add_argument("--port", type=int, default=TEAMS_PORT)
    args = parser.parse_args(argv)

    if args.self_test or args.cmd is None:
        return self_test()
    if args.cmd == "list":
        print(json.dumps(list_teams(args.payload, args.install), indent=2))
        return 0
    if args.cmd == "apply":
        print(
            json.dumps(
                apply_team(
                    args.id,
                    payload_root=args.payload,
                    install_root=args.install,
                    desktop_profiles_root=args.desktop,
                    embedded_profiles_root=args.embedded or None,
                ),
                indent=2,
            )
        )
        return 0
    if args.cmd == "import":
        print(
            json.dumps(
                import_team_file(
                    args.source,
                    payload_root=args.payload,
                    install_root=args.install,
                    desktop_profiles_root=args.desktop,
                    embedded_profiles_root=args.embedded or None,
                ),
                indent=2,
            )
        )
        return 0
    if args.cmd == "export":
        print(export_teams(args.ids, args.out, args.payload, args.install))
        return 0
    if args.cmd == "serve":
        serve(
            args.payload,
            args.install,
            args.desktop,
            args.embedded or None,
            host=args.host,
            port=args.port,
        )
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
