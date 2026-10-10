"""NSIS MAX_PATH budget, cache stripping, and robust payload deletes."""
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from scripts.bundles.windows_payload import (
    WINDOWS_PACKAGED_PATH_LIMIT,
    assert_payload_windows_paths,
    finalize_windows_payload,
    iter_overlong_cache_paths,
    iter_overlong_payload_paths,
    maybe_seal_windows_desktop_payload,
    nsis_upgrade_path,
    prepared_payload_root,
    robust_rmtree,
    strip_payload_caches,
)


def test_nsis_prefix_is_the_documented_worst_case():
    sample = nsis_upgrade_path("venv/Lib/site-packages/x.py")
    assert sample.startswith("C:\\Users\\")
    assert "\\AppData\\Local\\Temp\\" in sample
    assert sample.count("U") >= 20
    assert "resources\\agent-payload" in sample


def test_path_check_fails_on_a_realistic_elevenlabs_style_pyc(tmp_path):
    # Field abort was a nested vendor pyc once NSIS parked the install in
    # %TEMP%. Build a leaf in that tree that actually overflows the 250-char
    # budget with our documented prefix (a short ``client.pyc`` does not).
    rel_dir = (
        "venv/Lib/site-packages/elevenlabs/conversational_ai/conversation/__pycache__"
    )
    leaf = "conversation_initiation_client_data_config.cpython-312.pyc"
    while True:
        relative = f"{rel_dir}/{leaf}"
        if len(nsis_upgrade_path(relative)) > WINDOWS_PACKAGED_PATH_LIMIT:
            break
        leaf = "x" + leaf
    victim = tmp_path / Path(*relative.split("/"))
    victim.parent.mkdir(parents=True)
    victim.write_bytes(b"pyc")
    overlong = iter_overlong_cache_paths(tmp_path)
    assert overlong, "a deep site-packages pyc must fail the NSIS budget"
    assert overlong[0][1] > WINDOWS_PACKAGED_PATH_LIMIT
    with pytest.raises(ValueError, match="NSIS"):
        assert_payload_windows_paths(tmp_path)


def test_strip_removes_uv_cache_and_bytecode(tmp_path):
    (tmp_path / "uv-cache" / "wheels").mkdir(parents=True)
    (tmp_path / "uv-cache" / "wheels" / "a.whl").write_bytes(b"w")
    cache = tmp_path / "venv" / "Lib" / "site-packages" / "pkg" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "mod.cpython-312.pyc").write_bytes(b"x")
    (tmp_path / "venv" / "Lib" / "site-packages" / "pkg" / "mod.py").write_text("x=1\n")
    stripped = strip_payload_caches(tmp_path)
    assert stripped["dirs"] >= 2
    assert not (tmp_path / "uv-cache").exists()
    assert not cache.exists()
    assert (tmp_path / "venv" / "Lib" / "site-packages" / "pkg" / "mod.py").is_file()
    finalize_windows_payload(tmp_path)  # remaining paths must fit


def test_finalize_allows_overlong_third_party_source(tmp_path):
    """Vendor source like lark_oapi already overflows; do not fail the bundle."""
    rel_dir = (
        "venv/lib/python3.14/site-packages/lark_oapi/api/security_and_compliance/"
        "v2/model"
    )
    leaf = "p2_security_and_compliance_device_apply_record_device_apply_event_v2.py"
    while True:
        relative = f"{rel_dir}/{leaf}"
        if len(nsis_upgrade_path(relative)) > WINDOWS_PACKAGED_PATH_LIMIT:
            break
        leaf = "x" + leaf
    victim = tmp_path / Path(*relative.split("/"))
    victim.parent.mkdir(parents=True)
    victim.write_text("x = 1\n", encoding="utf-8")
    assert iter_overlong_payload_paths(tmp_path)
    assert not iter_overlong_cache_paths(tmp_path)
    finalize_windows_payload(tmp_path)
    assert victim.is_file()


def test_robust_rmtree_clears_readonly_files(tmp_path):
    tree = tmp_path / "agent-payload"
    locked = tree / "venv" / "__pycache__"
    locked.mkdir(parents=True)
    pyc = locked / "mod.pyc"
    pyc.write_bytes(b"x")
    pyc.chmod(0o444)
    tree.chmod(tree.stat().st_mode & ~stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
    robust_rmtree(tree)
    assert not tree.exists()


def test_robust_rmtree_missing_path_is_a_no_op(tmp_path):
    robust_rmtree(tmp_path / "does-not-exist")


def test_prepared_payload_root_strips_the_admitted_suffix(tmp_path):
    prepared = tmp_path / "agent-payload.prepared.json"
    assert prepared_payload_root(prepared) == tmp_path / "agent-payload"


def test_desktop_windows_seal_strips_uv_cache_after_prepare(tmp_path):
    payload = tmp_path / "agent-payload"
    (payload / "uv-cache" / "wheels").mkdir(parents=True)
    (payload / "uv-cache" / "wheels" / "a.whl").write_bytes(b"w")
    (payload / "venv" / "lib" / "pkg").mkdir(parents=True)
    (payload / "venv" / "lib" / "pkg" / "mod.py").write_text("x=1\n", encoding="utf-8")
    prepared = tmp_path / "agent-payload.prepared.json"
    assert maybe_seal_windows_desktop_payload("darwin-arm64", prepared) is None
    assert (payload / "uv-cache").is_dir()
    stripped = maybe_seal_windows_desktop_payload("win32-x64", prepared)
    assert stripped is not None and stripped["dirs"] >= 1
    assert not (payload / "uv-cache").exists()
    assert (payload / "venv" / "lib" / "pkg" / "mod.py").is_file()
