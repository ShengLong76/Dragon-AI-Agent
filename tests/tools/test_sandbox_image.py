"""Dragon sandbox image fallback and container naming."""
from __future__ import annotations

import subprocess

import pytest

from tools.environments.sandbox_image import (
    CONTAINER_NAME_PREFIX,
    DEFAULT_SANDBOX_IMAGE,
    LEGACY_CONTAINER_NAME_PREFIX,
    PUBLISHED_SANDBOX_IMAGE,
    UPSTREAM_SANDBOX_IMAGE,
    ensure_sandbox_image,
    fingerprint_alias_images,
    images_are_equivalent,
    is_managed_container_name,
    new_container_name,
)


class _FakeDocker:
    def __init__(self, local=(), pull_ok=(), tag_ok=True):
        self.local = set(local)
        self.pull_ok = set(pull_ok)
        self.tag_ok = tag_ok
        self.calls: list[list[str]] = []

    def __call__(self, cmd, timeout=None, check=False, **_kwargs):
        self.calls.append(list(cmd))
        sub = cmd[1] if len(cmd) > 1 else ""
        if sub == "image" and cmd[2] == "inspect":
            image = cmd[3]
            if image in self.local:
                return subprocess.CompletedProcess(cmd, 0, stdout="sha256:abc\n", stderr="")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="missing")
        if sub == "pull":
            image = cmd[2]
            if image in self.pull_ok:
                self.local.add(image)
                return subprocess.CompletedProcess(cmd, 0, stdout="pulled\n", stderr="")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="denied")
        if sub == "tag":
            if not self.tag_ok:
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="tag failed")
            self.local.add(cmd[3])
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")


def test_new_container_name_uses_dragon_prefix():
    name = new_container_name()
    assert name.startswith(CONTAINER_NAME_PREFIX)
    assert not name.startswith(LEGACY_CONTAINER_NAME_PREFIX)
    assert is_managed_container_name(name)
    assert is_managed_container_name("hermes-02e09f8d")


def test_images_are_equivalent_across_retag():
    assert images_are_equivalent(DEFAULT_SANDBOX_IMAGE, UPSTREAM_SANDBOX_IMAGE)
    assert images_are_equivalent(DEFAULT_SANDBOX_IMAGE, PUBLISHED_SANDBOX_IMAGE)
    assert not images_are_equivalent(DEFAULT_SANDBOX_IMAGE, "nikolaik/python-nodejs:python3.11-nodejs20")
    assert fingerprint_alias_images(DEFAULT_SANDBOX_IMAGE) == (
        DEFAULT_SANDBOX_IMAGE, PUBLISHED_SANDBOX_IMAGE, UPSTREAM_SANDBOX_IMAGE)
    assert fingerprint_alias_images("custom:1") == ("custom:1",)


def test_ensure_uses_local_dragon_tag_without_pull():
    docker = _FakeDocker(local={DEFAULT_SANDBOX_IMAGE})
    assert ensure_sandbox_image("docker", run_capture=docker) == DEFAULT_SANDBOX_IMAGE
    assert not any(cmd[1] == "pull" for cmd in docker.calls)


def test_ensure_pulls_upstream_and_retags_when_dragon_missing():
    docker = _FakeDocker(local=(), pull_ok={UPSTREAM_SANDBOX_IMAGE})
    assert ensure_sandbox_image("docker", run_capture=docker) == DEFAULT_SANDBOX_IMAGE
    pulls = [cmd[2] for cmd in docker.calls if cmd[1] == "pull"]
    assert UPSTREAM_SANDBOX_IMAGE in pulls
    tags = [cmd for cmd in docker.calls if cmd[1] == "tag"]
    assert any(cmd[2] == UPSTREAM_SANDBOX_IMAGE and cmd[3] == DEFAULT_SANDBOX_IMAGE for cmd in tags)
    assert DEFAULT_SANDBOX_IMAGE in docker.local


def test_ensure_prefers_published_ghcr_over_upstream():
    docker = _FakeDocker(local=(), pull_ok={PUBLISHED_SANDBOX_IMAGE, UPSTREAM_SANDBOX_IMAGE})
    assert ensure_sandbox_image("docker", run_capture=docker) == DEFAULT_SANDBOX_IMAGE
    pulls = [cmd[2] for cmd in docker.calls if cmd[1] == "pull"]
    assert pulls[0] == PUBLISHED_SANDBOX_IMAGE
    assert UPSTREAM_SANDBOX_IMAGE not in pulls


def test_ensure_raises_when_nothing_can_be_pulled():
    docker = _FakeDocker(local=(), pull_ok=())
    with pytest.raises(RuntimeError, match="fallback pull failed"):
        ensure_sandbox_image("docker", run_capture=docker)
