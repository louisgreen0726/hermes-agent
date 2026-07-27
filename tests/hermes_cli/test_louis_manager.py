"""Behavior coverage for the Hermes-Louis native management center."""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from hermes_cli.louis_manager import (
    inspect_legacy_manager_config,
    plan_legacy_manager_repair,
    repair_legacy_manager_config,
    run_manage_command,
)
from hermes_cli.subcommands.manage import build_manage_parser, entrypoint


def _legacy_config() -> dict:
    return {
        "_config_version": 21,
        "model": {
            "default": "gpt-5.6-sol",
            "provider": "custom",
            "base_url": "https://louis.example/v1",
            "api_key": "test-secret",
            "context_length": 200000,
        },
        "custom_providers": [
            {
                "name": "Louis/gpt-5.6-sol",
                "base_url": "https://louis.example/v1/",
                "api_key": "test-secret",
                "api_mode": "codex_responses",
                "model": "gpt-5.6-sol",
            },
            {
                "name": "Louis/claude-sonnet-4.6",
                "base_url": "https://louis.example/v1",
                "api_key": "test-secret",
                "api_mode": "codex_responses",
                "model": "claude-sonnet-4.6",
            },
            {
                "name": "DeepSeek",
                "base_url": "https://api.deepseek.example/v1",
                "key_env": "DEEPSEEK_API_KEY",
                "model": "deepseek-chat",
            },
        ],
        "gateway": {"platforms": {"telegram": {"enabled": True}}},
    }


def _write_config(home: Path, config: dict) -> Path:
    home.mkdir(parents=True, exist_ok=True)
    path = home / "config.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


def test_plan_consolidates_models_and_preserves_unrelated_config():
    original = _legacy_config()
    snapshot = copy.deepcopy(original)

    repaired, summary = plan_legacy_manager_repair(original)

    assert original == snapshot
    assert summary.changed is True
    assert summary.model_provider_updated is True
    assert summary.skipped_groups == ()
    assert [
        (item.name, item.source_entries, item.model_count) for item in summary.repairs
    ] == [("Louis", 2, 2)]

    providers = repaired["custom_providers"]
    assert [entry["name"] for entry in providers] == ["Louis", "DeepSeek"]
    assert set(providers[0]["models"]) == {"gpt-5.6-sol", "claude-sonnet-4.6"}
    assert providers[0]["base_url"] == "https://louis.example/v1"
    assert providers[0]["api_mode"] == "codex_responses"

    assert repaired["model"] == {
        "default": "gpt-5.6-sol",
        "provider": "custom:louis",
        "context_length": 200000,
    }
    assert repaired["gateway"] == original["gateway"]


def test_plan_merges_existing_root_and_preserves_model_metadata():
    config = {
        "model": {"default": "model-b", "provider": "custom:louis"},
        "custom_providers": [
            {
                "name": "Louis",
                "base_url": "https://louis.example/v1",
                "key_env": "LOUIS_API_KEY",
                "model": "model-a",
                "models": {"model-a": {"context_length": 32000}},
            },
            {
                "name": "Louis/model-b",
                "base_url": "https://louis.example/v1",
                "key_env": "LOUIS_API_KEY",
                "model": "model-b",
                "models": {"model-b": {"context_length": 64000}},
            },
        ],
    }

    repaired, summary = plan_legacy_manager_repair(config)

    assert summary.changed is True
    assert len(repaired["custom_providers"]) == 1
    provider = repaired["custom_providers"][0]
    assert provider["name"] == "Louis"
    assert provider["model"] == "model-a"
    assert provider["models"] == {
        "model-a": {"context_length": 32000},
        "model-b": {"context_length": 64000},
    }


def test_plan_preserves_distinct_model_and_default_model_values():
    config = {
        "custom_providers": [
            {
                "name": "Louis/model-a",
                "base_url": "https://louis.example/v1",
                "api_key": "test-key",
                "model": "model-a",
                "default_model": "model-b",
            },
            {
                "name": "Louis/model-c",
                "base_url": "https://louis.example/v1",
                "api_key": "test-key",
                "model": "model-c",
            },
        ]
    }

    repaired, summary = plan_legacy_manager_repair(config)

    assert summary.changed is True
    provider = repaired["custom_providers"][0]
    assert provider["model"] == "model-a"
    assert set(provider["models"]) == {"model-a", "model-b", "model-c"}


