from uuid import uuid4

from source.domain.value_objects import HealthStatus
from source.presentation.bot.keyboards.inlines import BotActionCD, build_health_kb


class TestBuildHealthKb:
    _BOT_OID = uuid4().hex
    _SYMBOL = "BTC_USDT_PERP"

    def _buttons(self, status: HealthStatus) -> list[str]:
        kb = build_health_kb(status=status, symbol=self._SYMBOL, bot_oid=self._BOT_OID)
        return [btn.text for row in kb.inline_keyboard for btn in row]

    def test_green_has_pause_and_close_only(self) -> None:
        buttons = self._buttons(HealthStatus.GREEN)
        assert "⏸️ Pause" in buttons
        assert "❌ Close" in buttons
        assert "🔄 Reconfigure" not in buttons
        assert "✅ Acknowledge" not in buttons
        assert "📊 Details" not in buttons

    def test_yellow_adds_reconfigure_and_details(self) -> None:
        buttons = self._buttons(HealthStatus.YELLOW)
        assert "⏸️ Pause" in buttons
        assert "❌ Close" in buttons
        assert "🔄 Reconfigure" in buttons
        assert "📊 Details" in buttons
        assert "✅ Acknowledge" not in buttons

    def test_red_adds_all_buttons(self) -> None:
        buttons = self._buttons(HealthStatus.RED)
        assert "⏸️ Pause" in buttons
        assert "❌ Close" in buttons
        assert "🔄 Reconfigure" in buttons
        assert "📊 Details" in buttons
        assert "✅ Acknowledge" in buttons

    def test_callback_data_contains_correct_values(self) -> None:
        kb = build_health_kb(status=HealthStatus.GREEN, symbol=self._SYMBOL, bot_oid=self._BOT_OID)
        for row in kb.inline_keyboard:
            for btn in row:
                cd = BotActionCD.unpack(btn.callback_data)
                assert cd.symbol == self._SYMBOL
                assert cd.bot_oid == self._BOT_OID
