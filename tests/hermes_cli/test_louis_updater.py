"""Integration coverage for the protected Louis release updater."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
UPDATER = ROOT / "scripts" / "hermes-update-louis"
RELEASE_TEST_MANIFEST = ROOT / "scripts" / "louis-release-tests.txt"
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
    (seed / "tests").mkdir()
    (seed / "tests" / "old_gate.py").write_text("# old gate\n", encoding="utf-8")
    (seed / "scripts").mkdir()
    (seed / "scripts" / "louis-release-tests.txt").write_text(
        "tests/old_gate.py\n", encoding="utf-8"
    )
    _write_executable(
        seed / "scripts" / "hermes-update-louis",
        UPDATER.read_text(encoding="utf-8"),
    )
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
    (seed / "tests" / "candidate_gate.py").write_text(
        "# candidate gate\n", encoding="utf-8"
    )
    (seed / "scripts" / "louis-release-tests.txt").write_text(
        "tests/candidate_gate.py\n", encoding="utf-8"
    )
    _git(seed, "add", "release.txt", "scripts/louis-release-tests.txt", "tests")
    _git(seed, "commit", "-m", "candidate release")
    target_sha = _git(seed, "rev-parse", "HEAD")
    _git(seed, "push", "origin", "main")
    return production, remote, old_sha, target_sha


def test_release_test_manifest_contains_unique_existing_test_paths():
    entries = RELEASE_TEST_MANIFEST.read_text(encoding="utf-8").splitlines()

    assert entries
    assert len(entries) == len(set(entries))
    assert all(entry.startswith("tests/") for entry in entries)
    assert all((ROOT / entry).is_file() for entry in entries)


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


@pytest.mark.parametrize(
    ("manifest_value", "expected_error"),
    [
        (None, "candidate release test manifest is missing"),
        ("/tmp/outside.py\n", "invalid release test path"),
        ("tests/../release.txt\n", "invalid release test path"),
        ("tests/missing.py\n", "missing or leaves the candidate worktree"),
        (
            "tests/candidate_gate.py\ntests/candidate_gate.py\n",
            "duplicate release test path",
        ),
    ],
)
def test_rejects_invalid_candidate_test_manifest(
    tmp_path, manifest_value, expected_error
):
    production, remote, _old_sha, _target_sha = _init_release_repo(tmp_path)
    seed = tmp_path / "seed"
    manifest = seed / "scripts" / "louis-release-tests.txt"
    if manifest_value is None:
        manifest.unlink()
        _git(seed, "rm", "scripts/louis-release-tests.txt")
    else:
        manifest.write_text(manifest_value, encoding="utf-8")
        _git(seed, "add", "scripts/louis-release-tests.txt")
    _git(seed, "commit", "-m", "invalid candidate manifest")
    _git(seed, "push", "origin", "main")

    _write_executable(production / "venv" / "bin" / "python", "#!/bin/sh\nexit 0\n")
    fake_bin = tmp_path / "bin"
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
    env = _base_env(tmp_path, production)
    env.update({
        "HERMES_TEST_LOUIS_ORIGIN": LOUIS_ORIGIN,
        "HERMES_TEST_REAL_GIT": GIT,
        "HERMES_TEST_REMOTE_URL": f"file://{remote}/",
        "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
    })

    result = subprocess.run(
        [str(production / "scripts" / "hermes-update-louis"), "--dry-run"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 4, output
    assert expected_error in output


@pytest.mark.parametrize("dashboard_active", [True, False])
def test_old_updater_uses_candidate_manifest_and_installs_manage_launcher(
    tmp_path, dashboard_active
):
    production, remote, _old_sha, target_sha = _init_release_repo(tmp_path)
    fake_bin = tmp_path / "bin"
    command_dir = tmp_path / "commands"
    editable_marker = tmp_path / "editable-source"
    hermes_calls = tmp_path / "hermes-calls"
    service_states = tmp_path / "service-states"
    service_events = tmp_path / "service-events"
    test_runs = tmp_path / "test-runs"
    editable_marker.write_text(f"{production}\n", encoding="utf-8")
    service_states.mkdir()
    (service_states / "hermes-gateway.service").write_text(
        "active\n", encoding="utf-8"
    )
    (service_states / "hermes-dashboard.service").write_text(
        "active\n" if dashboard_active else "inactive\n", encoding="utf-8"
    )

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
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$HERMES_TEST_HERMES_CALLS"
if [[ "${1:-}" == --version ]]; then
  printf 'Hermes Agent vLouis-updater-test\n'
fi
""",
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
service="${3:-}"
state_file="$HERMES_TEST_SERVICE_STATES/$service"
case "$action" in
  is-active)
    state="$(cat "$state_file")"
    printf '%s\n' "$state"
    [[ "$state" == active ]]
    ;;
  stop)
    head="$($HERMES_TEST_REAL_GIT -C "$HERMES_REPO" rev-parse HEAD)"
    printf 'stop:%s:%s\n' "$service" "$head" >> "$HERMES_TEST_SERVICE_EVENTS"
    printf 'inactive\n' > "$state_file"
    ;;
  start)
    head="$($HERMES_TEST_REAL_GIT -C "$HERMES_REPO" rev-parse HEAD)"
    printf 'start:%s:%s\n' "$service" "$head" >> "$HERMES_TEST_SERVICE_EVENTS"
    printf 'active\n' > "$state_file"
    ;;
  show)
    [[ "$(cat "$state_file")" == active ]] || { printf '0\n'; exit 0; }
    if [[ "$service" == hermes-gateway.service ]]; then
      printf '4242\n'
    else
      printf '4343\n'
    fi
    ;;
  *)
    echo "unexpected systemctl action: $*" >&2
    exit 64
    ;;
