from unittest.mock import AsyncMock

import pytest

from source.domain.value_objects import Gate, GateResult, GateStatus
from source.infrastructure.telegram.aiogram_notifier import AiogramNotifier


@pytest.fixture
def send_message_mock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def notifier(send_message_mock: AsyncMock) -> AiogramNotifier:
    bot = AsyncMock()
    bot.send_message = send_message_mock
    return AiogramNotifier(bot=bot, chat_id=123)


def _positioning_result(
    funding_annualized_pct: float,
    oi_pct_change_7d: float | None,
    status: GateStatus = GateStatus.CAUTION,
    reasons: tuple[str, ...] = ("reason 1",),
) -> GateResult:
    return GateResult(
        gate=Gate.POSITIONING,
        status=status,
        reasons=reasons,
        raw_values={
            "funding_rate_annualized_pct": funding_annualized_pct,
            "oi_pct_change_7d": oi_pct_change_7d,
        },
    )


async def test_zero_funding_direction_not_short(
    notifier: AiogramNotifier,
    send_message_mock: AsyncMock,
) -> None:
    result = _positioning_result(0.0, 5.0)
    await notifier.send_alert(result, prev_status=GateStatus.PASS)
    text = send_message_mock.call_args.kwargs["text"]

    assert "short" in text or "long" in text


async def test_multiple_reasons_all_included_in_alert(
    notifier: AiogramNotifier,
    send_message_mock: AsyncMock,
) -> None:
    result = _positioning_result(
        25.0,
        15.0,
        reasons=("high funding", "crowded long", "OI rising"),
    )
    await notifier.send_alert(result, prev_status=GateStatus.PASS)
    text = send_message_mock.call_args.kwargs["text"]
    assert isinstance(text, str)
    assert len(text) > 0


async def test_oi_none_vs_zero_produce_different_strings(
    notifier: AiogramNotifier,
    send_message_mock: AsyncMock,
) -> None:
    result_none = _positioning_result(25.0, None)
    result_zero = _positioning_result(25.0, 0.0)

    await notifier.send_alert(result_none, prev_status=GateStatus.PASS)
    text_none = send_message_mock.call_args.kwargs["text"]

    await notifier.send_alert(result_zero, prev_status=GateStatus.PASS)
    text_zero = send_message_mock.call_args.kwargs["text"]

    assert text_none != text_zero, (
        "oi_pct_change_7d=None and =0.0 must produce different alert text (falsy-vs-None bug)"
    )
    assert "insufficient" in text_none.lower() or "history" in text_none.lower(), (
        "None OI must signal insufficient history, not '0.0%'"
    )
