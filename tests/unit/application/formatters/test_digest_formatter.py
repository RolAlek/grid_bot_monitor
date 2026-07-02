from unittest.mock import AsyncMock

import pytest

from source.domain.entities import GateResult
from source.domain.value_objects import Gate, GateStatus, VerdictAction
from source.infrastructure.telegram.aiogram_notifier import AiogramNotifier
from tests.fixtures.factories import make_decision_verdict, make_gate_result, make_proposed_grid_params


@pytest.fixture
def send_message_mock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def notifier(send_message_mock: AsyncMock) -> AiogramNotifier:
    bot = AsyncMock()
    bot.send_message = send_message_mock
    return AiogramNotifier(bot=bot, chat_id=123)


async def test_suggested_range_omitted_when_none(
    notifier: AiogramNotifier,
    send_message_mock: AsyncMock,
) -> None:
    verdict = make_decision_verdict(
        action=VerdictAction.HOLD,
        suggested_parameters=None,
        gates=(make_gate_result(Gate.REGIME_RANGE_FIT, GateStatus.FAIL, ("adx too high",)),),
    )
    await notifier.send_digest(verdict)
    text = send_message_mock.call_args.kwargs["text"]
    assert "None" not in text


async def test_digest_gate_reason_present(
    notifier: AiogramNotifier,
    send_message_mock: AsyncMock,
) -> None:
    gate = GateResult(
        gate=Gate.POSITIONING,
        status=GateStatus.CAUTION,
        reasons=("high funding", "crowded long", "OI rising"),
        raw_values={},
    )
    verdict = make_decision_verdict(action=VerdictAction.REVIEW, gates=(gate,))
    await notifier.send_digest(verdict)
    text = send_message_mock.call_args.kwargs["text"]
    assert "high funding" in text


async def test_launch_verdict_includes_confirm_prompt(
    notifier: AiogramNotifier,
    send_message_mock: AsyncMock,
) -> None:
    verdict = make_decision_verdict(
        action=VerdictAction.LAUNCH,
        oid="vdct-001",
        suggested_parameters=make_proposed_grid_params(top=100_000.0, bottom=88_000.0, leverage=3),
        gates=(make_gate_result(Gate.REGIME_RANGE_FIT, GateStatus.PASS),),
    )
    await notifier.send_digest(verdict)
    reply_markup = send_message_mock.call_args.kwargs.get("reply_markup")
    assert reply_markup is not None


async def test_hold_verdict_excludes_confirm_prompt(
    notifier: AiogramNotifier,
    send_message_mock: AsyncMock,
) -> None:
    verdict = make_decision_verdict(
        action=VerdictAction.HOLD,
        suggested_parameters=None,
        gates=(make_gate_result(Gate.REGIME_RANGE_FIT, GateStatus.FAIL, ("adx too high",)),),
    )
    await notifier.send_digest(verdict)
    reply_markup = send_message_mock.call_args.kwargs.get("reply_markup")
    assert reply_markup is None
