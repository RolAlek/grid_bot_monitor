from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Router

from source.application.services.decision_log_service import DecisionLogService
from source.application.services.run_daily_positioning_check import RunDailyPositioningCheck
from source.application.services.run_weekly_full_assessment import RunWeeklyFullAssessment
from source.domain.value_objects import VerdictAction
from source.presentation.bot.handlers.decision_handlers import decision_router
from tests.fixtures.factories import make_decision_verdict


def _make_message(**kwargs: object) -> AsyncMock:
    msg = AsyncMock()
    msg.answer = AsyncMock()
    msg.reply = AsyncMock()
    msg.from_user = MagicMock()
    msg.from_user.id = 42
    msg.from_user.username = "testuser"
    msg.bot = AsyncMock()
    msg.chat = MagicMock()
    msg.chat.id = 12345
    msg.text = ""

    for key, value in kwargs.items():
        setattr(msg, key, value)

    return msg


def _answer_text(msg: AsyncMock) -> str:
    if msg.answer.call_args is None:
        return ""
    if msg.answer.call_args.args:
        return str(msg.answer.call_args.args[0])
    return str(msg.answer.call_args.kwargs.get("text", ""))


def _get_handler(router: Router, name: str) -> object:
    for observer in router.message.handlers:
        if name in observer.callback.__name__:
            return observer.callback
    raise LookupError(f"No handler matching '{name}' found in router")


@pytest.fixture
def mock_weekly_runner() -> AsyncMock:
    mock = AsyncMock(spec=RunWeeklyFullAssessment)
    mock.run = AsyncMock()
    return mock


@pytest.fixture
def mock_daily_runner() -> AsyncMock:
    mock = AsyncMock(spec=RunDailyPositioningCheck)
    mock.run = AsyncMock()
    return mock


@pytest.fixture
def mock_decision_service() -> AsyncMock:
    mock = AsyncMock(spec=DecisionLogService)
    mock.get_last_decision = AsyncMock(return_value=None)
    return mock


def test_router_factory_creates_independent_routers(
    mock_weekly_runner: AsyncMock,
    mock_daily_runner: AsyncMock,
    mock_decision_service: AsyncMock,
) -> None:
    router_a = decision_router(mock_weekly_runner, mock_daily_runner, mock_decision_service)
    router_b = decision_router(mock_weekly_runner, mock_daily_runner, mock_decision_service)

    assert router_a is not router_b
    assert isinstance(router_a, Router)
    assert isinstance(router_b, Router)


async def test_weekly_assessment_calls_runner(
    mock_weekly_runner: AsyncMock,
    mock_daily_runner: AsyncMock,
    mock_decision_service: AsyncMock,
) -> None:
    router = decision_router(mock_weekly_runner, mock_daily_runner, mock_decision_service)
    handler = _get_handler(router, "handle_assess")
    message = _make_message()

    await handler(message)

    mock_weekly_runner.run.assert_called()
    message.reply.assert_called_once()


async def test_weekly_assessment_handles_runner_error(
    mock_weekly_runner: AsyncMock,
    mock_daily_runner: AsyncMock,
    mock_decision_service: AsyncMock,
) -> None:
    mock_weekly_runner.run.side_effect = RuntimeError("boom")
    router = decision_router(mock_weekly_runner, mock_daily_runner, mock_decision_service)
    handler = _get_handler(router, "handle_assess")
    message = _make_message()

    await handler(message)

    message.answer.assert_called()
    text = _answer_text(message)
    assert "fail" in text.lower() or "check" in text.lower()


async def test_verdict_no_decision_shows_prompt(
    mock_weekly_runner: AsyncMock,
    mock_daily_runner: AsyncMock,
    mock_decision_service: AsyncMock,
) -> None:
    mock_decision_service.get_last_decision.return_value = None
    router = decision_router(mock_weekly_runner, mock_daily_runner, mock_decision_service)
    handler = _get_handler(router, "handle_verdict")
    message = _make_message()

    await handler(message)

    text = _answer_text(message)
    assert "no verdict" in text.lower() or "/assess" in text.lower()


async def test_verdict_with_decision_shows_action(
    mock_weekly_runner: AsyncMock,
    mock_daily_runner: AsyncMock,
    mock_decision_service: AsyncMock,
) -> None:
    verdict = make_decision_verdict(action=VerdictAction.REVIEW)
    mock_decision_service.get_last_decision.return_value = verdict

    router = decision_router(mock_weekly_runner, mock_daily_runner, mock_decision_service)
    handler = _get_handler(router, "handle_verdict")
    message = _make_message()

    await handler(message)

    text = _answer_text(message)
    assert "REVIEW" in text or "review" in text.lower()
