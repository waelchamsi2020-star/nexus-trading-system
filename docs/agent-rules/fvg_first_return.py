"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'fvg_first_return'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. العودة الأولى للفجوة السعرية'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = 'bc403e8bd8fd063fdaa3c4f189f624d441114969e19e220e4c0edcbfa647dd87'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
