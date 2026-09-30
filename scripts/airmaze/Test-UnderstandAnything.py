#!/usr/bin/env python3
"""Presence checks for the vendored Understand-Anything skill/plugin.

No network. Does not run /understand (first scan is token-heavy).
Safe on Linux CI or a Windows checkout.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
GITIGNORE = ROOT / ".gitignore"
PLUGIN = ROOT / ".cursor-plugin" / "plugin.json"
SKILLS_README = ROOT / ".cursor" / "skills" / "README.md"
SKILL_ROOT = ROOT / ".cursor" / "skills" / "understand-anything"
SKILL_POINTER = SKILL_ROOT / "SKILL.md"
SKILL_UNDERSTAND = SKILL_ROOT / "understand" / "SKILL.md"
SKILL_DASHBOARD = SKILL_ROOT / "understand-dashboard" / "SKILL.md"
SKILL_LICENSE = SKILL_ROOT / "LICENSE"
DOC = ROOT / "docs" / "airmaze" / "UNDERSTAND_ANYTHING.md"
NOTICES = ROOT / "THIRD_PARTY_NOTICES.md"
REPO_LICENSE = ROOT / "LICENSE"

REQUIRED_FILES = (
    GITIGNORE,
    PLUGIN,
    SKILLS_README,
    SKILL_POINTER,
    SKILL_UNDERSTAND,
    SKILL_DASHBOARD,
    SKILL_LICENSE,
    DOC,
    NOTICES,
)

GRAPH_FORBIDDEN = (
    ROOT / ".ua" / "knowledge-graph.json",
    ROOT / ".understand-anything" / "knowledge-graph.json",
)

PAID_EXTRAS = ("banner-design", "logo-design", "brand-pack")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require_tokens(path: pathlib.Path, tokens: tuple[str, ...], label: str) -> None:
    text = read(path)
    for token in tokens:
        if token not in text:
            fail(f"{path.relative_to(ROOT)} missing {label} token: {token}")
    print(f"OK  {label}: {path.relative_to(ROOT)}")


def check_files() -> None:
    for path in REQUIRED_FILES:
        if not path.is_file():
            fail(f"missing {path.relative_to(ROOT)}")
        print(f"OK  present: {path.relative_to(ROOT)}")


def check_gitignore() -> None:
    text = read(GITIGNORE)
    for token in (".ua/", ".understand-anything/"):
        if token not in text:
            fail(f".gitignore must ignore {token}")
    print("OK  gitignore covers .ua/ and .understand-anything/")


def check_plugin() -> None:
    data = json.loads(read(PLUGIN))
    if data.get("name") != "understand-anything":
        fail("plugin.json name must be understand-anything")
    if data.get("license") != "MIT":
        fail("plugin.json license must be MIT")
    repo = str(data.get("repository") or data.get("homepage") or "")
    if "github.com/Egonex-AI/Understand-Anything" not in repo:
        fail("plugin.json must point at Egonex-AI/Understand-Anything")
    skills = str(data.get("skills") or "")
    if "understand-anything" not in skills:
        fail("plugin.json skills path must include understand-anything")
    print("OK  plugin.json")


def check_skills() -> None:
    require_tokens(
        SKILL_POINTER,
        (
            "name: understand-anything",
            "disable-model-invocation: true",
            "/understand",
            "/understand-dashboard",
            "Do not run a first scan",
            "https://github.com/Egonex-AI/Understand-Anything",
            ".ua/",
        ),
        "pointer-skill",
    )
    require_tokens(
        SKILL_UNDERSTAND,
        (
            "name: understand",
            "disable-model-invocation: true",
            ".ua/",
            "Do not",
            "token-heavy",
        ),
        "understand-skill",
    )
    require_tokens(
        SKILL_DASHBOARD,
        (
            "name: understand-dashboard",
            "disable-model-invocation: true",
            "knowledge-graph.json",
            "/understand",
        ),
        "dashboard-skill",
    )
    require_tokens(SKILL_LICENSE, ("MIT License", "Yuxiang Lin", "Infinite Universe"), "skill-license")
    require_tokens(SKILLS_README, ("understand-anything", "/understand", ".ua/"), "skills-readme")
    require_tokens(
        DOC,
        (
            "/understand",
            "/understand-dashboard",
            ".ua/",
            "https://github.com/Egonex-AI/Understand-Anything",
            "token-heavy",
        ),
        "doc",
    )
    require_tokens(
        NOTICES,
        ("Understand-Anything", "https://github.com/Egonex-AI/Understand-Anything", "MIT"),
        "notices",
    )
    license_text = read(REPO_LICENSE)
    if "MIT License" not in license_text:
        fail("repo LICENSE must stay MIT")
    print("OK  repo LICENSE is MIT")


def check_no_graph() -> None:
    for path in GRAPH_FORBIDDEN:
        if path.is_file():
            fail(f"generated knowledge graph must not be committed: {path.relative_to(ROOT)}")
    print("OK  no generated knowledge-graph.json")


def check_no_paid_extras() -> None:
    skills = ROOT / ".cursor" / "skills"
    if not skills.is_dir():
        fail("missing .cursor/skills")
    found = []
    for extra in PAID_EXTRAS:
        if any(skills.rglob(extra)):
            found.append(extra)
    if found:
        fail(f"do not vendor paid extras: {', '.join(found)}")
    print("OK  no paid extras under .cursor/skills")


def main() -> int:
    check_files()
    check_gitignore()
    check_plugin()
    check_skills()
    check_no_graph()
    check_no_paid_extras()
    print("SMOKE OK: Understand-Anything skill/plugin files and gitignore are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
