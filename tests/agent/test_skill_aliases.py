"""Legacy hermes-* skill ids resolve to Dragon ids without breaking installs."""
from __future__ import annotations

from pathlib import Path

from agent.skill_aliases import (
    SKILL_NAME_ALIASES,
    canonical_skill_name,
    legacy_names_for,
    skill_name_equivalents,
)
from agent.skill_utils import ESSENTIAL_SKILLS, normalize_skill_lookup_name


def test_shipped_aliases_cover_the_three_rebranded_ids():
    assert SKILL_NAME_ALIASES["hermes-agent"] == "dragon-agent"
    assert SKILL_NAME_ALIASES["hermes-agent-skill-authoring"] == "dragon-agent-skill-authoring"
    assert SKILL_NAME_ALIASES["inspecting-hermes-desktop-dom"] == "inspecting-dragon-desktop-dom"


def test_canonical_name_rewrites_bare_and_path_forms():
    assert canonical_skill_name("hermes-agent") == "dragon-agent"
    assert canonical_skill_name("autonomous-ai-agents/hermes-agent") == "autonomous-ai-agents/dragon-agent"
    assert canonical_skill_name("dragon-agent") == "dragon-agent"
    assert canonical_skill_name("gif-search") == "gif-search"


def test_equivalents_include_legacy_and_canonical():
    names = skill_name_equivalents("hermes-agent")
    assert names == {"hermes-agent", "dragon-agent"}
    assert legacy_names_for("dragon-agent") == {"hermes-agent"}


def test_normalize_lookup_applies_alias_for_relative_ids():
    assert normalize_skill_lookup_name("hermes-agent") == "dragon-agent"
    assert normalize_skill_lookup_name("inspecting-hermes-desktop-dom") == "inspecting-dragon-desktop-dom"


def test_essential_skills_include_both_ids(tmp_path, monkeypatch):
    import agent.skill_utils as su

    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "skills:\n  disabled:\n    - hermes-agent\n    - dragon-agent\n    - gif-search\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(su, "get_config_path", lambda: cfg)
    su._RAW_CONFIG_CACHE.clear()
    disabled = su.get_disabled_skill_names(platform="cli")
    assert "hermes-agent" not in disabled
    assert "dragon-agent" not in disabled
    assert "gif-search" in disabled
    assert "dragon-agent" in ESSENTIAL_SKILLS
    assert "hermes-agent" in ESSENTIAL_SKILLS


def test_skill_view_resolves_legacy_name_to_renamed_dir(tmp_path, monkeypatch):
    """An existing install that still asks for hermes-agent gets dragon-agent."""
    from tools import skills_tool

    bundled = tmp_path / "skills"
    skill = bundled / "autonomous-ai-agents" / "dragon-agent"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: dragon-agent\ndescription: Use Dragon AI.\n---\n# Dragon AI\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(skills_tool, "SKILLS_DIR", bundled)
    monkeypatch.setattr(skills_tool, "_SKILLS_DIR_AT_IMPORT", Path("/__never__/skills"))
    skills_tool.clear_skills_cache()

    payload = skills_tool.skill_view("hermes-agent", preprocess=False)
    assert '"name": "dragon-agent"' in payload or "'name': 'dragon-agent'" in payload or "dragon-agent" in payload
    assert "Dragon AI" in payload
