"""Regression coverage for Telegram streamed final delivery."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import PlatformConfig
from gateway.platforms.base import SendResult
from gateway.stream_consumer import GatewayStreamConsumer, StreamConsumerConfig
from plugins.platforms.telegram.adapter import TelegramAdapter
from telegram.error import BadRequest


def _adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.REQUIRES_EDIT_FINALIZE = True
    adapter.FALLBACK_ON_FINAL_EDIT_FLOOD = True
    adapter.RESEND_FINAL_ON_EMPTY_STREAM_FALLBACK = True
    adapter.MAX_MESSAGE_LENGTH = 4096
    adapter.edit_message = AsyncMock()
    adapter.send = AsyncMock()
    adapter.delete_message = AsyncMock(return_value=True)
    return adapter


def _connected_telegram_adapter() -> TelegramAdapter:
    adapter = TelegramAdapter(PlatformConfig(
        enabled=True, token="test-token", extra={"rich_messages": True},
    ))
    message_ids = iter(range(1, 100))
    adapter._bot = SimpleNamespace(
        do_api_request=AsyncMock(return_value=SimpleNamespace(message_id=100)),
        send_message=AsyncMock(
            side_effect=lambda **kw: SimpleNamespace(message_id=next(message_ids)),
        ),
        send_message_draft=AsyncMock(return_value=True),
        send_chat_action=AsyncMock(),
        edit_message_text=AsyncMock(return_value=True),
        delete_message=AsyncMock(return_value=True),
    )
    return adapter


@pytest.mark.asyncio
@pytest.mark.parametrize("send_result", [
    SendResult(
        success=True, message_id="1", raw_response={"message_ids": ["1", "2"]},
    ),
    SendResult(success=True, message_id="2", continuation_message_ids=("2",)),
], ids=["send-message-ids", "continuation-message-ids"])
async def test_chunked_final_first_send_does_not_refinalize(send_result):
    """Re-editing the head with full text duplicates already-delivered tails."""
    adapter = _connected_telegram_adapter()
    adapter.send = AsyncMock(return_value=send_result)
    adapter.edit_message = AsyncMock(return_value=SendResult(success=True))
    consumer = GatewayStreamConsumer(adapter, "12345")
    consumer.on_delta("line\n" * 1000)
    consumer.finish()

    await consumer.run()

    adapter.send.assert_awaited_once()
    adapter.edit_message.assert_not_awaited()
    assert consumer.final_response_sent is True
    assert consumer.final_content_delivered is True


@pytest.mark.asyncio
@pytest.mark.parametrize("rows", [1, 60], ids=["short", "over-legacy-limit"])
async def test_draft_final_first_send_preserves_rich_table(rows):
    """A draft has no message id; its durable final should use rich sending."""
    adapter = _connected_telegram_adapter()
    text = "| Item | Detail |\n|---|---|\n" + "\n".join(
        f"| entry{i:04d} | {'x' * 80} |" for i in range(rows)
    )
    draft_sent = asyncio.Event()

    async def send_draft(**kwargs):
        draft_sent.set()
        return True

    adapter._bot.send_message_draft.side_effect = send_draft
    consumer = GatewayStreamConsumer(
        adapter, "12345", StreamConsumerConfig(transport="auto", chat_type="dm"),
        initial_reply_to_id="42",
    )
    consumer.on_delta(text)
    task = asyncio.create_task(consumer.run())
    try:
        await asyncio.wait_for(draft_sent.wait(), timeout=5)
        assert consumer.message_id is None
        assert consumer.already_sent is False
    finally:
        consumer.finish()
        await asyncio.wait_for(task, timeout=5)

    rich_sends = [
        call for call in adapter._bot.do_api_request.await_args_list
        if call.args[0] == "sendRichMessage"
    ]
    assert len(rich_sends) == 1
    payload = rich_sends[0].kwargs["api_kwargs"]
    assert payload["rich_message"]["markdown"] == text
    assert payload["reply_parameters"] == {"message_id": 42}
    adapter._bot.send_message.assert_not_awaited()
    adapter._bot.edit_message_text.assert_not_awaited()
    assert consumer.final_response_sent is True
    assert consumer.final_content_delivered is True


@pytest.mark.asyncio
@pytest.mark.parametrize("rich_rejected", [False, True], ids=["plain", "rich-fallback"])
async def test_final_first_send_legacy_chunks_deliver_each_row_once(rich_rejected):
    """Real legacy splitting, including rich fallback, must not re-edit the head."""
    adapter = _connected_telegram_adapter()
    rows = [f"entry{i:04d} {'x' * 80}" for i in range(60)]
    text = "\n".join(rows)
    if rich_rejected:
        text = "| Item | Detail |\n|---|---|\n" + "\n".join(
            f"| {row} | detail |" for row in rows
        )
        adapter._bot.do_api_request.side_effect = BadRequest("can't parse rich message")
    expected_chunks = adapter.truncate_message(
        adapter.format_message(text), adapter.MAX_MESSAGE_LENGTH,
    )
    assert len(expected_chunks) > 1
    consumer = GatewayStreamConsumer(adapter, "12345")
    consumer.on_delta(text)
    consumer.finish()

    await consumer.run()

    # A rejected rich send can create and retract a tiny placeholder first.
    visible_chunks = [
        call.kwargs["text"] for call in adapter._bot.send_message.await_args_list
        if call.kwargs["text"] != "..."
    ]
    assert len(visible_chunks) == len(expected_chunks)
    visible_text = "\n".join(visible_chunks)
    for i in range(len(rows)):
        assert visible_text.count(f"entry{i:04d}") == 1
    adapter._bot.edit_message_text.assert_not_awaited()
    if rich_rejected:
        assert [
            call.args[0] for call in adapter._bot.do_api_request.await_args_list
        ] == ["sendRichMessage", "editMessageText"]
    else:
        adapter._bot.do_api_request.assert_not_awaited()
    assert consumer.final_response_sent is True
    assert consumer.final_content_delivered is True


@pytest.mark.asyncio
async def test_turn_final_flood_immediately_delivers_missing_tail():
    """A short visible preview must not suppress the completed answer."""
    adapter = _adapter()
    adapter.edit_message.return_value = SendResult(
        success=False,
        error="Flood control exceeded. Retry in 180 seconds",
        retry_after=180.0,
    )
    adapter.send.return_value = SendResult(success=True, message_id="tail-1")

    consumer = GatewayStreamConsumer(
        adapter,
        "chat-1",
        StreamConsumerConfig(cursor=" ▉"),
        metadata={"thread_id": "77"},
    )
    consumer._message_id = "preview-1"
    consumer._last_sent_text = ":("
    consumer._already_sent = True

    ok = await consumer._send_or_edit(
        ":( The completed answer follows here.",
        finalize=True,
        is_turn_final=True,
    )

    assert ok is False
    assert consumer._flood_strikes == 1
    assert consumer._fallback_final_send is True
    assert consumer.final_content_delivered is False
    assert adapter.edit_message.await_count == 1

    await consumer._send_fallback_final(":( The completed answer follows here.")

    adapter.send.assert_awaited_once()
    assert adapter.send.await_args.kwargs["content"] == "The completed answer follows here."
    assert adapter.send.await_args.kwargs["metadata"] == {
        "thread_id": "77",
        "notify": True,
    }
    adapter.delete_message.assert_not_awaited()
    assert consumer.final_response_sent is True
    assert consumer.final_content_delivered is True


@pytest.mark.asyncio
async def test_non_opt_in_adapter_keeps_adaptive_final_edit_retry():
    """Immediate final fallback remains scoped to opted-in adapters."""
    adapter = _adapter()
    adapter.FALLBACK_ON_FINAL_EDIT_FLOOD = False
    adapter.edit_message.return_value = SendResult(
        success=False,
        error="Flood control exceeded. Retry in 30 seconds",
        retry_after=30.0,
    )

    consumer = GatewayStreamConsumer(adapter, "chat-1")
    consumer._message_id = "preview-1"
    consumer._last_sent_text = "partial"
    consumer._already_sent = True

    ok = await consumer._send_or_edit(
        "partial plus final",
        finalize=True,
        is_turn_final=True,
    )

    assert ok is False
    assert consumer._flood_strikes == 1
    assert consumer._fallback_final_send is False


@pytest.mark.asyncio
async def test_turn_final_flood_commits_empty_tail_as_fresh_message():
    """Telegram gets a durable final even when the internal tail is empty."""
    adapter = _adapter()
    adapter.edit_message.return_value = SendResult(
        success=False,
        error="Flood control exceeded. Retry in 30 seconds",
        retry_after=30.0,
    )
    adapter.send.return_value = SendResult(success=True, message_id="final-1")

    consumer = GatewayStreamConsumer(
        adapter,
        "chat-1",
        StreamConsumerConfig(cursor=" ▉"),
    )
    final_text = "The complete answer"
    consumer._message_id = "preview-1"
    consumer._preview_message_ids = {"preview-1"}
    consumer._last_sent_text = f"{final_text} ▉"
    consumer._already_sent = True

    ok = await consumer._send_or_edit(
        final_text,
        finalize=True,
        is_turn_final=True,
    )

    assert ok is False
    assert consumer._fallback_final_send is True
    assert consumer.final_content_delivered is True
    assert adapter.edit_message.await_count == 1

    await consumer._send_fallback_final(final_text)

    adapter.send.assert_awaited_once()
    assert adapter.send.await_args.kwargs["content"] == final_text
    assert adapter.send.await_args.kwargs["metadata"] == {"notify": True}
    adapter.delete_message.assert_awaited_once_with("chat-1", "preview-1")
    assert consumer.message_id == "final-1"
    assert consumer.final_response_sent is True
    assert consumer.final_content_delivered is True


@pytest.mark.asyncio
async def test_empty_tail_commit_honors_retry_after(monkeypatch):
    adapter = _adapter()
    adapter.send.side_effect = [
        SendResult(
            success=False,
            error="Flood control exceeded",
            retry_after=3.0,
        ),
        SendResult(success=True, message_id="final-1"),
    ]
    sleep = AsyncMock()
    monkeypatch.setattr("gateway.stream_consumer.asyncio.sleep", sleep)

    consumer = GatewayStreamConsumer(adapter, "chat-1")
    consumer._message_id = "preview-1"
    consumer._last_sent_text = "Final answer"
    consumer._fallback_final_send = True

    await consumer._send_fallback_final("Final answer")

    assert adapter.send.await_count == 2
    sleep.assert_awaited_once_with(3.0)
    assert consumer.final_content_delivered is True


@pytest.mark.asyncio
async def test_empty_tail_recovery_keeps_prior_segment_messages():
    """Recovery replaces only its current preview, not earlier preambles."""
    adapter = _adapter()
    adapter.send.return_value = SendResult(success=True, message_id="final-1")
    consumer = GatewayStreamConsumer(adapter, "chat-1")

    consumer._track_preview_id("preamble-1")
    consumer._reset_segment_state()
    consumer._track_preview_id("preview-1")
    consumer._message_id = "preview-1"
    consumer._last_sent_text = "Final answer"
    consumer._fallback_final_send = True

    await consumer._send_fallback_final("Final answer")

    adapter.delete_message.assert_awaited_once_with("chat-1", "preview-1")
    assert "preamble-1" in consumer._preview_message_ids


@pytest.mark.asyncio
async def test_empty_tail_commit_skips_long_flood_retry(monkeypatch):
    adapter = _adapter()
    adapter.send.return_value = SendResult(
        success=False,
        error="flood_control:30.0",
        retry_after=30.0,
    )
    sleep = AsyncMock()
    monkeypatch.setattr("gateway.stream_consumer.asyncio.sleep", sleep)

    consumer = GatewayStreamConsumer(adapter, "chat-1")
    consumer._message_id = "preview-1"
    consumer._last_sent_text = "Final answer"
    consumer._fallback_final_send = True

    await consumer._send_fallback_final("Final answer")

    adapter.send.assert_awaited_once()
    sleep.assert_not_awaited()
    assert consumer.final_response_sent is False
    assert consumer.final_content_delivered is False


@pytest.mark.asyncio
async def test_telegram_long_flood_result_keeps_retry_after():
    """The real adapter contract preserves the server delay for consumers."""
    class FloodError(Exception):
        retry_after = 30.0

    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="test-token"))
    adapter._bot = MagicMock()
    adapter._bot.edit_message_text = AsyncMock(side_effect=FloodError("Retry after 30"))

    result = await adapter.edit_message("123", "456", "Final answer", finalize=False)

    assert result.success is False
    assert result.error == "flood_control:30.0"
    assert result.retry_after == 30.0


@pytest.mark.asyncio
async def test_ambiguous_empty_tail_timeout_preserves_duplicate_suppression():
    adapter = _adapter()
    adapter.send.return_value = SimpleNamespace(
        success=False,
        error="Timed out",
        retryable=False,
    )

    consumer = GatewayStreamConsumer(adapter, "chat-1")
    consumer._message_id = "preview-1"
    consumer._last_sent_text = "Final answer"
    consumer._fallback_final_send = True

    await consumer._send_fallback_final("Final answer")

    adapter.delete_message.assert_not_awaited()
    assert consumer.final_response_sent is False
    assert consumer.final_content_delivered is True


@pytest.mark.asyncio
async def test_confirmed_empty_tail_send_failure_allows_gateway_retry():
    adapter = _adapter()
    adapter.send.return_value = SendResult(
        success=False,
        error="network unavailable",
        retryable=False,
    )

    consumer = GatewayStreamConsumer(adapter, "chat-1")
    consumer._message_id = "preview-1"
    consumer._last_sent_text = "Final answer"
    consumer._fallback_final_send = True
    consumer._final_content_delivered = True

    await consumer._send_fallback_final("Final answer")

    adapter.delete_message.assert_not_awaited()
    assert consumer.final_response_sent is False
    assert consumer.final_content_delivered is False


def test_timeout_exception_is_treated_as_ambiguous_delivery():
    class TimedOut(Exception):
        pass

    assert GatewayStreamConsumer._send_failure_may_have_delivered(
        TimedOut("request timed out")
    ) is True
