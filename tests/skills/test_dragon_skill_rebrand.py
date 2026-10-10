"""Bundled skills and the Skills Hub must not show Hermes/Nous/Teknium branding."""
from __future__ import annotations

import re
from pathlib import Path

import hermes_yaml as yaml

REPO = Path(__file__).resolve().parents[2]
SKILLS = REPO / "skills"
# Frontmatter + first heading are what the Skills screen lists and opens on.
BANNED = re.compile(r"\b(Hermes Agent|Hermes Desktop|Nous Research|Teknium)\b")
HERMES_ID = re.compile(r"\bhermes-agent\b|\binspecting-hermes-desktop-dom\b|\bhermes-agent-skill-authoring\b")


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), path
    close = re.search(r"\n---\s*\n", text[3:])
    assert close, path
    data = yaml.safe_load(text[3 : close.start() + 3])
    assert isinstance(data, dict)
    return data


def test_rebranded_skill_ids_ship_under_dragon_names():
    assert (SKILLS / "autonomous-ai-agents" / "dragon-agent" / "SKILL.md").is_file()
    assert (SKILLS / "software-development" / "dragon-agent-skill-authoring" / "SKILL.md").is_file()
    assert (SKILLS / "software-development" / "inspecting-dragon-desktop-dom" / "SKILL.md").is_file()
    assert not (SKILLS / "autonomous-ai-agents" / "hermes-agent" / "SKILL.md").exists()
    assert not (SKILLS / "software-development" / "hermes-agent-skill-authoring" / "SKILL.md").exists()
    assert not (SKILLS / "software-development" / "inspecting-hermes-desktop-dom" / "SKILL.md").exists()


def test_rebranded_skill_frontmatter_is_dragon():
    agent = _frontmatter(SKILLS / "autonomous-ai-agents" / "dragon-agent" / "SKILL.md")
    assert agent["name"] == "dragon-agent"
    assert "Dragon AI" in agent["description"]
    assert "Hermes" not in agent["description"]
    assert agent["author"] == "Dragon AI"
    authoring = _frontmatter(SKILLS / "software-development" / "dragon-agent-skill-authoring" / "SKILL.md")
    assert authoring["name"] == "dragon-agent-skill-authoring"
    assert authoring["author"] == "Dragon AI"
    inspect = _frontmatter(SKILLS / "software-development" / "inspecting-dragon-desktop-dom" / "SKILL.md")
    assert inspect["name"] == "inspecting-dragon-desktop-dom"
    assert inspect["author"] == "Dragon AI"


def test_bundled_skill_frontmatter_has_no_hermes_nous_teknium():
    hits: list[str] = []
    for skill in SKILLS.rglob("SKILL.md"):
        fm = _frontmatter(skill)
        blob = " ".join(str(fm.get(key, "")) for key in ("name", "description", "author"))
        if BANNED.search(blob) or HERMES_ID.search(str(fm.get("name", ""))):
            hits.append(f"{skill.relative_to(REPO)}: {blob}")
    assert not hits, "bundled skill list still shows Hermes branding:\n" + "\n".join(hits)


def test_dragon_agent_skill_body_opens_as_dragon():
    text = (SKILLS / "autonomous-ai-agents" / "dragon-agent" / "SKILL.md").read_text(encoding="utf-8")
    assert "# Dragon AI" in text
    assert "# Hermes Agent" not in text
    assert "author: Dragon AI" in text