def test_plan_refuses_same_name_with_different_credentials():
    config = {
        "custom_providers": [
            {
                "name": "Louis/model-a",
                "base_url": "https://louis.example/v1",
                "api_key": "key-a",
                "model": "model-a",
            },
            {
                "name": "Louis/model-b",
                "base_url": "https://louis.example/v1",
                "api_key": "key-b",
                "model": "model-b",
            },
        ]
    }

    repaired, summary = plan_legacy_manager_repair(config)

    assert repaired == config
    assert summary.changed is False
    assert summary.repairs == ()
    assert summary.skipped_groups == ("Louis",)


def test_plan_preserves_model_api_mode_on_named_provider():
    config = _legacy_config()
    for entry in config["custom_providers"][:2]:
        entry.pop("api_mode")
    config["model"]["api_mode"] = "codex_responses"

    repaired, summary = plan_legacy_manager_repair(config)

    assert summary.model_provider_updated is True
    assert repaired["custom_providers"][0]["api_mode"] == "codex_responses"
    assert "api_mode" not in repaired["model"]


def test_plan_refuses_conflicting_model_and_provider_api_modes():
    config = _legacy_config()
    config["model"]["provider"] = "custom:louis"
    config["model"]["api_mode"] = "anthropic_messages"

    repaired, summary = plan_legacy_manager_repair(config)

    assert summary.changed is True
    assert summary.model_provider_updated is False
    assert repaired["model"]["api_mode"] == "anthropic_messages"
    assert repaired["model"]["provider"] == "custom:louis"


def test_plan_does_not_merge_case_distinct_url_paths():
    config = _legacy_config()
    config["custom_providers"][1]["base_url"] = "https://louis.example/V1"

    repaired, summary = plan_legacy_manager_repair(config)

    assert repaired == config
    assert summary.changed is False
    assert summary.skipped_groups == ("Louis",)


def test_plan_ignores_unrelated_slash_in_provider_name():
    config = {
        "custom_providers": [
            {
                "name": "Org/Production",
                "base_url": "https://example.invalid/v1",
                "model": "actual-model-id",
            }
        ]
    }

    repaired, summary = plan_legacy_manager_repair(config)

    assert repaired == config
    assert summary == summary.__class__()


def test_plan_ignores_slash_name_without_a_declared_model():
    config = {
        "custom_providers": [
            {
                "name": "Org/Production",
                "base_url": "https://example.invalid/v1",
                "api_key": "test-key",
            }
        ]
    }

    repaired, summary = plan_legacy_manager_repair(config)

    assert repaired == config
    assert summary == summary.__class__()


def test_plan_ignores_single_slash_name_even_when_model_matches_suffix():
    config = {
        "custom_providers": [
            {
                "name": "Org/Production",
                "base_url": "https://example.invalid/v1",
                "api_key": "test-key",
                "model": "Production",
            }
        ]
    }

    repaired, summary = plan_legacy_manager_repair(config)

    assert repaired == config
    assert summary == summary.__class__()


def test_release_gate_covers_legacy_picker_provider_resolution():
    from hermes_cli.model_switch import (
        _custom_provider_picker_group_key,
        _resolve_grouped_custom_provider,
    )

    providers = [
        {
            "name": "Louis/model-a",
            "base_url": "https://louis.example/v1",
            "api_key": "test-key",
            "model": "model-a",
        },
        {
            "name": "Louis/model-b",
            "base_url": "https://louis.example/v1",
            "api_key": "test-key",
            "model": "model-b",
        },
    ]

    assert _resolve_grouped_custom_provider("custom:louis", "model-b", providers) == (
        "custom:louis/model-b",
        "Louis",
        "model-b",
    )
    assert (
        _resolve_grouped_custom_provider(
            "custom:org",
            "Production",
            [
                {
                    "name": "Org/Production",
                    "base_url": "https://example.invalid/v1",
                    "model": "Production",
                }
            ],
        )
        is None
    )

    tls_enabled = {
        "name": "Louis/model-a",
        "base_url": "https://louis.example/v1",
        "api_key": "test-key",
        "model": "model-a",
        "ssl_verify": True,
    }
    tls_disabled = {**tls_enabled, "ssl_verify": False}
    assert _custom_provider_picker_group_key(
        tls_enabled, "Louis"
    ) != _custom_provider_picker_group_key(tls_disabled, "Louis")


