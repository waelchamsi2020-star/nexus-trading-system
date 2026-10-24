"""Causal body-engulfing contract checks on deterministic test bars."""

from strategies.base import Direction
from strategies.schools.price_action import PriceAction


def bars() -> list[dict]:
    history = [
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0}
        for _ in range(14)
    ]
    history.append({"open": 101.0, "high": 101.2, "low": 99.2, "close": 100.0})
    history.append({"open": 99.5, "high": 102.0, "low": 99.0, "close": 101.5})
    return history


def evaluate(history=None, bid=101.5, ask=101.55):
    history = bars() if history is None else history
    return PriceAction().evaluate(
        history, {"bid": bid, "ask": ask}, {"closed_index": 15, "session_open": True}
    )


def test_accept_buy_with_structural_bracket() -> None:
    signal = evaluate()
    assert signal.direction is Direction.BUY
    assert signal.sl_hint < 99
    assert signal.tp_hint > 101.5


def test_reject_non_engulfing_reverse_series() -> None:
    history = bars()
    history[-1] = {"open": 100.5, "high": 101.0, "low": 99.8, "close": 100.2}
    assert evaluate(history).direction is Direction.NONE


def test_invalidation_before_entry() -> None:
    assert evaluate(bid=98.0, ask=98.05).reason == "INVALIDATED_PRE_ENTRY"


def test_look_ahead_poisoned_future_bar_is_not_read() -> None:
    class Poisoned(list):
        def __getitem__(self, key):
            if isinstance(key, slice) and key.stop is not None and key.stop > 16:
                raise AssertionError("future bar read")
            if isinstance(key, int) and key >= 16:
                raise AssertionError("future bar read")
            return super().__getitem__(key)

    history = Poisoned(bars() + [object()])
    assert evaluate(history).direction is Direction.BUY


def test_high_spread_has_no_signal() -> None:
    assert evaluate(ask=103.0).direction is Direction.NONE


def test_no_dual_signal_on_same_completed_bar() -> None:
    assert evaluate().direction is Direction.BUY
    assert evaluate().direction is not Direction.SELL


def test_missing_bars_refuse_signal() -> None:
    assert evaluate(bars()[:5]).direction is Direction.NONE
