"""Context engines retain named custom provider identity safely."""

from unittest.mock import patch

import pytest

from agent.context_compressor import ContextCompressor
from agent.context_engine import update_context_engine_model


def _compressor(requested_provider="custom:relay-a", api_key="key-a"):
    with patch(
        "agent.context_compressor.get_model_context_length",
        return_value=131_072,
    ) as resolve_context:
        compressor = ContextCompressor(
            model="shared-model",
            base_url="https://relay.example.test/v1",
            api_key=api_key,
            provider="custom",
            requested_provider=requested_provider,
            quiet_mode=True,
        )
    return compressor, resolve_context


def test_compressor_initial_context_resolution_receives_requested_provider():
    compressor, resolve_context = _compressor()

    assert compressor.requested_provider == "custom:relay-a"
    assert resolve_context.call_args.kwargs["provider"] == "custom"
    assert (
        resolve_context.call_args.kwargs["requested_provider"]
        == "custom:relay-a"
    )


def test_compressor_clears_probe_state_when_named_route_changes():
    compressor, _resolve_context = _compressor()
    compressor._context_probed = True
    compressor._context_probe_persistable = True

    compressor.update_model(
        model="shared-model",
        context_length=262_144,
        base_url="https://relay.example.test/v1",
        api_key="key-b",
        provider="custom",
        api_mode="chat_completions",
        requested_provider="custom:relay-b",
    )

    assert compressor.requested_provider == "custom:relay-b"
    assert compressor._context_probed is False
    assert compressor._context_probe_persistable is False


def test_compressor_clears_probe_state_when_named_route_key_rotates():
    compressor, _resolve_context = _compressor()
    compressor._context_probed = True
    compressor._context_probe_persistable = True

    compressor.update_model(
        model="shared-model",
        context_length=131_072,
        base_url="https://relay.example.test/v1",
        api_key="rotated-key-a",
        provider="custom",
        requested_provider="custom:relay-a",
    )

    assert compressor._context_probed is False
    assert compressor._context_probe_persistable is False


def test_context_engine_update_keeps_old_plugin_signature_compatible():
    class OldEngine:
        def __init__(self):
            self.call = None

        def update_model(
            self,
            model,
            context_length,
            base_url="",
            api_key="",
            provider="",
            api_mode="",
        ):
            self.call = {
                "model": model,
                "context_length": context_length,
                "provider": provider,
            }

    engine = OldEngine()
    update_context_engine_model(
        engine,
        model="shared-model",
        context_length=131_072,
        provider="custom",
        requested_provider="custom:relay-a",
    )

    assert engine.call == {
        "model": "shared-model",
        "context_length": 131_072,
        "provider": "custom",
    }


def test_context_engine_update_does_not_hide_plugin_type_error():
    class BrokenEngine:
        def update_model(self, **_kwargs):
            raise TypeError("plugin implementation failed")

    with pytest.raises(TypeError, match="plugin implementation failed"):
        update_context_engine_model(
            BrokenEngine(),
            model="shared-model",
            context_length=131_072,
            provider="custom",
            requested_provider="custom:relay-a",
        )
