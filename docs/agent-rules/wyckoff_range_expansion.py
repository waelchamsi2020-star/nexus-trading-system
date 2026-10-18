"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'wyckoff_range_expansion'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. وايكوف: توسع نطاق مع نشاط تكات'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = '4557e776098afd564fae98af8ce560beebbea6b567ccff5bb9ec917b63a309f5'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
