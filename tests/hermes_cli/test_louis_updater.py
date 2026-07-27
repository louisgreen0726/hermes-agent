"""Integration coverage for the protected Louis release updater."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UPDATER = ROOT / "scripts" / "hermes-update-louis"
LOUIS_ORIGIN = "https://github.com/louisgreen0726/hermes-agent.git"
UPSTREAM_ORIGIN = "https://github.com/NousResearch/hermes-agent.git"
GIT = shutil.which("git")


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        [GIT, "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _base_env(tmp_path: Path, repo: Path) -> dict[str, str]:
    hermes_home = tmp_path / "hermes-home"
    runtime_dir = tmp_path / "runtime"
    hermes_home.mkdir()
    runtime_dir.mkdir()
    return {
        **os.environ,
        "HERMES_HOME": str(hermes_home),
        "HERMES_REPO": str(repo),
        "HERMES_RELEASE_BRANCH": "main",
        "XDG_RUNTIME_DIR": str(runtime_dir),
    }


def _init_release_repo(tmp_path: Path) -> tuple[Path, Path, str, str]:
    seed = tmp_path / "seed"
    remote = tmp_path / "release.git"
    production = tmp_path / "production"
    seed.mkdir()
    remote.mkdir()

    _git(seed, "init", "--initial-branch=main")
    _git(seed, "config", "user.name", "Louis Updater Test")
    _git(seed, "config", "user.email", "louis-updater-test@example.invalid")
    (seed / ".gitignore").write_text("venv/\n", encoding="utf-8")
    (seed / "release.txt").write_text("old\n", encoding="utf-8")
    _write_executable(
        seed / "scripts" / "run_tests.sh",
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$HERMES_TEST_RUNS"
""",
    )
    _git(seed, "add", ".")
    _git(seed, "commit", "-m", "old release")
    old_sha = _git(seed, "rev-parse", "HEAD")

    _git(remote, "init", "--bare")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "-u", "origin", "main")
    subprocess.run(
        [
            GIT,
            "clone",
            "--quiet",
            "--depth",
            "1",
            "--branch",
            "main",
            f"file://{remote}",
            str(production),
        ],
        check=True,
    )
    _git(production, "remote", "set-url", "origin", LOUIS_ORIGIN)
    assert _git(production, "rev-parse", "--is-shallow-repository") == "true"

    (seed / "release.txt").write_text("candidate\n", encoding="utf-8")
    _git(seed, "add", "release.txt")
    _git(seed, "commit", "-m", "candidate release")
    target_sha = _git(seed, "rev-parse", "HEAD")
    _git(seed, "push", "origin", "main")
    return production, remote, old_sha, target_sha


