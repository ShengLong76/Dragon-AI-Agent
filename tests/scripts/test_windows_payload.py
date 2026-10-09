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
    iter_overlong_payload_paths,
    nsis_upgrade_path,
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
    rel = (
        "venv/Lib/site-packages/elevenlabs/conversational_ai/conversation/"
        "__pycache__/client.cpython-312.pyc"
    )
    victim = tmp_path / Path(*rel.split("/"))
    victim.parent.mkdir(parents=True)
    victim.write_bytes(b"pyc")
    overlong = iter_overlong_payload_paths(tmp_path)
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
