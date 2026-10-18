"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'breakout_retest'
THEORY_SCOPE_AR = 'اختراق نطاق سابق ثم إعادة اختبار ناجحة وفق ترتيب زمني محدد.'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '7d08f3b7ccb714f876f29fd03f8a4356d0ac1810f7bbbe011d0b29b24ebd3246'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
