"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'rsi_rebound'
THEORY_SCOPE_AR = 'عودة مؤشر القوة النسبية عبر 30 أو70؛ النسخة الحالية بمتوسط بسيط لا بتنعيم وايلدر.'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '98f2d201f760d50a4a7a9629d91830f9a906de759c6b687f845b7d35218c79cf'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
