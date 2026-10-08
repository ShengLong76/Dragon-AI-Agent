"""Single source of truth for Dragon AI's public update feed.

User-facing updates (desktop, CLI, ZIP, release links) read
``branding/product-feed.json``. ``NousResearch/hermes-agent`` is upstream for
the scheduled sync workflow only — never a product update source.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_FEED_PATH = Path(__file__).resolve().parents[1] / "branding" / "product-feed.json"
_GITHUB_ORIGIN = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def load_product_feed() -> dict:
    data = json.loads(_FEED_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("branding/product-feed.json must be an object")
    for key in ("productName", "productRepository", "upstreamRepository"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"branding/product-feed.json missing {key}")
    return data


def product_name() -> str:
    return load_product_feed()["productName"]


def product_repository() -> str:
    return load_product_feed()["productRepository"]


def upstream_repository() -> str:
    return load_product_feed()["upstreamRepository"]


def github_releases_html() -> str:
    return str(load_product_feed().get("githubReleasesHtml") or f"https://github.com/{product_repository()}/releases")


def public_assets_base() -> str | None:
    raw = load_product_feed().get("publicAssetsBase")
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def protected_paths() -> tuple[str, ...]:
    rows = load_product_feed().get("protectedPaths") or []
    return tuple(str(path) for path in rows if isinstance(path, str) and path.strip())


def product_https_url() -> str:
    return f"https://github.com/{product_repository()}.git"


def upstream_https_url() -> str:
    return f"https://github.com/{upstream_repository()}.git"


def github_repo_urls(repository: str) -> frozenset[str]:
    return frozenset({
        f"https://github.com/{repository}.git",
        f"git@github.com:{repository}.git",
        f"https://github.com/{repository}",
        f"git@github.com:{repository}",
    })


def product_repo_urls() -> frozenset[str]:
    return github_repo_urls(product_repository())


def normalize_github_url(url: str) -> str:
    url = url.rstrip("/")
    return url[:-4] if url.endswith(".git") else url


def repository_from_remote(url: str | None) -> str | None:
    if not url:
        return None
    match = _GITHUB_ORIGIN.fullmatch(url.strip())
    return match[1] if match else None


def _same_repo(value: str | None, repository: str) -> bool:
    if not value:
        return False
    parsed = repository_from_remote(value) or value.strip()
    return parsed.lower() == repository.lower()


def is_product_repository(repo_or_url: str | None) -> bool:
    return _same_repo(repo_or_url, product_repository())


def is_upstream_repository(repo_or_url: str | None) -> bool:
    """True for the Hermes/NousResearch remote. User updates must never follow it."""
    return _same_repo(repo_or_url, upstream_repository())


def update_repository(origin_repository: str | None = None) -> str:
    """GitHub owner/repo a user update may follow.

    Hermes remotes and missing origins resolve to Dragon. Other GitHub forks
    keep their own origin so a personal fork still owns its releases.
    """
    if origin_repository is None or is_upstream_repository(origin_repository):
        return product_repository()
    return origin_repository


def fetch_remote_for_origin(origin_url: str | None) -> str:
    """git-fetch remote for a user update: Dragon HTTPS when origin is Hermes."""
    if is_upstream_repository(origin_url):
        return product_https_url()
    return "origin"


def should_skip_upstream_remote(url: str | None) -> bool:
    """Ignore a checkout's ``upstream`` remote when it points at Hermes."""
    return is_upstream_repository(url)
