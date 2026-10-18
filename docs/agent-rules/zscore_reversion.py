"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'zscore_reversion'
THEORY_SCOPE_AR = 'عودة درجة معيارية عبر عتبة مع هدف متوسط صالح؛ لا يفترض ثبات التوزيع.'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '218329459865a4420ec2d7f5cfc0bee9fad3d99f757ab36be2f043e2b8c16603'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
