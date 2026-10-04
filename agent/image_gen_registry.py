"""Image generation provider registry.

Populated by plugins at import-time via ``PluginContext.register_image_gen_provider()``;
the ``image_generate`` tool dispatches to :func:`get_active_provider`. Selection is
``image_gen.provider`` in config.yaml; when unset: the single *available* provider,
else ``fal`` if registered and available (legacy default), else ``None`` (the tool
points the user at ``hermes tools``).
"""

from __future__ import annotations

import logging
from typing import Optional

from agent.image_gen_provider import ImageGenProvider
from agent.provider_registry import ProviderRegistry, configured_provider_name, is_available_safe

logger = logging.getLogger(__name__)


_registry: ProviderRegistry[ImageGenProvider] = ProviderRegistry(
    label="Image gen", provider_cls=ImageGenProvider, logger=logger,
)
_registry.export(globals())

# Auth-variant suffixes on an LLM/provider slug (``<id>-oauth``) that should
# still find the image plugin registered under the stem. Generic — no vendor
# key names live here.
_AUTH_VARIANT_SUFFIXES = ("-oauth", "-api")


def _identity_keys(provider: ImageGenProvider) -> set[str]:
    """Lowercased names a stored selection might use for *provider*."""
    keys: set[str] = set()
    for raw in (
        getattr(provider, "name", None),
        getattr(provider, "display_name", None),
        getattr(provider, "label", None),
        getattr(provider, "provider_id", None),
    ):
        if isinstance(raw, str) and raw.strip():
            keys.add(raw.strip().lower())
    try:
        schema = provider.get_setup_schema() or {}
    except Exception:
        schema = {}
    name = schema.get("name") if isinstance(schema, dict) else None
    if isinstance(name, str) and name.strip():
        keys.add(name.strip().lower())
    return keys


def _lookup_names(raw: str) -> list[str]:
    """Candidate strings for a stored provider identity, without assuming a vendor key."""
    needle = raw.strip().lower()
    if not needle:
        return []
    names = [needle]
    try:
        from hermes_cli.providers import ALIASES, normalize_provider

        canon = normalize_provider(needle)
        if canon and canon not in names:
            names.append(canon)
        for alias, target in ALIASES.items():
            if target in (needle, canon) and alias not in names:
                names.append(alias)
    except Exception:
        pass
    for suffix in _AUTH_VARIANT_SUFFIXES:
        if needle.endswith(suffix) and len(needle) > len(suffix):
            stem = needle[: -len(suffix)]
            if stem and stem not in names:
                names.append(stem)
            try:
                from hermes_cli.providers import normalize_provider

                stem_canon = normalize_provider(stem)
                if stem_canon and stem_canon not in names:
                    names.append(stem_canon)
            except Exception:
                pass
    return names


def resolve_provider(name: str, *, scope: Optional[str] = None) -> Optional[ImageGenProvider]:
    """Find a registered image provider by config/display/alias identity.

    Exact registry key first, then aliases and picker labels. Does not assume
    any vendor's key name — a selected backend stored as its display name or
    an LLM alias must still resolve.
    """
    if not isinstance(name, str) or not name.strip():
        return None
    snapshot = _registry.merged(scope)
    exact = snapshot.get(_registry.normalize(name))
    if exact is not None:
        return exact
    lowered = {key.lower(): provider for key, provider in snapshot.items()}
    folded = lowered.get(name.strip().lower())
    if folded is not None:
        return folded
    for candidate in _lookup_names(name):
        hit = snapshot.get(_registry.normalize(candidate)) or lowered.get(candidate.lower())
        if hit is not None:
            return hit
    needles = set(_lookup_names(name))
    for provider in snapshot.values():
        if _identity_keys(provider) & needles:
            return provider
    return None


def resolve_provider_for_model(model_id: str, *, scope: Optional[str] = None) -> Optional[ImageGenProvider]:
    """Registered provider whose catalog contains *model_id*, or None."""
    if not isinstance(model_id, str) or not model_id.strip():
        return None
    wanted = model_id.strip()
    for provider in _registry.merged(scope).values():
        try:
            models = provider.list_models() or []
        except Exception:
            continue
        for row in models:
            if isinstance(row, dict) and row.get("id") == wanted:
                return provider
    return None


def get_active_provider() -> Optional[ImageGenProvider]:
    """Resolve the currently-active provider. Availability semantics (mirrors
    :mod:`agent.web_search_registry`): an explicitly configured provider is returned
    even if ``is_available()`` is False, so the dispatcher surfaces a precise
    "X_API_KEY is not set" error instead of silently switching backends; only the
    unconfigured fallback path is filtered by availability."""
    configured = configured_provider_name("image_gen", logger)
    snapshot = _registry.merged()
    if configured:
        resolved = resolve_provider(configured)
        if resolved is not None:
            return resolved
        logger.debug("image_gen.provider='%s' configured but not registered; falling back", configured)

    def _available(p: ImageGenProvider) -> bool:
        return is_available_safe(p, logger, "image_gen provider %s.is_available() raised %s")

    available = [p for p in snapshot.values() if _available(p)]
    if len(available) == 1:
        return available[0]
    fal = snapshot.get("fal")
    return fal if fal is not None and _available(fal) else None
