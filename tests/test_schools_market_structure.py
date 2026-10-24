"""Causal structure-break contract checks on deterministic test bars."""

from strategies.base import Direction
from strategies.schools.market_structure import MarketStructure


def bars() -> list[dict]:
    history = [
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0}
        for _ in range(15)
    ]
    history.append({"open": 100.0, "high": 103.0, "low": 100.0, "close": 102.0})
    return history


def evaluate(history=None, bid=102.0, ask=102.05):
    history = bars() if history is None else history
    return MarketStructure().evaluate(
        history, {"bid": bid, "ask": ask}, {"closed_index": 15, "session_open": True}
    )


def test_accept_buy_with_structural_stop_and_target() -> None:
    signal = evaluate()
    assert signal.direction is Direction.BUY
    assert signal.sl_hint < 99
    assert signal.tp_hint > 102


def test_reject_close_inside_prior_range() -> None:
    history = bars()
    history[-1] = {"open": 100.0, "high": 100.8, "low": 99.4, "close": 100.2}
    assert evaluate(history).direction is Direction.NONE


def test_invalidation_on_reentry_before_execution() -> None:
    assert evaluate(bid=100.5, ask=100.55).reason == "INVALIDATED_PRE_ENTRY"


def test_look_ahead_poisoned_future_bar_is_not_read() -> None:
    class Poisoned(list):
        def __getitem__(self, key):
            if isinstance(key, slice) and key.stop is not None and key.stop > 16:
                raise AssertionError("future bar read")
            if isinstance(key, int) and key >= 16:
                raise AssertionError("future bar read")
            return super().__getitem__(key)

    assert evaluate(Poisoned(bars() + [object()])).direction is Direction.BUY


def test_cost_guard_rejects_high_spread() -> None:
    assert evaluate(ask=104.0).direction is Direction.NONE


def test_no_dual_signal_on_same_completed_bar() -> None:
    assert evaluate().direction is Direction.BUY
    assert evaluate().direction is not Direction.SELL


def test_missing_bars_refuse_signal() -> None:
    assert evaluate(bars()[:5]).direction is Direction.NONE
