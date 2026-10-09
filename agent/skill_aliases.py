"""Canonical skill-id aliases for the Dragon AI rebrand.

Bundled skills that used to ship as ``hermes-agent``, ``hermes-agent-skill-authoring``,
and ``inspecting-hermes-desktop-dom`` now live under Dragon ids. Lookups, disable
lists, essential-skill seeding, and skills-sync relocation must treat the old ids
as the new ones so existing installs and slash commands keep working.
"""
from __future__ import annotations

# old id → new id. Keys are the only names that ever shipped; values are the
# names in skills/ after the rebrand.
SKILL_NAME_ALIASES: dict[str, str] = {
    "hermes-agent": "dragon-agent",
    "hermes-agent-skill-authoring": "dragon-agent-skill-authoring",
    "inspecting-hermes-desktop-dom": "inspecting-dragon-desktop-dom",
}

# Reverse: new id → frozenset of every name that must resolve to it.
_LEGACY_BY_CANONICAL: dict[str, frozenset[str]] = {}
for _old, _new in SKILL_NAME_ALIASES.items():
    _LEGACY_BY_CANONICAL.setdefault(_new, set()).add(_old)
_LEGACY_BY_CANONICAL = {k: frozenset(v) for k, v in _LEGACY_BY_CANONICAL.items()}


def canonical_skill_name(name: str) -> str:
    """Map a legacy skill id to the shipped name; unknown names pass through."""
    raw = (name or "").strip()
    if not raw:
        return raw
    # Bare ids only — a path like ``autonomous-ai-agents/hermes-agent`` is
    # rewritten by rewriting its last segment.
    if "/" in raw or "\\" in raw:
        sep = "/" if "/" in raw else "\\"
        parts = raw.split(sep)
        parts[-1] = SKILL_NAME_ALIASES.get(parts[-1], parts[-1])
        return sep.join(parts)
    return SKILL_NAME_ALIASES.get(raw, raw)


def skill_name_equivalents(name: str) -> frozenset[str]:
    """The canonical id plus every legacy id that must resolve to it."""
    canonical = canonical_skill_name(name)
    aliases = _LEGACY_BY_CANONICAL.get(canonical, frozenset())
    return frozenset({canonical, *(aliases or ()), (name or "").strip()} - {""})


def legacy_names_for(canonical: str) -> frozenset[str]:
    """Legacy ids that should relocate/alias onto *canonical*."""
    return _LEGACY_BY_CANONICAL.get(canonical, frozenset())
