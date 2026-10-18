"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'darvas_rising_boxes'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. دارفاس: تتابع صندوقين مؤكدين'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '1e6971d1cda68d469efcd1fe4fefb51c19c493b7012ed538b635e9312f79445f'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
