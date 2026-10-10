"""Migration 49→50: the container sandbox default becomes dragon-sandbox:desktop.

A saved image still equal to the previous Nous default is dropped so the file
follows the new default at read time but stays unpinned (an existing persisted
Docker sandbox is kept). A user pin is never touched.
"""

import os
from unittest.mock import patch

import hermes_yaml as yaml


def _run(tmp_path, config):
    from hermes_cli.config_migrations import run_migrations

    (tmp_path / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    with patch.dict(os.environ, {"HERMES_HOME": str(tmp_path)}):
        run_migrations(49, {"env_added": [], "config_added": [], "warnings": []}, quiet=True)
    return yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))["terminal"]


def test_previous_default_is_dropped_and_a_user_pin_survives(tmp_path):
    from hermes_cli.config import load_config
    from hermes_cli.config_defaults import DEFAULT_SANDBOX_IMAGE, PREVIOUS_DEFAULT_SANDBOX_IMAGE

    terminal = _run(tmp_path, {"_config_version": 49, "terminal": {
        "backend": "docker",
        "docker_image": PREVIOUS_DEFAULT_SANDBOX_IMAGE,
        "singularity_image": f"docker://{PREVIOUS_DEFAULT_SANDBOX_IMAGE}",
        "modal_image": "ghcr.io/me/custom:1",
    }})
    assert "docker_image" not in terminal, "the previous default is the template copied, not a pin: drop it"
    assert "singularity_image" not in terminal
    assert terminal["modal_image"] == "ghcr.io/me/custom:1", "a user's own image must never be rewritten"
    with patch.dict(os.environ, {"HERMES_HOME": str(tmp_path)}):
        merged = load_config()["terminal"]
    assert merged["docker_image"] == DEFAULT_SANDBOX_IMAGE, "the dropped key follows the Dragon default"
    assert DEFAULT_SANDBOX_IMAGE == "dragon-sandbox:desktop"
