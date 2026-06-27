from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Router

from source.application.services.decision_log_service import DecisionLogService
from source.application.services.run_weekly_full_assessment import RunWeeklyFullAssessment
from source.domain.value_objects import VerdictAction
from source.presentation.bot.handlers.decision_handlers import router_factory
from tests.fixtures.factories import make_decision_verdict


@pytest.fixture
def mock_runner() -> AsyncMock:
    mock = AsyncMock(spec=RunWeeklyFullAssessment)
    verdict = make_decision_verdict(action=VerdictAction.LAUNCH)
    mock.run.return_value = verdict
    return mock


@pytest.fixture
def mock_decision_service() -> AsyncMock:
    mock = AsyncMock(spec=DecisionLogService)
    mock.get_last_decision = AsyncMock(return_value=None)
    return mock


def _make_message(**kwargs: object) -> AsyncMock:
    msg = AsyncMock()
    msg.answer = AsyncMock()
    msg.from_user = MagicMock()
    msg.from_user.id = 42

    for key, value in kwargs.items():
        setattr(msg, key, value)

    return msg


def test_router_factory_creates_independent_routers(mock_runner: AsyncMock, mock_decision_service: AsyncMock) -> None:
    router_a = router_factory(mock_runner, mock_decision_service)
    router_b = router_factory(mock_runner, mock_decision_service)

    assert router_a is not router_b
    assert isinstance(router_a, Router)
    assert isinstance(router_b, Router)


async def test_assess_from_user_none_does_not_raise(mock_runner: AsyncMock, mock_decision_service: AsyncMock) -> None:
    router = router_factory(mock_runner, mock_decision_service)
    message = _make_message(from_user=None)

    handlers = list(router.message.handlers)
    assert len(handlers) >= 1, "Router must have at least one message handler"

    router_ = router_factory(mock_runner, mock_decision_service)

    for observer in router_.message.handlers:
        callback = observer.callback

        if "assess" in callback.__name__:
            await callback(message)
            break

    message.answer.assert_called()


async def test_assess_runner_raises_sends_failure_and_does_not_reraise(
    mock_decision_service: AsyncMock,
) -> None:
    failing_runner = AsyncMock(spec=RunWeeklyFullAssessment)
    failing_runner.run.side_effect = RuntimeError("boom")

    router = router_factory(failing_runner, mock_decision_service)
    message = _make_message()

    for observer in router.message.handlers:
        callback = observer.callback

        if "assess" in callback.__name__:
            await callback(message)
            break

    message.answer.assert_called()
    calls = [c.args[0] if c.args else c.kwargs.get("text", "") for c in message.answer.call_args_list]
    assert any(
        "fail" in str(call).lower() or "error" in str(call).lower() or "check" in str(call).lower() for call in calls
    )


async def test_verdict_no_decision_sends_prompt(mock_runner: AsyncMock, mock_decision_service: AsyncMock) -> None:
    mock_decision_service.get_last_decision.return_value = None
    router = router_factory(mock_runner, mock_decision_service)
    message = _make_message()

    for observer in router.message.handlers:
        callback = observer.callback

        if "verdict" in callback.__name__:
            await callback(message)
            break

    text = (
        message.answer.call_args.args[0]
        if message.answer.call_args.args
        else message.answer.call_args.kwargs.get("text", "")
    )
    assert "/assess" in text or "no verdict" in text.lower() or "run" in text.lower()


async def test_verdict_with_decision_shows_action(mock_runner: AsyncMock, mock_decision_service: AsyncMock) -> None:
    verdict = make_decision_verdict(action=VerdictAction.REVIEW)
    mock_decision_service.get_last_decision.return_value = verdict

    router = router_factory(mock_runner, mock_decision_service)
    message = _make_message()

    for observer in router.message.handlers:
        callback = observer.callback
        if "verdict" in callback.__name__:
            await callback(message)
            break

    text = (
        message.answer.call_args.args[0]
        if message.answer.call_args.args
        else message.answer.call_args.kwargs.get("text", "")
    )
    assert "REVIEW" in text or "review" in text.lower()
