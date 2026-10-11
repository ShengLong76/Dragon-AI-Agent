"""Tests for cgroup resource-limit gating in the docker backend.

On hosts where the cgroup v2 cpu/memory/pids controllers are not delegated
(e.g. unprivileged Proxmox LXCs), passing ``--cpus``/``--memory``/``--pids-limit``
to ``docker run`` fails every container start with OCI runtime error / exit 126.
``_cgroup_limits_available`` probes once and the resource flags are gated on it,
so the sandbox degrades gracefully instead of failing.

The probe itself is a ``docker run --rm … sleep 0``. For Dragon alias tags that
run MUST go through ``ensure_sandbox_image`` — a bare
``docker run dragon-sandbox:desktop`` Hub-pulls ``library/dragon-sandbox``
even when ``nousresearch/hermes-sandbox:desktop`` is already local.
"""
import subprocess

import pytest

import tools.environments.docker as docker_env
from tools.environments.sandbox_image import (
    DEFAULT_SANDBOX_IMAGE,
    PUBLISHED_SANDBOX_IMAGE,
    UPSTREAM_SANDBOX_IMAGE,
)


@pytest.fixture(autouse=True)
def _reset_cgroup_cache():
    """The probe results are cached in module-level globals; reset per test."""
    docker_env._cgroup_limits_ok = None
    docker_env._storage_opt_ok = None
    yield
    docker_env._cgroup_limits_ok = None
    docker_env._storage_opt_ok = None




def test_probe_returns_true_when_container_starts(monkeypatch):
    monkeypatch.setattr(docker_env, "find_docker", lambda: "/usr/bin/docker")
    captured = {}

    def _run(cmd, *a, **k):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(docker_env.subprocess, "run", _run)
    assert docker_env._cgroup_limits_available("hermes-agent:latest") is True
    # Probes all three controllers together against the real sandbox image.
    assert "--cpus" in captured["cmd"]
    assert "--memory" in captured["cmd"]
    assert "--pids-limit" in captured["cmd"]
    assert "hermes-agent:latest" in captured["cmd"]


def test_probe_result_is_cached(monkeypatch):
    monkeypatch.setattr(docker_env, "find_docker", lambda: "/usr/bin/docker")
    calls = []

    def _run(cmd, *a, **k):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(docker_env.subprocess, "run", _run)
    docker_env._cgroup_limits_available("img")
    docker_env._cgroup_limits_available("img")
    docker_env._cgroup_limits_available("img")
    assert len(calls) == 1  # probe runs once, then cached


def test_probe_definitive_cgroup_failure_is_cached(monkeypatch):
    """A daemon rejection that names cgroups IS a host property; caching it is
    the point of the probe, so subsequent spawns do not pay it again (#116162
    only stops caching failures that say nothing about cgroups)."""
    monkeypatch.setattr(docker_env, "find_docker", lambda: "/usr/bin/docker")
    calls = []

    def _run(cmd, *a, **k):
        calls.append(cmd)
        return subprocess.CompletedProcess(
            cmd, 126, stdout="", stderr="docker: Error response from daemon: failed to "
            "create task for container: OCI runtime create failed: error setting cgroup "
            "config for procHooks process: permission denied")

    monkeypatch.setattr(docker_env.subprocess, "run", _run)
    assert docker_env._cgroup_limits_available("img") is False
    assert docker_env._cgroup_limits_available("img") is False
    assert len(calls) == 1


@pytest.mark.parametrize(
    "info, create, cached",
    [
        # `docker info` failing (daemon cold-start) is transient: not "not overlay2".
        ((1, "", "Cannot connect to the Docker daemon"), None, None),
        # The daemon rejecting --storage-opt is a host property: cached False.
        ((0, "overlay2\n", ""), (125, "", "Error response from daemon: --storage-opt is "
                                          "supported only for overlay2 with pquota"), False),
        # A create failure that never reached the storage check (pull error) is transient.
        ((0, "overlay2\n", ""), (125, "", "Unable to find image 'hello-world:latest'"), None),
    ],
)
def test_storage_opt_probe_caches_only_definitive_answers(monkeypatch, info, create, cached):
    """``_storage_opt_supported`` must not latch disk quota off for the process on a
    failure that says nothing about pquota support (#116162)."""
    monkeypatch.setattr(docker_env, "find_docker", lambda: "/usr/bin/docker")

    def _run(cmd, *a, **k):
        rc, out, err = info if cmd[1] == "info" else create
        return subprocess.CompletedProcess(cmd, rc, stdout=out, stderr=err)

    monkeypatch.setattr(docker_env.subprocess, "run", _run)
    assert docker_env.DockerEnvironment._storage_opt_supported() is False
    assert docker_env._storage_opt_ok is cached


