"""voxl process helpers: password stays off argv/URLs/logs; install scripts stay ASCII."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.bot_desktop import voxl, voxl_install


def test_redact_strips_token_query_and_password():
    secret = "s3cret-value"
    text = "open http://127.0.0.1:9/?token=" + secret + " auth=" + secret
    out = voxl.redact(text, secret)
    assert secret not in out
    assert "?token=[redacted]" in out
    assert "auth=[redacted]" in out


def test_argv_never_contains_the_password(tmp_path, monkeypatch):
    binary = tmp_path / "voxl"
    binary.write_text("#!/bin/sh\n", encoding="ascii")
    binary.chmod(0o755)
    monkeypatch.setattr(voxl_install, "resolve_binary", lambda: binary)
    args = voxl.argv_for(9400, audio=False, microphone=False)
    joined = " ".join(args)
    assert "--enable-basic-auth=true" in args
    assert "--addr=127.0.0.1" in args
    assert "--port=9400" in args
    assert "password" not in joined.lower() or "--enable-basic-auth" in joined
    assert not any(a.startswith("--basic-auth-password") for a in args)
    assert "Claude" not in joined


@pytest.mark.platforms("posix")
def test_password_file_is_0600(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from hermes_constants import reset_hermes_home_override, set_hermes_home_override
    token = set_hermes_home_override(tmp_path)
    try:
        password = voxl.ensure_password()
        path = voxl.secret_path()
        assert path.exists()
        assert (path.stat().st_mode & 0o777) == 0o600
        assert voxl.load_password() == password
        assert password not in str(path)
    finally:
        reset_hermes_home_override(token)


def test_install_scripts_are_ascii_only():
    root = Path(__file__).resolve().parents[2]
    for rel in ("scripts/install-voxl.sh", "scripts/install-voxl.ps1", "scripts/bot_desktop_voxl_smoke.py"):
        data = (root / rel).read_bytes()
        data.decode("ascii")
        assert b"Claude" not in data
        assert b"\xe2" not in data  # no UTF-8 continuation from smart punctuation


@pytest.mark.parametrize("flag", ["audio", "microphone"])
def test_audio_and_microphone_default_off(tmp_path, monkeypatch, flag):
    binary = tmp_path / "voxl"
    binary.write_text("x", encoding="ascii")
    monkeypatch.setattr(voxl_install, "resolve_binary", lambda: binary)
    args = voxl.argv_for(1)
    assert f"--{flag}-enabled=false" in args
