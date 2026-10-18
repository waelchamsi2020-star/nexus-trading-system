"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'volatility_breakout'
THEORY_SCOPE_AR = 'انكماش ثم إغلاق جديد خارج نطاق محسوب من الشموع السابقة.'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = 'ed63c8a29aaa1f6288e809843f237e0b2b9719218fd403c873ca3986a4654192'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