def test_transient_probe_failure_recovers_on_next_spawn(monkeypatch):
    """E2e through DockerEnvironment: the probe timing out on spawn one (auto-pull
    past the 60s timeout, daemon cold-start) leaves THAT container unlimited but
    must not disable limits process-wide. Spawn two re-probes, succeeds, and its
    docker run argv carries --cpus/--memory/--pids-limit."""
    monkeypatch.setattr(docker_env, "find_docker", lambda: "/usr/bin/docker")
    calls, probe_calls = [], []

    def _run(cmd, *a, **k):
        calls.append(cmd)
        if isinstance(cmd, list) and len(cmd) > 1 and cmd[1] == "run" and "--rm" in cmd:
            # the throwaway cgroup probe (`run --rm ... sleep 0`), not the real `run -d`
            probe_calls.append(cmd)
            if len(probe_calls) == 1:
                raise subprocess.TimeoutExpired(cmd, 60)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if isinstance(cmd, list) and len(cmd) > 1 and cmd[1] == "version":
            return subprocess.CompletedProcess(cmd, 0, stdout="Docker version", stderr="")
        if isinstance(cmd, list) and len(cmd) > 1 and cmd[1] == "run" and "-d" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="fake-container-id\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(docker_env.subprocess, "run", _run)
    docker_env.DockerEnvironment(image="img", cpu=1.0, memory=512, task_id="t1")
    docker_env.DockerEnvironment(image="img", cpu=1.0, memory=512, task_id="t2")

    run_argvs = [c for c in calls
                 if isinstance(c, list) and len(c) > 1 and c[1] == "run" and "-d" in c]
    assert len(run_argvs) == 2
    assert "--cpus" not in run_argvs[0] and "--memory" not in run_argvs[0]
    assert "--cpus" in run_argvs[1] and "1.0" in run_argvs[1]
    assert "--memory" in run_argvs[1] and "512m" in run_argvs[1]
    assert "--pids-limit" in run_argvs[1]
    assert len(probe_calls) == 2  # re-probed, not latched off the timeout


class _EnsureAwareDocker:
    """Fake ``subprocess.run`` that tracks inspect / pull / tag / run.

    Used to prove the cgroup probe (and DockerEnvironment construct) never
    ``docker run`` a missing local-only tag.
    """

    def __init__(self, local=(), pull_ok=()):
        self.local = set(local)
        self.pull_ok = set(pull_ok)
        self.calls: list[list[str]] = []

    def __call__(self, cmd, *a, **k):
        self.calls.append(list(cmd) if isinstance(cmd, list) else cmd)
        if not isinstance(cmd, list) or len(cmd) < 2:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        sub = cmd[1]
        if sub == "version":
            return subprocess.CompletedProcess(cmd, 0, stdout="Docker version", stderr="")
        if sub == "image" and cmd[2] == "inspect":
            image = cmd[3]
            if image in self.local:
                return subprocess.CompletedProcess(cmd, 0, stdout="sha256:abc\n", stderr="")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Error: No such image")
        if sub == "inspect":
            # entrypoint / container inspect used during construct
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Error: No such object")
        if sub == "pull":
            image = cmd[2]
            if image in self.pull_ok:
                self.local.add(image)
                return subprocess.CompletedProcess(cmd, 0, stdout="pulled\n", stderr="")
            return subprocess.CompletedProcess(
                cmd, 1, stdout="",
                stderr=f"Error: pull access denied for {image}, repository does not exist")
        if sub == "tag":
            self.local.add(cmd[3])
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if sub == "run":
            image = cmd[-3] if len(cmd) >= 3 and cmd[-2] == "sleep" else cmd[-1]
            # probe: … image sleep 0; launch: … image sleep infinity
            if image not in self.local:
                return subprocess.CompletedProcess(
                    cmd, 125, stdout="",
                    stderr=f"Unable to find image '{image}' locally\n"
                           f"pull access denied for {image.split(':')[0]}, "
                           f"repository does not exist")
            stdout = "" if "--rm" in cmd else "fake-container-id\n"
            return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")
        if sub == "ps":
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")


def _install_ensure_aware_docker(monkeypatch, docker):
    monkeypatch.setattr(docker_env, "find_docker", lambda: "/usr/bin/docker")
    monkeypatch.setattr(docker_env.subprocess, "run", docker)
    monkeypatch.setattr(docker_env.DockerEnvironment, "init_session", lambda self: None)
    return docker


