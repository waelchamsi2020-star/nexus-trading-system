"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'cci_reentry'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. مؤشر قناة السلع: عودة من التطرف'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = 'b8ff4087a6b22267d338e119c7819b108a5366ef1452d75bd6310744c0664f30'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
