"""WebDAV transport and restore orchestration for full Hermes backups.

The remote format is intentionally simple: an unmodified full-backup ZIP and
a small JSON manifest.  The manifest is uploaded last and is the completion
marker, so interrupted uploads never appear as restorable backups.
"""

from __future__ import annotations

import contextlib
import copy
import email.utils
import hashlib
import io
import json
import logging
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any, Callable, Iterator, Optional
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

import httpx

from hermes_constants import (
    get_default_hermes_root,
    reset_hermes_home_override,
    set_hermes_home_override,
)

logger = logging.getLogger(__name__)

WEBDAV_USERNAME_ENV = "HERMES_WEBDAV_USERNAME"
WEBDAV_PASSWORD_ENV = "HERMES_WEBDAV_PASSWORD"
MANIFEST_SCHEMA = 1
MANAGED_CRON_MARKER = "hermes.backup.webdav"
MANAGED_CRON_NAME = "Hermes WebDAV backup"
MANAGED_SCRIPT_NAME = "hermes-webdav-backup.py"
DEFAULT_REMOTE_PATH = "hermes-backups"
DEFAULT_SCHEDULE = "0 3 * * *"
DEFAULT_RETENTION = 14
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
MAX_HTTP_ATTEMPTS = 3
PART_MAX_AGE = timedelta(hours=24)
_BACKUP_ID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,99}$")
_COMPARABLE_VERSION_RE = re.compile(
    r"^(?P<prefix>.*?)(?P<numeric>\d+(?:\.\d+){1,3})(?:[-+._].*)?$"
)


class WebDAVError(RuntimeError):
    """A user-actionable WebDAV backup error."""


class BackupBusyError(WebDAVError):
    """Another upload or restore owns the cross-process lock."""


@dataclass(frozen=True)
class WebDAVSettings:
    enabled: bool
    url: str
    remote_path: str
    device_name: str
    schedule: str
    retention: int
    username: str = ""
    password: str = ""

    @property
    def anonymous(self) -> bool:
        return not self.username and not self.password

    @property
    def remote_segments(self) -> tuple[str, ...]:
        return _validate_relative_path(self.remote_path, label="remote_path")

    def validate(self, *, require_url: bool = True) -> None:
        if require_url or self.url:
            _validate_base_url(self.url)
        self.remote_segments
        if bool(self.username) != bool(self.password):
            raise WebDAVError(
                f"{WEBDAV_USERNAME_ENV} and {WEBDAV_PASSWORD_ENV} must both be set, "
                "or both be empty for anonymous WebDAV."
            )
        if not self.device_name.strip():
            raise WebDAVError("backup.webdav.device_name cannot be empty")
        if len(self.device_name) > 120:
            raise WebDAVError("backup.webdav.device_name must be 120 characters or fewer")
        if not self.schedule.strip():
            raise WebDAVError("backup.webdav.schedule cannot be empty")
        if not 1 <= self.retention <= 10000:
            raise WebDAVError("backup.webdav.retention must be between 1 and 10000")


@dataclass(frozen=True)
class DAVEntry:
    href: str
    name: str
    is_collection: bool
    size: Optional[int]
    modified_at: Optional[datetime]


@dataclass(frozen=True)
class DAVResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    url: str


@dataclass(frozen=True)
class RemoteBackup:
    backup_id: str
    archive: str
    created_at: str
    device_uuid: str
    device_name: str
    hermes_version: str
    size: int
    sha256: str
    manifest_path: tuple[str, ...]
    archive_path: tuple[str, ...]

    def public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("manifest_path", None)
        data.pop("archive_path", None)
        return data


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso(value: Optional[datetime] = None) -> str:
    return (value or _utc_now()).isoformat().replace("+00:00", "Z")


