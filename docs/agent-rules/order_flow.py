"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'order_flow'
THEORY_SCOPE_AR = 'نموذج محلي محدد القواعد، وليس المدرسة كاملة: تدفق النشاط: تقريب من شموع التكات'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '614692b8c6a0993b9fa431e8d72a29534d6dce16c2f07b1141ed0df5bd85e2b6'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
