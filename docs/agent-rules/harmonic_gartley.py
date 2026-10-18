"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'harmonic_gartley'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. الهارمونيك: غارتلي مؤكد'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '8ba40ed465acc6d2433e9460b49d447738748f08f2c71166ad8c9ec3b5922f81'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
