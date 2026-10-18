"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'geometric_triangle_breakout'
THEORY_SCOPE_AR = 'مثلث صاعد أو هابط أو متماثل من محاور مؤكدة وخطوط متقاربة؛ دخول عند اختراق جديد.'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '5db2b972a0c163f9d6defb6bd8775d7d0eedd9d38f2ba011ccc3ebf512709ed7'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
