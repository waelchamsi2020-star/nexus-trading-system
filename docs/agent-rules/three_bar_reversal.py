"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'three_bar_reversal'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. الشموع: انعكاس ثلاثي مؤكد'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '37b0373efbe2de5e1495f6e7d9c73aeca156c5391dfdcb54beb6d85daee9e639'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
