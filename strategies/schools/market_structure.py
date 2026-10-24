"""Fresh completed-close break of a prior ten-bar price structure."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from strategies.base import (
    Direction,
    Signal,
    Strategy,
    completed_prefix,
    mean_true_range,
)


class MarketStructure(Strategy):
    INPUTS = ("OHLC", "tick", "spread", "session")
    CONFIRMATION = "fresh completed close beyond prior ten-bar high or low"
    INVALIDATION = "quote re-enters the prior range before entry"
    TIMEFRAME = "M15"
    MINIMUM_BARS = 16

    def evaluate(
        self,
        bars: Sequence[Mapping[str, Any]],
        tick: Mapping[str, Any],
        ctx: Mapping[str, Any],
    ) -> Signal:
        visible = completed_prefix(bars, ctx)
        none = lambda reason: Signal(Direction.NONE, 0, None, None, reason)
        if len(visible) < self.MINIMUM_BARS or not ctx.get("session_open", False):
            return none("MISSING_CLOSED_BARS_OR_SESSION")
        previous_range = visible[-11:-1]
        high = max(float(bar["high"]) for bar in previous_range)
        low = min(float(bar["low"]) for bar in previous_range)
        previous_close = float(visible[-2]["close"])
        close = float(visible[-1]["close"])
        atr = mean_true_range(visible)
        if atr <= 0:
            return none("ATR_UNAVAILABLE")
        buy = previous_close <= high and close > high + 0.05 * atr
        sell = previous_close >= low and close < low - 0.05 * atr
        if buy == sell:
            return none("NO_FRESH_STRUCTURE_BREAK")
        bid, ask = float(tick["bid"]), float(tick["ask"])
        spread = ask - bid
        if spread < 0:
            return none("INVALID_QUOTE")
        if buy:
            if bid <= high:
                return none("INVALIDATED_PRE_ENTRY")
            stop = min(low, close - atr) - 0.1 * atr
            target = close + 2 * (close - stop)
            direction = Direction.BUY
        else:
            if ask >= low:
                return none("INVALIDATED_PRE_ENTRY")
            stop = max(high, close + atr) + 0.1 * atr
            target = close - 2 * (stop - close)
            direction = Direction.SELL
        if stop <= 0 or target <= 0 or not self.cost_is_eligible(spread, abs(target - close)):
            return none("COST_OR_BRACKET_REJECTED")
        return Signal(direction, 0.6, stop, target, "FRESH_TEN_BAR_STRUCTURE_BREAK")
