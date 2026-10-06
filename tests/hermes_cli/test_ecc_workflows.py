"""ECC workflow-pack installer targets the active Dragon data folder.

Regression: the official ecc-universal Hermes adapter writes ``HOME/.hermes``.
Dragon's data folder is ``HERMES_HOME`` (profiles, ``HERMES_DATA_DIR_SUFFIX``,
desktop ``~/.dragon-ai-claude``), so the wrapper must never fall back to a
hardcoded ``~/.hermes``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from hermes_cli.ecc_workflows import (
    DATA_FOLDER_LABEL,
    ECC_PACK_TITLE,
    ECC_PROFILE,
    ECC_TARGET,
    EccWorkflowError,
    apply_ecc_action,
    assert_no_framework_branding,
    bind_ecc_hermes_home,
    cmd_ecc,
    ecc_child_env,
    format_human_status,
    install_argv,
    normalize_ecc_action,
    read_status,
    uninstall_argv,
)


@pytest.fixture
def profile_home(tmp_path, monkeypatch):
    home = tmp_path / "dragon-data"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


def test_install_argv_is_official_minimal_hermes_target_without_hooks():
    argv = install_argv()
    assert "--target" in argv and argv[argv.index("--target") + 1] == ECC_TARGET
    assert "--profile" in argv and argv[argv.index("--profile") + 1] == ECC_PROFILE
    assert "--no-hooks" in argv
    assert "ecc-universal" in argv
    assert "memory" not in " ".join(argv).lower()
    assert "vault" not in " ".join(argv).lower()


def test_uninstall_argv_targets_hermes_only():
    argv = uninstall_argv()
    assert argv[argv.index("--target") + 1] == ECC_TARGET
    assert "--profile" not in argv


def test_bind_ecc_hermes_home_writes_through_to_active_home(tmp_path):
    dragon_home = tmp_path / "profiles" / "work"
    staging = tmp_path / "ecc-staging"
    bind_ecc_hermes_home(dragon_home, staging)

    marker = staging / ".hermes" / "ecc-install-state.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text('{"version": "test"}', encoding="utf-8")

    assert (dragon_home / "ecc-install-state.json").read_text(encoding="utf-8") == '{"version": "test"}'
    default_hermes = Path.home() / ".hermes" / "ecc-install-state.json"
    assert not default_hermes.exists() or "test" not in default_hermes.read_text(encoding="utf-8")


def test_bind_respects_suffixed_and_custom_homes(tmp_path):
    custom = tmp_path / ".dragon-ai-claude-magic-test"
    staging = tmp_path / "stage"
    bind_ecc_hermes_home(custom, staging)
    (staging / ".hermes" / "skills" / "ecc" / "demo").mkdir(parents=True)
    (staging / ".hermes" / "skills" / "ecc" / "demo" / "SKILL.md").write_text("# demo\n", encoding="utf-8")
    assert (custom / "skills" / "ecc" / "demo" / "SKILL.md").is_file()


def test_status_reads_install_state_under_hermes_home(profile_home):
    assert read_status(profile_home).installed is False
    (profile_home / "ecc-install-state.json").write_text(
        json.dumps({"version": "2.0.0-rc.1"}), encoding="utf-8"
    )
    (profile_home / "skills" / "ecc" / "tdd-workflow").mkdir(parents=True)
    (profile_home / "skills" / "ecc" / "tdd-workflow" / "SKILL.md").write_text("n: tdd\n", encoding="utf-8")
    status = read_status(profile_home)
    assert status.installed is True
    assert status.version == "2.0.0-rc.1"
    assert status.skill_count == 1
    assert status.memory_vault is False
    assert status.cursor_hooks is False
    assert status.home == str(profile_home)


def test_apply_install_uses_staging_home_and_real_data_home(profile_home):
    seen: dict[str, object] = {}

    def runner(argv, env):
        seen["argv"] = list(argv)
        seen["home"] = env["HOME"]
        seen["hermes_home"] = env["HERMES_HOME"]
        staging_link = Path(env["HOME"]) / ".hermes"
        assert staging_link.resolve() == profile_home.resolve()
        (profile_home / "ecc-install-state.json").write_text(
            json.dumps({"version": "from-runner"}), encoding="utf-8"
        )
        return SimpleNamespace(returncode=0, stdout="{}", stderr="")

    status = apply_ecc_action("install", home=profile_home, runner=runner)
    assert status.installed is True
    assert seen["argv"] == install_argv()
    assert Path(seen["home"]) != Path.home()
    assert seen["hermes_home"] == str(profile_home)
    assert (profile_home / "ecc-install-state.json").is_file()


def test_apply_remove_uses_uninstall_argv(profile_home):
    (profile_home / "ecc-install-state.json").write_text("{}", encoding="utf-8")
    seen = {}

    def runner(argv, env):
        seen["argv"] = list(argv)
        (profile_home / "ecc-install-state.json").unlink()
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    status = apply_ecc_action("remove", home=profile_home, runner=runner)
    assert seen["argv"] == uninstall_argv()
    assert status.installed is False


def test_apply_nonzero_exit_is_friendly_error(profile_home):
    def runner(_argv, _env):
        return SimpleNamespace(returncode=1, stdout="", stderr="npx failed")

    with pytest.raises(EccWorkflowError, match="Couldn't install ECC Workflows"):
        apply_ecc_action("install", home=profile_home, runner=runner)


def test_user_facing_copy_never_names_hermes(profile_home):
    status = read_status(profile_home)
    assert_no_framework_branding(format_human_status(status, "status"))
    assert_no_framework_branding(format_human_status(status, "install"))
    assert DATA_FOLDER_LABEL in format_human_status(status)
    assert ECC_PACK_TITLE in format_human_status(status)


def test_cmd_ecc_status_json(profile_home, capsys):
    cmd_ecc(SimpleNamespace(ecc_action="status", json=True))
    payload = json.loads(capsys.readouterr().out)
    assert payload["installed"] is False
    assert payload["title"] == ECC_PACK_TITLE
    assert payload["profile"] == ECC_PROFILE
    assert "hermes" not in json.dumps(payload).lower() or payload["target"] == "hermes"
    # Internal target id may say hermes; user-facing title/home_display must not.
    assert "hermes" not in payload["title"].lower()
    assert "hermes" not in payload["home_display"].lower()


def test_ecc_parser_alias_dest_is_the_literal_typed():
    import argparse

    from hermes_cli.subcommands.ecc import build_ecc_parser

    parser = argparse.ArgumentParser()
    build_ecc_parser(parser.add_subparsers(), cmd_ecc=cmd_ecc)
    uninstall = parser.parse_args(["ecc", "uninstall"])
    upgrade = parser.parse_args(["ecc", "upgrade"])
    assert uninstall.ecc_action == "uninstall"
    assert upgrade.ecc_action == "upgrade"
    assert normalize_ecc_action(uninstall.ecc_action) == "remove"
    assert normalize_ecc_action(upgrade.ecc_action) == "update"


def test_argparse_aliases_normalize_to_canonical_actions():
    assert normalize_ecc_action("uninstall") == "remove"
    assert normalize_ecc_action("upgrade") == "update"
    assert normalize_ecc_action("remove") == "remove"
    assert normalize_ecc_action(None) == "status"


def test_cmd_ecc_accepts_uninstall_alias(profile_home, monkeypatch, capsys):
    def runner(argv, env):
        (profile_home / "ecc-install-state.json").unlink(missing_ok=True)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("hermes_cli.ecc_workflows.run_ecc_subprocess", runner)
    (profile_home / "ecc-install-state.json").write_text("{}", encoding="utf-8")
    cmd_ecc(SimpleNamespace(ecc_action="uninstall", json=False))
    out = capsys.readouterr().out
    assert "removed" in out.lower()
    assert_no_framework_branding(out)


def test_apply_accepts_uninstall_alias(profile_home):
    seen = {}

    def runner(argv, env):
        seen["argv"] = list(argv)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    apply_ecc_action("uninstall", home=profile_home, runner=runner)
    assert seen["argv"] == uninstall_argv()


def test_child_env_does_not_point_home_at_user_hermes(profile_home, tmp_path):
    staging = tmp_path / "stage"
    staging.mkdir()
    env = ecc_child_env(staging, profile_home)
    assert env["HOME"] == str(staging)
    assert env["HERMES_HOME"] == str(profile_home)
    assert env["HOME"] != str(Path.home())
    # The real user ~/.hermes must not be the adapter destination.
    assert Path(env["HOME"]) / ".hermes" != Path.home() / ".hermes"
