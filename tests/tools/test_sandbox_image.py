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
    is_pull_fallthrough,
    is_registry_ref,
    new_container_name,
)


class _FakeDocker:
    def __init__(self, local=(), pull_ok=(), pull_stderr=None, tag_ok=True, raise_on_pull=None):
        self.local = set(local)
        self.pull_ok = set(pull_ok)
        self.pull_stderr = dict(pull_stderr or {})
        self.tag_ok = tag_ok
        self.raise_on_pull = dict(raise_on_pull or {})
        self.calls: list[list[str]] = []

    def __call__(self, cmd, timeout=None, check=False, **_kwargs):
        self.calls.append(list(cmd))
        sub = cmd[1] if len(cmd) > 1 else ""
        if sub == "image" and cmd[2] == "inspect":
            image = cmd[3]
            if image in self.local:
                return subprocess.CompletedProcess(cmd, 0, stdout="sha256:abc\n", stderr="")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Error: No such image")
        if sub == "pull":
            image = cmd[2]
            if image in self.raise_on_pull:
                raise RuntimeError(self.raise_on_pull[image])
            if image in self.pull_ok:
                self.local.add(image)
                return subprocess.CompletedProcess(cmd, 0, stdout="pulled\n", stderr="")
            stderr = self.pull_stderr.get(image, "denied")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr=stderr)
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


def test_local_only_tag_is_not_a_registry_ref():
    assert is_registry_ref(DEFAULT_SANDBOX_IMAGE) is False
    assert is_registry_ref(PUBLISHED_SANDBOX_IMAGE) is True
    assert is_registry_ref(UPSTREAM_SANDBOX_IMAGE) is True


def test_pull_fallthrough_recognizes_denied_and_missing():
    denied = subprocess.CompletedProcess(["docker", "pull", "x"], 1, stdout="", stderr="Error: pull access denied for dragon-sandbox")
    missing = subprocess.CompletedProcess(["docker", "pull", "x"], 1, stdout="", stderr="Error: not found")
    other = subprocess.CompletedProcess(["docker", "pull", "x"], 1, stdout="", stderr="TLS handshake timeout")
    assert is_pull_fallthrough(denied)
    assert is_pull_fallthrough(missing)
    assert is_pull_fallthrough(RuntimeError("pull access denied for ghcr.io/shenglong76/dragon-sandbox"))
    assert not is_pull_fallthrough(other)


def test_ensure_uses_local_dragon_tag_without_pull():
    docker = _FakeDocker(local={DEFAULT_SANDBOX_IMAGE})
    assert ensure_sandbox_image("docker", run_capture=docker) == DEFAULT_SANDBOX_IMAGE
    assert not any(cmd[1] == "pull" for cmd in docker.calls)


def test_ensure_never_pulls_bare_local_tag():
    docker = _FakeDocker(local=(), pull_ok={UPSTREAM_SANDBOX_IMAGE})
    assert ensure_sandbox_image("docker", run_capture=docker) == DEFAULT_SANDBOX_IMAGE
    pulls = [cmd[2] for cmd in docker.calls if cmd[1] == "pull"]
    assert DEFAULT_SANDBOX_IMAGE not in pulls
    assert "dragon-sandbox:desktop" not in pulls


def test_ensure_inspects_before_any_pull():
    docker = _FakeDocker(local={DEFAULT_SANDBOX_IMAGE}, pull_ok={PUBLISHED_SANDBOX_IMAGE, UPSTREAM_SANDBOX_IMAGE})
    assert ensure_sandbox_image("docker", run_capture=docker) == DEFAULT_SANDBOX_IMAGE
    first = docker.calls[0]
    assert first[1:3] == ["image", "inspect"]
    assert first[3] == DEFAULT_SANDBOX_IMAGE
    assert not any(cmd[1] == "pull" for cmd in docker.calls)


def test_ensure_ghcr_access_denied_falls_through_to_upstream():
    docker = _FakeDocker(
        local=(),
        pull_ok={UPSTREAM_SANDBOX_IMAGE},
        pull_stderr={PUBLISHED_SANDBOX_IMAGE: "Error response from daemon: pull access denied for ghcr.io/shenglong76/dragon-sandbox, repository does not exist or may require 'docker login'"},
    )
    assert ensure_sandbox_image("docker", run_capture=docker) == DEFAULT_SANDBOX_IMAGE
    pulls = [cmd[2] for cmd in docker.calls if cmd[1] == "pull"]
    assert pulls == [PUBLISHED_SANDBOX_IMAGE, UPSTREAM_SANDBOX_IMAGE]
    tags = [cmd for cmd in docker.calls if cmd[1] == "tag"]
    assert any(cmd[2] == UPSTREAM_SANDBOX_IMAGE and cmd[3] == DEFAULT_SANDBOX_IMAGE for cmd in tags)
    assert DEFAULT_SANDBOX_IMAGE in docker.local


def test_ensure_ghcr_not_found_falls_through_to_upstream():
    docker = _FakeDocker(
        local=(),
        pull_ok={UPSTREAM_SANDBOX_IMAGE},
        pull_stderr={PUBLISHED_SANDBOX_IMAGE: "Error: not found"},
    )
    assert ensure_sandbox_image("docker", run_capture=docker) == DEFAULT_SANDBOX_IMAGE
    pulls = [cmd[2] for cmd in docker.calls if cmd[1] == "pull"]
    assert PUBLISHED_SANDBOX_IMAGE in pulls
    assert UPSTREAM_SANDBOX_IMAGE in pulls


def test_ensure_raised_access_denied_falls_through():
    docker = _FakeDocker(
        local=(),
        pull_ok={UPSTREAM_SANDBOX_IMAGE},
        raise_on_pull={PUBLISHED_SANDBOX_IMAGE: "Error: pull access denied for ghcr.io/shenglong76/dragon-sandbox"},
    )
    assert ensure_sandbox_image("docker", run_capture=docker) == DEFAULT_SANDBOX_IMAGE
    assert DEFAULT_SANDBOX_IMAGE in docker.local


def test_ensure_retags_local_ghcr_without_pulling_it_again():
    docker = _FakeDocker(local={PUBLISHED_SANDBOX_IMAGE})
    assert ensure_sandbox_image("docker", run_capture=docker) == DEFAULT_SANDBOX_IMAGE
    assert not any(cmd[1] == "pull" for cmd in docker.calls)
    tags = [cmd for cmd in docker.calls if cmd[1] == "tag"]
    assert any(cmd[2] == PUBLISHED_SANDBOX_IMAGE and cmd[3] == DEFAULT_SANDBOX_IMAGE for cmd in tags)


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


def test_ensure_raises_when_everything_is_denied():
    docker = _FakeDocker(
        local=(),
        pull_ok=(),
        pull_stderr={
            PUBLISHED_SANDBOX_IMAGE: "Error: pull access denied for ghcr.io/shenglong76/dragon-sandbox",
            UPSTREAM_SANDBOX_IMAGE: "Error: not found",
        },
    )
    with pytest.raises(RuntimeError, match="fallback pull failed"):
        ensure_sandbox_image("docker", run_capture=docker)
    assert DEFAULT_SANDBOX_IMAGE not in docker.local
    assert not any(cmd[1] == "pull" and cmd[2] == DEFAULT_SANDBOX_IMAGE for cmd in docker.calls)


def test_ensure_raises_when_nothing_can_be_pulled():
    docker = _FakeDocker(local=(), pull_ok=())
    with pytest.raises(RuntimeError, match="fallback pull failed"):
        ensure_sandbox_image("docker", run_capture=docker)
