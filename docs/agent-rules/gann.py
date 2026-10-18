"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'gann'
THEORY_SCOPE_AR = 'نموذج محلي محدد القواعد، وليس المدرسة كاملة: جان: شبكة جذر سعر معيارية'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '0033660b137afaa1b3b3c5d3634a5f63d7b2a6f0854222c475969e8e1f1257c7'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
