"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'harmonic_butterfly'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. الهارمونيك: باترفلاي مؤكد'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '86b1d0119fdfb761e20446cbe61eb3cf73a62e984fdf1bb146a6ffcabdf54d69'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
