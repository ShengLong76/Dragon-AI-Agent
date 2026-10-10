"""HyperFrames catalog identifier, probes, and core-skill install wiring."""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from tools.hyperframes_skills import (
    HYPERFRAMES_CORE_SLUGS,
    HYPERFRAMES_IDENTIFIER,
    HYPERFRAMES_LICENSE,
    HYPERFRAMES_REPO_URL,
    HyperFramesProbe,
    core_skill_identifiers,
    install_hyperframes_core,
    is_hyperframes_identifier,
    parse_node_major,
    probe_hyperframes,
    setup_steps,
)


def test_umbrella_identifier_does_not_match_per_skill_paths():
    assert is_hyperframes_identifier(HYPERFRAMES_IDENTIFIER)
    assert is_hyperframes_identifier("hyperframes")
    assert is_hyperframes_identifier("heygen-com/hyperframes/")
    assert not is_hyperframes_identifier("heygen-com/hyperframes/skills/hyperframes")
    assert not is_hyperframes_identifier("dragon-agent")


def test_core_skill_identifiers_are_github_skill_folders():
    ids = core_skill_identifiers()
    assert ids[0] == "heygen-com/hyperframes/skills/hyperframes"
    assert set(slug.split("/")[-1] for slug in ids) == set(HYPERFRAMES_CORE_SLUGS)
    assert "hyperframes" in HYPERFRAMES_CORE_SLUGS
    assert "media-use" in HYPERFRAMES_CORE_SLUGS


def test_parse_node_major_accepts_v_prefix():
    assert parse_node_major("v22.14.0") == 22
    assert parse_node_major("24.1.0") == 24
    assert parse_node_major("v18.20.4") == 18
    assert parse_node_major("") is None


def test_probe_uses_injected_runner():
    def run(argv, _timeout):
        if argv[:2] == ("node", "-v"):
            return "v22.22.0"
        if argv[:2] == ("hyperframes", "--version"):
            return "0.8.27"
        if argv[:2] == ("ffmpeg", "-version"):
            return "ffmpeg version 6.0"
        return ""

    probe = probe_hyperframes(run)
    assert probe.node_ok
    assert probe.cli_ok
    assert probe.can_run_cli


def test_setup_steps_name_license_and_sandbox_not_upstream_product():
    text = setup_steps(
        HyperFramesProbe(node_major=18, node_ok=False, cli_ok=False, ffmpeg_ok=False, chrome_ok=False)
    )
    assert HYPERFRAMES_LICENSE in text
    assert HYPERFRAMES_REPO_URL in text
    assert "Node.js >= 22" in text
    assert "Linux sandbox" in text
    assert "Windows host" in text
    assert "ffmpeg" in text
    assert "hermes" not in text.lower()


def test_install_core_calls_install_one_for_each_skill_and_cli_update():
    seen: list[str] = []
    cli_ran = {"n": 0}
    sink = Console(file=StringIO(), force_terminal=False)
    probe = HyperFramesProbe(node_major=22, node_ok=True, cli_ok=True, ffmpeg_ok=True, chrome_ok=True)

    def install_one(identifier: str) -> bool:
        seen.append(identifier)
        return True

    ok = install_hyperframes_core(
        console=sink,
        probe=probe,
        install_one=install_one,
        run_cli_update=lambda: cli_ran.__setitem__("n", cli_ran["n"] + 1) or "updated",
        slugs=("hyperframes", "hyperframes-core"),
    )

    assert ok is True
    assert seen == [
        "heygen-com/hyperframes/skills/hyperframes",
        "heygen-com/hyperframes/skills/hyperframes-core",
    ]
    assert cli_ran["n"] == 1
    assert "Apache-2.0" in sink.file.getvalue()


def test_install_core_skips_cli_and_fails_when_nothing_lands():
    sink = Console(file=StringIO(), force_terminal=False)
    probe = HyperFramesProbe(node_major=None, node_ok=False, cli_ok=False, ffmpeg_ok=False, chrome_ok=False)
    cli_ran = {"n": 0}

    ok = install_hyperframes_core(
        console=sink,
        probe=probe,
        install_one=lambda _ident: False,
        run_cli_update=lambda: cli_ran.__setitem__("n", 1) or "",
        slugs=("hyperframes",),
    )

    assert ok is False
    assert cli_ran["n"] == 0
    assert "Skipped `npx hyperframes skills update`" in sink.file.getvalue()


def test_do_install_routes_umbrella_id_to_hyperframes(monkeypatch):
    from hermes_cli import skills_hub as hub

    called = {"n": 0}

    def fake_install(*, console, force=False):
        called["n"] += 1
        called["force"] = force
        console.print("core ready")
        return True

    monkeypatch.setattr("tools.hyperframes_skills.install_hyperframes_core", fake_install)
    sink = Console(file=StringIO(), force_terminal=False)
    assert hub.do_install("heygen-com/hyperframes", console=sink, skip_confirm=True) is True
    assert called["n"] == 1


def test_do_install_raises_when_hyperframes_install_fails(monkeypatch):
    from hermes_cli import skills_hub as hub

    monkeypatch.setattr("tools.hyperframes_skills.install_hyperframes_core", lambda **_kw: False)
    with pytest.raises(SystemExit):
        hub.do_install("hyperframes", console=Console(file=StringIO()), skip_confirm=True)