def _validate_relative_path(value: str, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise WebDAVError(f"{label} must be a string")
    raw = value.strip().strip("/")
    if not raw:
        raise WebDAVError(f"{label} cannot be empty")
    segments: list[str] = []
    for encoded in raw.split("/"):
        segment = unquote(encoded).strip()
        if not segment or segment in {".", ".."}:
            raise WebDAVError(f"{label} contains an unsafe path segment")
        if "/" in segment or "\\" in segment or "\x00" in segment:
            raise WebDAVError(f"{label} contains an unsafe path segment")
        segments.append(segment)
    return tuple(segments)


def _origin(parts) -> tuple[str, str, int]:
    default_port = 443 if parts.scheme.lower() == "https" else 80
    return (parts.scheme.lower(), (parts.hostname or "").lower(), parts.port or default_port)


def _validate_base_url(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise WebDAVError("backup.webdav.url is not configured")
    try:
        parsed = urlsplit(raw)
        parsed_port = parsed.port
    except ValueError as exc:
        raise WebDAVError(f"Invalid WebDAV URL: {exc}") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise WebDAVError("WebDAV URL must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise WebDAVError("WebDAV URL must not contain embedded credentials")
    if parsed.query or parsed.fragment:
        raise WebDAVError("WebDAV URL must not contain a query string or fragment")
    if parsed_port is not None and not 1 <= parsed_port <= 65535:
        raise WebDAVError("WebDAV URL contains an invalid port")
    path_segments: list[str] = []
    for encoded in parsed.path.split("/"):
        if not encoded:
            continue
        segment = unquote(encoded)
        if segment in {".", ".."} or "/" in segment or "\\" in segment or "\x00" in segment:
            raise WebDAVError("WebDAV URL contains an unsafe path segment")
        path_segments.append(segment)
    encoded_path = "/" + "/".join(quote(segment, safe="") for segment in path_segments)
    if not encoded_path.endswith("/"):
        encoded_path += "/"
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host
    if parsed.port is not None:
        netloc += f":{parsed.port}"
    return urlunsplit((parsed.scheme.lower(), netloc, encoded_path, "", ""))


@contextlib.contextmanager
def _base_home_scope(root: Path) -> Iterator[None]:
    token = set_hermes_home_override(root)
    try:
        yield
    finally:
        reset_hermes_home_override(token)


def load_webdav_settings(
    root: Optional[Path] = None, *, require_url: bool = True
) -> WebDAVSettings:
    root = (root or get_default_hermes_root()).expanduser().resolve()
    with _base_home_scope(root):
        from hermes_cli.config import load_env, read_raw_config

        raw = read_raw_config()
        backup = raw.get("backup") if isinstance(raw, dict) else None
        section = backup.get("webdav") if isinstance(backup, dict) else None
        section = section if isinstance(section, dict) else {}
        env = load_env()

    device_name = str(section.get("device_name") or socket.gethostname() or "Hermes device")
    try:
        retention = int(section.get("retention", DEFAULT_RETENTION))
    except (TypeError, ValueError) as exc:
        raise WebDAVError("backup.webdav.retention must be an integer") from exc
    enabled_value = section.get("enabled", False)
    if isinstance(enabled_value, str):
        enabled = enabled_value.strip().lower() in {"1", "true", "yes", "on"}
    else:
        enabled = bool(enabled_value)
    settings = WebDAVSettings(
        enabled=enabled,
        url=str(section.get("url") or "").strip(),
        remote_path=str(section.get("remote_path") or DEFAULT_REMOTE_PATH).strip(),
        device_name=device_name.strip(),
        schedule=str(section.get("schedule") or DEFAULT_SCHEDULE).strip(),
        retention=retention,
        username=str(env.get(WEBDAV_USERNAME_ENV) or ""),
        password=str(env.get(WEBDAV_PASSWORD_ENV) or ""),
    )
    settings.validate(require_url=require_url)
    return settings


def save_webdav_settings(root: Path, settings: WebDAVSettings) -> None:
    """Persist validated settings and credentials in the base Hermes home."""
    settings.validate(require_url=True)
    root = root.expanduser().resolve()
    with _base_home_scope(root):
        from hermes_cli.config import read_raw_config, save_config, save_env_value

        raw = read_raw_config()
        raw = copy.deepcopy(raw) if isinstance(raw, dict) else {}
        backup = raw.setdefault("backup", {})
        if not isinstance(backup, dict):
            backup = {}
            raw["backup"] = backup
        backup["webdav"] = {
            "enabled": settings.enabled,
            "url": _validate_base_url(settings.url).rstrip("/"),
            "remote_path": "/".join(settings.remote_segments),
            "device_name": settings.device_name.strip(),
            "schedule": settings.schedule.strip(),
            "retention": settings.retention,
        }
        save_config(raw, strip_defaults=False)
        save_env_value(WEBDAV_USERNAME_ENV, settings.username)
        save_env_value(WEBDAV_PASSWORD_ENV, settings.password)


def _state_path(root: Path) -> Path:
    return root / "backups" / "webdav-state.json"


def _default_state() -> dict[str, Any]:
    return {
        "schema": 1,
        "device_uuid": str(uuid.uuid4()),
        "cron_job_id": None,
        "last_result": None,
        "last_remote_backup_id": None,
    }


def load_webdav_state(root: Path, *, create: bool = True) -> dict[str, Any]:
    path = _state_path(root)
    state: dict[str, Any]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        state = payload if isinstance(payload, dict) else {}
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        state = {}
    try:
        device_uuid = str(uuid.UUID(str(state.get("device_uuid") or "")))
    except (ValueError, AttributeError):
        device_uuid = str(uuid.uuid4())
    state = {**_default_state(), **state, "schema": 1, "device_uuid": device_uuid}
    if create and not path.exists():
        save_webdav_state(root, state)
    return state


def save_webdav_state(root: Path, state: dict[str, Any]) -> None:
    path = _state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".webdav-state-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


class BackupLock:
    def __init__(self, root: Path):
        self.path = root / "backups" / "webdav.lock"
        self.handle = None

    def __enter__(self) -> "BackupLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = open(self.path, "a+b")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                if self.path.stat().st_size == 0:
                    self.handle.write(b"0")
                    self.handle.flush()
                    self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            self.handle.close()
            self.handle = None
            raise BackupBusyError("another WebDAV backup or restore is already running") from exc
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


class WebDAVClient:
    """Small synchronous WebDAV client with bounded retries and redirects."""

    def __init__(self, settings: WebDAVSettings):
        settings.validate(require_url=True)
        self.settings = settings
        self.base_url = _validate_base_url(settings.url)
        self.base_origin = _origin(urlsplit(self.base_url))
        auth = None if settings.anonymous else httpx.BasicAuth(settings.username, settings.password)
        self.client = httpx.Client(
            auth=auth,
            timeout=httpx.Timeout(connect=15.0, read=120.0, write=120.0, pool=15.0),
            follow_redirects=False,
            headers={"User-Agent": "Hermes-WebDAV-Backup/1"},
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "WebDAVClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def url_for(self, path: tuple[str, ...] = ()) -> str:
        encoded = "/".join(quote(segment, safe="") for segment in path)
        return self.base_url + encoded

    def _same_origin_redirect(self, current_url: str, location: str) -> str:
        target = urljoin(current_url, location)
        parsed = urlsplit(target)
        if parsed.username is not None or parsed.password is not None:
            raise WebDAVError("WebDAV redirect attempted to inject credentials")
        if _origin(parsed) != self.base_origin:
            raise WebDAVError("WebDAV cross-origin redirect was blocked")
        return target

    def request(
        self,
        method: str,
        path: tuple[str, ...] = (),
        *,
        headers: Optional[dict[str, str]] = None,
        content: Optional[bytes] = None,
        file_path: Optional[Path] = None,
        max_body: int = MAX_RESPONSE_BYTES,
    ) -> DAVResponse:
        last_error: Optional[BaseException] = None
        for attempt in range(MAX_HTTP_ATTEMPTS):
            current_url = self.url_for(path)
            redirects = 0
            try:
                while True:
                    handle = open(file_path, "rb") if file_path is not None else None
                    try:
                        request_content = handle if handle is not None else content
                        with self.client.stream(
                            method,
                            current_url,
                            headers=headers,
                            content=request_content,
                        ) as response:
                            body_parts: list[bytes] = []
                            body_size = 0
                            for chunk in response.iter_bytes():
                                body_size += len(chunk)
                                if body_size > max_body:
                                    raise WebDAVError(
                                        f"WebDAV {method} response exceeded {max_body} bytes"
                                    )
                                body_parts.append(chunk)
                            result = DAVResponse(
                                status_code=response.status_code,
                                headers=dict(response.headers),
                                body=b"".join(body_parts),
                                url=str(response.url),
                            )
                    finally:
                        if handle is not None:
                            handle.close()

                    if result.status_code in {301, 302, 303, 307, 308}:
                        location = result.headers.get("location")
                        if not location:
                            return result
                        redirects += 1
                        if redirects > 3:
                            raise WebDAVError("WebDAV returned too many redirects")
                        current_url = self._same_origin_redirect(current_url, location)
                        continue
                    if result.status_code >= 500 and attempt + 1 < MAX_HTTP_ATTEMPTS:
                        last_error = WebDAVError(
                            f"WebDAV {method} returned HTTP {result.status_code}"
                        )
                        break
                    return result
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
            if attempt + 1 < MAX_HTTP_ATTEMPTS:
                time.sleep(0.2 * (2**attempt))
        raise WebDAVError(f"WebDAV {method} failed after {MAX_HTTP_ATTEMPTS} attempts: {last_error}")

    @staticmethod
    def _require(response: DAVResponse, allowed: set[int], operation: str) -> DAVResponse:
        if response.status_code not in allowed:
            detail = response.body.decode("utf-8", errors="replace").strip()[:300]
            suffix = f": {detail}" if detail else ""
            raise WebDAVError(
                f"WebDAV {operation} failed with HTTP {response.status_code}{suffix}"
            )
        return response

    def ensure_collection(self, path: tuple[str, ...]) -> None:
        current: tuple[str, ...] = ()
        for segment in path:
            current += (segment,)
            response = self.request("MKCOL", current)
            self._require(response, {200, 201, 204, 301, 405}, "MKCOL")

    def put_file(self, path: tuple[str, ...], source: Path) -> None:
        response = self.request(
            "PUT", path, file_path=source, max_body=MAX_RESPONSE_BYTES
        )
        self._require(response, {200, 201, 204}, "PUT")

    def put_bytes(self, path: tuple[str, ...], content: bytes, content_type: str) -> None:
        response = self.request(
            "PUT",
            path,
            headers={"Content-Type": content_type},
            content=content,
            max_body=MAX_RESPONSE_BYTES,
        )
        self._require(response, {200, 201, 204}, "PUT")

    def get_bytes(self, path: tuple[str, ...], *, max_bytes: int) -> bytes:
        response = self.request("GET", path, max_body=max_bytes)
        self._require(response, {200}, "GET")
        return response.body

    def download(self, path: tuple[str, ...], destination: Path) -> None:
        last_error: Optional[BaseException] = None
        for attempt in range(MAX_HTTP_ATTEMPTS):
            current_url = self.url_for(path)
            redirects = 0
            try:
                while True:
                    with self.client.stream("GET", current_url) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location:
                                raise WebDAVError("WebDAV redirect did not include Location")
                            redirects += 1
                            if redirects > 3:
                                raise WebDAVError("WebDAV returned too many redirects")
                            current_url = self._same_origin_redirect(current_url, location)
                            continue
                        if response.status_code >= 500 and attempt + 1 < MAX_HTTP_ATTEMPTS:
                            last_error = WebDAVError(
                                f"WebDAV GET returned HTTP {response.status_code}"
                            )
                            break
                        if response.status_code != 200:
                            body = response.read()[:300].decode("utf-8", errors="replace")
                            raise WebDAVError(
                                f"WebDAV GET failed with HTTP {response.status_code}: {body}"
                            )
                        with open(destination, "wb") as handle:
                            for chunk in response.iter_bytes(1024 * 1024):
                                handle.write(chunk)
                            handle.flush()
                            os.fsync(handle.fileno())
                        return
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
            if attempt + 1 < MAX_HTTP_ATTEMPTS:
                time.sleep(0.2 * (2**attempt))
        raise WebDAVError(f"WebDAV GET failed after {MAX_HTTP_ATTEMPTS} attempts: {last_error}")

    def delete(self, path: tuple[str, ...]) -> None:
        response = self.request("DELETE", path)
        self._require(response, {200, 202, 204, 404}, "DELETE")

    def move(self, source: tuple[str, ...], destination: tuple[str, ...]) -> bool:
        response = self.request(
            "MOVE",
            source,
            headers={"Destination": self.url_for(destination), "Overwrite": "F"},
        )
        if response.status_code in {405, 501}:
            return False
        self._require(response, {200, 201, 204}, "MOVE")
        return True

    def propfind(self, path: tuple[str, ...], *, allow_missing: bool = False) -> list[DAVEntry]:
        body = b"""<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/><d:getcontentlength/>
<d:getlastmodified/></d:prop></d:propfind>"""
        response = self.request(
            "PROPFIND",
            path,
            headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
            content=body,
            max_body=MAX_RESPONSE_BYTES,
        )
        if allow_missing and response.status_code == 404:
            return []
        self._require(response, {207}, "PROPFIND")
        return _parse_propfind(response.body)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element, name: str) -> Optional[str]:
    for child in element.iter():
        if _local_name(child.tag) == name and child.text:
            return child.text.strip()
    return None


def _parse_propfind(payload: bytes) -> list[DAVEntry]:
    try:
        # ElementTree does not fetch external entities, and the response is
        # already capped at 2 MiB. Reject declarations as defense-in-depth
        # against internal entity expansion without adding an optional dep.
        lowered = payload.lower()
        if b"<!doctype" in lowered or b"<!entity" in lowered:
            raise ValueError("DTD/entity declarations are not allowed")
        from xml.etree import ElementTree as ET

        root = ET.fromstring(payload)
    except Exception as exc:
        raise WebDAVError(f"WebDAV returned invalid PROPFIND XML: {exc}") from exc
    entries: list[DAVEntry] = []
    for response in root.iter():
        if _local_name(response.tag) != "response":
            continue
        href = _child_text(response, "href")
        if not href:
            continue
        path = unquote(urlsplit(href).path).rstrip("/")
        name = path.rsplit("/", 1)[-1] if path else ""
        is_collection = any(_local_name(node.tag) == "collection" for node in response.iter())
        size_text = _child_text(response, "getcontentlength")
        try:
            size = int(size_text) if size_text is not None else None
        except ValueError:
            size = None
        modified_text = _child_text(response, "getlastmodified")
        modified_at = None
        if modified_text:
            try:
                modified_at = email.utils.parsedate_to_datetime(modified_text)
                if modified_at.tzinfo is None:
                    modified_at = modified_at.replace(tzinfo=timezone.utc)
                else:
                    modified_at = modified_at.astimezone(timezone.utc)
            except (TypeError, ValueError, OverflowError):
                modified_at = None
        entries.append(
            DAVEntry(
                href=href,
                name=name,
                is_collection=is_collection,
                size=size,
                modified_at=modified_at,
            )
        )
    return entries


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_to_backup(
    payload: Any, *, folder_uuid: str, names: set[str], base_path: tuple[str, ...]
) -> Optional[RemoteBackup]:
    if not isinstance(payload, dict) or payload.get("schema") != MANIFEST_SCHEMA:
        return None
    backup_id = payload.get("backup_id")
    archive = payload.get("archive")
    created_at = payload.get("created_at")
    device_uuid = payload.get("device_uuid")
    device_name = payload.get("device_name")
    hermes_version = payload.get("hermes_version")
    sha256 = payload.get("sha256")
    size = payload.get("size")
    if not isinstance(backup_id, str) or not _BACKUP_ID_RE.fullmatch(backup_id):
        return None
    if archive != f"{backup_id}.zip" or archive not in names:
        return None
    try:
        normalized_uuid = str(uuid.UUID(str(device_uuid)))
    except (ValueError, AttributeError):
        return None
    if normalized_uuid != folder_uuid:
        return None
    if not isinstance(device_name, str) or not device_name or len(device_name) > 120:
        return None
    if not isinstance(hermes_version, str) or not _VERSION_RE.fullmatch(hermes_version):
        return None
    if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
        return None
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        return None
    if not isinstance(created_at, str):
        return None
    try:
        parsed_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if parsed_time.tzinfo is None:
            return None
    except ValueError:
        return None
    return RemoteBackup(
        backup_id=backup_id,
        archive=archive,
        created_at=created_at,
        device_uuid=normalized_uuid,
        device_name=device_name,
        hermes_version=hermes_version,
        size=size,
        sha256=sha256,
        manifest_path=base_path + (f"{backup_id}.manifest.json",),
        archive_path=base_path + (archive,),
    )


def _validate_restore_version(source_version: str) -> None:
    """Reject malformed or known-newer backups before touching local data."""
    if not _VERSION_RE.fullmatch(source_version):
        raise WebDAVError("backup manifest contains an invalid Hermes version")
    from hermes_cli import __version__

    source_match = _COMPARABLE_VERSION_RE.fullmatch(source_version)
    current_match = _COMPARABLE_VERSION_RE.fullmatch(__version__)
    if not source_match or not current_match:
        return
    source_prefix = source_match.group("prefix").rstrip("-+._").lower()
    current_prefix = current_match.group("prefix").rstrip("-+._").lower()
    if source_prefix != current_prefix:
        return
    source_numbers = tuple(int(part) for part in source_match.group("numeric").split("."))
    current_numbers = tuple(int(part) for part in current_match.group("numeric").split("."))
    width = max(len(source_numbers), len(current_numbers))
    source_numbers += (0,) * (width - len(source_numbers))
    current_numbers += (0,) * (width - len(current_numbers))
    if source_numbers > current_numbers:
        raise WebDAVError(
            f"backup was created by newer Hermes version {source_version}; "
            f"update this device from {__version__} before restoring"
        )


def list_remote_backups(
    settings: WebDAVSettings, *, device_uuid: Optional[str] = None
) -> list[RemoteBackup]:
    settings.validate(require_url=True)
    with WebDAVClient(settings) as client:
        root_entries = client.propfind(settings.remote_segments, allow_missing=True)
        device_ids: list[str] = []
        for entry in root_entries:
            if not entry.is_collection or not entry.name:
                continue
            try:
                normalized = str(uuid.UUID(entry.name))
            except ValueError:
                continue
            if device_uuid is None or normalized == device_uuid:
                device_ids.append(normalized)
        results: list[RemoteBackup] = []
        for remote_device in sorted(set(device_ids)):
            folder = settings.remote_segments + (remote_device,)
            entries = client.propfind(folder, allow_missing=True)
            names = {entry.name for entry in entries if entry.name and not entry.is_collection}
            for name in sorted(names):
                if not name.endswith(".manifest.json"):
                    continue
                try:
                    raw = client.get_bytes(folder + (name,), max_bytes=MAX_MANIFEST_BYTES)
                    payload = json.loads(raw.decode("utf-8"))
                except (WebDAVError, UnicodeDecodeError, json.JSONDecodeError):
                    continue
                backup = _manifest_to_backup(
                    payload,
                    folder_uuid=remote_device,
                    names=names,
                    base_path=folder,
                )
                if backup is not None:
                    results.append(backup)
        return sorted(results, key=lambda item: (item.created_at, item.backup_id), reverse=True)


def test_webdav_connection(settings: WebDAVSettings) -> dict[str, Any]:
    """Exercise the exact WebDAV methods required by backup and restore."""
    settings.validate(require_url=True)
    marker = f"hermes-test-{uuid.uuid4().hex[:12]}"
    test_dir = settings.remote_segments + (marker,)
    source = test_dir + ("probe.txt",)
    moved = test_dir + ("probe-moved.txt",)
    payload = os.urandom(48)
    move_supported = False
    with WebDAVClient(settings) as client:
        client.ensure_collection(settings.remote_segments)
        client.ensure_collection(test_dir)
        try:
            client.put_bytes(source, payload, "application/octet-stream")
            received = client.get_bytes(source, max_bytes=1024)
            if received != payload:
                raise WebDAVError("WebDAV GET returned data different from the uploaded probe")
            listed = {entry.name for entry in client.propfind(test_dir)}
            if "probe.txt" not in listed:
                raise WebDAVError("WebDAV PROPFIND did not list the uploaded probe")
            move_supported = client.move(source, moved)
            if move_supported:
                if client.get_bytes(moved, max_bytes=1024) != payload:
                    raise WebDAVError("WebDAV MOVE destination failed verification")
                client.delete(moved)
            else:
                client.delete(source)
        finally:
            client.delete(test_dir)
    return {
        "ok": True,
        "authentication": "anonymous" if settings.anonymous else "basic",
        "move_supported": move_supported,
        "move_fallback": not move_supported,
    }


def _record_result(
    root: Path,
    *,
    operation: str,
    success: bool,
    message: str,
    backup_id: Optional[str] = None,
) -> None:
    state = load_webdav_state(root)
    state["last_result"] = {
        "operation": operation,
        "success": success,
        "at": _utc_iso(),
        "message": message[:2000],
    }
    if success and backup_id:
        state["last_remote_backup_id"] = backup_id
    save_webdav_state(root, state)


def _cleanup_remote_device(
    client: WebDAVClient,
    settings: WebDAVSettings,
    device_uuid: str,
    completed: list[RemoteBackup],
) -> None:
    folder = settings.remote_segments + (device_uuid,)
    for old in sorted(completed, key=lambda item: (item.created_at, item.backup_id))[
        : max(0, len(completed) - settings.retention)
    ]:
        client.delete(old.archive_path)
        client.delete(old.manifest_path)
    cutoff = _utc_now() - PART_MAX_AGE
    for entry in client.propfind(folder, allow_missing=True):
        if (
            not entry.is_collection
            and entry.name.endswith(".part")
            and entry.modified_at is not None
            and entry.modified_at < cutoff
        ):
            client.delete(folder + (entry.name,))


def upload_backup(
    root: Optional[Path] = None,
    *,
    settings: Optional[WebDAVSettings] = None,
    scheduled: bool = False,
) -> Optional[RemoteBackup]:
    root = (root or get_default_hermes_root()).expanduser().resolve()
    settings = settings or load_webdav_settings(root)
    try:
        lock = BackupLock(root)
        lock.__enter__()
    except BackupBusyError:
        if scheduled:
            return None
        raise
    archive_path: Optional[Path] = None
    try:
        state = load_webdav_state(root)
        device_uuid = state["device_uuid"]
        backup_id = _utc_now().strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        backups_dir = root / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        archive_path = backups_dir / f".{backup_id}.upload.zip"
        with _base_home_scope(root):
            from hermes_cli.backup import run_backup

            if scheduled:
                with contextlib.redirect_stdout(io.StringIO()):
                    created = run_backup(
                        SimpleNamespace(output=str(archive_path), quick=False, label=None)
                    )
            else:
                created = run_backup(
                    SimpleNamespace(output=str(archive_path), quick=False, label=None)
                )
        if created is None or not archive_path.is_file():
            raise WebDAVError("full local backup was incomplete; upload was cancelled")
        archive_size = archive_path.stat().st_size
        archive_sha = _sha256_file(archive_path)
        from hermes_cli import __version__

        archive_name = f"{backup_id}.zip"
        part_name = f"{archive_name}.part"
        folder = settings.remote_segments + (device_uuid,)
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "backup_id": backup_id,
            "archive": archive_name,
            "created_at": _utc_iso(),
            "device_uuid": device_uuid,
            "device_name": settings.device_name,
            "hermes_version": __version__,
            "size": archive_size,
            "sha256": archive_sha,
        }
        manifest_bytes = (
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
            + b"\n"
        )
        with WebDAVClient(settings) as client:
            client.ensure_collection(folder)
            client.put_file(folder + (part_name,), archive_path)
            if not client.move(folder + (part_name,), folder + (archive_name,)):
                client.put_file(folder + (archive_name,), archive_path)
                client.delete(folder + (part_name,))
            client.put_bytes(
                folder + (f"{backup_id}.manifest.json",),
                manifest_bytes,
                "application/json; charset=utf-8",
            )
            completed = list_remote_backups(settings, device_uuid=device_uuid)
            _cleanup_remote_device(client, settings, device_uuid, completed)
        remote = _manifest_to_backup(
            manifest,
            folder_uuid=device_uuid,
            names={archive_name},
            base_path=folder,
        )
        if remote is None:
            raise WebDAVError("internal manifest validation failed after upload")
        _record_result(
            root,
            operation="upload",
            success=True,
            message="Backup uploaded successfully",
            backup_id=backup_id,
        )
        return remote
    except Exception as exc:
        _record_result(
            root,
            operation="upload",
            success=False,
            message=str(exc),
        )
        raise
    finally:
        if archive_path is not None:
            try:
                archive_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not remove temporary upload ZIP %s", archive_path)
        lock.__exit__(None, None, None)


def _safe_zip_members(path: Path) -> list[str]:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            members = archive.infolist()
            if not members:
                raise WebDAVError("backup ZIP is empty")
            for info in members:
                name = info.filename
                normalized = name.replace("\\", "/")
                pure = PurePosixPath(normalized)
                if (
                    not name
                    or name.startswith(("/", "\\"))
                    or pure.is_absolute()
                    or any(part in {"", ".", ".."} for part in pure.parts)
                    or (pure.parts and ":" in pure.parts[0])
                ):
                    raise WebDAVError(f"backup ZIP contains unsafe path: {name!r}")
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise WebDAVError(f"backup ZIP contains a symbolic link: {name!r}")
            corrupt = archive.testzip()
            if corrupt:
                raise WebDAVError(f"backup ZIP is corrupt at member: {corrupt}")
            from hermes_cli.backup import _validate_backup_zip

            ok, reason = _validate_backup_zip(archive)
            if not ok:
                raise WebDAVError(reason)
            return [info.filename for info in members if not info.is_dir()]
    except zipfile.BadZipFile as exc:
        raise WebDAVError(f"backup ZIP is invalid: {exc}") from exc


def _gateway_running(root: Path) -> bool:
    try:
        from gateway.status import is_gateway_running

        return is_gateway_running(root / "gateway.pid", cleanup_stale=False)
    except Exception:
        return False


def _gateway_command(root: Path, action: str) -> None:
    env = os.environ.copy()
    env["HERMES_HOME"] = str(root)
    result = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", "gateway", action],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or f"exit {result.returncode}").strip()
        raise WebDAVError(f"could not {action} Gateway: {detail}")


def _webdav_config_snapshot(root: Path) -> tuple[bool, Any, Optional[str], Optional[str]]:
    with _base_home_scope(root):
        from hermes_cli.config import load_env, read_raw_config

        raw = read_raw_config()
        backup = raw.get("backup") if isinstance(raw, dict) else None
        present = isinstance(backup, dict) and "webdav" in backup
        value = copy.deepcopy(backup.get("webdav")) if present else None
        env = load_env()
        return (
            present,
            value,
            env.get(WEBDAV_USERNAME_ENV),
            env.get(WEBDAV_PASSWORD_ENV),
        )


def _restore_webdav_config(
    root: Path,
    snapshot: tuple[bool, Any, Optional[str], Optional[str]],
) -> None:
    present, value, username, password = snapshot
    with _base_home_scope(root):
        from hermes_cli.config import (
            read_raw_config,
            remove_env_value,
            save_config,
            save_env_value,
        )

        raw = read_raw_config()
        raw = copy.deepcopy(raw) if isinstance(raw, dict) else {}
        backup = raw.get("backup")
        if not isinstance(backup, dict):
            backup = {}
            raw["backup"] = backup
        if present:
            backup["webdav"] = copy.deepcopy(value)
        else:
            backup.pop("webdav", None)
            if not backup:
                raw.pop("backup", None)
        save_config(raw, strip_defaults=False)
        if username is None:
            remove_env_value(WEBDAV_USERNAME_ENV)
        else:
            save_env_value(WEBDAV_USERNAME_ENV, username)
        if password is None:
            remove_env_value(WEBDAV_PASSWORD_ENV)
        else:
            save_env_value(WEBDAV_PASSWORD_ENV, password)


def _managed_cron_snapshot(root: Path) -> Optional[dict[str, Any]]:
    state = load_webdav_state(root, create=False)
    preferred_id = state.get("cron_job_id")
    with _base_home_scope(root):
        from cron.jobs import load_jobs, use_cron_store

        with use_cron_store(root):
            jobs = load_jobs()
    match = next(
        (
            job
            for job in jobs
            if job.get("managed_by") == MANAGED_CRON_MARKER
            or (preferred_id and job.get("id") == preferred_id)
        ),
        None,
    )
    return copy.deepcopy(match) if match is not None else None


def _restore_managed_cron(
    root: Path,
    snapshot: Optional[dict[str, Any]],
    *,
    reconcile: bool = True,
) -> None:
    """Remove source-device WebDAV jobs and put back the target job identity."""
    with _base_home_scope(root):
        from cron.jobs import load_jobs, save_jobs, use_cron_store

        with use_cron_store(root):
            jobs = load_jobs()
            snapshot_id = snapshot.get("id") if snapshot else None
            jobs = [
                job
                for job in jobs
                if job.get("managed_by") != MANAGED_CRON_MARKER
                and (not snapshot_id or job.get("id") != snapshot_id)
            ]
            if snapshot is not None:
                restored = copy.deepcopy(snapshot)
                restored["managed_by"] = MANAGED_CRON_MARKER
                jobs.append(restored)
            save_jobs(jobs)
    if reconcile:
        ensure_webdav_cron(root)


def _restore_state_bytes(root: Path, snapshot: Optional[bytes]) -> None:
    path = _state_path(root)
    if snapshot is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".webdav-state-restore-", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(snapshot)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def apply_webdav_settings(root: Path, settings: WebDAVSettings) -> dict[str, Any]:
    """Persist settings and reconcile Cron without leaving partial changes."""
    root = root.expanduser().resolve()
    config_snapshot = _webdav_config_snapshot(root)
    state_path = _state_path(root)
    state_snapshot = state_path.read_bytes() if state_path.exists() else None
    cron_snapshot = _managed_cron_snapshot(root)
    try:
        save_webdav_settings(root, settings)
        job = ensure_webdav_cron(root)
        return {"settings": settings, "cron": job}
    except Exception as apply_error:
        rollback_errors: list[str] = []
        try:
            _restore_webdav_config(root, config_snapshot)
        except Exception as exc:
            rollback_errors.append(f"config: {exc}")
        try:
            _restore_managed_cron(root, cron_snapshot, reconcile=False)
        except Exception as exc:
            rollback_errors.append(f"Cron: {exc}")
        try:
            _restore_state_bytes(root, state_snapshot)
        except Exception as exc:
            rollback_errors.append(f"state: {exc}")
        if rollback_errors:
            raise WebDAVError(
                "WebDAV settings could not be applied and rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from apply_error
        raise


def _targets_created_by_archive(root: Path, archive_path: Path) -> tuple[list[Path], list[Path]]:
    created_files: list[Path] = []
    created_dirs: list[Path] = []
    home = Path.home().resolve()
    with zipfile.ZipFile(archive_path, "r") as archive:
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("_external/"):
                target = home / name[len("_external/") :]
                boundary = home
            else:
                target = root / name
                boundary = root
            try:
                target.resolve().relative_to(boundary.resolve())
            except ValueError:
                continue
            if not target.exists():
                created_files.append(target)
                parent = target.parent
                while parent != boundary and not parent.exists():
                    created_dirs.append(parent)
                    parent = parent.parent
    return created_files, created_dirs


def _remove_created_targets(files: list[Path], dirs: list[Path]) -> None:
    for target in sorted(set(files), key=lambda item: len(item.parts), reverse=True):
        try:
            if target.is_file() or target.is_symlink():
                target.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove restore-created file %s", target)
    for target in sorted(set(dirs), key=lambda item: len(item.parts), reverse=True):
        try:
            target.rmdir()
        except OSError:
            pass


def restore_backup(
    backup_id: str,
    *,
    root: Optional[Path] = None,
    settings: Optional[WebDAVSettings] = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    root = (root or get_default_hermes_root()).expanduser().resolve()
    settings = settings or load_webdav_settings(root)
    if not _BACKUP_ID_RE.fullmatch(str(backup_id or "")):
        raise WebDAVError("invalid WebDAV backup ID")
    matches = [item for item in list_remote_backups(settings) if item.backup_id == backup_id]
    if not matches:
        raise WebDAVError(f"WebDAV backup not found: {backup_id}")
    if len(matches) > 1:
        raise WebDAVError(f"WebDAV backup ID is ambiguous across devices: {backup_id}")
    remote = matches[0]
    _validate_restore_version(remote.hermes_version)
    if not confirmed:
        answer = input(
            f"Restore {backup_id} from {remote.device_name}? Existing Hermes data will be overwritten. [y/N] "
        ).strip().lower()
        if answer not in {"y", "yes"}:
            return {"ok": False, "cancelled": True, "backup_id": backup_id}

    with BackupLock(root):
        backups_dir = root / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        fd, download_name = tempfile.mkstemp(
            prefix=f".{backup_id}.", suffix=".restore.zip", dir=backups_dir
        )
        os.close(fd)
        download_path = Path(download_name)
        rollback_path = backups_dir / (
            "rollback-" + _utc_now().strftime("%Y%m%dT%H%M%SZ") + ".zip"
        )
        rollback_failed = False
        gateway_was_running = _gateway_running(root)
        gateway_stopped = False
        webdav_snapshot = _webdav_config_snapshot(root)
        cron_snapshot = _managed_cron_snapshot(root)
        state_path = _state_path(root)
        state_bytes = state_path.read_bytes() if state_path.exists() else None
        created_files: list[Path] = []
        created_dirs: list[Path] = []
        try:
            with WebDAVClient(settings) as client:
                client.download(remote.archive_path, download_path)
            if download_path.stat().st_size != remote.size:
                raise WebDAVError(
                    f"downloaded ZIP size mismatch: expected {remote.size}, got {download_path.stat().st_size}"
                )
            actual_sha = _sha256_file(download_path)
            if actual_sha != remote.sha256:
                raise WebDAVError(
                    f"downloaded ZIP SHA-256 mismatch: expected {remote.sha256}, got {actual_sha}"
                )
            _safe_zip_members(download_path)

            with _base_home_scope(root):
                from hermes_cli.backup import run_backup

                rollback = run_backup(
                    SimpleNamespace(output=str(rollback_path), quick=False, label=None)
                )
            if rollback is None or not rollback_path.is_file():
                raise WebDAVError("could not create a complete rollback ZIP")
            _safe_zip_members(rollback_path)
            created_files, created_dirs = _targets_created_by_archive(root, download_path)

            if gateway_was_running:
                _gateway_command(root, "stop")
                gateway_stopped = True
            try:
                with _base_home_scope(root):
                    from hermes_cli.backup import run_import

                    imported = run_import(SimpleNamespace(zipfile=str(download_path), force=True))
                if not imported:
                    raise WebDAVError("Hermes import reported one or more restore errors")
                _restore_webdav_config(root, webdav_snapshot)
                if state_bytes is None:
                    state_path.unlink(missing_ok=True)
                else:
                    state_path.parent.mkdir(parents=True, exist_ok=True)
                    state_path.write_bytes(state_bytes)
                    os.chmod(state_path, 0o600)
                _restore_managed_cron(root, cron_snapshot)
            except Exception as import_error:
                _remove_created_targets(created_files, created_dirs)
                try:
                    with _base_home_scope(root):
                        from hermes_cli.backup import run_import

                        rolled_back = run_import(
                            SimpleNamespace(zipfile=str(rollback_path), force=True)
                        )
                    if not rolled_back:
                        raise WebDAVError("rollback import reported errors")
                    _restore_webdav_config(root, webdav_snapshot)
                    if state_bytes is None:
                        state_path.unlink(missing_ok=True)
                    else:
                        state_path.write_bytes(state_bytes)
                        os.chmod(state_path, 0o600)
                    _restore_managed_cron(root, cron_snapshot)
                except Exception as rollback_error:
                    rollback_failed = True
                    diagnostic = backups_dir / (
                        "restore-failure-" + _utc_now().strftime("%Y%m%dT%H%M%SZ") + ".json"
                    )
                    save_webdav_state(
                        root,
                        {
                            **load_webdav_state(root),
                            "restore_diagnostic": {
                                "backup_id": backup_id,
                                "download_zip": str(download_path),
                                "rollback_zip": str(rollback_path),
                                "import_error": str(import_error),
                                "rollback_error": str(rollback_error),
                                "at": _utc_iso(),
                            },
                        },
                    )
                    diagnostic.write_text(
                        json.dumps(
                            {
                                "backup_id": backup_id,
                                "download_zip": str(download_path),
                                "rollback_zip": str(rollback_path),
                                "import_error": str(import_error),
                                "rollback_error": str(rollback_error),
                            },
                            indent=2,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    os.chmod(diagnostic, 0o600)
                    raise WebDAVError(
                        "restore failed and automatic rollback also failed; "
                        f"Gateway remains stopped. Diagnostics: {diagnostic}"
                    ) from rollback_error
                raise WebDAVError(
                    f"restore failed and was rolled back automatically: {import_error}"
                ) from import_error

            _record_result(
                root,
                operation="restore",
                success=True,
                message=f"Restored {backup_id}",
                backup_id=backup_id,
            )
            return {
                "ok": True,
                "backup_id": backup_id,
                "rollback_zip": str(rollback_path),
            }
        except Exception as exc:
            _record_result(
                root,
                operation="restore",
                success=False,
                message=str(exc),
            )
            raise
        finally:
            if gateway_stopped and not rollback_failed:
                active_error = sys.exc_info()[0] is not None
                try:
                    _gateway_command(root, "start")
                except Exception as exc:
                    _record_result(
                        root,
                        operation="restore",
                        success=False,
                        message=f"data restore completed but Gateway restart failed: {exc}",
                    )
                    logger.exception("Could not restart Gateway after WebDAV restore")
                    if not active_error:
                        raise WebDAVError(
                            f"restore finished but the original Gateway state could not be restored: {exc}"
                        ) from exc
            if not rollback_failed:
                download_path.unlink(missing_ok=True)


def _write_managed_script(root: Path) -> Path:
    scripts_dir = root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    path = scripts_dir / MANAGED_SCRIPT_NAME
    content = (
        "# Generated by Hermes WebDAV backup management.\n"
        "import os\n"
        f"os.environ['HERMES_HOME'] = {str(root)!r}\n"
        "from hermes_cli.webdav_backup import cron_main\n"
        "raise SystemExit(cron_main())\n"
    )
    if not path.exists() or path.read_text(encoding="utf-8", errors="replace") != content:
        fd, tmp_name = tempfile.mkstemp(prefix=".webdav-cron-", suffix=".py", dir=scripts_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp_name, 0o700)
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path


def ensure_webdav_cron(root: Optional[Path] = None) -> Optional[dict[str, Any]]:
    root = (root or get_default_hermes_root()).expanduser().resolve()
    settings = load_webdav_settings(root, require_url=False)
    if not settings.url:
        return None
    settings.validate(require_url=True)
    _write_managed_script(root)
    with _base_home_scope(root):
        from cron.jobs import (
            create_job,
            load_jobs,
            pause_job,
            remove_job,
            resume_job,
            update_job,
            use_cron_store,
        )

        with use_cron_store(root):
            managed = [
                job for job in load_jobs() if job.get("managed_by") == MANAGED_CRON_MARKER
            ]
            primary = managed[0] if managed else None
            for duplicate in managed[1:]:
                remove_job(duplicate["id"])
            if primary is None:
                primary = create_job(
                    prompt=None,
                    schedule=settings.schedule,
                    name=MANAGED_CRON_NAME,
                    deliver="origin",
                    script=MANAGED_SCRIPT_NAME,
                    no_agent=True,
                    workdir=str(root),
                )
            primary = update_job(
                primary["id"],
                {
                    "name": MANAGED_CRON_NAME,
                    "schedule": settings.schedule,
                    "script": MANAGED_SCRIPT_NAME,
                    "no_agent": True,
                    "deliver": "origin",
                    "workdir": str(root),
                    "managed_by": MANAGED_CRON_MARKER,
                },
            )
            if primary is None:
                raise WebDAVError("could not create the managed WebDAV Cron job")
            if settings.enabled:
                primary = resume_job(primary["id"]) or primary
            else:
                primary = pause_job(primary["id"], "WebDAV automatic backup disabled") or primary
    state = load_webdav_state(root)
    state["cron_job_id"] = primary["id"]
    save_webdav_state(root, state)
    return primary


def set_webdav_enabled(root: Path, enabled: bool) -> WebDAVSettings:
    current = load_webdav_settings(root)
    updated = WebDAVSettings(**{**asdict(current), "enabled": bool(enabled)})
    save_webdav_settings(root, updated)
    ensure_webdav_cron(root)
    return updated


def webdav_status(root: Optional[Path] = None) -> dict[str, Any]:
    root = (root or get_default_hermes_root()).expanduser().resolve()
    settings = load_webdav_settings(root, require_url=False)
    state = load_webdav_state(root)
    job = None
    with _base_home_scope(root):
        from cron.jobs import load_jobs, use_cron_store

        with use_cron_store(root):
            jobs = load_jobs()
            job = next(
                (item for item in jobs if item.get("managed_by") == MANAGED_CRON_MARKER),
                None,
            )
    return {
        "configured": bool(settings.url),
        "enabled": settings.enabled,
        "url": _validate_base_url(settings.url).rstrip("/") if settings.url else "",
        "remote_path": settings.remote_path,
        "device_name": settings.device_name,
        "device_uuid": state.get("device_uuid"),
        "authentication": "anonymous" if settings.anonymous else "basic",
        "username": "(set)" if settings.username else "",
        "password": "(set)" if settings.password else "",
        "schedule": settings.schedule,
        "retention": settings.retention,
        "cron": {
            "configured": job is not None,
            "job_id": job.get("id") if job else None,
            "enabled": bool(job and job.get("enabled", True)),
            "state": job.get("state") if job else None,
            "next_run_at": job.get("next_run_at") if job else None,
            "gateway_running": _gateway_running(root),
            "requires_gateway": True,
        },
        "last_result": state.get("last_result"),
        "last_remote_backup_id": state.get("last_remote_backup_id"),
    }


def _print_status(payload: dict[str, Any]) -> None:
    print("Hermes WebDAV backup")
    print(f"  Configured:      {'yes' if payload['configured'] else 'no'}")
    print(f"  Automatic:       {'enabled' if payload['enabled'] else 'disabled'}")
    print(f"  URL:             {payload['url'] or '(not set)'}")
    print(f"  Remote path:     {payload['remote_path']}")
    print(f"  Device:          {payload['device_name']} ({payload['device_uuid']})")
    print(f"  Authentication:  {payload['authentication']}")
    print(f"  Schedule:        {payload['schedule']} (local time)")
    print(f"  Retention:       {payload['retention']} backup(s) for this device")
    cron = payload["cron"]
    print(
        f"  Cron:            {'active' if cron['enabled'] else 'inactive'}"
        + (f" ({cron['job_id']})" if cron["job_id"] else "")
    )
    if cron["next_run_at"]:
        print(f"  Next run:        {cron['next_run_at']}")
    if not cron["gateway_running"]:
        print("  Gateway:         not running; scheduled backups will not run or catch up")
    last = payload.get("last_result")
    if last:
        print(
            f"  Last result:     {'success' if last.get('success') else 'failed'} "
            f"at {last.get('at')} ({last.get('message')})"
        )


def run_webdav_command(args) -> None:
    root = get_default_hermes_root().expanduser().resolve()
    command = getattr(args, "webdav_command", None)
    try:
        if command == "status":
            payload = webdav_status(root)
            if getattr(args, "json", False):
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                _print_status(payload)
            return
        settings = load_webdav_settings(root)
        if command == "test":
            result = test_webdav_connection(settings)
            print("WebDAV read/write test succeeded.")
            if result["move_supported"]:
                print("  MOVE: supported (atomic finalization enabled)")
            else:
                print("  MOVE: unsupported (verified PUT fallback will be used)")
            return
        if command == "upload":
            result = upload_backup(root, settings=settings, scheduled=False)
            if result is not None:
                print(f"WebDAV backup complete: {result.backup_id}")
            return
        if command == "list":
            backups = list_remote_backups(settings)
            if getattr(args, "json", False):
                print(
                    json.dumps(
                        [item.public_dict() for item in backups],
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            elif not backups:
                print("No complete WebDAV backups found.")
            else:
                print("Complete WebDAV backups:")
                for item in backups:
                    print(
                        f"  {item.backup_id}  {item.created_at}  {item.device_name}  "
                        f"{item.size} bytes"
                    )
            return
        if command == "restore":
            result = restore_backup(
                args.backup_id,
                root=root,
                settings=settings,
                confirmed=bool(getattr(args, "yes", False)),
            )
            if result.get("ok"):
                print(f"WebDAV restore complete: {args.backup_id}")
            return
        raise WebDAVError("missing WebDAV backup command")
    except (WebDAVError, httpx.HTTPError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def cron_main() -> int:
    root = get_default_hermes_root().expanduser().resolve()
    try:
        settings = load_webdav_settings(root)
        if not settings.enabled:
            return 0
        upload_backup(root, settings=settings, scheduled=True)
        return 0
    except BackupBusyError:
        return 0
    except Exception as exc:
        logger.exception("Scheduled WebDAV backup failed")
        print(f"Hermes WebDAV automatic backup failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(cron_main())
