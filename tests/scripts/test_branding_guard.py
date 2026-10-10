"""Branding guard allows attribution and rejects user-visible Hermes naming."""
from __future__ import annotations

from scripts.dragon import branding_guard


def test_product_feed_must_stay_on_dragon():
    assert branding_guard.check_product_feed() == []


def test_readme_attribution_is_allowed():
    assert branding_guard.scan_visible() == []


def test_banned_copy_is_flagged(tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text("Welcome to Hermes Agent desktop\n", encoding="utf-8")
    monkeypatch.setattr(branding_guard, "ROOT", tmp_path)
    monkeypatch.setattr(branding_guard, "VISIBLE_SCAN", [readme])
    hits = branding_guard.scan_visible()
    assert hits
    assert "Hermes Agent" in hits[0]


def test_license_style_attribution_is_not_flagged(tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text(
        "It is a fork of the open-source [Hermes Agent](https://github.com/NousResearch/hermes-agent) framework (MIT).\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(branding_guard, "ROOT", tmp_path)
    monkeypatch.setattr(branding_guard, "VISIBLE_SCAN", [readme])
    assert branding_guard.scan_visible() == []
