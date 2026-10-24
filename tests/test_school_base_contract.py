"""Phase A checks the contract only; no school is activated here."""

import pytest

from strategies.base import Direction, Signal, Strategy
from strategies.schools import REGISTRY, register


def test_base_is_abstract() -> None:
    with pytest.raises(TypeError):
        Strategy()


def test_no_signal_carries_no_price_hints() -> None:
    assert Signal(Direction.NONE, 0, None, None, "missing data").direction is Direction.NONE
    with pytest.raises(ValueError):
        Signal(Direction.NONE, 0, 1.0, None, "missing data")


def test_trade_signal_requires_finite_hints() -> None:
    with pytest.raises(ValueError):
        Signal(Direction.BUY, 0.8, None, 2.0, "fixture")
    with pytest.raises(ValueError):
        Signal(Direction.SELL, float("nan"), 1.0, 2.0, "fixture")


def test_cost_contract_rejects_high_or_unknown_cost() -> None:
    assert Strategy.cost_is_eligible(2, 10)
    assert not Strategy.cost_is_eligible(2.01, 10)
    assert not Strategy.cost_is_eligible(float("nan"), 10)


def test_registry_has_only_research_pilots_and_rejects_non_strategies() -> None:
    assert set(REGISTRY) == {"price_action", "market_structure"}
    with pytest.raises(TypeError):
        register("invalid", object)
