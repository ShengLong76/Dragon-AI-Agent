#!/usr/bin/env python3
"""Prove dirty root-owned logs become writable and a health endpoint can succeed.

Mirrors the UltraDragon 2026-10-01 failure:
  warm $HERMES_HOME owned by the runtime user, logs/agent.log root:root 0644,
  runtime user hits PermissionError, wrapper heals, runtime user writes and
  serves /health.

No secrets. Privileged half needs passwordless sudo (creates a throwaway user).
"""

from __future__ import annotations

import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
GATEWAY_SH = ROOT / "scripts" / "airmaze" / "start-gateway.sh"
TEST_USER = "dragonheal"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, **kwargs)


def have_sudo() -> bool:
    return run(["sudo", "-n", "true"]).returncode == 0


def test_unprivileged_self_test() -> None:
    proc = run(["/bin/sh", str(GATEWAY_SH), "--self-test"], cwd=str(ROOT))
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        fail(f"start-gateway.sh --self-test exited {proc.returncode}")
    if "OK  start-gateway.sh --self-test" not in proc.stdout:
        fail("self-test did not print OK")
    print("OK  unprivileged self-test")


def sudo(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return run(["sudo", "-n", *args], **kwargs)


def ensure_test_user() -> None:
    if run(["id", TEST_USER]).returncode == 0:
        return
    created = sudo(["useradd", "-M", "-U", "-s", "/usr/sbin/nologin", TEST_USER])
    if created.returncode != 0:
        fail(f"useradd {TEST_USER}: {created.stderr.strip()}")


def remove_test_user() -> None:
    sudo(["userdel", TEST_USER])


def write_as(user: str, path: pathlib.Path, text: str) -> subprocess.CompletedProcess[str]:
    return sudo(
        [
            "-u",
            user,
            "python3",
            "-c",
            "import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.open('a').write(sys.argv[2])",
            str(path),
            text,
        ]
    )


def test_dirty_root_owned_logs_and_health() -> None:
    if not have_sudo():
        print("SKIP privileged dirty-log/health (no passwordless sudo)")
        return
    ensure_test_user()
    tmp = pathlib.Path(sudo(["mktemp", "-d", "-p", "/tmp", "dragon-heal.XXXXXX"]).stdout.strip())
    if not tmp or not str(tmp).startswith("/tmp/"):
        fail(f"mktemp failed: {tmp}")
    home = tmp / "data"
    logs = home / "logs"
    agent = logs / "agent.log"
    helpers = None
    try:
        sudo(["mkdir", "-p", str(logs), str(home / "backups")])
        # mktemp as root is 0700; the runtime user must be able to traverse
        # to logs/ the same way hermes can traverse /opt/data on the bind mount.
        sudo(["chmod", "755", str(tmp), str(home)])
        sudo(["touch", str(agent), str(logs / "errors.log")])
        # Warm volume: top-level already runtime-owned (stage2 skips logs chown).
        sudo(["chown", f"{TEST_USER}:{TEST_USER}", str(home)])
        sudo(["chown", "root:root", str(agent), str(logs / "errors.log"), str(home / "backups")])
        sudo(["chmod", "644", str(agent), str(logs / "errors.log")])
        sudo(["chmod", "755", str(logs), str(home / "backups")])

        denied = write_as(TEST_USER, agent, "should-fail\n")
        if denied.returncode == 0:
            fail("runtime user could write root-owned 0644 agent.log before heal (setup is wrong)")
        err = (denied.stderr or "") + (denied.stdout or "")
        if "Permission denied" not in err and "PermissionError" not in err:
            # python may print OSError [Errno 13]
            if "Errno 13" not in err:
                fail(f"expected PermissionError before heal, got: {err}")
        print("OK  dirty root-owned agent.log denies runtime user (UltraDragon shape)")

        heal = sudo(
            ["env", f"HERMES_HOME={home}", f"DRAGON_HEAL_OWNER={TEST_USER}", "/bin/sh", str(GATEWAY_SH), "--heal-only"]
        )
        sys.stdout.write(heal.stdout)
        sys.stderr.write(heal.stderr)
        if heal.returncode != 0:
            fail(f"--heal-only exited {heal.returncode}")

        wrote = write_as(TEST_USER, agent, "healed\n")
        if wrote.returncode != 0:
            fail(f"runtime user still cannot write agent.log after heal: {wrote.stderr}")
        body = sudo(["cat", str(agent)]).stdout
        if "healed" not in body:
            fail(f"agent.log missing healed write: {body!r}")
        print("OK  heal lets runtime user append agent.log (no manual chown)")

        helpers = pathlib.Path(tempfile.mkdtemp(prefix="dragon-heal-helpers-"))
        health_py = helpers / "fake-gateway-run.py"
        dispatch = helpers / "fake-dispatch.sh"
        port_file = helpers / "health.port"
        health_py.write_text(
            "import pathlib, socket, sys\n"
            "log = pathlib.Path(sys.argv[1])\n"
            "port_path = pathlib.Path(sys.argv[2])\n"
            "log.open('a').write('gateway-run\\n')\n"
            "srv = socket.socket()\n"
            "srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
            "srv.bind(('127.0.0.1', 0))\n"
            "port_path.write_text(str(srv.getsockname()[1]))\n"
            "srv.listen(1)\n"
            "conn, _ = srv.accept()\n"
            "req = conn.recv(1024)\n"
            "if b'/health' not in req:\n"
            "    conn.sendall(b'HTTP/1.1 404 Not Found\\r\\nContent-Length: 0\\r\\n\\r\\n')\n"
            "else:\n"
            "    body = b'ok\\n'\n"
            "    conn.sendall(\n"
            "        b'HTTP/1.1 200 OK\\r\\nContent-Type: text/plain\\r\\n'\n"
            "        b'Content-Length: 3\\r\\n\\r\\n' + body\n"
            "    )\n"
            "conn.close()\n"
            "srv.close()\n",
            encoding="utf-8",
        )
        dispatch.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            'if [ "${1:-}" != "gateway" ] || [ "${2:-}" != "run" ]; then\n'
            '  echo "FAIL: expected gateway run, got $*" >&2\n'
            "  exit 2\n"
            "fi\n"
            f'owner="${{DRAGON_HEAL_OWNER:-{TEST_USER}}}"\n'
            f'exec su -s /bin/sh "$owner" -c \'python3 "{health_py}" "{agent}" "{port_file}"\'\n',
            encoding="utf-8",
        )
        os.chmod(dispatch, 0o755)
        os.chmod(helpers, 0o1777)

        env = [
            "env",
            f"HERMES_HOME={home}",
            f"DRAGON_HEAL_OWNER={TEST_USER}",
            f"DRAGON_HANDOFF_DISPATCH={dispatch}",
            "/bin/sh",
            str(GATEWAY_SH),
            "gateway",
            "run",
        ]
        # Re-dirty logs so the default (heal then hand off) path is what recovers them.
        sudo(["chown", "root:root", str(agent)])
        sudo(["chmod", "644", str(agent)])
        if write_as(TEST_USER, agent, "again\n").returncode == 0:
            fail("re-dirty agent.log was still writable")

        proc = subprocess.Popen(
            ["sudo", "-n", "-u", "root", *env],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.time() + 8
        port = None
        while time.time() < deadline:
            if port_file.is_file():
                raw = port_file.read_text(encoding="utf-8").strip()
                if raw.isdigit():
                    port = int(raw)
                    break
            if proc.poll() is not None:
                out, err = proc.communicate()
                fail(f"handoff exited {proc.returncode} before listen: {out}{err}")
            time.sleep(0.05)
        if port is None:
            proc.kill()
            out, err = proc.communicate()
            fail(f"health port never appeared: {out}{err}")

        req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status != 200:
                fail(f"/health status {resp.status}")
            if resp.read() != b"ok\n":
                fail("/health body mismatch")
        proc.wait(timeout=5)
        if proc.returncode != 0:
            out, err = proc.communicate()
            fail(f"handoff exited {proc.returncode}: {out}{err}")
        final = sudo(["cat", str(agent)]).stdout
        if "gateway-run" not in final:
            fail(f"handoff runtime did not write agent.log: {final!r}")
        print("OK  heal-then-handoff serves /health after dirty root-owned agent.log")
    finally:
        sudo(["rm", "-rf", str(tmp)])
        if helpers is not None:
            shutil.rmtree(helpers, ignore_errors=True)
        remove_test_user()


def test_compose_still_fail_closed_and_vbs() -> None:
    compose = (ROOT / "docker-compose.embedded.yml").read_text(encoding="utf-8")
    if 'entrypoint: ["/bin/sh", "/opt/dragon/start-gateway.sh"]' not in compose:
        fail("compose must use start-gateway.sh as gateway entrypoint")
    if 'command: ["gateway", "run"]' not in compose:
        fail("compose must still run gateway run")
    vbs = (ROOT / "scripts" / "airmaze" / "Start-DragonAI.vbs").read_text(encoding="utf-8", errors="replace")
    if "wscript" not in vbs.lower() or "start-embedded.ps1" not in vbs:
        fail("Start-DragonAI.vbs is not the product host")
    if " -StartDocker" in vbs.replace("Do not pass -StartDocker", "").replace("fail-closed", ""):
        fail("VBS product host must not pass -StartDocker; default launch starts Docker itself")
    if "fail-closed" in vbs.lower():
        fail("VBS comment still describes fail-closed Docker; launch now starts Docker in the tray")
    print("OK  compose wrap + VBS auto-Docker contract")


def main() -> int:
    if not GATEWAY_SH.is_file():
        fail(f"missing {GATEWAY_SH}")
    test_unprivileged_self_test()
    test_compose_still_fail_closed_and_vbs()
    test_dirty_root_owned_logs_and_health()
    print("SMOKE OK: dirty root-owned logs heal; health path can succeed without manual chown.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
