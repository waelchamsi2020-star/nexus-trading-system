"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'adx_di_cross'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. الحركة الاتجاهية: تقاطع مؤكد'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = 'f549d0b7bf11101d1462fccd42632d9febc03945fdc8d4a18cd08f2a18e8e52e'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
