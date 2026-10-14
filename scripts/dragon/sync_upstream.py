#!/usr/bin/env python3
"""Merge NousResearch/hermes-agent into a Dragon sync branch and describe the PR.

Never merges to main. James approves every sync pull request. On conflicts the
script still produces a draft-PR body that lists the conflicting files.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEED_PATH = ROOT / "branding" / "product-feed.json"
SYNC_BRANCH = "dragon/upstream-sync"
UPSTREAM_REMOTE = "hermes-upstream"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class UpstreamTipError(RuntimeError):
    """The Hermes upstream tip SHA could not be resolved."""


def load_feed() -> dict:
    return json.loads(FEED_PATH.read_text(encoding="utf-8-sig"))


def protected_paths(feed: dict | None = None) -> tuple[str, ...]:
    data = feed or load_feed()
    rows = data.get("protectedPaths") or []
    return tuple(str(path) for path in rows if isinstance(path, str) and path.strip())


def is_protected(path: str, prefixes: tuple[str, ...] | None = None) -> bool:
    prefixes = prefixes or protected_paths()
    normalized = path.replace("\\", "/").lstrip("./")
    for prefix in prefixes:
        token = prefix.replace("\\", "/").lstrip("./")
        if normalized == token.rstrip("/") or normalized.startswith(token if token.endswith("/") else f"{token}/"):
            return True
        if normalized == token:
            return True
    return False


def protected_touched(changed_paths: list[str], prefixes: tuple[str, ...] | None = None) -> list[str]:
    return sorted({path for path in changed_paths if is_protected(path, prefixes)})


@dataclass
class SyncReport:
    upstream_repository: str
    upstream_sha: str
    base_branch: str
    sync_branch: str
    conflicts: list[str] = field(default_factory=list)
    protected_touched: list[str] = field(default_factory=list)
    changed_paths: list[str] = field(default_factory=list)
    has_conflicts: bool = False
    draft: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2) + "\n"


def build_pr_title(report: SyncReport) -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    suffix = " (conflicts)" if report.has_conflicts else ""
    return f"chore: sync upstream Hermes {report.upstream_sha[:12]}{suffix} — {day}"


def build_pr_body(report: SyncReport) -> str:
    feed = load_feed()
    product = feed["productName"]
    lines = [
        f"## {product} upstream sync",
        "",
        "Hermes upstream changes are **not** an automatic product update. This PR",
        "is the review gate: nothing here reaches users until it is merged to",
        f"`{report.base_branch}` and {product} publishes a release.",
        "",
        "```",
        f"Hermes ({report.upstream_repository}) → `{report.sync_branch}` → PR →",
        f"James approves → `{report.base_branch}` → {product} release → {product} updater",
        "```",
        "",
        f"- Upstream: `{report.upstream_repository}@{report.upstream_sha}`",
        f"- Sync branch: `{report.sync_branch}`",
        "- Auto-merge: **never**",
        "",
    ]
    if report.has_conflicts:
        lines.extend([
            "### Conflicts — resolve before merge",
            "",
            "Git could not complete the merge. Conflict markers remain in:",
            "",
        ])
        for path in report.conflicts:
            lines.append(f"- `{path}`")
        lines.extend(["", "Open this draft, resolve the files, and re-run the branding check.", ""])
    else:
        lines.extend(["### Merge status", "", "The upstream merge completed without conflicts.", ""])
    if report.protected_touched:
        lines.extend([
            "### Protected Dragon files touched by upstream",
            "",
            "Review these carefully so branding, logo, and installer config are not overwritten:",
            "",
        ])
        for path in report.protected_touched:
            lines.append(f"- `{path}`")
        lines.append("")
    lines.extend([
        "### Branding",
        "",
        "After the merge, `python3 scripts/dragon/rebrand_strings.py` is applied on",
        "the sync branch. `scripts/dragon/branding_guard.py` must stay green.",
        "",
        "### Test plan",
        "",
        "- [ ] Branding guard is green",
        "- [ ] Existing CI on this PR is green",
        "- [ ] Conflict files (if any) are resolved by hand",
        "- [ ] Protected Dragon files still show Dragon AI, not Hermes",
        "",
    ])
    return "\n".join(lines) + "\n"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def peel_commit(repo: Path, rev: str) -> str | None:
    """Return the 40-char commit SHA for rev, or None if it is not a commit."""
    result = _git(repo, "rev-parse", "--verify", f"{rev}^{{commit}}")
    sha = result.stdout.strip().lower()
    if result.returncode == 0 and _SHA_RE.fullmatch(sha):
        return sha
    return None


def discover_upstream_default_branch(repo: Path, remote: str) -> str | None:
    """Read the remote's symbolic HEAD (e.g. refs/heads/main → main)."""
    result = _git(repo, "ls-remote", "--symref", remote, "HEAD")
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if not line.startswith("ref:"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        prefix = "refs/heads/"
        if ref.startswith(prefix) and ref[len(prefix):]:
            return ref[len(prefix):]
    return None


def fetch_upstream_tip(repo: Path, remote: str) -> str:
    """Fetch the remote default tip into an explicit tracking ref.

    `git fetch <remote> HEAD` only writes FETCH_HEAD and does not create
    `refs/remotes/<remote>/HEAD`, so a later `git rev-parse <remote>/HEAD`
    cannot resolve. Fetch the named default branch (or HEAD) into
    `refs/remotes/<remote>/<branch>` instead.
    """
    branch = discover_upstream_default_branch(repo, remote)
    if branch:
        tracking_ref = f"refs/remotes/{remote}/{branch}"
        fetchspec = f"refs/heads/{branch}:{tracking_ref}"
    else:
        tracking_ref = f"refs/remotes/{remote}/main"
        fetchspec = f"HEAD:{tracking_ref}"
    result = _git(repo, "fetch", remote, fetchspec)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "unknown error"
        raise UpstreamTipError(
            f"Could not resolve a Hermes upstream tip SHA from {remote}: "
            f"fetch {fetchspec} failed: {detail}"
        )
    return tracking_ref


def resolve_fetched_tip(repo: Path, tracking_ref: str, remote: str | None = None) -> str:
    """Resolve a commit SHA from a tracking ref, or FETCH_HEAD if that is missing."""
    sha = peel_commit(repo, tracking_ref) or peel_commit(repo, "FETCH_HEAD")
    if not sha:
        source = f" from {remote}" if remote else ""
        raise UpstreamTipError(
            f"Could not resolve a Hermes upstream tip SHA{source} "
            f"(tried {tracking_ref} and FETCH_HEAD)."
        )
    return sha


def resolve_upstream_tip(repo: Path, remote: str = UPSTREAM_REMOTE) -> str:
    """Return the 40-char SHA at the remote's default-branch tip."""
    tracking_ref = fetch_upstream_tip(repo, remote)
    return resolve_fetched_tip(repo, tracking_ref, remote=remote)


def collect_report(
    *,
    repo: Path,
    upstream_repository: str,
    upstream_sha: str,
    base_branch: str,
    conflicts: list[str],
    changed_paths: list[str],
) -> SyncReport:
    touched = protected_touched(changed_paths)
    has_conflicts = bool(conflicts)
    return SyncReport(
        upstream_repository=upstream_repository,
        upstream_sha=upstream_sha,
        base_branch=base_branch,
        sync_branch=SYNC_BRANCH,
        conflicts=sorted(conflicts),
        protected_touched=touched,
        changed_paths=sorted(changed_paths),
        has_conflicts=has_conflicts,
        draft=has_conflicts,
    )


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def read_list_file(path: Path) -> list[str]:
    return _lines(path.read_text(encoding="utf-8-sig")) if path.is_file() else []


def read_conflicts(repo: Path) -> list[str]:
    """Unmerged paths, or files that still contain conflict markers after a commit."""
    unmerged = _lines(_git(repo, "diff", "--name-only", "--diff-filter=U").stdout)
    if unmerged:
        return unmerged
    return _lines(_git(repo, "grep", "-l", "^<<<<<<< ").stdout)


def read_changed(repo: Path, base: str) -> list[str]:
    result = _git(repo, "diff", "--name-only", f"{base}...HEAD")
    if result.returncode != 0:
        result = _git(repo, "diff", "--name-only", "--cached")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    body = sub.add_parser("pr-body", help="print the sync PR title/body from a JSON report")
    body.add_argument("--report", type=Path, required=True)
    describe = sub.add_parser("describe", help="write a SyncReport for the current merge state")
    describe.add_argument("--repo", type=Path, default=ROOT)
    describe.add_argument("--base", default="main")
    describe.add_argument("--upstream-sha", required=True)
    describe.add_argument("--conflicts-file", type=Path)
    describe.add_argument("--out", type=Path)
    resolve = sub.add_parser(
        "resolve-tip",
        help="print the commit SHA at an upstream remote's default tip",
    )
    resolve.add_argument("--repo", type=Path, default=ROOT)
    resolve.add_argument("--remote", default=UPSTREAM_REMOTE)
    args = parser.parse_args(argv)

    if args.cmd == "resolve-tip":
        try:
            sys.stdout.write(resolve_upstream_tip(args.repo, args.remote) + "\n")
        except UpstreamTipError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 1
        return 0

    feed = load_feed()
    if args.cmd == "describe":
        conflicts = (
            read_list_file(args.conflicts_file)
            if args.conflicts_file
            else read_conflicts(args.repo)
        )
        report = collect_report(
            repo=args.repo,
            upstream_repository=feed["upstreamRepository"],
            upstream_sha=args.upstream_sha,
            base_branch=args.base,
            conflicts=conflicts,
            changed_paths=read_changed(args.repo, args.base),
        )
        text = report.to_json()
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    report_data = json.loads(Path(args.report).read_text(encoding="utf-8-sig"))
    report = SyncReport(**report_data)
    sys.stdout.write(build_pr_title(report) + "\n---\n" + build_pr_body(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
