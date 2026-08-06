import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
LOUIS_REPOSITORY = "github.com/louisgreen0726/hermes-agent"


def _canonical_repository(url: str) -> str:
    parsed = urlparse(url)
    value = f"{parsed.netloc}{parsed.path}".rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    return value.lower()


def test_louis_versions_follow_the_same_release_relationship():
    import tomllib

    from hermes_cli import (
        __release_date__,
        __upstream_release_date__,
        __upstream_version__,
        __version__,
    )

    with (ROOT / "pyproject.toml").open("rb") as handle:
        metadata = tomllib.load(handle)

    cli_version = re.fullmatch(
        r"Louis-(?P<base>\d+\.\d+\.\d+)\.(?P<revision>\d+)", __version__
    )
    python_version = re.fullmatch(
        r"(?P<base>\d+\.\d+\.\d+)\+Louis\.(?P<revision>\d+)",
        metadata["project"]["version"],
    )
    upstream_version = re.fullmatch(r"\d+\.\d+\.\d+", __upstream_version__)

    assert cli_version is not None
    assert python_version is not None
    assert upstream_version is not None
    assert cli_version.group("base") == python_version.group("base")
    assert cli_version.group("revision") == python_version.group("revision")
    assert python_version.group("base") == __upstream_version__

    release_date = datetime.strptime(__release_date__, "%Y.%m.%d").date()
    upstream_release_date = datetime.strptime(
        __upstream_release_date__, "%Y.%m.%d"
    ).date()
    assert upstream_release_date <= release_date


def test_linux_installer_manifest_identifies_louis_repository():
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "install.sh"), "--manifest"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    manifest = json.loads(result.stdout.strip().splitlines()[-1])

    assert _canonical_repository(manifest["source_repository"]) == LOUIS_REPOSITORY
    assert any(stage["name"] == "repository" for stage in manifest["stages"])


def test_model_catalog_fallbacks_stay_with_louis_release_repository():
    from hermes_cli.model_catalog import DEFAULT_CATALOG_FALLBACK_URLS

    assert DEFAULT_CATALOG_FALLBACK_URLS
    for url in DEFAULT_CATALOG_FALLBACK_URLS:
        parsed = urlparse(url)
        assert parsed.netloc.lower() == "raw.githubusercontent.com"
        assert parsed.path.lower().startswith(
            "/louisgreen0726/hermes-agent/"
        )


def test_management_center_is_packaged_and_installed():
    import tomllib

    with (ROOT / "pyproject.toml").open("rb") as handle:
        metadata = tomllib.load(handle)
    assert metadata["project"]["scripts"]["hermes-manage"] == (
        "hermes_cli.subcommands.manage:entrypoint"
    )

    installer = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
    assert 'rm -f "$command_link_dir/hermes-manage"' in installer
    assert 'exec "$HERMES_BIN" manage "\\$@"' in installer
