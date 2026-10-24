"""Completed-bar body engulfing with a pre-entry invalidation and structural stop."""
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


class PriceAction(Strategy):
    INPUTS = ("OHLC", "tick", "spread", "session")
    CONFIRMATION = "latest completed bar engulfs previous real body"
    INVALIDATION = "quote crosses the engulfed bar's far extreme before entry"
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
        previous, current = visible[-2], visible[-1]
        atr = mean_true_range(visible)
        if atr <= 0:
            return none("ATR_UNAVAILABLE")
        po, pc = float(previous["open"]), float(previous["close"])
        co, cc = float(current["open"]), float(current["close"])
        buy = pc < po and cc > co and co <= pc and cc >= po and cc - co >= 0.5 * atr
        sell = pc > po and cc < co and co >= pc and cc <= po and co - cc >= 0.5 * atr
        if buy == sell:
            return none("NO_SINGLE_ENGULFING_DIRECTION")
        bid, ask = float(tick["bid"]), float(tick["ask"])
        spread = ask - bid
        if spread < 0:
            return none("INVALID_QUOTE")
        if buy:
            if bid <= float(previous["low"]):
                return none("INVALIDATED_PRE_ENTRY")
            stop = min(float(previous["low"]), float(current["low"])) - 0.1 * atr
            target = cc + 2 * (cc - stop)
            direction = Direction.BUY
        else:
            if ask >= float(previous["high"]):
                return none("INVALIDATED_PRE_ENTRY")
            stop = max(float(previous["high"]), float(current["high"])) + 0.1 * atr
            target = cc - 2 * (stop - cc)
            direction = Direction.SELL
        if stop <= 0 or target <= 0 or not self.cost_is_eligible(spread, abs(target - cc)):
            return none("COST_OR_BRACKET_REJECTED")
        return Signal(direction, 0.6, stop, target, "COMPLETED_BODY_ENGULFING")
