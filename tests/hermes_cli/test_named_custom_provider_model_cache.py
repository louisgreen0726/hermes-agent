"""Named custom model catalogs must retain their route identity."""

import json

import yaml

from hermes_cli import models


def _write_shared_relay_config(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    relay_url = "https://relay.example.test/v1"
    (home / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "providers": {
                    "relay-a": {
                        "name": "Relay A",
                        "base_url": relay_url,
                        "api_key": "key-a",
                        "transport": "chat_completions",
                        "extra_headers": {"X-Tenant": "tenant-a"},
                    },
                    "relay-b": {
                        "name": "Relay B",
                        "base_url": relay_url,
                        "api_key": "key-b",
                        "transport": "anthropic_messages",
                        "extra_headers": {"X-Tenant": "tenant-b"},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    return home, relay_url


def test_provider_model_ids_resolves_each_shared_relay_identity(
    tmp_path, monkeypatch
):
    _home, relay_url = _write_shared_relay_config(tmp_path, monkeypatch)
    calls = []

    def fake_fetch(api_key, base_url, **kwargs):
        calls.append((api_key, base_url, kwargs))
        return ["model-a"] if api_key == "key-a" else ["model-b"]

    monkeypatch.setattr(models, "fetch_api_models", fake_fetch)

    assert models.provider_model_ids("custom:relay-a") == ["model-a"]
    # Bare mapping keys are also accepted by the runtime resolver.
    assert models.provider_model_ids("relay-b") == ["model-b"]

    assert calls == [
        (
            "key-a",
            relay_url,
            {
                "api_mode": "chat_completions",
                "headers": {"X-Tenant": "tenant-a"},
            },
        ),
        (
            "key-b",
            relay_url,
            {
                "api_mode": "anthropic_messages",
                "headers": {"X-Tenant": "tenant-b"},
            },
        ),
    ]


def test_cached_model_ids_isolate_shared_relay_credentials(tmp_path, monkeypatch):
    home, relay_url = _write_shared_relay_config(tmp_path, monkeypatch)
    calls = []

    def fake_fetch(api_key, base_url, **kwargs):
        calls.append((api_key, base_url, kwargs))
        return ["model-a"] if api_key == "key-a" else ["model-b"]

    monkeypatch.setattr(models, "fetch_api_models", fake_fetch)

    # Bare mapping keys and explicit custom: slugs are aliases for one route,
    # so each provider gets exactly one cache namespace and one live probe.
    assert models.cached_provider_model_ids("relay-a") == ["model-a"]
    assert models.cached_provider_model_ids("custom:relay-b") == ["model-b"]
    assert models.cached_provider_model_ids("custom:relay-a") == ["model-a"]
    assert models.cached_provider_model_ids("relay-b") == ["model-b"]

    assert [call[0] for call in calls] == ["key-a", "key-b"]
    assert all(call[1] == relay_url for call in calls)

    cache = json.loads((home / "provider_models_cache.json").read_text())
    assert cache["custom:relay-a"]["models"] == ["model-a"]
    assert cache["custom:relay-b"]["models"] == ["model-b"]
    serialized = json.dumps(cache)
    assert "key-a" not in serialized
    assert "key-b" not in serialized
    assert "tenant-a" not in serialized
    assert "tenant-b" not in serialized


def test_clear_cached_model_ids_accepts_both_named_provider_aliases(
    tmp_path, monkeypatch
):
    _home, _relay_url = _write_shared_relay_config(tmp_path, monkeypatch)
    calls = []

    def fake_fetch(api_key, base_url, **kwargs):
        calls.append((api_key, base_url, kwargs))
        return ["model-a"]

    monkeypatch.setattr(models, "fetch_api_models", fake_fetch)

    assert models.cached_provider_model_ids("relay-a") == ["model-a"]
    models.clear_provider_models_cache("custom:relay-a")
    assert models.cached_provider_model_ids("relay-a") == ["model-a"]
    models.clear_provider_models_cache("relay-a")
    assert models.cached_provider_model_ids("custom:relay-a") == ["model-a"]

    assert len(calls) == 3


def _isolate_picker_discovery(monkeypatch):
    monkeypatch.setattr("agent.models_dev.fetch_models_dev", lambda: {})
    monkeypatch.setattr("agent.models_dev.PROVIDER_TO_MODELS_DEV", {})
    monkeypatch.setattr("hermes_cli.providers.HERMES_OVERLAYS", {})


def test_modern_provider_picker_probe_preserves_each_shared_relay_api_mode(
    tmp_path, monkeypatch
):
    _home, relay_url = _write_shared_relay_config(tmp_path, monkeypatch)
    _isolate_picker_discovery(monkeypatch)
    calls = []

    def fake_fetch(api_key, base_url, **kwargs):
        calls.append((api_key, base_url, kwargs))
        return [f"model-{api_key[-1]}"]

    monkeypatch.setattr(models, "fetch_api_models", fake_fetch)

    from hermes_cli.model_switch import list_authenticated_providers

    providers = list_authenticated_providers(
        current_provider="relay-a",
        user_providers={
            "relay-a": {
                "name": "Relay A",
                "base_url": relay_url,
                "api_key": "key-a",
                "transport": "chat_completions",
                "extra_headers": {"X-Tenant": "tenant-a"},
            },
            "relay-b": {
                "name": "Relay B",
                "base_url": relay_url,
                "api_key": "key-b",
                "transport": "anthropic_messages",
                "extra_headers": {"X-Tenant": "tenant-b"},
            },
        },
        custom_providers=[],
        max_models=50,
    )

    assert [call[2]["api_mode"] for call in calls] == [
        "chat_completions",
        "anthropic_messages",
    ]
    assert [call[0] for call in calls] == ["key-a", "key-b"]
    rows = {row["slug"]: row for row in providers if row.get("is_user_defined")}
    assert rows["relay-a"]["models"] == ["model-a"]
    assert rows["relay-b"]["models"] == ["model-b"]


def test_legacy_provider_picker_probe_preserves_each_shared_relay_api_mode(
    tmp_path, monkeypatch
):
    _home, relay_url = _write_shared_relay_config(tmp_path, monkeypatch)
    _isolate_picker_discovery(monkeypatch)
    calls = []

    def fake_fetch(api_key, base_url, **kwargs):
        calls.append((api_key, base_url, kwargs))
        return [f"model-{api_key[-1]}"]

    monkeypatch.setattr(models, "fetch_api_models", fake_fetch)

    from hermes_cli.model_switch import list_authenticated_providers

    providers = list_authenticated_providers(
        current_provider="custom:relay-a",
        user_providers={},
        custom_providers=[
            {
                "name": "Relay A",
                "base_url": relay_url,
                "api_key": "key-a",
                "api_mode": "chat_completions",
                "extra_headers": {"X-Tenant": "tenant-a"},
            },
            {
                "name": "Relay B",
                "base_url": relay_url,
                "api_key": "key-b",
                "transport": "anthropic_messages",
                "extra_headers": {"X-Tenant": "tenant-b"},
            },
        ],
        max_models=50,
    )

    assert [call[2]["api_mode"] for call in calls] == [
        "chat_completions",
        "anthropic_messages",
    ]
    assert [call[0] for call in calls] == ["key-a", "key-b"]
    rows = {row["name"]: row for row in providers if row.get("is_user_defined")}
    assert rows["Relay A"]["models"] == ["model-a"]
    assert rows["Relay B"]["models"] == ["model-b"]
