"""Telegram Bot API 10.0 native Guest Mode integration tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import PlatformConfig
from gateway.platforms.base import MessageType, _thread_metadata_for_source
from plugins.platforms.telegram.adapter import TelegramAdapter


OWNER_ID = "6464333549"


def _make_adapter(*, guest_allow_from=None, rich_messages=False):
    extra = {
        "native_guest_mode": True,
        "rich_messages": rich_messages,
    }
    if guest_allow_from is not None:
        extra["guest_allow_from"] = guest_allow_from
    adapter = TelegramAdapter(
        PlatformConfig(enabled=True, token="fake-token", extra=extra)
    )
    adapter._bot = MagicMock()
    adapter._bot.username = "louishermesagentbot"
    adapter._bot.do_api_request = AsyncMock(
        return_value={"inline_message_id": "guest-inline-1"}
    )
    adapter.handle_message = AsyncMock()
    return adapter


def _guest_message(*, user_id=OWNER_ID, query_id="guest-query-1"):
    return SimpleNamespace(
        message_id=77,
        text="@louishermesagentbot hello from another group",
        caption=None,
        entities=[],
        caption_entities=[],
        message_thread_id=None,
        is_topic_message=False,
        chat=SimpleNamespace(
            id=-100123,
            type="supergroup",
            title="Guest Test",
            full_name=None,
            is_forum=False,
        ),
        from_user=SimpleNamespace(
            id=int(user_id),
            username="owner",
            full_name="Owner",
            first_name="Owner",
            is_bot=False,
        ),
        reply_to_message=None,
        date=None,
        api_kwargs={"guest_query_id": query_id},
    )


@pytest.mark.asyncio
async def test_guest_update_dispatches_owner_message_with_one_shot_route():
    adapter = _make_adapter(guest_allow_from=[OWNER_ID])
    update = SimpleNamespace(
        update_id=101,
        guest_message=_guest_message(),
        api_kwargs={},
    )

    await adapter._handle_guest_update(update, None)

    adapter.handle_message.assert_awaited_once()
    event = adapter.handle_message.await_args.args[0]
    assert event.message_type == MessageType.TEXT
    assert event.text == "hello from another group"
    assert event.source.user_id == OWNER_ID
    assert event.source.chat_id == "-100123"
    assert event.source.chat_type == "group"
    assert event.source.telegram_guest_query_id == "guest-query-1"
    assert event.source.telegram_guest_authorized is True
    assert event.metadata["telegram_native_guest"] is True


@pytest.mark.asyncio
async def test_guest_update_rejects_non_owner_before_agent_dispatch():
    adapter = _make_adapter(guest_allow_from=[OWNER_ID])
    update = SimpleNamespace(
        update_id=102,
        guest_message=_guest_message(user_id="123456"),
        api_kwargs={},
    )

    await adapter._handle_guest_update(update, None)

    adapter.handle_message.assert_not_awaited()


def test_guest_query_route_is_carried_to_delivery_metadata():
    source = SimpleNamespace(
        platform=SimpleNamespace(value="telegram"),
        chat_type="group",
        thread_id=None,
        telegram_guest_query_id="guest-query-1",
    )

    assert _thread_metadata_for_source(source) == {
        "telegram_guest_query_id": "guest-query-1"
    }


def test_guest_query_route_and_authorization_are_not_serialized():
    from gateway.config import Platform
    from gateway.session import SessionSource

    source = SessionSource(
        platform=Platform.TELEGRAM,
        chat_id="-100123",
        chat_type="group",
        user_id=OWNER_ID,
        telegram_guest_query_id="guest-query-1",
        telegram_guest_authorized=True,
    )

    stored = source.to_dict()

    assert "telegram_guest_query_id" not in stored
    assert "telegram_guest_authorized" not in stored


def test_guest_query_route_and_authorization_are_removed_from_live_source_cache():
    from collections import OrderedDict

    from gateway.config import Platform
    from gateway.run import GatewayRunner
    from gateway.session import SessionSource

    runner = object.__new__(GatewayRunner)
    runner._session_sources = OrderedDict()
    runner._session_sources_max = 8
    source = SessionSource(
        platform=Platform.TELEGRAM,
        chat_id="-100123",
        chat_type="group",
        user_id=OWNER_ID,
        telegram_guest_query_id="guest-query-1",
        telegram_guest_authorized=True,
    )

    runner._cache_session_source("guest-session", source)
    cached = runner._get_cached_session_source("guest-session")

    assert cached.telegram_guest_query_id is None
    assert cached.telegram_guest_authorized is False
    assert source.telegram_guest_query_id == "guest-query-1"


@pytest.mark.asyncio
async def test_guest_reply_uses_answer_guest_query_instead_of_send_message():
    adapter = _make_adapter()
    adapter._bot.send_message = AsyncMock()

    result = await adapter.send(
        "-100123",
        "Guest reply",
        metadata={"telegram_guest_query_id": "guest-query-1", "notify": True},
    )

    assert result.success is True
    assert result.message_id == "guest-inline-1"
    adapter._bot.send_message.assert_not_awaited()
    adapter._bot.do_api_request.assert_awaited_once()
    call = adapter._bot.do_api_request.await_args
    assert call.args[0] == "answerGuestQuery"
    assert call.kwargs["api_kwargs"]["guest_query_id"] == "guest-query-1"
    guest_result = call.kwargs["api_kwargs"]["result"]
    assert guest_result["type"] == "article"
    assert guest_result["input_message_content"]["message_text"]


@pytest.mark.asyncio
async def test_guest_reply_uses_rich_message_content_for_markdown_table():
    adapter = _make_adapter(rich_messages=True)
    table = (
        "| 模型 | IQ |\n"
        "|---|---:|\n"
        "| Sol | 92 |"
    )

    result = await adapter.send(
        "-100123",
        table,
        metadata={"telegram_guest_query_id": "guest-query-1", "notify": True},
    )

    assert result.success is True
    call = adapter._bot.do_api_request.await_args
    assert call.args[0] == "answerGuestQuery"
    guest_result = call.kwargs["api_kwargs"]["result"]
    input_content = guest_result["input_message_content"]
    assert input_content["rich_message"]["markdown"] == table
    assert "message_text" not in input_content


def test_allowed_updates_include_native_guest_messages():
    adapter = _make_adapter()

    allowed = adapter._telegram_allowed_updates()

    assert "guest_message" in {getattr(item, "value", item) for item in allowed}


@pytest.mark.asyncio
async def test_guest_reply_failure_is_not_retried_or_plaintext_resent():
    adapter = _make_adapter()
    adapter._bot.do_api_request = AsyncMock(side_effect=RuntimeError("expired query"))

    result = await adapter._send_with_retry(
        "-100123",
        "Guest reply",
        metadata={"telegram_guest_query_id": "guest-query-1", "notify": True},
    )

    assert result.success is False
    assert adapter._bot.do_api_request.await_count == 1


@pytest.mark.asyncio
async def test_guest_reply_truncates_as_one_message_without_chunk_suffix():
    adapter = _make_adapter()

    result = await adapter.send(
        "-100123",
        "x" * 5000,
        metadata={"telegram_guest_query_id": "guest-query-1"},
    )

    assert result.success is True
    payload = adapter._bot.do_api_request.await_args.kwargs["api_kwargs"]
    message_text = payload["result"]["input_message_content"]["message_text"]
    assert message_text.endswith("…")
    assert "(1/" not in message_text
    assert len(message_text) == adapter.MAX_MESSAGE_LENGTH


def test_guest_compat_parser_accepts_raw_ptb_api_kwargs_shape():
    adapter = _make_adapter(guest_allow_from=[OWNER_ID])
    raw_message = {
        "message_id": 77,
        "date": 1785030000,
        "chat": {"id": -100123, "type": "supergroup", "title": "Guest Test"},
        "from": {
            "id": int(OWNER_ID),
            "is_bot": False,
            "first_name": "Owner",
        },
        "text": "@louishermesagentbot hello",
        "guest_query_id": "guest-query-raw",
    }
    update = SimpleNamespace(
        guest_message=None,
        api_kwargs={"guest_message": raw_message},
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "plugins.platforms.telegram.adapter.Message.de_json",
            lambda payload, bot: SimpleNamespace(
                text=payload["text"],
                api_kwargs={"guest_query_id": payload["guest_query_id"]},
            ),
        )
        message = adapter._guest_message_from_update(update)

    assert message is not None
    assert message.text == "@louishermesagentbot hello"
    assert adapter._guest_query_id(message) == "guest-query-raw"
