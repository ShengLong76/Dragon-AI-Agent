"""Default image_gen from the active LLM provider — not from a leftover key."""

from __future__ import annotations

import pytest

from agent.image_gen_provider import ImageGenProvider
from tools import image_generation_defaults as defaults


class _FakeImage(ImageGenProvider):
    def __init__(self, name: str, available: bool = True, model: str = "img-default"):
        self._name = name
        self._available = available
        self._model = model

    @property
    def name(self):
        return self._name

    def is_available(self):
        return self._available

    def default_model(self):
        return self._model

    def generate(self, prompt, aspect_ratio="square", **kwargs):
        return {"success": True}


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    saved = []

    def _save(config, **kwargs):
        saved.append(dict(config.get("image_gen") or {}))

    monkeypatch.setattr(defaults, "_fal_already_ready", lambda: False)
    monkeypatch.setattr("hermes_cli.plugins._ensure_plugins_discovered", lambda **kwargs: None)
    return saved, _save


def test_defaults_to_the_llm_provider_image_model(monkeypatch, isolated):
    saved, save = isolated
    monkeypatch.setattr(defaults, "_image_backend", lambda name: _FakeImage("xai") if name == "xai" else None)
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {"model": {"provider": "xai"}})
    monkeypatch.setattr("hermes_cli.config.save_config", save)

    assert defaults.maybe_default_image_gen_from_llm() == "xai"
    assert saved[-1]["provider"] == "xai"
    assert saved[-1]["model"] == "img-default"


def test_skips_when_the_llm_provider_has_no_image_backend(monkeypatch, isolated):
    saved, save = isolated
    monkeypatch.setattr(defaults, "_image_backend", lambda name: None)
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {"model": {"provider": "anthropic"}})
    monkeypatch.setattr("hermes_cli.config.save_config", save)

    assert defaults.maybe_default_image_gen_from_llm() is None
    assert saved == []


def test_does_not_opt_a_leftover_key_into_a_paid_backend(monkeypatch, isolated):
    """OPENAI_API_KEY for chat is not consent to OpenAI image billing when the
    active LLM is someone else."""
    saved, save = isolated
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(
        defaults, "_image_backend",
        lambda name: _FakeImage("openai") if name == "openai" else None,
    )
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {"model": {"provider": "anthropic"}})
    monkeypatch.setattr("hermes_cli.config.save_config", save)

    assert defaults.maybe_default_image_gen_from_llm() is None
    assert saved == []


def test_leaves_an_explicit_image_provider_alone(monkeypatch, isolated):
    saved, save = isolated
    monkeypatch.setattr(defaults, "_image_backend", lambda name: _FakeImage("xai"))
    monkeypatch.setattr(
        "hermes_cli.config.load_config",
        lambda: {"model": {"provider": "xai"}, "image_gen": {"provider": "fal"}},
    )
    monkeypatch.setattr("hermes_cli.config.save_config", save)

    assert defaults.maybe_default_image_gen_from_llm() is None
    assert saved == []
