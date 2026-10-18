"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'pin_rejection'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. رفض الذيل عند حد سعري'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = 'fec1795c938b7da4c2c0ea380b455e3b4178b636c006926dbcddb59a5266dd44'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
