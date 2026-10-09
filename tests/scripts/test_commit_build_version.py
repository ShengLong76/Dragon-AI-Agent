"""Commit builds stamp the Dragon product version, not pyproject 0.0.0."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.releases.commit_build import version_at

ROOT = Path(__file__).resolve().parents[2]


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True, encoding="utf-8").strip()


def test_version_at_prefers_product_feed_over_pyproject(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text('[project]\nname="x"\nversion="0.0.0"\n', encoding="utf-8")
    branding = repo / "branding"
    branding.mkdir()
    (branding / "product-feed.json").write_text(
        json.dumps({"productVersion": "0.3.0", "productName": "Dragon AI"}), encoding="utf-8"
    )
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "stamp")
    commit = git(repo, "rev-parse", "HEAD")
    assert version_at(repo, commit) == "0.3.0"


def test_version_at_falls_back_to_desktop_package_json(tmp_path):
    repo = tmp_path / "repo"
    desktop = repo / "apps" / "desktop"
    desktop.mkdir(parents=True)
    (repo / "pyproject.toml").write_text('[project]\nname="x"\nversion="0.0.0"\n', encoding="utf-8")
    (desktop / "package.json").write_text(json.dumps({"version": "0.3.0"}), encoding="utf-8")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "stamp")
    commit = git(repo, "rev-parse", "HEAD")
    assert version_at(repo, commit) == "0.3.0"


def test_live_checkout_commit_version_is_the_dragon_product():
    feed = json.loads((ROOT / "branding" / "product-feed.json").read_text(encoding="utf-8"))
    desktop = json.loads((ROOT / "apps" / "desktop" / "package.json").read_text(encoding="utf-8"))
    assert feed["productVersion"] == desktop["version"]
    assert feed["productVersion"] != "0.0.0"
    commit = git(ROOT, "rev-parse", "HEAD")
    assert version_at(ROOT, commit) == feed["productVersion"]
