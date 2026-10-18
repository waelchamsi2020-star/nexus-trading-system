"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'wyckoff_spring'
THEORY_SCOPE_AR = 'نموذج محلي محدد القواعد، وليس المدرسة كاملة: وايكوف: نموذج كسر واختبار محلي'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = 'a6c99e9ebad1b0f6373a10f0f6591f8ae88258c78b41a7749482ca7732f43f97'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