def test_probe_retags_local_upstream_before_docker_run(monkeypatch):
    """Windows repro: upstream desktop image is local, dragon tag is not.

    The probe must retag first. A ``docker run dragon-sandbox:desktop`` that
    skips ensure Hub-pulls library/dragon-sandbox and never creates a container.
    """
    docker = _install_ensure_aware_docker(
        monkeypatch, _EnsureAwareDocker(local={UPSTREAM_SANDBOX_IMAGE}))

    assert docker_env._cgroup_limits_available(DEFAULT_SANDBOX_IMAGE) is True

    pulls = [cmd[2] for cmd in docker.calls if cmd[1] == "pull"]
    assert DEFAULT_SANDBOX_IMAGE not in pulls
    tags = [cmd for cmd in docker.calls if cmd[1] == "tag"]
    assert any(cmd[2] == UPSTREAM_SANDBOX_IMAGE and cmd[3] == DEFAULT_SANDBOX_IMAGE for cmd in tags)
    probe_runs = [
        cmd for cmd in docker.calls
        if cmd[1] == "run" and "--rm" in cmd
    ]
    assert probe_runs, "cgroup probe must still run after ensure"
    assert DEFAULT_SANDBOX_IMAGE in probe_runs[0]
    assert "--pull" in probe_runs[0] and "never" in probe_runs[0]
    # ensure (inspect/tag) happens before the throwaway run
    first_tag = next(i for i, cmd in enumerate(docker.calls) if cmd[1] == "tag")
    first_run = next(i for i, cmd in enumerate(docker.calls) if cmd[1] == "run")
    assert first_tag < first_run
    assert DEFAULT_SANDBOX_IMAGE in docker.local


def test_probe_uses_local_dragon_tag_without_pull(monkeypatch):
    docker = _install_ensure_aware_docker(
        monkeypatch, _EnsureAwareDocker(local={DEFAULT_SANDBOX_IMAGE}))

    assert docker_env._cgroup_limits_available(DEFAULT_SANDBOX_IMAGE) is True
    assert not any(cmd[1] == "pull" for cmd in docker.calls)
    assert not any(cmd[1] == "tag" for cmd in docker.calls)


def test_probe_skips_docker_run_when_every_fallback_fails(monkeypatch):
    docker = _install_ensure_aware_docker(monkeypatch, _EnsureAwareDocker(local=()))

    assert docker_env._cgroup_limits_available(DEFAULT_SANDBOX_IMAGE) is False
    assert not any(cmd[1] == "run" for cmd in docker.calls)
    assert not any(cmd[1] == "pull" and cmd[2] == DEFAULT_SANDBOX_IMAGE for cmd in docker.calls)
    assert docker_env._cgroup_limits_ok is None  # transient: image may appear later


def test_probe_prefers_ghcr_then_upstream_when_nothing_is_local(monkeypatch):
    docker = _install_ensure_aware_docker(
        monkeypatch, _EnsureAwareDocker(local=(), pull_ok={PUBLISHED_SANDBOX_IMAGE, UPSTREAM_SANDBOX_IMAGE}))

    assert docker_env._cgroup_limits_available(DEFAULT_SANDBOX_IMAGE) is True
    pulls = [cmd[2] for cmd in docker.calls if cmd[1] == "pull"]
    assert pulls[0] == PUBLISHED_SANDBOX_IMAGE
    assert UPSTREAM_SANDBOX_IMAGE not in pulls
    assert DEFAULT_SANDBOX_IMAGE not in pulls


def test_docker_environment_retags_local_upstream_before_launch(monkeypatch):
    """Constructing the Linux guest must produce dragon-sandbox:desktop and a container."""
    docker = _install_ensure_aware_docker(
        monkeypatch, _EnsureAwareDocker(local={UPSTREAM_SANDBOX_IMAGE}))

    env = docker_env.DockerEnvironment(
        image=DEFAULT_SANDBOX_IMAGE, cwd="/root", timeout=60, cpu=0, memory=0, disk=0,
        task_id="bot-desktop-guest:test", persist_across_processes=False,
    )
    assert env._image == DEFAULT_SANDBOX_IMAGE
    assert DEFAULT_SANDBOX_IMAGE in docker.local
    assert not any(cmd[1] == "pull" and cmd[2] == DEFAULT_SANDBOX_IMAGE for cmd in docker.calls)
    launch = [cmd for cmd in docker.calls if cmd[1] == "run" and "-d" in cmd]
    assert launch, "fresh guest must docker run -d"
    assert DEFAULT_SANDBOX_IMAGE in launch[0]


def test_docker_environment_raises_clear_ui_error_when_image_missing(monkeypatch):
    from tools.environments.sandbox_image import SandboxImageError

    _install_ensure_aware_docker(monkeypatch, _EnsureAwareDocker(local=()))

    with pytest.raises(SandboxImageError, match="Bot Desktop cannot start") as ei:
        docker_env.DockerEnvironment(
            image=DEFAULT_SANDBOX_IMAGE, cwd="/root", timeout=60, cpu=0, memory=0, disk=0,
            task_id="bot-desktop-guest:test", persist_across_processes=False,
        )
    msg = str(ei.value)
    assert UPSTREAM_SANDBOX_IMAGE in msg
    assert "pull access denied" in msg
