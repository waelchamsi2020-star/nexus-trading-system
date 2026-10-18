"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'support_bounce'
THEORY_SCOPE_AR = 'ملامسة دعم أو مقاومة من محور مؤكد ثم رفض سعري بإغلاق مكتمل.'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '90dbff3fff0c5f960c5c5de53c1301d8323cd0b559c2ec554dbeebfa38e2a2f0'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
