"""Dragon AI product feed is the only user-facing update source.

Invariant: check/apply helpers never follow NousResearch/hermes-agent. The
scheduled sync workflow is the only path that may fetch Hermes.
"""
from __future__ import annotations

import json

from hermes_cli.product_feed import (
    fetch_remote_for_origin,
    is_product_repository,
    is_upstream_repository,
    load_product_feed,
    product_https_url,
    product_repository,
    should_skip_upstream_remote,
    update_repository,
    upstream_repository,
)
from hermes_cli.source_releases import OFFICIAL_REPOSITORY
from hermes_cli.update_cmd_git import OFFICIAL_REPO_URL, _is_fork


def test_product_feed_names_dragon_and_keeps_hermes_as_upstream_only():
    feed = load_product_feed()
    assert feed["productRepository"] == "ShengLong76/Dragon-AI-Agent"
    assert feed["upstreamRepository"] == "NousResearch/hermes-agent"
    assert product_repository() == feed["productRepository"]
    assert upstream_repository() == feed["upstreamRepository"]
    assert OFFICIAL_REPOSITORY == product_repository()
    assert OFFICIAL_REPO_URL == product_https_url()
    assert feed["publicAssetsBase"] is None


def test_hermes_remotes_are_not_a_user_update_source():
    hermes = "https://github.com/NousResearch/hermes-agent.git"
    dragon = "https://github.com/ShengLong76/Dragon-AI-Agent.git"
    other = "https://github.com/Fixture/hermes-agent.git"

    assert is_upstream_repository(hermes)
    assert is_upstream_repository("NousResearch/hermes-agent")
    assert is_upstream_repository("git@github.com:NousResearch/hermes-agent.git")
    assert not is_product_repository(hermes)
    assert is_product_repository(dragon)
    assert update_repository("NousResearch/hermes-agent") == product_repository()
    assert update_repository(None) == product_repository()
    assert update_repository("Fixture/hermes-agent") == "Fixture/hermes-agent"
    assert fetch_remote_for_origin(hermes) == product_https_url()
    assert fetch_remote_for_origin(dragon) == "origin"
    assert should_skip_upstream_remote(hermes)
    assert not should_skip_upstream_remote(dragon)
    assert _is_fork(dragon) is False
    assert _is_fork(hermes) is False
    assert _is_fork(other) is True


def test_zip_default_is_dragon_and_refuses_hermes_upstream(monkeypatch):
    from hermes_cli import update_cmd_zip
    from types import SimpleNamespace

    monkeypatch.setattr(update_cmd_zip, "_abort_zip_update_if_dirty_tree", lambda: None)
    seen = []

    class Stop(Exception):
        pass

    def download(branch, url):
        seen.append(url)
        raise Stop

    monkeypatch.setattr(update_cmd_zip, "_download_and_swap_zip", download)

    try:
        update_cmd_zip._update_via_zip(
            SimpleNamespace(branch=None),
            target_sha="a" * 40,
            completion_request={"expected_sha": None},
        )
    except Stop:
        pass
    assert seen == [f"https://github.com/{product_repository()}/archive/{'a' * 40}.zip"]

    try:
        update_cmd_zip._update_via_zip(
            SimpleNamespace(branch=None),
            target_sha="b" * 40,
            target_repository="NousResearch/hermes-agent",
            completion_request={"expected_sha": None},
        )
        raise AssertionError("Hermes ZIP updates must be refused")
    except ValueError as exc:
        assert "Dragon AI" in str(exc)


def test_fetch_compare_branch_skips_hermes_upstream(tmp_path, monkeypatch, capsys):
    from hermes_cli import update_cmd_check

    calls = []

    class Result:
        def __init__(self, code=0, stdout=""):
            self.returncode = code
            self.stdout = stdout
            self.stderr = ""

    def fake_git(git_cmd, root, args, **kwargs):
        calls.append(args)
        if args[:3] == ["remote", "get-url", "upstream"]:
            return Result(0, "https://github.com/NousResearch/hermes-agent.git")
        if args[:3] == ["remote", "get-url", "origin"]:
            return Result(0, "https://github.com/ShengLong76/Dragon-AI-Agent.git")
        if args[0] == "fetch":
            return Result(0, "")
        return Result(1, "")

    monkeypatch.setattr(update_cmd_check, "_git", fake_git)

    result, compare = update_cmd_check.fetch_compare_branch(["git"], tmp_path, "main", [])
    assert compare == "origin/main"
    assert result.returncode == 0
    fetch_remotes = [args[1] for args in calls if args and args[0] == "fetch"]
    assert "upstream" not in fetch_remotes
    assert "origin" in fetch_remotes
    assert "NousResearch/hermes-agent" not in json.dumps(calls)
    assert "Ignoring Hermes upstream" in capsys.readouterr().out


def test_fork_upstream_sync_skips_hermes_remote(tmp_path, monkeypatch, capsys):
    from hermes_cli import update_cmd_git

    def fake_stdout(git_cmd, args, cwd, **kwargs):
        if args[:3] == ["remote", "get-url", "upstream"]:
            return "https://github.com/NousResearch/hermes-agent.git"
        return None

    monkeypatch.setattr(update_cmd_git, "_git_stdout", fake_stdout)
    assert update_cmd_git._sync_with_upstream_if_needed(["git"], tmp_path, assume_yes=True) is False
    assert "Ignoring Hermes upstream" in capsys.readouterr().out
