"""UTC bar boundaries. MN1 is a calendar month, never a fixed 30-day close."""
from datetime import datetime, timezone

PERIODS = {
    "M1":60,"M2":120,"M3":180,"M4":240,"M5":300,"M6":360,
    "M10":600,"M12":720,"M15":900,"M20":1200,"M30":1800,
    "H1":3600,"H2":7200,"H3":10800,"H4":14400,"H6":21600,
    "H8":28800,"H12":43200,"D1":86400,"W1":604800,"MN1":2592000,
}
# MN1's nominal duration above is for sizing/count estimates only.
def month_start(timestamp, offset=0):
    dt=datetime.fromtimestamp(timestamp,timezone.utc)
    year,month=divmod(dt.year*12+dt.month-1+offset,12)
    return datetime(year,month+1,1,tzinfo=timezone.utc).timestamp()

def bar_close_time(open_time,timeframe):
    return month_start(open_time,1) if timeframe=="MN1" else open_time+PERIODS[timeframe]
