"""Generated icons must derive from Dragon artwork, never Nous/Hermes assets."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
BANNED = ("nous-girl", "nous-logo", "hermes.png", "hermes-sprite", "hermes-frame")


def load_generator(monkeypatch):
    monkeypatch.setitem(sys.modules, "resvg_py", ModuleType("resvg_py"))
    spec = importlib.util.spec_from_file_location("generate_icons", ROOT / "scripts/generate_icons.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repo_has_no_nous_or_hermes_icon_sources():
    hits = []
    for path in (
        *ROOT.joinpath("assets").rglob("*"),
        *ROOT.joinpath("branding").rglob("*"),
        *ROOT.joinpath("apps/desktop/public").rglob("*"),
        *ROOT.joinpath("apps/bootstrap-installer/public").rglob("*"),
    ):
        if path.is_file() and any(token in path.name.lower() for token in BANNED):
            hits.append(path.relative_to(ROOT).as_posix())
    assert hits == []


def test_generator_targets_and_sources_are_dragon(monkeypatch):
    module = load_generator(monkeypatch)
    for rel, _kind, _arg in module.TARGETS:
        assert not any(token in rel.lower() for token in BANNED), rel
    art = module.resolve_dragon_art(ROOT)
    assert art.name == "dragon-logo.png"
    assert "nous" not in art.as_posix().lower()
    assert "hermes" not in art.name.lower()
    with pytest.raises(ValueError, match="Hermes/Nous"):
        module.refuse_banned_icon_source(Path("assets/nous-girl-black.svg"))
    with pytest.raises(ValueError, match="Hermes/Nous"):
        module.refuse_banned_icon_source(Path("apps/desktop/public/hermes.png"))


def test_icon_art_refuses_a_tree_that_only_has_nous_girl(tmp_path, monkeypatch):
    module = load_generator(monkeypatch)
    source = tmp_path / "only-nous"
    assets = source / "assets"
    assets.mkdir(parents=True)
    (assets / "nous-girl-black.svg").write_text("<svg/>", encoding="utf-8")
    (assets / "nous-girl-white.svg").write_text("<svg/>", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="Dragon artwork"):
        module.resolve_dragon_art(source)
    with pytest.raises(FileNotFoundError, match="Dragon artwork"):
        module.IconArt(source)
