"""Upstream sync reports conflicts and protected Dragon files without merging."""
from __future__ import annotations

from scripts.dragon.sync_upstream import (
    SyncReport,
    build_pr_body,
    build_pr_title,
    collect_report,
    is_protected,
    protected_touched,
)


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
