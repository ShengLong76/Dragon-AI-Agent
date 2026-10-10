"""Dragon-named sandbox image + container ids, with Hermes fallback.

The Computer pane and docker terminal backend used to start ``hermes-<id>``
containers from ``nousresearch/hermes-sandbox:desktop``. Dragon AI ships a
local ``dragon-sandbox:desktop`` tag. If that tag is missing (first run, no
GHCR publish yet), we pull the published GHCR image or the upstream desktop
image and retag it locally so the pane keeps working.

Never ``docker pull dragon-sandbox:desktop``: that name is a local-only tag
with no Docker Hub repo, and Hub answers ``pull access denied``. Check local
existence first, then GHCR, then upstream + ``docker tag``.
"""
from __future__ import annotations

import logging
import uuid
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

CONTAINER_NAME_PREFIX = "dragon-"
LEGACY_CONTAINER_NAME_PREFIX = "hermes-"

# What we *name* the image after ensure_sandbox_image. Local tag, no registry.
DEFAULT_SANDBOX_IMAGE = "dragon-sandbox:desktop"
# Prefer our GHCR publish when it exists; upstream is the compatibility pull.
PUBLISHED_SANDBOX_IMAGE = "ghcr.io/shenglong76/dragon-sandbox:desktop"
UPSTREAM_SANDBOX_IMAGE = "nousresearch/hermes-sandbox:desktop"

SANDBOX_IMAGE_ALIASES = frozenset({
    DEFAULT_SANDBOX_IMAGE,
    PUBLISHED_SANDBOX_IMAGE,
    UPSTREAM_SANDBOX_IMAGE,
})

# Docker Hub / GHCR wording that means "this ref is not ours" — fall through.
_PULL_FALLTHROUGH_MARKERS = (
    "pull access denied",
    "access denied",
    "not found",
    "repository does not exist",
    "manifest unknown",
    "unauthorized",
    "requested access to the resource is denied",
)


def new_container_name() -> str:
    return f"{CONTAINER_NAME_PREFIX}{uuid.uuid4().hex[:8]}"


def is_managed_container_name(name: str) -> bool:
    """True for Dragon or leftover Hermes sandbox names."""
    return bool(name) and (
        name.startswith(CONTAINER_NAME_PREFIX) or name.startswith(LEGACY_CONTAINER_NAME_PREFIX)
    )


def is_registry_ref(image: str) -> bool:
    """True when *image* names a registry path (``ghcr.io/...`` / ``org/name``).

    Bare tags such as ``dragon-sandbox:desktop`` have no registry; pulling them
    hits Docker Hub as library/dragon-sandbox and gets access-denied.
    """
    return "/" in (image or "")


def images_are_equivalent(left: str, right: str) -> bool:
    """A retagged upstream desktop image is the same sandbox as the Dragon tag."""
    return left == right or (left in SANDBOX_IMAGE_ALIASES and right in SANDBOX_IMAGE_ALIASES)


def fingerprint_alias_images(image: str) -> tuple[str, ...]:
    """Images that share a reuse identity with *image*.

    New containers hash ``dragon-sandbox:desktop``. Leftover
    ``hermes-sandbox:desktop`` containers still match when we also try the
    alias hashes.
    """
    if image in SANDBOX_IMAGE_ALIASES:
        return (DEFAULT_SANDBOX_IMAGE, PUBLISHED_SANDBOX_IMAGE, UPSTREAM_SANDBOX_IMAGE)
    return (image,)


def _result_text(result) -> str:
    if result is None:
        return ""
    if isinstance(result, BaseException):
        return str(result)
    parts = [getattr(result, "stderr", ""), getattr(result, "stdout", ""), str(result)]
    return " ".join(str(part or "") for part in parts)


def is_pull_fallthrough(result) -> bool:
    """True when a failed pull is a missing/denied image, not a Docker crash."""
    text = _result_text(result).lower()
    return any(marker in text for marker in _PULL_FALLTHROUGH_MARKERS)


def _inspect_image(run_capture, docker_exe: str, image: str) -> bool:
    try:
        probe = run_capture(
            [docker_exe, "image", "inspect", image, "--format", "{{.Id}}"], timeout=30)
        return probe.returncode == 0
    except (OSError, Exception):
        return False


def _pull_image(run_capture, docker_exe: str, image: str) -> bool:
    if not is_registry_ref(image):
        logger.info("Docker: not pulling local-only tag %s (no registry)", image)
        return False
    try:
        pull = run_capture([docker_exe, "pull", image], timeout=900)
        if pull.returncode == 0:
            return True
        if is_pull_fallthrough(pull):
            logger.info("Docker: %s not pullable (%s); falling through", image, (pull.stderr or "").strip())
        else:
            logger.warning("Docker: could not pull %s: %s", image, (pull.stderr or pull.stdout or "").strip())
        return False
    except (OSError, Exception) as exc:
        if is_pull_fallthrough(exc):
            logger.info("Docker: %s not pullable (%s); falling through", image, exc)
        else:
            logger.warning("Docker: could not pull %s: %s", image, exc)
        return False


def _retag(run_capture, docker_exe: str, source: str, dest: str) -> bool:
    try:
        tagged = run_capture([docker_exe, "tag", source, dest], timeout=30)
        return tagged.returncode == 0
    except (OSError, Exception) as exc:
        logger.warning("Docker: could not tag %s as %s: %s", source, dest, exc)
        return False


def ensure_sandbox_image(
    docker_exe: str,
    desired: str = DEFAULT_SANDBOX_IMAGE,
    *,
    run_capture,
    pull_candidates: Optional[Iterable[str]] = None,
) -> str:
    """Return a locally-available image name for *desired*.

    Order: ``docker image inspect`` *desired* → (registry refs only) pull
    *desired* → inspect/pull each published/upstream candidate and ``docker tag``
    as *desired*. Local-only tags are never pulled. ``pull access denied`` and
    ``not found`` fall through to the next candidate. Raises RuntimeError only
    when nothing can be made local; callers that must keep an existing
    container should catch that.
    """
    if _inspect_image(run_capture, docker_exe, desired):
        return desired
    if is_registry_ref(desired) and _pull_image(run_capture, docker_exe, desired) and _inspect_image(
        run_capture, docker_exe, desired
    ):
        return desired
    candidates = list(pull_candidates or (PUBLISHED_SANDBOX_IMAGE, UPSTREAM_SANDBOX_IMAGE))
    for candidate in candidates:
        if candidate == desired:
            continue
        available = _inspect_image(run_capture, docker_exe, candidate)
        if not available:
            available = _pull_image(run_capture, docker_exe, candidate) and _inspect_image(
                run_capture, docker_exe, candidate)
        if not available:
            continue
        if _retag(run_capture, docker_exe, candidate, desired):
            logger.info("Docker: tagged %s as %s (sandbox fallback)", candidate, desired)
            return desired
    raise RuntimeError(f"sandbox image {desired} is not available locally and fallback pull failed")