esac
""",
    )
    _write_executable(fake_bin / "sleep", "#!/bin/sh\nexit 0\n")

    env = _base_env(tmp_path, production)
    env.update({
        "HERMES_COMMAND_LINK_DIR": str(command_dir),
        "HERMES_TEST_EDITABLE": str(editable_marker),
        "HERMES_TEST_HERMES_CALLS": str(hermes_calls),
        "HERMES_TEST_LOUIS_ORIGIN": LOUIS_ORIGIN,
        "HERMES_TEST_REAL_GIT": GIT,
        "HERMES_TEST_REMOTE_URL": f"file://{remote}/",
        "HERMES_TEST_RUNS": str(test_runs),
        "HERMES_TEST_SERVICE_EVENTS": str(service_events),
        "HERMES_TEST_SERVICE_STATES": str(service_states),
        "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
        "UV_BIN": str(fake_bin / "uv"),
    })

    result = subprocess.run(
        [str(production / "scripts" / "hermes-update-louis"), "--worker"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert _git(production, "rev-parse", "HEAD") == target_sha
    launcher = command_dir / "hermes-manage"
    assert launcher.is_file()
    assert launcher.stat().st_mode & stat.S_IXUSR
    assert test_runs.read_text(encoding="utf-8").splitlines() == [
        "tests/candidate_gate.py -q",
        "tests/candidate_gate.py -q",
    ]
    expected_service_events = [
        f"stop:hermes-gateway.service:{_old_sha}",
        f"start:hermes-gateway.service:{target_sha}",
    ]
    if dashboard_active:
        expected_service_events.insert(
            0, f"stop:hermes-dashboard.service:{_old_sha}"
        )
        expected_service_events.append(
            f"start:hermes-dashboard.service:{target_sha}"
        )
    assert service_events.read_text(
        encoding="utf-8"
    ).splitlines() == expected_service_events
    assert "Gateway stable with PID 4242." in output
    assert ("Dashboard stable with PID 4343." in output) is dashboard_active

    launched = subprocess.run(
        [str(launcher), "--check"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    assert launched.returncode == 0
    assert hermes_calls.read_text(encoding="utf-8").splitlines()[-1] == "manage --check"
    assert "Louis manager launcher installed" in output


def test_current_release_repairs_missing_manage_launcher(tmp_path):
    production, remote, _old_sha, target_sha = _init_release_repo(tmp_path)
    _git(production, "remote", "set-url", "origin", f"file://{remote}")
    _git(production, "fetch", "origin", "main")
    _git(production, "reset", "--hard", target_sha)
    _git(production, "remote", "set-url", "origin", LOUIS_ORIGIN)

    fake_bin = tmp_path / "bin"
    command_dir = tmp_path / "commands"
    editable_checks = tmp_path / "editable-checks"
    hermes_calls = tmp_path / "hermes-calls"
    _write_executable(
        production / "venv" / "bin" / "python",
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "${@: -1}" >> "$HERMES_TEST_EDITABLE_CHECKS"
""",
    )
    _write_executable(
        production / "venv" / "bin" / "hermes",
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$HERMES_TEST_HERMES_CALLS"
if [[ "${1:-}" == --version ]]; then
  printf 'Hermes Agent vLouis-updater-test\n'
fi
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

    env = _base_env(tmp_path, production)
    env.update({
        "HERMES_COMMAND_LINK_DIR": str(command_dir),
        "HERMES_TEST_EDITABLE_CHECKS": str(editable_checks),
        "HERMES_TEST_HERMES_CALLS": str(hermes_calls),
        "HERMES_TEST_LOUIS_ORIGIN": LOUIS_ORIGIN,
        "HERMES_TEST_REAL_GIT": GIT,
        "HERMES_TEST_REMOTE_URL": f"file://{remote}/",
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

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Already running the current Louis release." in output
    assert "Runtime smoke check passed" in output
    assert editable_checks.read_text(encoding="utf-8").strip() == str(production)
    launcher = command_dir / "hermes-manage"
    assert launcher.is_file()
    assert launcher.stat().st_mode & stat.S_IXUSR

    launched = subprocess.run(
        [str(launcher), "--check"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    assert launched.returncode == 0
    assert hermes_calls.read_text(encoding="utf-8").splitlines()[-1] == "manage --check"


def test_managed_service_activation_failure_restores_previous_release(tmp_path):
    production, remote, old_sha, target_sha = _init_release_repo(tmp_path)
    fake_bin = tmp_path / "bin"
    editable_marker = tmp_path / "editable-source"
    service_states = tmp_path / "service-states"
    service_events = tmp_path / "service-events"
    test_runs = tmp_path / "test-runs"
    editable_marker.write_text(f"{production}\n", encoding="utf-8")
    service_states.mkdir()
    for service in ("hermes-gateway.service", "hermes-dashboard.service"):
        (service_states / service).write_text("active\n", encoding="utf-8")

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
        "#!/bin/sh\nprintf 'Hermes Agent vLouis-updater-test\n'\n",
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
service="${3:-}"
state_file="$HERMES_TEST_SERVICE_STATES/$service"
case "$action" in
  is-active)
    state="$(cat "$state_file")"
    printf '%s\n' "$state"
    [[ "$state" == active ]]
    ;;
  stop)
    head="$($HERMES_TEST_REAL_GIT -C "$HERMES_REPO" rev-parse HEAD)"
    printf 'stop:%s:%s\n' "$service" "$head" >> "$HERMES_TEST_SERVICE_EVENTS"
    printf 'inactive\n' > "$state_file"
    ;;
  start)
    head="$($HERMES_TEST_REAL_GIT -C "$HERMES_REPO" rev-parse HEAD)"
    printf 'start:%s:%s\n' "$service" "$head" >> "$HERMES_TEST_SERVICE_EVENTS"
    if [[ "$service" == hermes-dashboard.service \
       && "$head" != "$HERMES_TEST_OLD_SHA" ]]; then
      exit 55
    fi
    printf 'active\n' > "$state_file"
    ;;
  show)
    if [[ "$(cat "$state_file")" == active ]]; then
      if [[ "$service" == hermes-gateway.service ]]; then
        printf '4242\n'
      else
        printf '4343\n'
      fi
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
    _write_executable(fake_bin / "sleep", "#!/bin/sh\nexit 0\n")

    env = _base_env(tmp_path, production)
    env.update({
        "HERMES_TEST_EDITABLE": str(editable_marker),
        "HERMES_TEST_LOUIS_ORIGIN": LOUIS_ORIGIN,
        "HERMES_TEST_OLD_SHA": old_sha,
        "HERMES_TEST_REAL_GIT": GIT,
        "HERMES_TEST_REMOTE_URL": f"file://{remote}/",
        "HERMES_TEST_RUNS": str(test_runs),
        "HERMES_TEST_SERVICE_EVENTS": str(service_events),
        "HERMES_TEST_SERVICE_STATES": str(service_states),
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
    assert (service_states / "hermes-gateway.service").read_text(
        encoding="utf-8"
    ).strip() == "active"
    assert (service_states / "hermes-dashboard.service").read_text(
        encoding="utf-8"
    ).strip() == "active"
    assert service_events.read_text(encoding="utf-8").splitlines() == [
        f"stop:hermes-dashboard.service:{old_sha}",
        f"stop:hermes-gateway.service:{old_sha}",
        f"start:hermes-gateway.service:{target_sha}",
        f"start:hermes-dashboard.service:{target_sha}",
        f"stop:hermes-dashboard.service:{target_sha}",
        f"stop:hermes-gateway.service:{target_sha}",
        f"start:hermes-gateway.service:{old_sha}",
        f"start:hermes-dashboard.service:{old_sha}",
    ]
    assert "Rollback restored source and Python environment." in output
    assert "FAILED (exit 55)." in output

    run_lines = test_runs.read_text(encoding="utf-8").splitlines()
    assert run_lines == [
        "tests/candidate_gate.py -q",
        "tests/candidate_gate.py -q",
    ]

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
