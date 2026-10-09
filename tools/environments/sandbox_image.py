"""Dragon-named sandbox image + container ids, with Hermes fallback.

The Computer pane and docker terminal backend used to start ``hermes-<id>``
containers from ``nousresearch/hermes-sandbox:desktop``. Dragon AI ships a
local ``dragon-sandbox:desktop`` tag. If that tag is missing (first run, no
GHCR publish yet), we pull the upstream desktop image and retag it locally so
the pane keeps working.

Existing ``hermes-*`` containers stay reusable: they still carry
``hermes-agent=1`` labels, and new containers keep that label plus
``dragon-agent=1``.
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


def new_container_name() -> str:
    return f"{CONTAINER_NAME_PREFIX}{uuid.uuid4().hex[:8]}"


def is_managed_container_name(name: str) -> bool:
    """True for Dragon or leftover Hermes sandbox names."""
    return bool(name) and (
        name.startswith(CONTAINER_NAME_PREFIX) or name.startswith(LEGACY_CONTAINER_NAME_PREFIX)
    )


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


def _inspect_image(run_capture, docker_exe: str, image: str) -> bool:
    try:
        probe = run_capture(
            [docker_exe, "image", "inspect", image, "--format", "{{.Id}}"], timeout=30)
        return probe.returncode == 0
    except (OSError, Exception):
        return False


def _pull_image(run_capture, docker_exe: str, image: str) -> bool:
    try:
        pull = run_capture([docker_exe, "pull", image], timeout=900)
        return pull.returncode == 0
    except (OSError, Exception) as exc:
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

    Order: already local → pull *desired* → pull published/upstream and retag
    as *desired*. Raises RuntimeError only when nothing can be pulled; callers
    that must keep an existing container should catch that.
    """
    if _inspect_image(run_capture, docker_exe, desired):
        return desired
    # Local-only tags (``dragon-sandbox:desktop``) have no registry; pulling
    # them is a guaranteed miss. Registry refs (ghcr / Docker Hub) are pulled.
    if "/" in desired and _pull_image(run_capture, docker_exe, desired) and _inspect_image(
        run_capture, docker_exe, desired
    ):
        return desired
    candidates = list(pull_candidates or (PUBLISHED_SANDBOX_IMAGE, UPSTREAM_SANDBOX_IMAGE))
    for candidate in candidates:
        if candidate == desired:
            continue
        available = _inspect_image(run_capture, docker_exe, candidate) or _pull_image(
            run_capture, docker_exe, candidate)
        if not available:
            continue
        if _retag(run_capture, docker_exe, candidate, desired):
            logger.info("Docker: tagged %s as %s (sandbox fallback)", candidate, desired)
            return desired
    raise RuntimeError(f"sandbox image {desired} is not available locally and fallback pull failed")
