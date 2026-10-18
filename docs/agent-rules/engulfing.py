"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'engulfing'
THEORY_SCOPE_AR = 'ابتلاع جسم الشمعة السابقة مع حد أدنى لحجم الجسم نسبة إلى التقلب.'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = 'ac81f13259c35e6b5759134f2525d3d0abd4bbaf43331bdf92bdeaecb84aa3cb'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