def test_rejects_non_louis_origin_before_fetch(tmp_path):
    repo = tmp_path / "production"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    _git(repo, "config", "user.name", "Louis Updater Test")
    _git(repo, "config", "user.email", "louis-updater-test@example.invalid")
    (repo / ".gitignore").write_text("venv/\n", encoding="utf-8")
    (repo / "release.txt").write_text("old\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "old release")
    _git(repo, "remote", "add", "origin", UPSTREAM_ORIGIN)
    _write_executable(repo / "venv" / "bin" / "python", "#!/bin/sh\nexit 0\n")

    fake_bin = tmp_path / "bin"
    git_log = tmp_path / "git-calls.log"
    _write_executable(
        fake_bin / "git",
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$HERMES_TEST_GIT_LOG"
exec "$HERMES_TEST_REAL_GIT" "$@"
""",
    )
    env = _base_env(tmp_path, repo)
    env.update({
        "HERMES_TEST_GIT_LOG": str(git_log),
        "HERMES_TEST_REAL_GIT": GIT,
        "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
    })

    result = subprocess.run(
        [str(UPDATER), "--worker"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "origin is not the Louis product repository" in result.stdout
    assert all(
        " fetch " not in f" {line} " for line in git_log.read_text().splitlines()
    )
    assert not (Path(env["HERMES_HOME"]) / "louis-releases" / "STATUS").exists()


def test_gateway_activation_failure_restores_previous_release(tmp_path):
    production, remote, old_sha, target_sha = _init_release_repo(tmp_path)
    fake_bin = tmp_path / "bin"
    editable_marker = tmp_path / "editable-source"
    gateway_state = tmp_path / "gateway-state"
    gateway_events = tmp_path / "gateway-events"
    test_runs = tmp_path / "test-runs"
    editable_marker.write_text(f"{production}\n", encoding="utf-8")
    gateway_state.write_text("active\n", encoding="utf-8")

    _write_executable(
        production / "venv" / "bin" / "python",
        """#!/usr/bin/env bash
set -euo pipefail
expected="${@: -1}"
actual="$(cat "$HERMES_TEST_EDITABLE")"
if [[ "$(realpath "$actual")" != "$(realpath "$expected")" ]]; then
  echo "editable source mismatch: $actual != $expected" >&2
  exit 1
fi
printf 'Editable install verified: %s/hermes_cli/main.py\n' "$actual"
""",
    )
    _write_executable(
        production / "venv" / "bin" / "hermes",
        "#!/bin/sh\nprintf 'Louis updater test\n'\n",
    )
    _write_executable(
        fake_bin / "uv",
        """#!/usr/bin/env bash
set -euo pipefail
source_root="${@: -1}"
source_root="${source_root%\\[all\\]}"
printf '%s\n' "$source_root" > "$HERMES_TEST_EDITABLE"
""",
    )
    _write_executable(
        fake_bin / "git",
        """#!/usr/bin/env bash
set -euo pipefail
args=("$@")
count="${#args[@]}"
if (( count >= 3 )); then
  command_index=$((count - 3))
  if [[ "${args[$command_index]}" == remote \
     && "${args[$((command_index + 1))]}" == get-url \
     && "${args[$((command_index + 2))]}" == origin ]]; then
    exec "$HERMES_TEST_REAL_GIT" "$@"
  fi
fi
exec "$HERMES_TEST_REAL_GIT" \
  -c "url.${HERMES_TEST_REMOTE_URL}.insteadOf=${HERMES_TEST_LOUIS_ORIGIN}" \
  "$@"
""",
    )
    _write_executable(
        fake_bin / "systemctl",
        """#!/usr/bin/env bash
set -euo pipefail
action="${2:-}"
case "$action" in
  is-active)
    state="$(cat "$HERMES_TEST_GATEWAY_STATE")"
    printf '%s\n' "$state"
    [[ "$state" == active ]]
    ;;
  stop)
    head="$($HERMES_TEST_REAL_GIT -C "$HERMES_REPO" rev-parse HEAD)"
    printf 'stop:%s\n' "$head" >> "$HERMES_TEST_GATEWAY_EVENTS"
    printf 'inactive\n' > "$HERMES_TEST_GATEWAY_STATE"
    ;;
  start)
    head="$($HERMES_TEST_REAL_GIT -C "$HERMES_REPO" rev-parse HEAD)"
    printf 'start:%s\n' "$head" >> "$HERMES_TEST_GATEWAY_EVENTS"
    if [[ "$head" != "$HERMES_TEST_OLD_SHA" ]]; then
      exit 55
    fi
    printf 'active\n' > "$HERMES_TEST_GATEWAY_STATE"
    ;;
  show)
    if [[ "$(cat "$HERMES_TEST_GATEWAY_STATE")" == active ]]; then
      printf '4242\n'
    else
      printf '0\n'
    fi
    ;;
  *)
    echo "unexpected systemctl action: $*" >&2
    exit 64
    ;;
esac
""",
    )

    env = _base_env(tmp_path, production)
    env.update({
        "HERMES_TEST_EDITABLE": str(editable_marker),
        "HERMES_TEST_GATEWAY_EVENTS": str(gateway_events),
        "HERMES_TEST_GATEWAY_STATE": str(gateway_state),
        "HERMES_TEST_LOUIS_ORIGIN": LOUIS_ORIGIN,
        "HERMES_TEST_OLD_SHA": old_sha,
        "HERMES_TEST_REAL_GIT": GIT,
        "HERMES_TEST_REMOTE_URL": f"file://{remote}/",
        "HERMES_TEST_RUNS": str(test_runs),
        "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
        "UV_BIN": str(fake_bin / "uv"),
    })

    result = subprocess.run(
        [str(UPDATER), "--worker"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 55, output
    assert _git(production, "rev-parse", "HEAD") == old_sha
    assert _git(production, "status", "--porcelain") == ""
    assert editable_marker.read_text(encoding="utf-8").strip() == str(production)
    assert gateway_state.read_text(encoding="utf-8").strip() == "active"
    assert gateway_events.read_text(encoding="utf-8").splitlines() == [
        f"stop:{old_sha}",
        f"start:{target_sha}",
        f"stop:{target_sha}",
        f"start:{old_sha}",
    ]
    assert "Rollback restored source and Python environment." in output
    assert "FAILED (exit 55)." in output

    run_lines = test_runs.read_text(encoding="utf-8").splitlines()
    assert len(run_lines) == 2
    for run_line in run_lines:
        assert "tests/hermes_cli/test_louis_distribution.py" in run_line
        assert "tests/hermes_cli/test_louis_updater.py" in run_line
        assert "tests/test_packaging_metadata.py" in run_line

    release_dir = Path(env["HERMES_HOME"]) / "louis-releases"
    assert not (release_dir / "STATUS").exists()
    bundles = list(release_dir.glob("louis-before-*.bundle"))
    assert len(bundles) == 1
    assert bundles[0].with_suffix(".bundle.sha256").is_file()
    verify = subprocess.run(
        [GIT, "-C", str(production), "bundle", "verify", str(bundles[0])],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert old_sha in _git(production, "bundle", "list-heads", str(bundles[0]))
