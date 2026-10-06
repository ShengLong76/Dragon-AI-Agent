"""HTTP smoke for ECC Workflows marketplace routes.

Install/update/remove spawn ``hermes ecc …`` against the requested profile;
status reads ``ecc-install-state.json`` in that profile's Dragon data folder
without running npx.
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def isolated_profiles(tmp_path, monkeypatch, _isolate_hermes_home):
    from hermes_cli import profiles

    # Named like a Dragon data folder so home_display cannot leak framework branding.
    default_home = tmp_path / "dragon-data"
    default_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(default_home))
    profiles_root = default_home / "profiles"
    worker_home = profiles_root / "worker_alpha"
    for home in (default_home, worker_home):
        (home / "skills").mkdir(parents=True, exist_ok=True)
        (home / "config.yaml").write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(profiles, "_get_default_hermes_home", lambda: default_home)
    monkeypatch.setattr(profiles, "_get_profiles_root", lambda: profiles_root)
    return {"default": default_home, "worker_alpha": worker_home}


@pytest.fixture
def client(monkeypatch, isolated_profiles):
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")

    import hermes_state
    from hermes_cli.web_server import app, _SESSION_HEADER_NAME, _SESSION_TOKEN
    from hermes_constants import get_hermes_home

    monkeypatch.setattr(hermes_state, "DEFAULT_DB_PATH", get_hermes_home() / "state.db")
    c = TestClient(app)
    c.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
    return c


def test_status_reads_active_home_without_npx(client, isolated_profiles):
    home = isolated_profiles["default"]
    (home / "ecc-install-state.json").write_text(
        json.dumps({"version": "2.0.0-rc.1"}), encoding="utf-8"
    )
    (home / "skills" / "ecc" / "tdd").mkdir(parents=True)
    (home / "skills" / "ecc" / "tdd" / "SKILL.md").write_text("# tdd\n", encoding="utf-8")

    resp = client.get("/api/workflows/ecc")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["installed"] is True
    assert payload["version"] == "2.0.0-rc.1"
    assert payload["skill_count"] == 1
    assert payload["memory_vault"] is False
    assert payload["cursor_hooks"] is False
    assert payload["title"] == "ECC Workflows"
    assert "hermes" not in payload["title"].lower()
    assert "hermes" not in payload["home_display"].lower()
    assert payload["home"] == str(home)


def test_status_profile_query_reads_named_home_only(client, isolated_profiles):
    worker = isolated_profiles["worker_alpha"]
    (worker / "ecc-install-state.json").write_text(
        json.dumps({"version": "named"}), encoding="utf-8"
    )

    resp = client.get("/api/workflows/ecc", params={"profile": "worker_alpha"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["installed"] is True
    assert payload["version"] == "named"
    assert payload["home"] == str(worker)

    default_resp = client.get("/api/workflows/ecc")
    assert default_resp.json()["installed"] is False


def test_install_spawns_ecc_install_for_named_profile(client, isolated_profiles, monkeypatch):
    import hermes_cli.web_server_gateway as gateway

    calls = []

    class _FakeProc:
        pid = 4242

    def _fake_spawn(subcommand, name):
        calls.append((list(subcommand), name))
        return _FakeProc()

    monkeypatch.setattr(gateway, "_spawn_hermes_action", _fake_spawn)
    resp = client.post("/api/workflows/ecc/install", params={"profile": "worker_alpha"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["name"] == "ecc-workflows-install"
    assert calls == [(["-p", "worker_alpha", "ecc", "install"], "ecc-workflows-install")]


@pytest.mark.parametrize(
    ("path", "argv_verb", "action_name"),
    [
        ("/api/workflows/ecc/update", "update", "ecc-workflows-update"),
        ("/api/workflows/ecc/remove", "remove", "ecc-workflows-uninstall"),
        ("/api/workflows/ecc/uninstall", "remove", "ecc-workflows-uninstall"),
    ],
)
def test_mutate_routes_spawn_canonical_ecc_argv(client, path, argv_verb, action_name, monkeypatch):
    import hermes_cli.web_server_gateway as gateway

    calls = []

    class _FakeProc:
        pid = 7

    def _fake_spawn(subcommand, name):
        calls.append((list(subcommand), name))
        return _FakeProc()

    monkeypatch.setattr(gateway, "_spawn_hermes_action", _fake_spawn)
    resp = client.post(path)
    assert resp.status_code == 200
    assert calls == [([ "ecc", argv_verb], action_name)]
    assert resp.json()["name"] == action_name
