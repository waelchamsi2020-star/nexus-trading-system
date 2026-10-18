"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'donchian_20'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. اختراق قناة عشرين شمعة'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '90737dfcf499c19a16caa6c11ac29af73c982311c62fa800893c1c932c0f9940'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
