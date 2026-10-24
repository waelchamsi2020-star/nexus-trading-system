"""MT5-only school strategy contract for phased implementation.

No strategy here may send an order. The caller supplies only completed bars.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Any


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"


@dataclass(frozen=True)
class Signal:
    direction: Direction
    confidence: float
    sl_hint: float | None
    tp_hint: float | None
    reason: str

    def __post_init__(self) -> None:
        if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be finite and in [0, 1]")
        if not self.reason.strip():
            raise ValueError("reason is required")
        if self.direction is Direction.NONE:
            if self.sl_hint is not None or self.tp_hint is not None:
                raise ValueError("NONE must not carry stop or target hints")
        elif not all(
            value is not None and isfinite(value) and value > 0
            for value in (self.sl_hint, self.tp_hint)
        ):
            raise ValueError("trade signals require finite positive stop and target hints")


class Strategy(ABC):
    """Read-only school evaluator; the risk service owns final SL/TP approval."""

    INPUTS: tuple[str, ...] = ()
    CONFIRMATION = "COMPLETED_BARS_ONLY"
    INVALIDATION: str = ""
    COST_CHECK = "SPREAD_TO_TARGET_AT_MOST_0.20"

    @abstractmethod
    def evaluate(
        self,
        bars: Sequence[Mapping[str, Any]],
        tick: Mapping[str, Any],
        ctx: Mapping[str, Any],
    ) -> Signal:
        """Return a signal from closed bars and current MT5 quote; never send orders."""

    @staticmethod
    def cost_is_eligible(spread: float, target_distance: float) -> bool:
        return (
            isfinite(spread)
            and isfinite(target_distance)
            and spread >= 0
            and target_distance > 0
            and spread / target_distance <= 0.20
        )


def completed_prefix(
    bars: Sequence[Mapping[str, Any]], ctx: Mapping[str, Any]
) -> Sequence[Mapping[str, Any]]:
    """Expose no bar after the explicit last-completed decision index."""
    index = ctx.get("closed_index")
    if type(index) is not int or index < 0 or index >= len(bars):
        return ()
    return bars[: index + 1]


def mean_true_range(bars: Sequence[Mapping[str, Any]], period: int = 14) -> float:
    if len(bars) < period + 1:
        return 0.0
    ranges = []
    for index in range(len(bars) - period, len(bars)):
        bar, previous = bars[index], bars[index - 1]
        high, low, prior_close = float(bar["high"]), float(bar["low"]), float(previous["close"])
        ranges.append(max(high - low, abs(high - prior_close), abs(low - prior_close)))
    return sum(ranges) / period
