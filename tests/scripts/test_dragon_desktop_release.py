"""Dragon GitHub-only Windows release: no R2, one Setup exe, Dragon titles."""
from __future__ import annotations

import json
from pathlib import Path

import hermes_yaml
import pytest

from scripts.dragon import desktop_release
from scripts.releases.job_groups import JOB_GROUPS

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/desktop-bundled-release.yml"


def test_github_only_when_product_feed_has_no_cdn():
    assert desktop_release.github_only() is True
    assert desktop_release.windows_builder_targets() == ["--win", "nsis"]
    assert desktop_release.release_title("0.3.0") == "Dragon AI v0.3.0"
    assert "Hermes" not in desktop_release.release_title("0.3.0")


def test_admit_without_r2_disables_hermes_job_groups(tmp_path):
    desktop = tmp_path / "apps/desktop"
    desktop.mkdir(parents=True)
    (desktop / "package.json").write_text('{"version": "0.3.0"}\n', encoding="utf-8")

    outputs = desktop_release.admit(
        env={
            "CLOUDFLARE_R2_ACCESS_KEY_ID": "",
            "GITHUB_SHA": "a" * 40,
            "TAG": "",
            "GITHUB_REPOSITORY": "ShengLong76/Dragon-AI-Agent",
        },
        repo=tmp_path,
    )
    assert outputs["dragon-github-only"] == "true"
    assert outputs["payload-tag"] == "v0.3.0"
    assert outputs["payload-version"] == "0.3.0"
    assert outputs["channel"] == "latest"
    assert outputs["sha"] == "a" * 40
    assert all(outputs[group] == "false" for group in JOB_GROUPS)


def test_admit_keeps_a_canary_tag_but_still_skips_r2_jobs(tmp_path):
    desktop = tmp_path / "apps/desktop"
    desktop.mkdir(parents=True)
    (desktop / "package.json").write_text('{"version": "0.3.0"}\n', encoding="utf-8")

    outputs = desktop_release.admit(
        env={
            "TAG": "v0.3.0+canary.20261008T120000Z",
            "GITHUB_SHA": "b" * 40,
            "GITHUB_REPOSITORY": "ShengLong76/Dragon-AI-Agent",
        },
        repo=tmp_path,
    )
    assert outputs["dragon-github-only"] == "true"
    assert outputs["payload-tag"] == "v0.3.0+canary.20261008T120000Z"
    assert outputs["channel"] == "canary"
    assert outputs["win32-x64"] == "false"


def test_admit_leaves_hermes_graph_when_r2_is_configured():
    assert desktop_release.admit(
        env={
            "CLOUDFLARE_R2_ACCESS_KEY_ID": "present",
            "GITHUB_REPOSITORY": "ShengLong76/Dragon-AI-Agent",
        }
    ) == {"dragon-github-only": "false"}


def test_admit_leaves_hermes_graph_on_fixture_repos():
    assert desktop_release.admit(
        env={"CLOUDFLARE_R2_ACCESS_KEY_ID": "", "GITHUB_REPOSITORY": "fixture/repo"}
    ) == {"dragon-github-only": "false"}


def test_latest_yml_names_the_setup_exe(tmp_path):
    exe = tmp_path / "DragonAIAgent-Setup-0.3.0-x64.exe"
    exe.write_bytes(b"dragon-setup")
    dest = desktop_release.write_latest_yml(tmp_path)
    text = dest.read_text(encoding="utf-8")
    assert "version: 0.3.0" in text
    assert "DragonAIAgent-Setup-0.3.0-x64.exe" in text
    assert "Hermes" not in text
    assert "nousresearch" not in text.lower()
    names = [path.name for path in desktop_release.release_assets(tmp_path)]
    assert names[0] == "DragonAIAgent-Setup-0.3.0-x64.exe"
    assert "latest.yml" in names


def test_workflow_skips_r2_archive_and_runs_dragon_windows_job():
    workflow = hermes_yaml.safe_load(WORKFLOW.read_text(encoding="utf-8-sig"))
    validate = workflow["jobs"]["validate"]
    archive = next(step for step in validate["steps"] if step.get("name") == "Archive every pinned input")
    assert "CLOUDFLARE_R2_ACCESS_KEY_ID" in str(archive.get("if") or "")

    dragon = workflow["jobs"]["dragon-windows"]
    assert dragon["runs-on"] == "windows-latest"
    assert "windows-latest-32-core" not in json.dumps(dragon)
    assert "AZURE_SIGN" not in json.dumps(dragon)
    assert "dragon-github-only" in str(dragon.get("if") or "")

    attach = workflow["jobs"]["dragon-attach-github"]
    assert attach.get("permissions", {}).get("contents") == "write"
    script = json.dumps(attach)
    assert "scripts.dragon.desktop_release attach" in script
    assert "scripts/dragon/desktop_release.py" in WORKFLOW.read_text(encoding="utf-8-sig")
    assert "upload_release" in str(attach.get("if") or "")
    assert "gh release edit" not in script or "--draft" in script
    assert "NousResearch" not in script
    assert "hermes-assets" not in script
    assert "gh release edit --draft=false" not in script
    assert "publish" not in script.lower() or "never" in script.lower() or "draft" in script.lower()


def test_dragon_stable_dispatch_uses_bundled_release_on_main(monkeypatch, tmp_path):
    import subprocess

    from scripts import release

    calls = []
    monkeypatch.setattr(release, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(release.shutil, "which", lambda _: "gh")

    def run(command, **kwargs):
        calls.append(command)
        if command[:3] == ["gh", "repo", "view"]:
            return subprocess.CompletedProcess(command, 0, "main\n", "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(release.subprocess, "run", run)
    assert release.dispatch_desktop_build("v0.3.0", "ShengLong76/Dragon-AI-Agent")
    dispatch = next(call for call in calls if call[1:3] == ["workflow", "run"])
    assert dispatch == [
        "gh", "workflow", "run", "desktop-bundled-release.yml", "--ref", "main",
        "-f", "tag=v0.3.0", "-f", "upload_release=true",
        "--repo", "ShengLong76/Dragon-AI-Agent",
    ]


def test_dragon_latest_prepares_without_a_hermes_claim(tmp_path, monkeypatch):
    import subprocess

    from scripts.bundles.desktop_prepare import BuildRequest
    from tests.scripts.test_desktop_preparation import _project

    monkeypatch.delenv("RELEASE_CLAIM_TAG", raising=False)
    monkeypatch.delenv("RELEASE_CLAIM_OBJECT", raising=False)
    source, commit = _project(tmp_path)
    subprocess.run(["git", "tag", "v1.2.3", commit], cwd=source, check=True, capture_output=True)
    request = BuildRequest.create(
        source, tag="v1.2.3", commit=None, variant="bundled",
        work=tmp_path / "work", cache=tmp_path / "cache", bundle_env={},
    )
    assert request.version == "1.2.3"
    assert request.tag == "v1.2.3"
    assert request.release_epoch is None
    assert request.commit == commit
