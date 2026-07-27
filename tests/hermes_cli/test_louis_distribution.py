from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_louis_versions_are_distinct_and_consistent():
    import tomllib
    from hermes_cli import (
        __release_date__,
        __upstream_release_date__,
        __upstream_version__,
        __version__,
    )

    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert __version__ == "Louis-0.19.0.1"
    assert metadata["project"]["version"] == "0.19.0+Louis.1"
    assert __upstream_version__ == "0.19.0"
    assert __release_date__ == "2026.7.27"
    assert __upstream_release_date__ == "2026.7.20"


def test_installers_and_catalog_use_louis_repository():
    paths = (
        ROOT / "scripts" / "install.sh",
        ROOT / "scripts" / "install.ps1",
        ROOT / "hermes_cli" / "model_catalog.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "louisgreen0726/hermes-agent" in text, path


def test_readme_identifies_the_independent_louis_distribution():
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Louis Hermes Agent" in text
    assert "independently maintained fork" in text
    assert "not an official Nous Research release" in text
    assert "raw.githubusercontent.com/louisgreen0726/hermes-agent/main/scripts/install.sh" in text
    assert "raw.githubusercontent.com/louisgreen0726/hermes-agent/main/scripts/install.ps1" in text
    assert "https://github.com/louisgreen0726/hermes-agent/issues" in text
    assert "https://hermes-agent.nousresearch.com/install.sh" not in text
    assert "https://hermes-agent.nousresearch.com/install.ps1" not in text


def test_louis_updater_never_mentions_upstream_git_commands():
    text = (ROOT / "scripts" / "hermes-update-louis").read_text(encoding="utf-8")
    forbidden = (
        "git fetch upstream",
        "git pull upstream",
        "git merge upstream",
        "git rebase upstream",
    )
    assert all(command not in text for command in forbidden)
    assert 'REMOTE="origin"' in text