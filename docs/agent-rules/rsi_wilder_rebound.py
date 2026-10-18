"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'rsi_wilder_rebound'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. القوة النسبية: عودة بتنعيم وايلدر'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '1e4e59f4e6ee4eeb4ed006e04f26f4e177321e6a77ac2ea2fb5721ed0b2619a7'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
