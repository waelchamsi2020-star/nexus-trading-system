"""Phase A school registry; no school is active before implementation and review."""

from strategies.base import Strategy
from strategies.schools.market_structure import MarketStructure
from strategies.schools.price_action import PriceAction

REGISTRY: dict[str, type[Strategy]] = {}


def register(name: str, strategy_type: type[Strategy]) -> None:
    if name in REGISTRY:
        raise ValueError(f"duplicate school: {name}")
    if not issubclass(strategy_type, Strategy):
        raise TypeError("school must implement Strategy")
    REGISTRY[name] = strategy_type


register("price_action", PriceAction)
register("market_structure", MarketStructure)
