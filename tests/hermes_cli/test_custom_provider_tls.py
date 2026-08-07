"""Tests for per-provider TLS settings in custom_providers config."""

from hermes_cli.config import (
    apply_custom_provider_tls_to_client_kwargs,
    custom_provider_matches_identity,
    get_custom_provider_tls_settings,
)


def test_get_custom_provider_tls_settings_matches_base_url():
    providers = [
        {
            "name": "Ollama",
            "base_url": "https://ollama.example.com/v1",
            "ssl_ca_cert": "/etc/ssl/mkcert-root.pem",
        }
    ]
    tls = get_custom_provider_tls_settings(
        "https://ollama.example.com/v1/",
        custom_providers=providers,
    )
    assert tls == {"ssl_ca_cert": "/etc/ssl/mkcert-root.pem"}


def test_apply_custom_provider_tls_to_client_kwargs():
    client_kwargs = {"api_key": "x", "base_url": "https://ollama.example.com/v1"}
    providers = [
        {
            "name": "Ollama",
            "base_url": "https://ollama.example.com/v1",
            "ssl_ca_cert": "/etc/ssl/mkcert-root.pem",
            "ssl_verify": True,
        }
    ]
    apply_custom_provider_tls_to_client_kwargs(
        client_kwargs,
        "https://ollama.example.com/v1",
        custom_providers=providers,
    )
    assert client_kwargs["ssl_ca_cert"] == "/etc/ssl/mkcert-root.pem"
    assert client_kwargs["ssl_verify"] is True


def test_get_custom_provider_tls_settings_matches_case_insensitively():
    """A config base_url with mixed case must still match a lowercased runtime base_url."""
    providers = [
        {
            "name": "Ollama",
            "base_url": "https://Ollama.Example.com/v1",
            "ssl_ca_cert": "/etc/ssl/mkcert-root.pem",
        }
    ]
    tls = get_custom_provider_tls_settings(
        "https://ollama.example.com/v1",
        custom_providers=providers,
    )
    assert tls == {"ssl_ca_cert": "/etc/ssl/mkcert-root.pem"}


def test_get_custom_provider_tls_settings_no_substring_bypass():
    """A base_url that is only a prefix of an entry must NOT match."""
    providers = [
        {
            "name": "Ollama",
            "base_url": "https://ollama.example.com/v1",
            "ssl_verify": False,
        }
    ]
    # A different host that shares a prefix must not pick up ssl_verify:false.
    assert get_custom_provider_tls_settings(
        "https://ollama.example.com.attacker.test/v1",
        custom_providers=providers,
    ) == {}


def test_get_custom_provider_tls_settings_preserves_extra_path_segment():
    providers = [
        {
            "base_url": "https://ollama.example.com/v1//",
            "ssl_verify": False,
        }
    ]

    assert get_custom_provider_tls_settings(
        "https://ollama.example.com/v1",
        custom_providers=providers,
    ) == {}


def test_same_url_tls_settings_are_scoped_by_provider_identity():
    providers = [
        {
            "name": "Relay A",
            "base_url": "https://relay.example.com/v1",
            "ssl_ca_cert": "/etc/ssl/relay-a.pem",
        },
        {
            "name": "Relay B",
            "base_url": "https://relay.example.com/v1",
            "ssl_verify": False,
        },
    ]

    assert get_custom_provider_tls_settings(
        "https://relay.example.com/v1",
        custom_providers=providers,
        provider_identity="custom:relay-b",
    ) == {"ssl_verify": False}
    assert get_custom_provider_tls_settings(
        "https://relay.example.com/v1",
        custom_providers=providers,
        provider_identity="custom:relay-a",
    ) == {"ssl_ca_cert": "/etc/ssl/relay-a.pem"}


def test_custom_identity_accepts_migrated_nested_prefixes_but_not_bad_spacing():
    entry = {"name": "Prefixed Key", "provider_key": "custom:Prefixed Key"}

    for identity in (
        "custom:Prefixed Key",
        "custom:custom:Prefixed Key",
        "custom:Prefixed-Key",
    ):
        assert custom_provider_matches_identity(entry, identity)

    assert not custom_provider_matches_identity(entry, "custom: Prefixed Key")
    assert not custom_provider_matches_identity(entry, "custom:\tPrefixed Key")
