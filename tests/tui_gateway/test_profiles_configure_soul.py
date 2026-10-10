"""profiles.configure writes SOUL.md inside the named profile directory.

The Bot Details pane reads the persona via profiles.describe and saves edits
through profiles.configure. The write must land on ``<profile>/SOUL.md`` and
refuse a traversal profile name so it cannot escape the profiles root.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tui_gateway.server as server


@pytest.fixture
def profile_dir(tmp_path, monkeypatch) -> Path:
    """Named profile ``research`` under a temp HERMES_HOME."""
    root = tmp_path / "hermes_home"
    path = root / "profiles" / "research"
    path.mkdir(parents=True)
    (path / "config.yaml").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(root))
    return path


def _configure(params: dict) -> dict:
    resp = server._methods["profiles.configure"](1, params)
    return resp


def test_configure_writes_soul_inside_the_profile_dir(profile_dir: Path):
    soul = "# Researcher\n\nYou look things up.\n"

    resp = _configure({"name": "research", "soul": soul})

    assert "error" not in resp, resp.get("error")
    assert resp["result"]["applied"]["soul"] is True
    written = profile_dir / "SOUL.md"
    assert written.is_file()
    assert written.read_text(encoding="utf-8") == soul
    assert written.parent == profile_dir
    assert not (profile_dir.parent / "SOUL.md").exists()


def test_configure_replaces_existing_soul(profile_dir: Path):
    existing = profile_dir / "SOUL.md"
    existing.write_text("# Old\n", encoding="utf-8")

    resp = _configure({"name": "research", "soul": "# New\n"})

    assert "error" not in resp, resp.get("error")
    assert existing.read_text(encoding="utf-8") == "# New\n"


@pytest.mark.parametrize("name", ["..", "../outside", "../../tmp", "a/b"])
def test_configure_rejects_traversal_profile_name(profile_dir: Path, name: str):
    resp = _configure({"name": name, "soul": "# escaped\n"})

    assert "error" in resp
    assert resp["error"]["code"] == 4064
    assert not (profile_dir.parent / "SOUL.md").exists()
    assert not (profile_dir / "SOUL.md").exists() or (
        profile_dir / "SOUL.md"
    ).read_text(encoding="utf-8") != "# escaped\n"
