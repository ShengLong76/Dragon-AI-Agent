"""Default ``image_gen`` from the active LLM provider.

If the chat provider also ships an image-generation backend, setup (and the
avatar Generate probe) should pick that backend's default model instead of
leaving image gen unconfigured. A leftover API key for some other vendor is
not consent — only ``model.provider`` is considered.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Chat slugs that share an image plugin under a neighboring id.
_LLM_IMAGE_GEN_ALIASES = {
    "openai-codex": ("openai-codex", "openai"),
}


def _active_llm_provider(config: Dict[str, Any]) -> str:
    model = config.get("model") if isinstance(config, dict) else None
    if not isinstance(model, dict):
        return ""
    provider = str(model.get("provider") or "").strip().lower()
    return "" if provider in {"", "auto"} else provider


def _candidate_image_backends(llm_provider: str) -> tuple[str, ...]:
    return _LLM_IMAGE_GEN_ALIASES.get(llm_provider, (llm_provider,))


def _fal_already_ready() -> bool:
    try:
        from tools.image_generation_tool import check_fal_api_key
        return bool(check_fal_api_key())
    except Exception:
        return False


def _image_backend(name: str):
    from hermes_cli.plugins import _ensure_plugins_discovered
    from agent.image_gen_registry import resolve_provider

    _ensure_plugins_discovered()
    provider = resolve_provider(name)
    if provider is None:
        return None
    try:
        if not provider.is_available():
            return None
    except Exception:
        return None
    return provider


def maybe_default_image_gen_from_llm(config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Persist ``image_gen.provider`` (+ default model) from the active LLM.

    Returns the image-gen plugin name when a default was written, else None.
    No-ops when image gen is already chosen, FAL is already serving, or the
    LLM provider has no available image backend.
    """
    from hermes_cli.config import load_config, save_config

    cfg = config if config is not None else load_config()
    if not isinstance(cfg, dict):
        return None

    image_cfg = cfg.get("image_gen")
    if isinstance(image_cfg, dict) and str(image_cfg.get("provider") or "").strip():
        return None
    if _fal_already_ready():
        return None

    llm = _active_llm_provider(cfg)
    if not llm:
        return None

    provider = None
    for name in _candidate_image_backends(llm):
        provider = _image_backend(name)
        if provider is not None:
            break
    if provider is None:
        return None

    section = image_cfg if isinstance(image_cfg, dict) else {}
    cfg["image_gen"] = section
    section["provider"] = provider.name
    default_model = provider.default_model()
    if default_model:
        section["model"] = default_model
    save_config(cfg)
    logger.info("Defaulted image_gen.provider to %s from model.provider=%s", provider.name, llm)
    return provider.name
