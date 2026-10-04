from __future__ import annotations

import json

import pytest

from agent import image_gen_registry


@pytest.fixture(autouse=True)
def _reset_registry():
    image_gen_registry._reset_for_tests()
    yield
    image_gen_registry._reset_for_tests()


class TestPluginDispatch:


    def test_handler_forwards_only_the_creative_controls_the_plugin_declares(self, monkeypatch, tmp_path):
        """Declared controls reach generate(); an undeclared one the model sent anyway is dropped, so a
        plugin whose generate() lacks **kwargs never sees it."""
        from agent.image_gen_provider import ImageGenProvider
        from hermes_cli import plugins as plugins_module
        from tools import image_generation_tool

        seen = {}

        class _Recorder(ImageGenProvider):
            @property
            def name(self):
                return "recorder"

            def capabilities(self):
                return {"modalities": ["text"], "creative_controls": ["intensity"]}

            def generate(self, prompt, aspect_ratio="landscape", **kwargs):
                seen.update(kwargs)
                return {"success": True, "image": "/tmp/recorder.png", "model": "m", "prompt": prompt,
                        "aspect_ratio": aspect_ratio, "provider": "recorder"}

            def list_models(self):
                return []

        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        image_gen_registry.register_provider(_Recorder())
        monkeypatch.setattr(image_generation_tool, "_read_configured_image_provider", lambda: "recorder")
        monkeypatch.setattr(plugins_module, "_ensure_plugins_discovered", lambda **kwargs: None)

        result = json.loads(image_generation_tool._handle_image_generate(
            {"prompt": "draw cat", "aspect_ratio": "square", "intensity": 80, "creativity": "raw"}))

        assert result["success"] is True
        assert seen["intensity"] == 80
        assert "creativity" not in seen

    def test_deepinfra_key_alone_does_not_select_image_backend(self, monkeypatch):
        """DeepInfra chat credentials do not imply consent to image billing."""
        from tools import image_generation_tool

        monkeypatch.setenv("DEEPINFRA_API_KEY", "«redacted:sk-…»")
        monkeypatch.delenv("FAL_KEY", raising=False)
        monkeypatch.setattr(image_generation_tool, "_read_configured_image_provider", lambda: None)
        assert image_generation_tool._dispatch_to_plugin_provider("a cat", "square") is None

    def test_requirements_ignore_unselected_paid_plugin(self, monkeypatch):
        from tools import image_generation_tool

        monkeypatch.setattr(image_generation_tool, "check_fal_api_key", lambda: False)
        monkeypatch.setattr(
            image_generation_tool, "_read_configured_image_provider", lambda: None
        )
        monkeypatch.setattr(
            image_generation_tool, "_read_configured_image_model", lambda: None
        )
        assert image_generation_tool.check_image_generation_requirements() is False

    def test_selected_backend_is_ready_even_when_is_available_is_false(self, monkeypatch):
        """Generate must use an already-selected backend; is_available() is not
        the probe. A selected plugin whose credentials check fails is still
        selected — the empty-state picker is only for no selection."""
        from agent.image_gen_provider import ImageGenProvider
        from tools import image_generation_tool

        class _Selected(ImageGenProvider):
            @property
            def name(self):
                return "selected-img"

            def is_available(self):
                return False

            def generate(self, prompt, aspect_ratio="square", **kwargs):
                return {"success": True}

        image_gen_registry.register_provider(_Selected())
        monkeypatch.setattr(image_generation_tool, "check_fal_api_key", lambda: False)
        monkeypatch.setattr(
            image_generation_tool, "_read_configured_image_provider", lambda: "selected-img"
        )
        monkeypatch.setattr(
            image_generation_tool, "_read_configured_image_model", lambda: None
        )
        assert image_generation_tool.check_image_generation_requirements() is True

    def test_selected_backend_resolves_by_identity_not_registry_key(self, monkeypatch):
        """The stored selection is whatever the picker wrote (display name,
        schema title, alias) — not necessarily the plugin's registry key.
        Generate must still dispatch to that backend."""
        from agent.image_gen_provider import ImageGenProvider
        from hermes_cli import plugins as plugins_module
        from tools import image_generation_tool

        seen = {}

        class _Labeled(ImageGenProvider):
            @property
            def name(self):
                return "labeled-img"

            def get_setup_schema(self):
                return {"name": "Labeled Imagine (image)", "badge": "paid",
                        "tag": "", "env_vars": []}

            def is_available(self):
                return False

            def list_models(self):
                return [{"id": "labeled-imagine-1", "display": "Labeled Imagine"}]

            def generate(self, prompt, aspect_ratio="square", **kwargs):
                seen["prompt"] = prompt
                seen["provider"] = self.name
                return {"success": True, "image": "/tmp/labeled.png", "model": "labeled-imagine-1",
                        "prompt": prompt, "aspect_ratio": aspect_ratio, "provider": self.name}

        image_gen_registry.register_provider(_Labeled())
        monkeypatch.setattr(plugins_module, "_ensure_plugins_discovered", lambda **kwargs: None)
        monkeypatch.setattr(image_generation_tool, "check_fal_api_key", lambda: False)
        monkeypatch.setattr(
            image_generation_tool, "_read_configured_image_provider",
            lambda: "Labeled Imagine (image)",
        )
        monkeypatch.setattr(
            image_generation_tool, "_read_configured_image_model", lambda: "labeled-imagine-1"
        )

        assert image_generation_tool.check_image_generation_requirements() is True
        result = json.loads(image_generation_tool._handle_image_generate(
            {"prompt": "draw a face", "aspect_ratio": "square"}))
        assert result["success"] is True
        assert seen["provider"] == "labeled-img"
