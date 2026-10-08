#!/usr/bin/env python3
"""Dragon GitHub-only Windows desktop release.

Hermes's bundled-release workflow archives pinned inputs to Cloudflare R2 and
signs with Azure Trusted Signing. This fork has neither. When R2 credentials
are absent the workflow takes this path: one NSIS Setup.exe on windows-latest,
attached to a Dragon-titled GitHub draft together with latest.yml + blockmap.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hermes_cli.product_feed import product_name, product_repository, public_assets_base
from scripts.releases.job_groups import JOB_GROUPS

SETUP_EXE_RE = re.compile(r"^DragonAIAgent-Setup-(?P<version>.+)-x64\.exe$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def github_only() -> bool:
    """True when this product publishes to GitHub Releases, not an assets CDN."""
    return public_assets_base() is None


def r2_configured(env: dict[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return bool(source.get("CLOUDFLARE_R2_ACCESS_KEY_ID", "").strip())


def desktop_version(repo: Path = ROOT) -> str:
    raw = json.loads((repo / "apps/desktop/package.json").read_text(encoding="utf-8-sig"))
    version = raw.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise ValueError(f"apps/desktop/package.json version must be X.Y.Z, got {version!r}")
    return version


def windows_builder_targets() -> list[str]:
    """electron-builder targets for the product feed. NSIS when there is no CDN."""
    return ["--win", "msix"] if public_assets_base() else ["--win", "nsis"]


def release_title(version: str) -> str:
    return f"{product_name()} v{version}"


def find_setup_exe(release_dir: Path) -> Path:
    matches = [path for path in release_dir.glob("DragonAIAgent-Setup-*-x64.exe") if path.is_file()]
    if len(matches) != 1:
        names = sorted(path.name for path in matches)
        raise ValueError(f"expected one DragonAIAgent-Setup-*-x64.exe in {release_dir}, found {names}")
    return matches[0]


def version_from_setup_exe(path: Path) -> str:
    match = SETUP_EXE_RE.fullmatch(path.name)
    if match is None:
        raise ValueError(f"not a Dragon Setup exe: {path.name}")
    return match.group("version")


def sha512_b64(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return base64.b64encode(digest.digest()).decode("ascii")


def latest_yml_text(*, version: str, file_name: str, sha512: str, size: int,
                    release_date: str | None = None) -> str:
    stamped = release_date or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return (
        f"version: {version}\n"
        f"files:\n"
        f"  - url: {file_name}\n"
        f"    sha512: {sha512}\n"
        f"    size: {size}\n"
        f"path: {file_name}\n"
        f"sha512: {sha512}\n"
        f"releaseDate: '{stamped}'\n"
    )


def write_latest_yml(release_dir: Path, *, version: str | None = None) -> Path:
    exe = find_setup_exe(release_dir)
    resolved = version or version_from_setup_exe(exe)
    text = latest_yml_text(
        version=resolved,
        file_name=exe.name,
        sha512=sha512_b64(exe),
        size=exe.stat().st_size,
    )
    dest = release_dir / "latest.yml"
    dest.write_text(text, encoding="utf-8")
    return dest


def release_assets(release_dir: Path) -> list[Path]:
    exe = find_setup_exe(release_dir)
    yml = release_dir / "latest.yml"
    if not yml.is_file():
        write_latest_yml(release_dir)
    assets = [exe, yml]
    blockmap = Path(str(exe) + ".blockmap")
    if blockmap.is_file():
        assets.append(blockmap)
    return assets


def _git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def on_product_github(env: dict[str, str] | None = None) -> bool:
    """True only on ShengLong76/Dragon-AI-Agent CI — fixture repos keep the Hermes graph."""
    source = os.environ if env is None else env
    repo = (source.get("GITHUB_REPOSITORY") or "").strip()
    return bool(repo) and repo.lower() == product_repository().lower()


def admit(*, env: dict[str, str] | None = None, repo: Path = ROOT) -> dict[str, str]:
    """Outputs for desktop-bundled-release.yml Pre-build setup.

    With R2 credentials the Hermes graph stays in charge. Without them, on this
    product GitHub repo, every Hermes job group is forced off and the Dragon
    Windows job is the only builder. Fixture / Hermes admission tests keep the
    inherited graph.
    """
    source = os.environ if env is None else env
    if r2_configured(source) or not on_product_github(source):
        return {"dragon-github-only": "false"}

    outputs = {group: "false" for group in JOB_GROUPS}
    outputs["all-jobs"] = "false"
    outputs["dragon-github-only"] = "true"

    requested = (source.get("TAG") or "").strip()
    version = desktop_version(repo)
    if requested:
        tag = requested
        version = requested[1:] if requested.startswith("v") else requested
    else:
        tag = f"v{version}"

    sha = (source.get("GITHUB_SHA") or "").strip() or _git("rev-parse", "HEAD", cwd=repo)
    tagged = _git("rev-parse", "--verify", f"{tag}^{{commit}}", cwd=repo)
    if tagged:
        sha = tagged
        tag_object = _git("rev-parse", "--verify", f"{tag}^{{tag}}", cwd=repo)
        if tag_object:
            outputs["tag-object"] = tag_object

    if not sha:
        raise ValueError("Dragon admit needs GITHUB_SHA or a resolvable HEAD")

    outputs["sha"] = sha
    outputs["payload-tag"] = tag
    outputs["payload-version"] = version
    outputs["channel"] = "canary" if "+canary." in tag else "latest"
    outputs["archive-tag"] = tag
    outputs["public-root"] = ""
    outputs["public-base"] = ""
    return outputs


def write_outputs(outputs: dict[str, str], dest) -> None:
    for key, value in outputs.items():
        dest.write(f"{key}={value}\n")


def _gh(argv: list[str], *, repo: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *argv, "--repo", repo],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def ensure_draft(*, tag: str, version: str, sha: str, notes: str) -> None:
    """Create or keep a Dragon-titled draft. Never publishes."""
    repo = product_repository()
    view = _gh(["release", "view", tag, "--json", "isDraft,isPrerelease,name"], repo=repo)
    title = release_title(version)
    if view.returncode != 0:
        created = _gh(
            [
                "release", "create", tag, "--draft", "--target", sha,
                "--title", title, "--notes", notes,
            ],
            repo=repo,
        )
        if created.returncode != 0:
            raise RuntimeError(created.stderr.strip() or f"could not draft {tag}")
        return
    release = json.loads(view.stdout)
    if release.get("isDraft") is not True:
        raise RuntimeError(f"{tag} is already published; bump the desktop version to cut a new latest")
    if "Hermes Agent" in str(release.get("name") or ""):
        _gh(["release", "edit", tag, "--title", title], repo=repo)


def attach(*, release_dir: Path, tag: str, version: str, sha: str, notes: str) -> list[str]:
    ensure_draft(tag=tag, version=version, sha=sha, notes=notes)
    assets = release_assets(release_dir)
    uploaded = _gh(
        ["release", "upload", tag, *[str(path) for path in assets], "--clobber"],
        repo=product_repository(),
    )
    if uploaded.returncode != 0:
        raise RuntimeError(uploaded.stderr.strip() or f"could not upload {tag} assets")
    return [path.name for path in assets]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("admit", help="Write Dragon-mode GITHUB_OUTPUT keys")
    targets = sub.add_parser("windows-targets", help="Print electron-builder Windows flags")
    targets.add_argument("--json", action="store_true")

    latest = sub.add_parser("write-latest-yml", help="Write latest.yml next to the Setup exe")
    latest.add_argument("--root", type=Path, required=True)
    latest.add_argument("--version")

    attach_cmd = sub.add_parser("attach", help="Draft (if needed) and upload Windows assets")
    attach_cmd.add_argument("--root", type=Path, required=True)
    attach_cmd.add_argument("--tag", required=True)
    attach_cmd.add_argument("--version", required=True)
    attach_cmd.add_argument("--sha", required=True)
    attach_cmd.add_argument("--notes", default="")

    args = parser.parse_args(argv)
    if args.cmd == "admit":
        write_outputs(admit(), sys.stdout)
        return 0
    if args.cmd == "windows-targets":
        flags = windows_builder_targets()
        print(json.dumps(flags) if args.json else " ".join(flags))
        return 0
    if args.cmd == "write-latest-yml":
        print(write_latest_yml(args.root, version=args.version))
        return 0
    attach(
        release_dir=args.root, tag=args.tag, version=args.version,
        sha=args.sha, notes=args.notes or f"{release_title(args.version)}\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
