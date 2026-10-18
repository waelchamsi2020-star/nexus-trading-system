"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'ema_cross'
THEORY_SCOPE_AR = 'تقاطع جديد بين المتوسطين الأسيين 12 و26.'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '900e125ad26fa560f90174a77886f23ad5c4f54e37b32e7e9abb48d169619d8b'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
