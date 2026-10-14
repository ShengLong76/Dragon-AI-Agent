"""Upstream sync reports conflicts and protected Dragon files without merging."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from scripts.dragon.sync_upstream import (
    SyncReport,
    UpstreamTipError,
    build_pr_body,
    build_pr_title,
    collect_report,
    is_protected,
    main,
    protected_touched,
    resolve_upstream_tip,
)

_SHA = re.compile(r"^[0-9a-f]{40}$")


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _init_repo(path: Path, branch: str = "main") -> Path:
    path.mkdir()
    _git(path, "init", "-b", branch)
    _git(path, "config", "user.email", "sync@example.invalid")
    _git(path, "config", "user.name", "Sync")
    (path / "shared.txt").write_text("shared\n", encoding="utf-8")
    _git(path, "add", "shared.txt")
    _git(path, "commit", "-m", "shared base")
    return path


def _commit_file(repo: Path, name: str, content: str, message: str) -> str:
    (repo / name).write_text(content, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def test_protected_paths_cover_branding_and_ignore_unrelated():
    assert is_protected("branding/dragon-logo.png")
    assert is_protected("apps/desktop/src/dragon/brand.ts")
    assert is_protected("README.md")
    assert not is_protected("hermes_cli/source_check.py")
    assert protected_touched([
        "hermes_cli/source_check.py",
        "branding/dragon-logo.png",
        "apps/desktop/src/dragon/brand.ts",
    ]) == ["apps/desktop/src/dragon/brand.ts", "branding/dragon-logo.png"]


def test_conflict_report_is_draft_and_lists_files(tmp_path):
    report = collect_report(
        repo=tmp_path,
        upstream_repository="NousResearch/hermes-agent",
        upstream_sha="a" * 40,
        base_branch="main",
        conflicts=["apps/desktop/package.json", "README.md"],
        changed_paths=["apps/desktop/package.json", "README.md", "hermes_cli/source_check.py"],
    )
    assert report.has_conflicts is True
    assert report.draft is True
    assert report.conflicts == ["README.md", "apps/desktop/package.json"]
    assert "README.md" in report.protected_touched
    body = build_pr_body(report)
    assert "Auto-merge: **never**" in body
    assert "`README.md`" in body
    assert "`apps/desktop/package.json`" in body
    assert "Protected Dragon files" in body
    assert "James approves" in body
    title = build_pr_title(report)
    assert "conflicts" in title
    assert report.upstream_sha[:12] in title


def test_read_conflicts_finds_markers_after_commit(tmp_path):
    import subprocess
    from scripts.dragon.sync_upstream import read_conflicts, read_list_file

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "sync@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Sync"], cwd=repo, check=True)
    conflicted = repo / "README.md"
    conflicted.write_text("<<<<<<< HEAD\nDragon\n=======\nHermes\n>>>>>>> upstream\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "conflicts remain"], cwd=repo, check=True, capture_output=True)
    assert read_conflicts(repo) == ["README.md"]

    listed = tmp_path / "conflicts.txt"
    listed.write_text("apps/desktop/package.json\nREADME.md\n", encoding="utf-8")
    assert read_list_file(listed) == ["apps/desktop/package.json", "README.md"]


def test_clean_merge_is_not_draft(tmp_path):
    report = collect_report(
        repo=tmp_path,
        upstream_repository="NousResearch/hermes-agent",
        upstream_sha="b" * 40,
        base_branch="main",
        conflicts=[],
        changed_paths=["hermes_cli/source_check.py"],
    )
    assert report.has_conflicts is False
    assert report.draft is False
    assert report.protected_touched == []
    body = build_pr_body(report)
    assert "completed without conflicts" in body
    assert SyncReport(**report.__dict__).has_conflicts is False


def test_bare_head_fetch_does_not_create_remote_tracking_head(tmp_path):
    """Regression for the scheduled sync: `git fetch remote HEAD` only writes FETCH_HEAD."""
    upstream = _init_repo(tmp_path / "upstream")
    expected = _commit_file(upstream, "tip.txt", "upstream tip\n", "upstream tip")
    downstream = _init_repo(tmp_path / "downstream")
    _git(downstream, "remote", "add", "hermes-upstream", str(upstream))

    _git(downstream, "fetch", "hermes-upstream", "HEAD")
    broken = _git(downstream, "rev-parse", "hermes-upstream/HEAD", check=False)
    assert broken.returncode != 0
    assert not _SHA.fullmatch(broken.stdout.strip())
    fetch_head = _git(downstream, "rev-parse", "--verify", "FETCH_HEAD").stdout.strip()
    assert fetch_head == expected
    show_ref = _git(downstream, "show-ref", "hermes-upstream/HEAD", check=False)
    assert show_ref.returncode != 0


def test_resolve_upstream_tip_from_simulated_default_branch(tmp_path):
    upstream = _init_repo(tmp_path / "upstream")
    expected = _commit_file(upstream, "hermes.txt", "from hermes\n", "hermes change")
    downstream = tmp_path / "downstream"
    _git(tmp_path, "clone", str(upstream), str(downstream))
    _git(downstream, "config", "user.email", "sync@example.invalid")
    _git(downstream, "config", "user.name", "Sync")
    _commit_file(downstream, "dragon.txt", "dragon only\n", "dragon change")
    _git(downstream, "remote", "add", "hermes-upstream", str(upstream))

    sha = resolve_upstream_tip(downstream, "hermes-upstream")
    assert sha == expected
    tracking = _git(downstream, "rev-parse", "--verify", "refs/remotes/hermes-upstream/main")
    assert tracking.stdout.strip() == expected


def test_resolve_upstream_tip_follows_non_main_default_branch(tmp_path):
    upstream = _init_repo(tmp_path / "upstream", branch="trunk")
    expected = _commit_file(upstream, "trunk.txt", "trunk tip\n", "trunk tip")
    downstream = _init_repo(tmp_path / "downstream")
    _git(downstream, "remote", "add", "hermes-upstream", str(upstream))

    sha = resolve_upstream_tip(downstream, "hermes-upstream")
    assert sha == expected
    tracking = _git(downstream, "rev-parse", "--verify", "refs/remotes/hermes-upstream/trunk")
    assert tracking.stdout.strip() == expected


def test_resolve_fetched_tip_falls_back_to_fetch_head(tmp_path):
    upstream = _init_repo(tmp_path / "upstream")
    expected = _commit_file(upstream, "tip.txt", "tip\n", "tip")
    downstream = _init_repo(tmp_path / "downstream")
    _git(downstream, "remote", "add", "hermes-upstream", str(upstream))
    _git(downstream, "fetch", "hermes-upstream", "HEAD")

    from scripts.dragon.sync_upstream import resolve_fetched_tip

    sha = resolve_fetched_tip(downstream, "refs/remotes/hermes-upstream/main")
    assert sha == expected


def test_resolve_upstream_tip_fails_loudly_when_unresolvable(tmp_path):
    downstream = _init_repo(tmp_path / "downstream")
    _git(downstream, "remote", "add", "hermes-upstream", str(tmp_path / "missing-upstream"))
    with pytest.raises(UpstreamTipError, match="Could not resolve a Hermes upstream tip SHA"):
        resolve_upstream_tip(downstream, "hermes-upstream")


def test_resolved_tip_is_something_git_can_merge(tmp_path):
    upstream = _init_repo(tmp_path / "upstream")
    downstream = tmp_path / "downstream"
    _git(tmp_path, "clone", str(upstream), str(downstream))
    _git(downstream, "config", "user.email", "sync@example.invalid")
    _git(downstream, "config", "user.name", "Sync")
    _commit_file(downstream, "dragon.txt", "dragon only\n", "dragon change")
    expected = _commit_file(upstream, "hermes.txt", "from hermes\n", "hermes change")
    _git(downstream, "remote", "add", "hermes-upstream", str(upstream))

    sha = resolve_upstream_tip(downstream, "hermes-upstream")
    _git(downstream, "checkout", "-B", "dragon/upstream-sync")
    merge = _git(downstream, "merge", "--no-ff", "--no-edit", sha)
    assert merge.returncode == 0
    assert (downstream / "hermes.txt").read_text(encoding="utf-8") == "from hermes\n"
    assert (downstream / "dragon.txt").read_text(encoding="utf-8") == "dragon only\n"


def test_resolve_tip_cli_prints_sha(tmp_path, capsys):
    upstream = _init_repo(tmp_path / "upstream")
    expected = _git(upstream, "rev-parse", "HEAD").stdout.strip()
    downstream = _init_repo(tmp_path / "downstream")
    _git(downstream, "remote", "add", "hermes-upstream", str(upstream))

    assert main(["resolve-tip", "--repo", str(downstream), "--remote", "hermes-upstream"]) == 0
    assert capsys.readouterr().out.strip() == expected


def test_resolve_tip_cli_fails_loudly(tmp_path, capsys):
    downstream = _init_repo(tmp_path / "downstream")
    _git(downstream, "remote", "add", "hermes-upstream", str(tmp_path / "missing-upstream"))
    assert main(["resolve-tip", "--repo", str(downstream), "--remote", "hermes-upstream"]) == 1
    err = capsys.readouterr().err
    assert "Could not resolve a Hermes upstream tip SHA" in err
