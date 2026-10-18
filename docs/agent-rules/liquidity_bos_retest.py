"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'liquidity_bos_retest'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. السيولة: سحب ثم كسر وإعادة اختبار'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = 'f19ddabcf928f85bed92dc0342597f730ad4b4aa0251965fb1af6ec810587ff2'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
