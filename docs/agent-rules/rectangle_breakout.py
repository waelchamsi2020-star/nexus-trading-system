"""Saved agent definition; research only, no broker access."""
from snapshot.nexus import strategies as _shared

AGENT_ID = 'rectangle_breakout'
THEORY_SCOPE_AR = 'تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. الكلاسيكي: اختراق مستطيل سعري'
COVERAGE = 'IMPLEMENTED'
RULES_SHA256 = 'cd90b05c65ceb04220e320792bdf4fb9b2ccecfc704b2ff23385dba2fa397582'
def analyze(symbol, timeframe, bars, as_of=None, context=None):
    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)
