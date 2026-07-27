import json
import subprocess
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


def test_louis_versions_are_distinct_and_consistent():
    import tomllib

    from hermes_cli import (
        __release_date__,
        __upstream_release_date__,
        __upstream_version__,
        __version__,
    )

    with (ROOT / "pyproject.toml").open("rb") as handle:
        metadata = tomllib.load(handle)

    assert __version__ == "Louis-0.19.0.1"
    assert metadata["project"]["version"] == "0.19.0+Louis.1"
    assert __upstream_version__ == "0.19.0"
    assert __release_date__ == "2026.7.27"
    assert __upstream_release_date__ == "2026.7.20"


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
