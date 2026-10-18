"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'inside_bar_break'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. اختراق الشمعة الداخلية'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = 'c74ffcab9b79f1d1f127a4ecb45f94a8025985f8e95a26fe2d8d25f1ce99676a'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
