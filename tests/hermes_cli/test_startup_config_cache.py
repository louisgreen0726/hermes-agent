"""Runtime contracts for sharing the startup raw-config cache."""

from __future__ import annotations

import importlib
import sys


def test_startup_consumers_share_one_process_home_parse(tmp_path, monkeypatch):
    process_home = tmp_path / "process-home"
    process_home.mkdir()
    config_path = process_home / "config.yaml"
    config_path.write_text(
        "secrets:\n"
        "  bitwarden:\n"
        "    enabled: false\n"
        "security:\n"
        "  redact_secrets: true\n"
        "logging:\n"
        "  level: DEBUG\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(process_home))

    from hermes_cli import config

    config._RAW_CONFIG_CACHE.clear()
    real_load = config.fast_safe_load
    parse_count = 0

    def counting_load(stream):
        nonlocal parse_count
        if getattr(stream, "name", None) == str(config_path):
            parse_count += 1
        return real_load(stream)

    monkeypatch.setattr(config, "fast_safe_load", counting_load)
    sys.modules.pop("hermes_cli.main", None)
    importlib.import_module("hermes_cli.main")

    import hermes_logging

    assert hermes_logging._read_logging_config() == ("DEBUG", None, None)
    assert parse_count == 1


def test_non_process_home_uses_its_own_config(tmp_path, monkeypatch):
    process_home = tmp_path / "process-home"
    other_home = tmp_path / "other-home"
    process_home.mkdir()
    other_home.mkdir()
    (process_home / "config.yaml").write_text(
        "secrets:\n  bitwarden:\n    enabled: false\n",
        encoding="utf-8",
    )
    (other_home / "config.yaml").write_text(
        "secrets:\n  onepassword:\n    enabled: true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(process_home))

    from hermes_cli import config, env_loader

    config._RAW_CONFIG_CACHE.clear()
    assert config.read_raw_config()["secrets"]["bitwarden"]["enabled"] is False
    assert env_loader._load_secrets_config(other_home) == {
        "onepassword": {"enabled": True}
    }
