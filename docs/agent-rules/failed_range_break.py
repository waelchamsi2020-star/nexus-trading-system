"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'failed_range_break'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. فشل اختراق النطاق'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = 'f9059a070f3942f2d8432e63486673be795245ad0d6f42e10f607c9c9cd040d6'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
