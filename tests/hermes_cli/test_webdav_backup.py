"""End-to-end tests for WebDAV backup using a real local HTTP server."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import threading
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import pytest

import hermes_cli.webdav_backup as webdav_backup
from hermes_cli.webdav_backup import (
    MANAGED_CRON_MARKER,
    BackupBusyError,
    BackupLock,
    WebDAVError,
    WebDAVSettings,
    apply_webdav_settings,
    cron_main,
    ensure_webdav_cron,
    list_remote_backups,
    load_webdav_settings,
    load_webdav_state,
    restore_backup,
    save_webdav_settings,
    save_webdav_state,
    test_webdav_connection as exercise_webdav_connection,
    upload_backup,
)


class _DAVState:
    def __init__(
        self,
        root: Path,
        *,
        username: str = "",
        password: str = "",
        move_supported: bool = True,
    ):
        self.root = root
        self.username = username
        self.password = password
        self.move_supported = move_supported
        self.failures: dict[str, int] = {}
        self.path_failures: dict[tuple[str, str], int] = {}
        self.counts: dict[str, int] = {}


def _handler_for(state: _DAVState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "HermesTestWebDAV/1"

        def log_message(self, format, *args):
            return

        def _authorized(self) -> bool:
            if not state.username and not state.password:
                return True
            expected = base64.b64encode(
                f"{state.username}:{state.password}".encode("utf-8")
            ).decode("ascii")
            if self.headers.get("Authorization") == f"Basic {expected}":
                return True
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Hermes test"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return False

        def _begin(self) -> bool:
            method = self.command.upper()
            state.counts[method] = state.counts.get(method, 0) + 1
            if not self._authorized():
                return False
            request_path = urlsplit(self.path).path
            for (failed_method, suffix), count in list(state.path_failures.items()):
                if failed_method == method and request_path.endswith(suffix) and count > 0:
                    state.path_failures[(failed_method, suffix)] = count - 1
                    self._send(503, b"temporary path failure")
                    return False
            remaining = state.failures.get(method, 0)
            if remaining > 0:
                state.failures[method] = remaining - 1
                self._send(503, b"temporary failure")
                return False
            return True

        def _path(self, raw: str | None = None) -> Path:
            parsed = urlsplit(raw or self.path)
            parts = [unquote(part) for part in parsed.path.split("/") if part]
            if any(part in {".", ".."} or "/" in part or "\\" in part for part in parts):
                raise ValueError("unsafe path")
            target = state.root.joinpath(*parts)
            target.resolve().relative_to(state.root.resolve())
            return target

        def _send(
            self,
            status: int,
            body: bytes = b"",
            *,
            content_type: str = "text/plain; charset=utf-8",
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_MKCOL(self):
            if not self._begin():
                return
            target = self._path()
            if target.exists():
                self._send(405)
                return
            if not target.parent.is_dir():
                self._send(409)
                return
            target.mkdir()
            self._send(201)

        def do_PUT(self):
            if not self._begin():
                return
            target = self._path()
            if not target.parent.is_dir():
                self._send(409)
                return
            length = int(self.headers.get("Content-Length") or "0")
            payload = self.rfile.read(length)
            existed = target.exists()
            target.write_bytes(payload)
            self._send(204 if existed else 201)

        def do_GET(self):
            if not self._begin():
                return
            target = self._path()
            if not target.is_file():
                self._send(404)
                return
            self._send(200, target.read_bytes(), content_type="application/octet-stream")

        def do_PROPFIND(self):
            if not self._begin():
                return
            target = self._path()
            if not target.exists():
                self._send(404)
                return
            entries = [target]
            if target.is_dir():
                entries.extend(sorted(target.iterdir(), key=lambda path: path.name))
            responses: list[str] = []
            for entry in entries:
                relative = entry.relative_to(state.root)
                href = "/" + "/".join(quote(part, safe="") for part in relative.parts)
                if entry.is_dir():
                    href += "/"
                    resource_type = "<d:collection/>"
                    size = 0
                else:
                    resource_type = ""
                    size = entry.stat().st_size
                modified = formatdate(entry.stat().st_mtime, usegmt=True)
                responses.append(
                    "<d:response>"
                    f"<d:href>{href}</d:href>"
                    "<d:propstat><d:status>HTTP/1.1 200 OK</d:status><d:prop>"
                    f"<d:resourcetype>{resource_type}</d:resourcetype>"
                    f"<d:getcontentlength>{size}</d:getcontentlength>"
                    f"<d:getlastmodified>{modified}</d:getlastmodified>"
                    "</d:prop></d:propstat></d:response>"
                )
            body = (
                '<?xml version="1.0" encoding="utf-8"?>'
                '<d:multistatus xmlns:d="DAV:">'
                + "".join(responses)
                + "</d:multistatus>"
            ).encode("utf-8")
            self._send(207, body, content_type="application/xml; charset=utf-8")

        def do_DELETE(self):
            if not self._begin():
                return
            target = self._path()
            if not target.exists():
                self._send(404)
                return
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            self._send(204)

        def do_MOVE(self):
            if not self._begin():
                return
            if not state.move_supported:
                self._send(405)
                return
            source = self._path()
            destination_header = self.headers.get("Destination")
            if not destination_header:
                self._send(400)
                return
            destination = self._path(destination_header)
            if not source.exists():
                self._send(404)
                return
            if destination.exists() and self.headers.get("Overwrite", "T") == "F":
                self._send(412)
                return
            os.replace(source, destination)
            self._send(201)

    return Handler


class LocalDAV:
    def __init__(
        self,
        root: Path,
        *,
        username: str = "",
        password: str = "",
        move_supported: bool = True,
    ):
        self.state = _DAVState(
            root,
            username=username,
            password=password,
            move_supported=move_supported,
        )
        (root / "dav").mkdir(parents=True)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _handler_for(self.state))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}/dav"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


@pytest.fixture
def dav_factory(tmp_path):
    servers: list[LocalDAV] = []

    def create(**kwargs) -> LocalDAV:
        server = LocalDAV(tmp_path / f"server-{len(servers)}", **kwargs)
        servers.append(server)
        return server

    yield create
    for server in servers:
        server.close()


def _home() -> Path:
    return Path(os.environ["HERMES_HOME"])


def _seed_home(root: Path) -> None:
    (root / "config.yaml").write_text("model: test-model\n", encoding="utf-8")
    (root / ".env").write_text("USER_SECRET=original-secret\n", encoding="utf-8")
    (root / "notes.txt").write_text("original notes\n", encoding="utf-8")


def _settings(
    server: LocalDAV,
    *,
    username: str = "",
    password: str = "",
    retention: int = 14,
    enabled: bool = True,
) -> WebDAVSettings:
    return WebDAVSettings(
        enabled=enabled,
        url=server.url,
        remote_path="hermes-backups",
        device_name="test-device",
        schedule="0 3 * * *",
        retention=retention,
        username=username,
        password=password,
    )


def _configure(root: Path, settings: WebDAVSettings) -> None:
    _seed_home(root)
    save_webdav_settings(root, settings)


def test_real_anonymous_webdav_capability_probe(dav_factory):
    server = dav_factory()
    result = exercise_webdav_connection(_settings(server))
    assert result == {
        "ok": True,
        "authentication": "anonymous",
        "move_supported": True,
        "move_fallback": False,
    }
    assert {"MKCOL", "PUT", "GET", "PROPFIND", "DELETE", "MOVE"}.issubset(
        server.state.counts
    )


def test_basic_auth_and_move_405_upload_fallback(dav_factory):
    server = dav_factory(username="alice", password="secret", move_supported=False)
    root = _home()
    settings = _settings(server, username="alice", password="secret")
    _configure(root, settings)

    remote = upload_backup(root, settings=settings)

    assert remote is not None
    assert server.state.counts["MOVE"] >= 1
    folder = server.state.root / "dav" / "hermes-backups" / remote.device_uuid
    assert (folder / remote.archive).is_file()
    assert not list(folder.glob("*.part"))
    with zipfile.ZipFile(folder / remote.archive) as archive:
        env_text = archive.read(".env").decode("utf-8")
    assert "HERMES_WEBDAV_PASSWORD=secret" in env_text
    assert not list((root / "backups").glob("*.upload.zip"))
    assert [item.backup_id for item in list_remote_backups(settings)] == [remote.backup_id]


def test_authentication_failure_is_not_retried(dav_factory):
    server = dav_factory(username="alice", password="correct")
    wrong = _settings(server, username="alice", password="wrong")
    with pytest.raises(WebDAVError, match="HTTP 401"):
        exercise_webdav_connection(wrong)
    assert server.state.counts["MKCOL"] == 1


def test_transient_5xx_is_retried_three_attempts(dav_factory):
    server = dav_factory()
    server.state.failures["PUT"] = 2
    result = exercise_webdav_connection(_settings(server))
    assert result["ok"] is True
    assert server.state.counts["PUT"] == 3


def test_manifest_completion_cross_device_retention_and_orphan_ignored(dav_factory):
    server = dav_factory()
    root = _home()
    settings = _settings(server, retention=1)
    _configure(root, settings)

    first = upload_backup(root, settings=settings)
    second = upload_backup(root, settings=settings)
    assert first is not None and second is not None
    assert [item.backup_id for item in list_remote_backups(settings)] == [second.backup_id]

    state = load_webdav_state(root)
    second_device = str(uuid.uuid4())
    state["device_uuid"] = second_device
    save_webdav_state(root, state)
    third = upload_backup(root, settings=settings)
    assert third is not None

    remote = list_remote_backups(settings)
    assert {item.device_uuid for item in remote} == {second.device_uuid, second_device}
    second_folder = server.state.root / "dav" / "hermes-backups" / second_device
    (second_folder / "orphan.zip").write_bytes(b"not complete")
    assert {item.backup_id for item in list_remote_backups(settings)} == {
        second.backup_id,
        third.backup_id,
    }


def test_restore_rejects_checksum_mismatch_before_local_changes(dav_factory):
    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)
    remote = upload_backup(root, settings=settings)
    assert remote is not None
    archive = server.state.root / "dav" / Path(*remote.archive_path)
    archive.write_bytes(archive.read_bytes() + b"tampered")
    (root / "notes.txt").write_text("keep current\n", encoding="utf-8")

    with pytest.raises(WebDAVError, match="size mismatch"):
        restore_backup(remote.backup_id, root=root, settings=settings, confirmed=True)

    assert (root / "notes.txt").read_text(encoding="utf-8") == "keep current\n"
    assert not list((root / "backups").glob("rollback-*.zip"))


def test_restore_rejects_malicious_zip_path(dav_factory):
    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)
    state = load_webdav_state(root)
    device_uuid = state["device_uuid"]
    folder = server.state.root / "dav" / "hermes-backups" / device_uuid
    folder.mkdir(parents=True)
    backup_id = "20260728T030000Z-abcdef12"
    archive_name = f"{backup_id}.zip"
    archive_path = folder / archive_name
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("config.yaml", "model: safe\n")
        archive.writestr("../outside.txt", "blocked")
    manifest = {
        "schema": 1,
        "backup_id": backup_id,
        "archive": archive_name,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "device_uuid": device_uuid,
        "device_name": "malicious-source",
        "hermes_version": "1.0.0",
        "size": archive_path.stat().st_size,
        "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
    }
    (folder / f"{backup_id}.manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    with pytest.raises(WebDAVError, match="unsafe path"):
        restore_backup(backup_id, root=root, settings=settings, confirmed=True)
    assert not (_home().parent / "outside.txt").exists()


def test_restore_preserves_target_credentials_device_id_and_single_cron(dav_factory):
    server = dav_factory(username="alice", password="old-password")
    root = _home()
    old = _settings(server, username="alice", password="old-password")
    _configure(root, old)
    ensure_webdav_cron(root)
    original_state = load_webdav_state(root)
    original_job_id = original_state["cron_job_id"]
    remote = upload_backup(root, settings=old)
    assert remote is not None

    server.state.password = "new-password"
    current = _settings(server, username="alice", password="new-password")
    save_webdav_settings(root, current)
    (root / "notes.txt").write_text("changed after upload\n", encoding="utf-8")
    result = restore_backup(remote.backup_id, root=root, settings=current, confirmed=True)

    assert result["ok"] is True
    assert (root / "notes.txt").read_text(encoding="utf-8") == "original notes\n"
    restored_settings = load_webdav_settings(root)
    assert restored_settings.password == "new-password"
    restored_state = load_webdav_state(root)
    assert restored_state["device_uuid"] == original_state["device_uuid"]
    assert restored_state["cron_job_id"] == original_job_id

    from cron.jobs import load_jobs, use_cron_store

    with use_cron_store(root):
        managed = [
            job for job in load_jobs() if job.get("managed_by") == MANAGED_CRON_MARKER
        ]
    assert len(managed) == 1
    assert managed[0]["id"] == original_job_id
    assert managed[0]["no_agent"] is True


def test_cron_configuration_is_idempotent_and_success_is_silent(dav_factory, capsys):
    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)
    first = ensure_webdav_cron(root)
    second = ensure_webdav_cron(root)
    assert first is not None and second is not None
    assert first["id"] == second["id"]

    from cron.jobs import load_jobs, use_cron_store

    with use_cron_store(root):
        managed = [
            job for job in load_jobs() if job.get("managed_by") == MANAGED_CRON_MARKER
        ]
        assert len(managed) == 1
        assert managed[0]["no_agent"] is True
        assert managed[0]["deliver"] == "origin"

    capsys.readouterr()
    assert cron_main() == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_interrupted_manifest_upload_is_not_listed_and_temp_zip_is_removed(dav_factory):
    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)
    server.state.path_failures[("PUT", ".manifest.json")] = 3

    with pytest.raises(WebDAVError, match="HTTP 503"):
        upload_backup(root, settings=settings)
    assert server.state.path_failures[("PUT", ".manifest.json")] == 0

    device_uuid = load_webdav_state(root)["device_uuid"]
    folder = server.state.root / "dav" / "hermes-backups" / device_uuid
    assert list(folder.glob("*.zip"))
    assert not list(folder.glob("*.manifest.json"))
    assert list_remote_backups(settings) == []
    assert not list((root / "backups").glob("*.upload.zip"))
    assert load_webdav_state(root)["last_result"]["success"] is False


def test_cleanup_removes_only_expired_part_files_for_current_device(dav_factory):
    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)
    first = upload_backup(root, settings=settings)
    assert first is not None
    folder = server.state.root / "dav" / Path(*first.archive_path).parent
    old_part = folder / "old.zip.part"
    recent_part = folder / "recent.zip.part"
    old_part.write_bytes(b"old")
    recent_part.write_bytes(b"recent")
    old_timestamp = time.time() - timedelta(hours=25).total_seconds()
    os.utime(old_part, (old_timestamp, old_timestamp))

    assert upload_backup(root, settings=settings) is not None

    assert not old_part.exists()
    assert recent_part.exists()


def test_restore_rejects_same_size_sha256_mismatch_before_rollback(dav_factory):
    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)
    remote = upload_backup(root, settings=settings)
    assert remote is not None
    archive = server.state.root / "dav" / Path(*remote.archive_path)
    payload = bytearray(archive.read_bytes())
    payload[len(payload) // 2] ^= 0x01
    archive.write_bytes(payload)
    (root / "notes.txt").write_text("keep current\n", encoding="utf-8")

    with pytest.raises(WebDAVError, match="SHA-256 mismatch"):
        restore_backup(remote.backup_id, root=root, settings=settings, confirmed=True)

    assert (root / "notes.txt").read_text(encoding="utf-8") == "keep current\n"
    assert not list((root / "backups").glob("rollback-*.zip"))


def test_restore_rejects_corrupt_zip_after_manifest_integrity_checks(dav_factory):
    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)
    remote = upload_backup(root, settings=settings)
    assert remote is not None
    archive = server.state.root / "dav" / Path(*remote.archive_path)
    manifest_path = server.state.root / "dav" / Path(*remote.manifest_path)
    corrupt = b"not-a-zip" * 32
    archive.write_bytes(corrupt)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["size"] = len(corrupt)
    manifest["sha256"] = hashlib.sha256(corrupt).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (root / "notes.txt").write_text("keep current\n", encoding="utf-8")

    with pytest.raises(WebDAVError, match="backup ZIP is invalid"):
        restore_backup(remote.backup_id, root=root, settings=settings, confirmed=True)

    assert (root / "notes.txt").read_text(encoding="utf-8") == "keep current\n"
    assert not list((root / "backups").glob("rollback-*.zip"))


def test_restore_rejects_backup_from_newer_same_product_version(dav_factory):
    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)
    remote = upload_backup(root, settings=settings)
    assert remote is not None
    manifest_path = server.state.root / "dav" / Path(*remote.manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["hermes_version"] = "Louis-99.0.0"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(WebDAVError, match="newer Hermes version"):
        restore_backup(remote.backup_id, root=root, settings=settings, confirmed=True)

    assert not list((root / "backups").glob("rollback-*.zip"))


def test_scheduled_failure_records_state_and_emits_alert_output(dav_factory, capsys):
    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)
    server.state.failures["PUT"] = 3

    assert cron_main() == 1

    captured = capsys.readouterr()
    assert "automatic backup failed" in captured.out
    state = load_webdav_state(root)
    assert state["last_result"]["operation"] == "upload"
    assert state["last_result"]["success"] is False
    assert not list((root / "backups").glob("*.upload.zip"))


def test_scheduled_lock_contention_is_silent_but_manual_upload_reports_busy(dav_factory, capsys):
    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)

    with BackupLock(root):
        assert upload_backup(root, settings=settings, scheduled=True) is None
        with pytest.raises(BackupBusyError):
            upload_backup(root, settings=settings, scheduled=False)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_profile_scoped_configuration_reuses_one_base_cron_job(
    dav_factory, monkeypatch
):
    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)
    profile_a = root / "profiles" / "alpha"
    profile_b = root / "profiles" / "beta"
    profile_a.mkdir(parents=True)
    profile_b.mkdir(parents=True)

    monkeypatch.setenv("HERMES_HOME", str(profile_a))
    first = ensure_webdav_cron()
    monkeypatch.setenv("HERMES_HOME", str(profile_b))
    second = ensure_webdav_cron()

    assert first is not None and second is not None
    assert first["id"] == second["id"]
    from cron.jobs import load_jobs, use_cron_store

    with use_cron_store(root):
        managed = [
            job for job in load_jobs() if job.get("managed_by") == MANAGED_CRON_MARKER
        ]
    assert len(managed) == 1


def test_manager_configuration_failure_restores_config_credentials_cron_and_state(
    dav_factory, monkeypatch
):
    import hermes_cli.louis_manager as manager

    server = dav_factory(username="alice", password="old-password")
    root = _home()
    old = _settings(server, username="alice", password="old-password")
    _configure(root, old)
    applied = apply_webdav_settings(root, old)
    assert applied["cron"] is not None
    state_before = (root / "backups" / "webdav-state.json").read_bytes()

    answers = iter(
        [
            "https://new.example/dav",
            "new-backups",
            "new-device",
            "15 4 * * *",
            "7",
            "bob",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr(manager, "_select", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(manager.getpass, "getpass", lambda _prompt="": "new-password")
    monkeypatch.setattr(
        webdav_backup,
        "test_webdav_connection",
        lambda _settings: {"ok": True, "move_supported": True},
    )

    def fail_cron(_root=None):
        raise WebDAVError("simulated Cron failure")

    monkeypatch.setattr(webdav_backup, "ensure_webdav_cron", fail_cron)

    assert manager._configure_webdav_interactive() is False
    restored = load_webdav_settings(root)
    assert restored.url == old.url
    assert restored.username == "alice"
    assert restored.password == "old-password"
    assert (root / "backups" / "webdav-state.json").read_bytes() == state_before

    from cron.jobs import load_jobs, use_cron_store

    with use_cron_store(root):
        managed = [
            job for job in load_jobs() if job.get("managed_by") == MANAGED_CRON_MARKER
        ]
    assert len(managed) == 1
    assert managed[0]["id"] == applied["cron"]["id"]


def test_import_failure_rolls_back_and_restores_gateway_state(dav_factory, monkeypatch):
    import hermes_cli.backup as backup_module

    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)
    remote = upload_backup(root, settings=settings)
    assert remote is not None
    original_state = load_webdav_state(root)
    (root / "notes.txt").write_text("target before restore\n", encoding="utf-8")

    original_import = backup_module.run_import
    calls = 0

    def fail_first_import(args):
        nonlocal calls
        calls += 1
        if calls == 1:
            (root / "notes.txt").write_text("partial restore\n", encoding="utf-8")
            return False
        return original_import(args)

    gateway_actions: list[str] = []
    monkeypatch.setattr(backup_module, "run_import", fail_first_import)
    monkeypatch.setattr(webdav_backup, "_gateway_running", lambda _root: True)
    monkeypatch.setattr(
        webdav_backup,
        "_gateway_command",
        lambda _root, action: gateway_actions.append(action),
    )

    with pytest.raises(WebDAVError, match="rolled back automatically"):
        restore_backup(remote.backup_id, root=root, settings=settings, confirmed=True)

    assert calls == 2
    assert gateway_actions == ["stop", "start"]
    assert (root / "notes.txt").read_text(encoding="utf-8") == "target before restore\n"
    assert load_webdav_state(root)["device_uuid"] == original_state["device_uuid"]
    assert list((root / "backups").glob("rollback-*.zip"))
    assert not list((root / "backups").glob(".*.restore.zip"))


def test_rollback_failure_keeps_gateway_stopped_and_preserves_diagnostics(
    dav_factory, monkeypatch
):
    import hermes_cli.backup as backup_module

    server = dav_factory()
    root = _home()
    settings = _settings(server)
    _configure(root, settings)
    remote = upload_backup(root, settings=settings)
    assert remote is not None
    gateway_actions: list[str] = []
    monkeypatch.setattr(backup_module, "run_import", lambda _args: False)
    monkeypatch.setattr(webdav_backup, "_gateway_running", lambda _root: True)
    monkeypatch.setattr(
        webdav_backup,
        "_gateway_command",
        lambda _root, action: gateway_actions.append(action),
    )

    with pytest.raises(WebDAVError, match="Gateway remains stopped"):
        restore_backup(remote.backup_id, root=root, settings=settings, confirmed=True)

    assert gateway_actions == ["stop"]
    backups_dir = root / "backups"
    diagnostics = list(backups_dir.glob("restore-failure-*.json"))
    downloads = list(backups_dir.glob(".*.restore.zip"))
    rollbacks = list(backups_dir.glob("rollback-*.zip"))
    assert len(diagnostics) == 1
    assert len(downloads) == 1
    assert len(rollbacks) == 1
    diagnostic = json.loads(diagnostics[0].read_text(encoding="utf-8"))
    assert Path(diagnostic["download_zip"]).is_file()
    assert Path(diagnostic["rollback_zip"]).is_file()
    assert load_webdav_state(root)["restore_diagnostic"]["backup_id"] == remote.backup_id
