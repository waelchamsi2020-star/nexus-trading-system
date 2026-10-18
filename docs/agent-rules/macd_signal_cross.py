"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'macd_signal_cross'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. تقاطع الماكد: تأكيد اتجاه'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '27f132659b9b2d659f0b5f8d1d9adbf9b623de27408ea99c1a20184d156b4fd4'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
