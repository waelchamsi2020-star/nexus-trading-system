"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'flag_breakout'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. الكلاسيكي: استمرار راية محددة'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '7f8a209f9b9417cef87e4d70490a72ad0dd904d084b2c6c9d4472d22e27eeb7e'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
