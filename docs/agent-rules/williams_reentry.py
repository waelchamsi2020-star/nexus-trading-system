"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'williams_reentry'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. ويليامز: استعادة نطاق الزخم'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = 'd2755ffa39214a2ccdc16822ce8e3d2aa865913a77fc229ebfdeef473f340b31'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
