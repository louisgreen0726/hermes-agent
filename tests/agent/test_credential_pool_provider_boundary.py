"""Credential pools must never cross provider or custom-endpoint boundaries."""

from types import SimpleNamespace
from unittest.mock import patch

from agent.credential_pool import credential_pool_matches_provider
from hermes_cli import runtime_provider as rp


def test_provider_match_requires_exact_non_custom_identity():
    assert credential_pool_matches_provider("deepseek", "deepseek")
    assert not credential_pool_matches_provider("openai-codex", "deepseek")
    assert not credential_pool_matches_provider("", "deepseek")


def test_custom_pool_match_is_scoped_by_endpoint():
    with patch(
        "agent.credential_pool.get_custom_provider_pool_key",
        return_value="custom:lab",
    ):
        assert credential_pool_matches_provider(
            "custom:lab", "custom", base_url="https://lab.example/v1"
        )
        assert not credential_pool_matches_provider(
            "custom:other", "custom", base_url="https://lab.example/v1"
        )


def test_named_custom_pool_match_is_scoped_by_name_and_url(tmp_path, monkeypatch):
    import yaml

    home = tmp_path / "hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    relay_url = "https://relay.example.test/v1"
    (home / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "custom_providers": [
                    {"name": "Relay A", "base_url": relay_url},
                    {"name": "Relay B", "base_url": relay_url},
                ]
            }
        )
    )

    assert credential_pool_matches_provider(
        "custom:relay-b",
        "custom",
        base_url=relay_url,
        requested_provider="custom:relay-b",
    )
    assert not credential_pool_matches_provider(
        "custom:relay-a",
        "custom",
        base_url=relay_url,
        requested_provider="custom:relay-b",
    )
    assert not credential_pool_matches_provider(
        "custom:relay-b",
        "custom",
        base_url="https://other.example.test/v1",
        requested_provider="custom:relay-b",
    )


def test_named_custom_pool_maps_provider_key_to_display_name_pool(
    tmp_path, monkeypatch
):
    import yaml

    from agent.credential_pool import get_custom_provider_pool_key

    home = tmp_path / "hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    relay_url = "https://relay.example.test/v1"
    (home / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "providers": {
                    "relay-a-id": {
                        "name": "Relay A",
                        "base_url": relay_url,
                    },
                    "relay-b-id": {
                        "name": "Relay B",
                        "base_url": relay_url,
                    },
                }
            }
        )
    )

    assert get_custom_provider_pool_key(
        relay_url,
        provider_name="relay-b-id",
    ) == "custom:relay-b"
    assert credential_pool_matches_provider(
        "custom:relay-b",
        "custom",
        base_url=relay_url,
        requested_provider="custom:relay-b-id",
    )
    assert not credential_pool_matches_provider(
        "custom:relay-a",
        "custom",
        base_url=relay_url,
        requested_provider="custom:relay-b-id",
    )


def test_runtime_ignores_pool_loaded_for_different_provider(monkeypatch):
    entry = SimpleNamespace(
        provider="openai-codex",
        access_token="wrong-token",
        runtime_api_key="wrong-token",
        runtime_base_url="https://chatgpt.com/backend-api/codex",
        base_url="https://chatgpt.com/backend-api/codex",
    )
    pool = SimpleNamespace(
        provider="openai-codex",
        has_credentials=lambda: True,
        select=lambda: entry,
    )
    monkeypatch.setattr(rp, "load_pool", lambda _provider: pool)
    monkeypatch.setattr(rp, "resolve_provider", lambda *_a, **_kw: "deepseek")
    monkeypatch.setattr(
        rp,
        "_get_model_config",
        lambda: {"provider": "deepseek", "default": "deepseek-chat"},
    )
    monkeypatch.setattr(
        rp,
        "resolve_api_key_provider_credentials",
        lambda _provider: {
            "provider": "deepseek",
            "api_key": "deepseek-key",
            "base_url": "https://api.deepseek.com/v1",
            "source": "env",
        },
    )

    resolved = rp.resolve_runtime_provider(requested="deepseek")

    assert resolved["provider"] == "deepseek"
    assert resolved["api_key"] == "deepseek-key"
    assert resolved["base_url"] == "https://api.deepseek.com/v1"
