"""Bundled Dragon hub skills: identifiers, local copy, pinned deps, no remote fetch."""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from tools.dragon_hub_skills import (
    AGENT_REACH_CREDIT,
    DRAGON_HUB_SKILLS,
    RSS_IDENTIFIER,
    RSS_REQUIREMENT,
    WEB_READER_IDENTIFIER,
    YOUTUBE_IDENTIFIER,
    YOUTUBE_REQUIREMENT,
    bundled_skill_dir,
    copy_bundled_skill,
    install_dragon_hub_skill,
    is_dragon_hub_identifier,
    read_pinned_requirements,
    resolve_dragon_hub_skill,
    setup_steps,
)


def test_identifiers_match_aliases_not_unrelated_skills():
    assert is_dragon_hub_identifier(YOUTUBE_IDENTIFIER)
    assert is_dragon_hub_identifier("dragon-youtube")
    assert is_dragon_hub_identifier("official/research/dragon-rss/")
    assert is_dragon_hub_identifier(WEB_READER_IDENTIFIER)
    assert not is_dragon_hub_identifier("heygen-com/hyperframes")
    assert not is_dragon_hub_identifier("dragon-agent")
    assert resolve_dragon_hub_skill("dragon/youtube").name == "dragon-youtube"


def test_bundled_folders_are_local_and_have_helpers():
    for skill in DRAGON_HUB_SKILLS:
        src = bundled_skill_dir(skill)
        assert src.is_dir()
        assert (src / "SKILL.md").is_file()
        assert list(src.glob("scripts/*.py"))
        assert src.as_posix().startswith("/") or src.drive
        assert "http://" not in str(src)
        assert "https://" not in str(src)


def test_read_pinned_requirements_tolerates_utf8_bom(tmp_path):
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "requirements.txt").write_bytes(b"\xef\xbb\xbfyt-dlp>=2025.1.26,<2027\n")
    assert read_pinned_requirements(skill_dir) == [YOUTUBE_REQUIREMENT]


def test_pins_are_bounded_and_match_requirements_files():
    youtube = resolve_dragon_hub_skill(YOUTUBE_IDENTIFIER)
    rss = resolve_dragon_hub_skill(RSS_IDENTIFIER)
    web = resolve_dragon_hub_skill(WEB_READER_IDENTIFIER)
    assert youtube.requirements == (YOUTUBE_REQUIREMENT,)
    assert rss.requirements == (RSS_REQUIREMENT,)
    assert web.requirements == ()
    assert YOUTUBE_REQUIREMENT.startswith("yt-dlp>=") and ",<" in YOUTUBE_REQUIREMENT
    assert RSS_REQUIREMENT.startswith("feedparser>=") and ",<" in RSS_REQUIREMENT
    assert read_pinned_requirements(bundled_skill_dir(youtube)) == [YOUTUBE_REQUIREMENT]
    assert read_pinned_requirements(bundled_skill_dir(rss)) == [RSS_REQUIREMENT]
    assert read_pinned_requirements(bundled_skill_dir(web)) == []


def test_setup_steps_credit_agent_reach_and_stay_local():
    text = setup_steps(resolve_dragon_hub_skill(YOUTUBE_IDENTIFIER))
    assert AGENT_REACH_CREDIT in text
    assert "Panniantong/Agent-Reach" in text
    assert "not bundled" in text
    assert "No cookies" in text
    assert "Windows" in text
    assert "raw.githubusercontent" not in text
    assert "curl " not in text
    assert not re.search(r"\bhermes\b", text, flags=re.IGNORECASE)


def test_install_copies_local_files_and_pins_deps(tmp_path):
    dest_root = tmp_path / "skills"
    helper_root = tmp_path / "helpers"
    seen: list[tuple] = []

    def install_deps(name, requirements, root):
        seen.append((name, tuple(requirements), root))
        python = root / name / "python"
        python.parent.mkdir(parents=True, exist_ok=True)
        python.write_text("fake", encoding="utf-8")
        return python

    sink = Console(file=StringIO(), force_terminal=False)
    ok = install_dragon_hub_skill(
        YOUTUBE_IDENTIFIER,
        console=sink,
        dest_root=dest_root,
        helper_root=helper_root,
        install_deps=install_deps,
        record_lock=False,
    )
    assert ok is True
    dest = dest_root / "dragon-youtube"
    assert (dest / "SKILL.md").is_file()
    assert (dest / "scripts" / "youtube.py").is_file()
    assert (dest / ".helper-python").read_text(encoding="utf-8-sig").endswith("python")
    assert seen == [("dragon-youtube", (YOUTUBE_REQUIREMENT,), helper_root)]
    log = sink.file.getvalue()
    assert "Agent-Reach" in log
    assert "yt-dlp" in log


def test_copy_does_not_follow_a_remote_url(tmp_path):
    src = bundled_skill_dir(resolve_dragon_hub_skill(WEB_READER_IDENTIFIER))
    dest = tmp_path / "dragon-web-reader"
    files = copy_bundled_skill(src, dest)
    assert "SKILL.md" in files
    assert (dest / "scripts" / "read_page.py").is_file()
    assert not any(name.startswith("http") for name in files)


def test_do_install_routes_dragon_hub_ids(monkeypatch):
    from hermes_cli import skills_hub as hub

    called = {}

    def fake_install(identifier, *, console, force=False):
        called["id"] = identifier
        called["force"] = force
        console.print("ready")
        return True

    monkeypatch.setattr("tools.dragon_hub_skills.install_dragon_hub_skill", fake_install)
    sink = Console(file=StringIO(), force_terminal=False)
    assert hub.do_install("dragon/rss", console=sink, skip_confirm=True) is True
    assert called["id"] == "dragon/rss"


def test_do_install_raises_when_dragon_hub_install_fails(monkeypatch):
    from hermes_cli import skills_hub as hub

    monkeypatch.setattr("tools.dragon_hub_skills.install_dragon_hub_skill", lambda *_a, **_k: False)
    with pytest.raises(SystemExit):
        hub.do_install("dragon/web-reader", console=Console(file=StringIO()), skip_confirm=True)