def test_disk_repair_uses_profile_home_and_creates_backup(tmp_path, monkeypatch):
    home = tmp_path / "profiles" / "production"
    original = _legacy_config()
    config_path = _write_config(home, original)
    monkeypatch.setenv("HERMES_HOME", str(home))

    summary = repair_legacy_manager_config()

    assert summary.changed is True
    assert summary.backup_path is not None
    assert summary.backup_path.parent == home / "backups"
    assert summary.backup_path.stat().st_mode & 0o777 == 0o600
    assert yaml.safe_load(summary.backup_path.read_text(encoding="utf-8")) == original

    persisted = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert [entry["name"] for entry in persisted["custom_providers"]] == [
        "Louis",
        "DeepSeek",
    ]
    assert persisted["model"]["provider"] == "custom:louis"
    assert "api_key" not in persisted["model"]
    assert inspect_legacy_manager_config().changed is False


def test_disk_repair_refuses_malformed_yaml(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "config.yaml").write_text("model: [unterminated\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))

    with pytest.raises(Exception):
        repair_legacy_manager_config()

    assert not (home / "backups").exists()


def test_disk_repair_refuses_managed_profile(tmp_path, monkeypatch):
    home = tmp_path / "managed"
    config_path = _write_config(home, _legacy_config())
    (home / ".managed").write_text("NixOS\n", encoding="utf-8")
    before = config_path.read_bytes()
    monkeypatch.setenv("HERMES_HOME", str(home))

    with pytest.raises(RuntimeError, match="managed"):
        repair_legacy_manager_config()

    assert config_path.read_bytes() == before
    assert not (home / "backups").exists()


def test_check_output_never_prints_inline_api_key(tmp_path, monkeypatch, capsys):
    home = tmp_path / "hermes"
    _write_config(home, _legacy_config())
    monkeypatch.setenv("HERMES_HOME", str(home))

    rc = run_manage_command(SimpleNamespace(check=True, repair=False, yes=False))

    output = capsys.readouterr()
    assert rc == 1
    assert "Louis" in output.out
    assert "test-secret" not in output.out
    assert "test-secret" not in output.err


def test_noninteractive_repair_yes_applies_config_and_creates_backup(
    tmp_path, monkeypatch, capsys
):
    home = tmp_path / "hermes"
    config_path = _write_config(home, _legacy_config())
    monkeypatch.setenv("HERMES_HOME", str(home))

    rc = run_manage_command(SimpleNamespace(check=False, repair=True, yes=True))

    output = capsys.readouterr()
    assert rc == 0
    assert "已修复旧管理器配置" in output.out
    assert "test-secret" not in output.out
    assert "test-secret" not in output.err
    assert len(list((home / "backups").glob("config-before-louis-manager-*.yaml"))) == 1
    persisted = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert [entry["name"] for entry in persisted["custom_providers"]] == [
        "Louis",
        "DeepSeek",
    ]


def test_yes_without_repair_is_rejected(capsys):
    rc = run_manage_command(SimpleNamespace(check=False, repair=False, yes=True))

    output = capsys.readouterr()
    assert rc == 2
    assert "--yes" in output.err


def test_manage_parser_exposes_check_and_repair_modes():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    sentinel = object()
    build_manage_parser(subparsers, cmd_manage=sentinel)

    args = parser.parse_args(["manage", "--repair", "--yes"])

    assert args.command == "manage"
    assert args.repair is True
    assert args.yes is True
    assert args.func is sentinel


def test_shortcut_entrypoint_routes_through_main(monkeypatch):
    called = []
    monkeypatch.setattr("hermes_cli.main.main", lambda: called.append(list(sys.argv)))
    monkeypatch.setattr(sys, "argv", ["hermes-manage", "--check", "-p", "production"])

    entrypoint()

    assert called == [["hermes-manage", "manage", "--check", "-p", "production"]]
