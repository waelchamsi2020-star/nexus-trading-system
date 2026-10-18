"""Explicit research calendar policies, not a verified broker holiday calendar."""
from datetime import UTC, datetime

PROFILES=('CONTINUOUS','FX_UTC22_V1')


def validate_profile(profile):
    if profile not in PROFILES:raise ValueError('Unknown research calendar profile')
    return profile


def expected_closure_gap(previous_close, next_open, seconds, profile):
    validate_profile(profile)
    if profile=='CONTINUOUS' or seconds not in (300,3600):return False
    missing=next_open-previous_close
    if missing<=0 or missing%seconds or missing>7*86400:return False
    for stamp in range(int(previous_close),int(next_open),seconds):
        dt=datetime.fromtimestamp(stamp,UTC)
        weekend=(dt.weekday()==4 and dt.hour>=22) or dt.weekday()==5 or (dt.weekday()==6 and dt.hour<22)
        holiday=(dt.month,dt.day) in ((12,25),(1,1))
        if not (weekend or holiday):return False
    return True
